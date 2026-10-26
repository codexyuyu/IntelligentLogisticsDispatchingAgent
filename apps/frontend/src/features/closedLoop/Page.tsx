import { useCallback, useEffect, useMemo, useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import WarehouseTwin3D, { type WarehouseCamera, type WarehouseSelection } from '../../components/WarehouseTwin3D';
import DigitalTwin3D from '../../components/DigitalTwin3D';
import { useSimClock } from '../../hooks/useSimClock';
import { warehouseTwinData } from '../../lib/warehouseTwin';
import { routesToTwinRoutes, type CandidatePlan, type Snapshot } from '../../appTypes';
import { pgRequest } from '../postgres/api';
import { fmtClock } from '../../lib/format';
import ExceptionPanel, { type ExceptionResult } from './ExceptionPanel';

type Kind = 'warehouse_work_start'|'warehouse_work_finished'|'loading_ready'|'vehicle_departure'|'order_delivered'|'vehicle_return'|'exception_occurred';
type WorkflowEvent = {time_s:number;kind:Kind;object_id:string;resource_id?:string;vehicle_id?:string;order_ids?:string[];operation_kind?:string};
type Workflow = {
  mode:string;source:'scenario_demo'|'verified_postgres'|'postgres_synthetic_demo';database_mutated:boolean;
  business_plans_mutated:boolean;validated:boolean;snapshot:Snapshot;plan:CandidatePlan;
  events:WorkflowEvent[];meta:Record<string,unknown>;note:string;
  reconciliation:{status:'passed';scope_order_count:number;planned_delivery_order_count:number;unserved_order_count:number;loading_ready_order_count:number;order_statuses:{order_id:string;warehouse_task_count:number;loading_ready:boolean;routing_status:'planned'|'unserved';planned_delivery_at_s:number|null;planned_vehicle_id:string|null;loading_ready_at_s:number;unserved_reason:string|null}[]};
};
type Readiness = {
  single_warehouse:boolean;warehouse_codes:string[];r24_tables_installed:boolean;r27_table_installed:boolean;
  r24_reference_data_present:boolean;complete_presence:boolean;work_operation_count:number;
  missing:Record<string,number>;missing_codes:Record<string,string[]>;
  provenance?:{installed:boolean;source_kind:string;warehouse_code?:string};
};
const LABEL:Record<Kind,string> = {
  warehouse_work_start:'仓储作业开始',warehouse_work_finished:'仓储作业完成',loading_ready:'装车就绪',
  vehicle_departure:'车辆发车',order_delivered:'订单预计交付（规划时点）',vehicle_return:'车辆回仓',
  exception_occurred:'模拟异常发生（非真实监测）',
};
type Diagnostics={mode:string;database_mutated:boolean;warehouse:{warehouse_codes:string[];can_apply:boolean;dependent_rows:{relation:string;column:string;count:number|null;blocking:boolean}[]};business:Readiness;stages:{stage:string;ready:boolean;action:string}[];ready_to_try_verified_solver:boolean};
const DIAG_LABEL:Record<string,string>={single_depot:'单仓一致性',r24_business_facts:'R24 冷链业务资料',r27_work_standards:'R27 仓储工时与资源'};
const SPEEDS=[1,4,16,64,256];

export default function ClosedLoopPage(){
  const [originalWorkflow,setWorkflow]=useState<Workflow|null>(null);
  // R30-C: one-time browser-only handoff from verified Agent tool result.
  // Never treat transferred replay as official dispatch confirmation.
  useEffect(()=>{
    try{
      const raw=sessionStorage.getItem('r30c-replay-transfer');
      if(!raw)return;
      sessionStorage.removeItem('r30c-replay-transfer');
      const data=JSON.parse(raw) as {workflow:Workflow;exception:ExceptionResult|null;source:'single_warehouse_demo'|'verified_postgres';zone:'chilled'|'frozen'};
      if(data.workflow?.validated && data.workflow?.reconciliation?.status==='passed'
        && data.workflow.database_mutated===false && data.workflow.business_plans_mutated===false){
        setWorkflow(data.workflow);setDataSource(data.source);setZone(data.zone);
        if(data.exception?.verification?.status==='passed' && data.exception.database_mutated===false){
          setExceptionResult(data.exception);setReplayMode('replanned');
        }else{setExceptionResult(null);setReplayMode('original');}
      }
    }catch{ /* Ignore damaged browser-only handoff; R27 can always rerun. */ }
  },[]);

  const [exceptionResult,setExceptionResult]=useState<ExceptionResult|null>(null);
  const [replayMode,setReplayMode]=useState<'original'|'replanned'>('original');
  const workflow=useMemo<Workflow|null>(()=>{
    if (!originalWorkflow || !exceptionResult || replayMode==='original') return originalWorkflow;
    const replay=exceptionResult.replay;
    // Projection accounting is independently verified by R30-B/R30-E, NOT
    // a newly R28-reconciled executable plan. Loading status derives from the
    // merged event record, never assumed true for every unserved order.
    const readyAt=new Map(replay.events.filter(e=>e.kind==='loading_ready').map(e=>[e.object_id,e.time_s]));
    const status=exceptionResult.comparison.order_changes.map(x=>({
      order_id:x.order_id,warehouse_task_count:originalWorkflow.reconciliation.order_statuses.find(o=>o.order_id===x.order_id)?.warehouse_task_count??0,
      loading_ready:readyAt.has(x.order_id),routing_status:(x.status==='unserved'?'unserved':'planned') as 'unserved'|'planned',
      planned_delivery_at_s:x.new_delivery_at_s,planned_vehicle_id:x.next_vehicle_id,
      loading_ready_at_s:readyAt.get(x.order_id)??0,
      unserved_reason:exceptionResult.comparison.unserved_orders.find(z=>z.order_id===x.order_id)?.reason_code??null,
    }));
    return {...originalWorkflow,snapshot:replay.snapshot,plan:replay.plan,
      events:replay.events as WorkflowEvent[],reconciliation:{status:'passed',scope_order_count:status.length,
        planned_delivery_order_count:exceptionResult.comparison.forecast_delivered_total,
        unserved_order_count:exceptionResult.comparison.unserved_total,
        loading_ready_order_count:status.filter(z=>z.loading_ready).length,order_statuses:status}};
  },[originalWorkflow,exceptionResult,replayMode]);
  const [readiness,setReadiness]=useState<Readiness|null>(null);
  const [diagnostics,setDiagnostics]=useState<Diagnostics|null>(null);
  const [readinessError,setReadinessError]=useState('');
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [dataSource,setDataSource]=useState<'single_warehouse_demo'|'verified_postgres'>('single_warehouse_demo');
  const [zone,setZone]=useState<'chilled'|'frozen'>('chilled');
  const [budget,setBudget]=useState(60000);
  const [view,setView]=useState<'warehouse'|'transport'>('warehouse');
  const [camera,setCamera]=useState<WarehouseCamera>('isometric');
  const [selection,setSelection]=useState<WarehouseSelection|null>({kind:'zone',id:'chilled'});
  const [follow,setFollow]=useState<string|null>(null);
  const horizon=workflow ? Math.max(1800,...workflow.events.map(e=>e.time_s)) : 1800;
  const clock=useSimClock(horizon,false);
  const refresh=useCallback(async()=>{
    try {const report=await pgRequest<Diagnostics>('/r28/diagnostics');setDiagnostics(report);setReadiness(report.business);setReadinessError('');}
    catch(e){setDiagnostics(null);setReadiness(null);setReadinessError(e instanceof Error?e.message:'无法检查实库');}
  },[]);
  useEffect(()=>{void refresh();},[refresh]);
  const data=useMemo(()=>workflow?warehouseTwinData(workflow.snapshot,workflow.plan,'plan'):null,[workflow]);
  const vehicles=workflow?.snapshot.vehicles;
  const routes=useMemo(()=>routesToTwinRoutes(workflow?.plan,vehicles??[]),[workflow,vehicles]);
  const warehouseList=useMemo(()=>(workflow?.snapshot.warehouses??[]).map(w=>({id:w.warehouse_id,zones:[...w.temperature_zones]})),[workflow]);
  const nodeIds=useMemo(()=>workflow?.snapshot.matrix.node_ids??[],[workflow]);
  const nodesZone=useMemo(()=>Object.fromEntries((workflow?.snapshot.orders??[]).map(x=>[x.delivery_node_id,x.temperature_zone])),[workflow]);
  const allEvents=workflow?.events??[];
  const occurred=allEvents.filter(e=>e.time_s<=clock.t);
  const delivered=occurred.filter(e=>e.kind==='order_delivered').length;
  const totalPlanned=workflow?.reconciliation?.planned_delivery_order_count??0;
  const pendingPlanned=Math.max(0,totalPlanned-delivered);
  const finished=occurred.filter(e=>e.kind==='warehouse_work_finished').length;
  const departed=occurred.filter(e=>e.kind==='vehicle_departure').length;
  const handoffs=occurred.filter(e=>e.kind==='loading_ready').length;

  async function run(){
    setBusy(true);setError('');setWorkflow(null);setExceptionResult(null);setReplayMode('original');clock.pause();clock.seek(0);
    try{
      const result=await pgRequest<Workflow>('/r27/workflow',{
        source:dataSource,temperature_zone:zone,travel_mode:'straight_line_simulation',
        speed_kmh:30,max_orders:20,budget_ms:budget,acknowledge_dry_run_only:true,
      });
      if(!result.validated||result.database_mutated||result.business_plans_mutated||result.reconciliation?.status!=='passed')throw Error('后端没有返回通过 R28 逐单对账的安全只读方案');
      setWorkflow(result);setView('warehouse');setFollow(null);clock.seek(0);
    }catch(e){setError(e instanceof Error?e.message:'仓运闭环求解失败');}
    finally{setBusy(false);}
  }
  return <div className="r27-page">
    <SectionHeader title="仓运闭环与异常重排" />
    <div className="pg-warning"><strong>业务边界：</strong>“单仓演示”使用合成场景；“PostgreSQL 数据驱动”要求 WH001、R24/R27 资料齐全；R30-A 导入的合成 CSV 将永久标记为演示，不能视为实际经营数据。当前不连接设备遥测、不自动修改库存或派车；道路未配置 OSRM 时仍是示意路线。</div>
    <div className="panel r27-config"><div className="panel-title-row"><div><h3>选择数据来源并生成全流程方案</h3><p>不会从演示模式静默切换成真实业务，也不会在真实资料缺失时补假值。</p></div><span className="soft-badge">CP-SAT + OR-Tools · 独立校验</span></div>
      <div className="r27-source-pills"><button className={`btn ${dataSource==='single_warehouse_demo'?'btn-primary':'btn-ghost'}`} onClick={()=>setDataSource('single_warehouse_demo')}>单仓演示 · 开箱即用</button><button className={`btn ${dataSource==='verified_postgres'?'btn-primary':'btn-ghost'}`} onClick={()=>setDataSource('verified_postgres')}>PostgreSQL 核验 · 数据驱动（来源标识）</button></div>
      {dataSource==='verified_postgres'&&<div className="r27-readiness">{readinessError&&<p className="pg-error">实库状态：{readinessError}</p>}
        {readiness&&<><p><b>单仓检查：</b>{readiness.single_warehouse?'WH001 已统一':'尚未统一，需运行 R26 只读预检'}　 <b>R27 作业表：</b>{readiness.r27_table_installed?'已建表':'未创建'}　 <b>已录入任务：</b>{readiness.work_operation_count} 条</p>
          <p className="pg-hint"><strong>R30-A 数据来源：</strong>{readiness.provenance?.source_kind==='explicit_synthetic_demo'?'R30-A 合成演示数据（已在 PostgreSQL 中标记）':readiness.provenance?.source_kind==='unmarked_operator_or_legacy_rows'?'原有人工/历史记录（来源未经独立核实）':'尚未安装来源标记'}。此页面始终是只读求解预览。</p>
          <div className="r27-missing">{Object.entries(readiness.missing).map(([key,n])=><span key={key} className={n===0?'ok':''}>{key}: {n}</span>)}</div>
          {diagnostics&&<div className="r28-diagnostic-stages">{diagnostics.stages.map(step=><div key={step.stage} className={step.ready?'ready':'pending'}><strong>{DIAG_LABEL[step.stage]??step.stage}</strong><span>{step.ready?'已齐备 / 等待业务校验':'待处理'}</span></div>)}</div>}
          {diagnostics&&!diagnostics.business.single_warehouse&&<p className="pg-hint">单仓迁移预检：{diagnostics.warehouse.can_apply?'当前检查允许走 R26 受保护迁移（仍须备份并单独授权）':'存在历史关联或不符合安全迁移条件；不会改动 WH002'}。关联阻挡：{diagnostics.warehouse.dependent_rows.filter(x=>x.blocking).map(x=>`${x.relation}.${x.column} (${x.count??'未知'})`).join('、')||'无'}。</p>}
          {!readiness.complete_presence&&<p className="pg-hint">先运行演示；实库缺失的订单/车辆编号及空白补录清单可用 R28 的只读工具导出，见 docs/R28_DATA_RECONCILIATION.md。空白数值必须人工提供，程序不会编造。</p>}
        </>}
        <button className="btn btn-ghost btn-sm" onClick={()=>void refresh()}>重新检查实库完整性</button>
      </div>}
      <div className="pg-form r27-fields"><label>求解总预算 (ms)<select value={budget} onChange={e=>setBudget(Number(e.target.value))}><option value={30000}>30000</option><option value={60000}>60000</option><option value={120000}>120000</option></select></label>
        {dataSource==='verified_postgres'&&<label>当前核验温区<select value={zone} onChange={e=>setZone(e.target.value as 'chilled'|'frozen')}><option value="chilled">冷藏 chilled</option><option value="frozen">冷冻 frozen</option></select></label>}
      </div>
      <button className="btn btn-primary" onClick={()=>void run()} disabled={busy||(dataSource==='verified_postgres'&&!readiness?.complete_presence)}>{busy?'仓储与运输联合求解中…':'运行 R28 仓运一体化核对预览'}</button>
      {error&&<div className="pg-error" role="alert">{error}</div>}
    </div>
    {originalWorkflow&&<ExceptionPanel snapshot={originalWorkflow.snapshot} plan={originalWorkflow.plan}
      source={dataSource} zone={zone} budget={budget} currentResult={exceptionResult}
      onResult={r=>{setWorkflow(r.baseline as Workflow);setExceptionResult(r);setReplayMode('replanned');clock.pause();clock.seek(0);}}
      onReset={()=>{setExceptionResult(null);setReplayMode('original');}}
      onSelectOriginal={()=>{setReplayMode('original');clock.pause();clock.seek(0);}}
      onSelectReplanned={()=>{setReplayMode('replanned');clock.pause();clock.seek(0);}}
      replayMode={replayMode}/>}
    {workflow&&data&&<>
      <div className={`r27-source-flag ${workflow.source==='scenario_demo'||workflow.source==='postgres_synthetic_demo'?'demo':''}`}><strong>{workflow.source==='scenario_demo'?'纯场景合成演示 · 已运行求解算法':workflow.source==='postgres_synthetic_demo'?'PostgreSQL 合成演示资料 · 已运行求解算法（非真实经营数据）':'PostgreSQL 人工/历史业务记录 · 已运行求解算法（来源未独立核实）'}</strong><span>{exceptionResult&&replayMode==='replanned'?'R30-E 后缀账户核对通过 · 回放仅是展示投影（非 R28 新 Plan）':`R28 原方案独立校验 ${workflow.plan.validation.status}`} · 不写 PostgreSQL · 未实际派车 · 仓库/道路 3D 路径是展示映射</span></div>
      <div className="pg-hint">本次仿真时钟基点：{new Date(workflow.snapshot.origin_at).toLocaleString('zh-CN',{hour12:false})}；进度条显示相对此基点的时间。</div>
      <div className="r27-metrics">
        <div><small>业务仓库</small><strong>{workflow.snapshot.warehouses[0]?.warehouse_id}</strong><span>唯一配送中心</span></div>
        <div><small>订单数</small><strong>{workflow.snapshot.orders.length}</strong><span>含批次与时间窗</span></div>
        <div><small>仓库 CP-SAT 作业</small><strong>{workflow.plan.warehouse.operations.length}</strong><span>已完成 {finished} 项</span></div>
        <div><small>装车交接</small><strong>{workflow.plan.warehouse.warehouse_handoffs.length}</strong><span>就绪 {handoffs} 单</span></div>
        <div><small>实际求解车辆</small><strong>{routes.length}</strong><span>已发车 {departed} 辆</span></div>
        <div><small>全程计划配送</small><strong>{totalPlanned} / {workflow.reconciliation.scope_order_count}</strong><span>{exceptionResult&&replayMode==='replanned'?'R30-E 后缀对账':'R28 对账'} {workflow.reconciliation.status}</span></div>
        <div><small>当前已回放配送</small><strong>{delivered} / {totalPlanned}</strong><span>后续仍待回放 {pendingPlanned} 单 · 未服务 {workflow.reconciliation.unserved_order_count} 单</span></div>
      </div>
      <div className="panel r28-audit"><div className="panel-title-row"><div><h3>{exceptionResult&&replayMode==='replanned'?'R30-E 历史事实 + 异常后续订单预测（非执行方案）':'R28 订单级业务对账'}</h3><p>全程预计交付 {totalPlanned} 单；当前进度条仅展示已回放 {delivered} 单。异常模式含已完成前缀及新预测，不代表真实签收。</p></div><span className="soft-badge">完整范围 {workflow.reconciliation.scope_order_count} 单 · {workflow.reconciliation.status}</span></div>
        <div className="r28-order-scroll"><table><thead><tr><th>订单</th><th>仓储任务</th><th>装车就绪</th><th>运输计划</th><th>预计交付时点</th><th>回放进度</th></tr></thead><tbody>{workflow.reconciliation.order_statuses.map(x=><tr key={x.order_id}><td>{x.order_id}</td><td>{x.warehouse_task_count} 项</td><td>{fmtClock(x.loading_ready_at_s)}</td><td>{x.planned_vehicle_id??`未服务：${x.unserved_reason??'待核查'}`}</td><td>{x.planned_delivery_at_s===null?'—':fmtClock(x.planned_delivery_at_s)}</td><td>{x.planned_delivery_at_s===null?'未规划':clock.t>=x.planned_delivery_at_s?'已播放':'待播放'}</td></tr>)}</tbody></table></div>
        <button className="btn btn-ghost btn-sm" onClick={()=>clock.seek(horizon)}>跳至回放结尾 · 核对全程配送</button>
      </div>
      <div className="r27-controls panel"><div className="r27-view-buttons"><button className={`btn ${view==='warehouse'?'btn-primary':'btn-ghost'}`} onClick={()=>setView('warehouse')}>仓库内部 · 叉车与装车</button><button className={`btn ${view==='transport'?'btn-primary':'btn-ghost'}`} onClick={()=>setView('transport')}>城市配送 · 车辆运行</button></div>
        <p>两个画面使用<strong>同一仿真时钟</strong>。切换视图不重置时间；同一时刻的仓储交接和车辆位置来自同一份已校验方案。</p>
      </div>
      {view==='warehouse'?<div className="r27-canvas"><div className="r27-canvas-top"><strong>单仓内部 / CP-SAT 作业时间</strong><div>{([['isometric','剖切俯视'],['top','垂直俯视'],['dock','装车月台']] as const).map(([name,label])=><button key={name} className={`btn btn-sm ${camera===name?'btn-primary':'btn-ghost'}`} onClick={()=>setCamera(name)}>{label}</button>)}</div></div><WarehouseTwin3D data={data} getTime={clock.getTime} cameraPreset={camera} showRoof={false} selected={selection} onSelect={setSelection} height={490}/>
        <p className="pg-hint">真实求解的是仓储任务起止、资源绑定与装车交接；货架位置、叉车轨迹仍是可视化映射。</p></div>:<div className="r27-canvas"><div className="r27-canvas-top"><strong>配送车辆 / OR-Tools 实际启用路线</strong><div><button className={`btn btn-sm ${follow===null?'btn-primary':'btn-ghost'}`} onClick={()=>setFollow(null)}>全局视角</button>{routes.map(route=><button className={`btn btn-sm ${follow===route.vehicleId?'btn-primary':'btn-ghost'}`} key={route.vehicleId} onClick={()=>setFollow(route.vehicleId)}>{route.vehicleId} 跟车</button>)}</div></div>
        <DigitalTwin3D routes={routes} warehouses={warehouseList} nodeIds={[...nodeIds]} nodeZones={nodesZone} orderCount={workflow.snapshot.orders.length} simTimeS={clock.t} getTime={clock.getTime} followVehicleId={follow} selectedVehicleId={follow} onPickVehicle={setFollow} eventActive={Boolean(exceptionResult&&replayMode==='replanned')} affectedVehicleIds={exceptionResult&&replayMode==='replanned'?exceptionResult.comparison.changed_vehicle_ids:[]} holdWindows={exceptionResult&&replayMode==='replanned'?Object.fromEntries(Object.entries(exceptionResult.replay.halted_vehicles).map(([k,v])=>[k,{fromS:v.from_s,untilS:v.until_s}])):{}} height={490}/>
        <p className="pg-hint">车辆数量尊重实际 OR-Tools 求解结果；未接 OSRM 时只显示示意道路，而非可导航的真实道路。</p></div>}
      <div className="panel r27-player"><div className="r27-play-row"><button className="btn btn-primary" onClick={clock.toggle}>{clock.playing?'暂停':'播放'}</button><button className="btn btn-ghost" onClick={()=>{clock.pause();clock.seek(0);}}>重置</button>{SPEEDS.map(s=><button key={s} className={`btn btn-sm ${clock.speed===s?'btn-primary':'btn-ghost'}`} onClick={()=>clock.setSpeed(s)}>{s}×</button>)}<b>{fmtClock(clock.t)} / {fmtClock(horizon)}</b></div>
        <input type="range" aria-label="R30 统一仓运时间轴" min={0} max={horizon} step={1} value={Math.round(clock.t)} onChange={e=>clock.seek(Number(e.target.value))} />
        <div className="r27-timeline-markers">{allEvents.filter(e=>e.kind==='vehicle_departure'||e.kind==='loading_ready'||e.kind==='exception_occurred').map((e,i)=><button key={`${e.kind}-${e.object_id}-${i}`} style={{left:`${e.time_s/horizon*100}%`}} title={`${LABEL[e.kind]} ${e.object_id} @ ${fmtClock(e.time_s)}`} onClick={()=>clock.seek(e.time_s)} />)}</div>
      </div>
      <div className="panel r27-event-panel"><div className="panel-title-row"><div><h3>统一仓运事件流</h3><p>由通过校验的 CP-SAT、OR-Tools 计划时间确定性生成，供回放，不是实时传感或物流签收回执。</p></div><span className="soft-badge">{occurred.length} / {allEvents.length} 条</span></div>
        <div className="r27-event-list">{allEvents.map((event,i)=><button key={`${event.kind}-${event.object_id}-${i}`} className={event.time_s<=clock.t?'active':''} onClick={()=>clock.seek(event.time_s)}><time>{fmtClock(event.time_s)}</time><strong>{LABEL[event.kind]}</strong><span>{event.object_id}</span><small>{event.resource_id??event.vehicle_id??(event.order_ids??[]).join(', ')}</small></button>)}</div>
      </div>
    </>}
  </div>;
}
