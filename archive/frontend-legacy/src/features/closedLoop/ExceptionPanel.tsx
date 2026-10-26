import { useEffect, useMemo, useState } from 'react';
import { pgRequest } from '../postgres/api';
import type { CandidatePlan, Snapshot } from '../../appTypes';
import { fmtClock } from '../../lib/format';

export type ExceptionKind = 'vehicle_breakdown'|'delivery_delay'|'warehouse_resource_failure'|'inventory_quarantine';
export type ExceptionResult = {
  mode: string; source: string; database_mutated: boolean; business_plans_mutated: boolean;
  baseline: {snapshot:Snapshot;plan:CandidatePlan;events:{time_s:number;kind:string;object_id:string}[];source:string};
  previous_plan_id: string; previous_plan_version: number; new_plan_id: string; new_plan_version: number;
  event: { event_type: ExceptionKind; object_id: string; occurred_at_s: number; delay_s: number; source_kind: string };
  state: { completed_order_ids: string[]; completed_operation_ids: string[]; active_operation_ids: string[];
    in_transit_vehicle_ids: string[]; not_yet_departed_vehicle_ids: string[]; onboard_pending_order_ids: string[];
    available_depot_vehicle_ids: string[]; halted_vehicle_positions: Record<string, Record<string,string>>;
    interrupted_operation_ids: string[] };
  comparison: { order_changes: { order_id: string; previous_vehicle_id: string|null; next_vehicle_id: string|null;
    previous_delivery_at_s: number|null; new_delivery_at_s: number|null; status: string;unserved_reason_code?:string|null }[];
    changed_warehouse_operations: { operation_id: string; resource_id: string; start_s:number; end_s:number }[];
    changed_vehicle_ids: string[]; delivered_before_event: number; forecast_delivered_total: number; unserved_total: number;
    unserved_orders: {order_id: string;reason_code:string}[]; warnings: string[] };
  impact_evidence?: { schema:string;counts:{ affected_orders:number;delivery_time_changed_orders:number;vehicle_reassigned_served_orders:number;interrupted_operations:number;changed_or_cancelled_operations:number;replay_predicted_delivery_orders:number };
    orders:{order_id:string;previous_vehicle_id:string|null;next_vehicle_id:string|null;previous_delivery_at_s:number|null;new_delivery_at_s:number|null;delivery_delta_s:number|null;vehicle_changed:boolean;time_changed:boolean;affected:boolean;status:string;unserved_reason_code?:string|null}[];
    vehicles:{vehicle_id:string;previous_order_sequence:string[];forecast_delivery_order_ids:string[];halted_at_event:boolean;halted_location:Record<string,string>|null}[];
    warehouse_operation_changes:{operation_id:string;status:string;previous_resource_id:string|null;new_resource_id:string|null;previous_start_s:number|null;new_start_s:number|null;previous_end_s:number|null;new_end_s:number|null}[];
    evidence_limits:string[] };
  verification: { status:string; baseline_r28:string; future_transport:string; suffix_accounting:string;
    no_teleport:string; partial_service_allowed:boolean; violations:string[] };
  solver: { warehouse_status:string; routing_status:string };
  replay: { snapshot:Snapshot; plan:CandidatePlan; events: {time_s:number;kind:string;object_id:string;resource_id?:string;vehicle_id?:string;order_ids?:string[];operation_kind?:string}[];
    halted_vehicles:Record<string,{from_s:number;until_s:number}>; disclaimer:string };
};

const LABEL: Record<ExceptionKind,string> = {
  vehicle_breakdown:'车辆途中故障 / 车库停用', delivery_delay:'配送行驶延误',
  warehouse_resource_failure:'仓储设备 / 月台停用', inventory_quarantine:'库存批次隔离',
};
const REASONS:Record<string,string> = {
  stranded_on_disabled_vehicle_requires_verified_transfer:'货物仍在故障车上；缺少已核验转运地点和交接条件，禁止凭空返回仓库',
  warehouse_resource_unavailable_no_verified_substitute:'仓储资源不可用，当前记录无已验证的替代资源',
  inventory_batch_quarantined_no_verified_reallocation:'原库存批次已隔离，未取得合规的替换批次分配',
  no_remaining_unstarted_vehicle_at_depot:'当前无尚未发车且可用的配送车辆（已发车车辆不能瞬移回仓）',
  in_transit_delay_exceeds_window_requires_operator_intervention:'在途延误使时间窗/班次不可行，车载货物需人工处置',
  remaining_service_unresolved_not_assumed_delivered:'仍未证明订单可履约，不计为送达',
};
const briefReason=(value:string) => REASONS[value] ?? (value.startsWith('routing_')?'运输求解未安排：':value.startsWith('warehouse_')?'仓储求解无法安排：':'')+value;

type Props = {
  snapshot:Snapshot; plan:CandidatePlan; source:'single_warehouse_demo'|'verified_postgres';
  zone:'chilled'|'frozen'; budget:number;
  currentResult:ExceptionResult|null;
  onResult:(result:ExceptionResult)=>void;
  onReset:()=>void;
  onSelectOriginal:()=>void;
  onSelectReplanned:()=>void;
  replayMode:'original'|'replanned';
};

export default function ExceptionPanel({snapshot,plan,source,zone,budget,currentResult,onResult,onReset,onSelectOriginal,onSelectReplanned,replayMode}:Props){
  const [kind,setKind]=useState<ExceptionKind>('vehicle_breakdown');
  const [objectId,setObjectId]=useState('');
  const [at,setAt]=useState(0);
  const [delay,setDelay]=useState(900);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const objects=useMemo(()=>kind==='vehicle_breakdown'||kind==='delivery_delay'
    ? snapshot.vehicles.map(v=>v.vehicle_id)
    : kind==='warehouse_resource_failure' ? snapshot.resources.map(x=>x.resource_id)
      : snapshot.stock_lots.map(x=>x.batch_id),[kind,snapshot]);
  const routeDepartures=plan.routing.routes.filter(x=>x.stops.length).map(x=>x.stops[0].departure_at_s);
  const horizon=Math.max(0,...plan.routing.routes.flatMap(x=>x.stops.map(y=>y.arrival_at_s)));
  useEffect(()=>{setObjectId(objects[0]??'');},[objects]);
  useEffect(()=>{const first=Math.min(...(routeDepartures.length?routeDepartures:[0]));setAt(Math.max(0,Math.min(horizon-1,first+60)));},[snapshot.snapshot_id]); // eslint-disable-line react-hooks/exhaustive-deps
  const exportResult=()=>{
    if(!currentResult)return;
    const contents=new Blob([JSON.stringify(currentResult,null,2)],{type:'application/json;charset=utf-8'});
    const url=URL.createObjectURL(contents);
    const anchor=document.createElement('a');
    anchor.href=url;anchor.download=`R30B_${currentResult.event.event_type}_${currentResult.event.occurred_at_s}_readonly.json`;
    document.body.appendChild(anchor);anchor.click();anchor.remove();
    URL.revokeObjectURL(url);
  };
  const run=async()=>{
    setBusy(true);setError('');onReset();
    try {
      if (!objectId) throw Error('本数据源没有该类型的异常对象');
      const result=await pgRequest<ExceptionResult>('/r30b/reschedule',{
        source,temperature_zone:zone,travel_mode:'straight_line_simulation',
        speed_kmh:30,max_orders:20,budget_ms:budget,acknowledge_dry_run_only:true,
        event_type:kind,object_id:objectId,occurred_at_s:at,delay_s:kind==='delivery_delay'?delay:0,
      });
      if (result.verification.status!=='passed'||result.database_mutated||result.business_plans_mutated) {
        throw Error('后端未提供通过独立核验的只读异常处置结果');
      }
      onResult(result);
    } catch(err){setError(err instanceof Error?err.message:'异常重排失败');}
    finally{setBusy(false);}
  };
  return <div className="panel r30b-panel" id="r30b-panel">
    <div className="panel-title-row"><div><h3>R30 阶段 E · 异常事件与动态重调度</h3>
      <p>先锁定指定时间前的业务事实，再调用 CP-SAT / OR-Tools 对尚未执行的作业和仓库内可用车辆进行重排；仅预览，绝不修改正式库存、订单或历史路线。</p></div>
      <span className="soft-badge">状态快照 · 局部重排 · 独立对账</span></div>
    <div className="pg-form r27-fields">
      <label>异常类型<select value={kind} onChange={e=>{setKind(e.target.value as ExceptionKind);setError('');}}>{(Object.keys(LABEL) as ExceptionKind[]).map(k=><option value={k} key={k}>{LABEL[k]}</option>)}</select></label>
      <label>异常对象<select value={objectId} onChange={e=>setObjectId(e.target.value)}>{objects.map(x=><option value={x} key={x}>{x}</option>)}</select></label>
      <label>异常时间（相对仿真起点 / 秒）<input type="number" min={0} max={Math.max(0,horizon-1)} value={at} onChange={e=>setAt(Math.max(0,Number(e.target.value)||0))}/></label>
      {kind==='delivery_delay'&&<label>增加行驶时长（秒）<input type="number" min={1} max={86400} value={delay} onChange={e=>setDelay(Number(e.target.value)||1)}/></label>}
    </div>
    <p className="pg-hint">仿真异常时刻：{fmtClock(at)}；时间来源为调度方案，不是车辆 GPS。道路与延误数据为示意模拟；已在途货物不会自动转移至仓库或其他车辆。</p>
    <button className="btn btn-primary" disabled={busy||!objectId||at>=horizon} onClick={()=>void run()}>{busy?'正在生成 R30-B 后缀方案…':'模拟异常并重新调度（只读）'}</button>
    {error&&<p className="pg-error" role="alert">{error}</p>}
    {currentResult&&<>
      <div className="r27-source-flag demo"><strong>R30-B 后缀独立核验：{currentResult.verification.status} · {currentResult.comparison.unserved_total===0?'全部预计可服务':'部分订单明确不可服务'}</strong>
        <span>原方案 v{currentResult.previous_plan_version} → 异常预览 v{currentResult.new_plan_version}。R28 原方案对账 {currentResult.verification.baseline_r28}；后缀账户对账 {currentResult.verification.suffix_accounting}。原数据库及历史计划均未改写。</span></div>
      <div className="r27-metrics">
        <div><small>异常前已完成配送</small><strong>{currentResult.comparison.delivered_before_event}</strong><span>冻结，不再配送</span></div>
        <div><small>新方案预计可交付合计</small><strong>{currentResult.comparison.forecast_delivered_total} / {snapshot.orders.length}</strong><span>包括已经完成的配送</span></div>
        <div><small>未服务 / 需人工处置</small><strong>{currentResult.comparison.unserved_total}</strong><span>明确说明原因</span></div>
        <div><small>变动仓储任务</small><strong>{currentResult.comparison.changed_warehouse_operations.length}</strong><span>CP-SAT 后缀排程</span></div>
        <div><small>变动配送车辆</small><strong>{currentResult.comparison.changed_vehicle_ids.length}</strong><span>包含冻结在途车辆</span></div>
      </div>
      <div className="r27-controls"><button className={`btn ${replayMode==='original'?'btn-primary':'btn-ghost'}`} onClick={onSelectOriginal}>回放原方案</button>
        <button className={`btn ${replayMode==='replanned'?'btn-primary':'btn-ghost'}`} onClick={onSelectReplanned}>回放重调度预览</button><button className="btn btn-ghost" onClick={exportResult}>导出本次原/新方案和核验 JSON</button></div>
      <p className="pg-hint">R30-B 重排求解状态：仓储 {currentResult.solver.warehouse_status}；运输 {currentResult.solver.routing_status}。车载故障时旧路线仅用于定位，车辆在异常时刻冻结；不意味着未来仍沿旧路线配送。</p>
      <p className="pg-hint">异常时正在路上的车辆：{currentResult.state.in_transit_vehicle_ids.join('、')||'无'}；已送达订单：{currentResult.state.completed_order_ids.length}；车载待送货物：{currentResult.state.onboard_pending_order_ids.length}。</p>
      {Object.entries(currentResult.state.halted_vehicle_positions).map(([vid,loc])=><p className="pg-hint" key={vid}>车辆 {vid} 故障/停靠位置：{loc.state==='in_transit_between_nodes'?`${loc.from_node_id} → ${loc.to_node_id}（仅已知路段，非 GPS 点）`:loc.node_id??loc.state}。</p>)}
      {currentResult.comparison.warnings.map(w=><p key={w} className="pg-hint">适用范围提示：{w}</p>)}
      {currentResult.comparison.unserved_orders.length>0&&<div className="r28-order-scroll"><table><thead><tr><th>不可服务订单</th><th>业务约束 / 原因</th></tr></thead><tbody>{currentResult.comparison.unserved_orders.map(x=><tr key={x.order_id}><td>{x.order_id}</td><td>{briefReason(x.reason_code)}</td></tr>)}</tbody></table></div>}
      {currentResult.impact_evidence&&<>
        <h4>R30-E · 经过事件核对的异常影响明细</h4>
        <p className="pg-hint">受影响订单 {currentResult.impact_evidence.counts.affected_orders}；预计送达时间变化 {currentResult.impact_evidence.counts.delivery_time_changed_orders}；仍可服务但更换车辆 {currentResult.impact_evidence.counts.vehicle_reassigned_served_orders}；仓储中断作业 {currentResult.impact_evidence.counts.interrupted_operations}。仅计入事件流中的预计送达，不把故障车旧路线当作新方案。</p>
        <h4>逐车原始订单 / 异常后预计送达订单</h4>
        <div className="r28-order-scroll"><table><thead><tr><th>车辆</th><th>原订单顺序</th><th>后续事件预测可送达（含历史已送达）</th><th>异常状态</th></tr></thead><tbody>{currentResult.impact_evidence.vehicles.map(v=><tr key={v.vehicle_id}><td>{v.vehicle_id}</td><td>{v.previous_order_sequence.join(' → ')||'—'}</td><td>{v.forecast_delivery_order_ids.join(' → ')||'无'}</td><td>{v.halted_at_event?'模拟停驶，未来旧路线不计为交付':'按当前事件预测'}</td></tr>)}</tbody></table></div>
        <h4>仓储作业中断 / 取消 / 重排</h4>
        {currentResult.impact_evidence.warehouse_operation_changes.length===0?<p className="pg-hint">此次未发现发生变更的仓储作业。</p>:<div className="r28-order-scroll"><table><thead><tr><th>作业</th><th>变更类型</th><th>原资源及时间</th><th>新资源及时间</th></tr></thead><tbody>{currentResult.impact_evidence.warehouse_operation_changes.map(w=><tr key={w.operation_id}><td>{w.operation_id}</td><td>{w.status}</td><td>{w.previous_resource_id??'—'}：{w.previous_start_s==null?'—':fmtClock(w.previous_start_s)} ～ {w.previous_end_s==null?'—':fmtClock(w.previous_end_s)}</td><td>{w.new_resource_id??'—'}：{w.new_start_s==null?'—':fmtClock(w.new_start_s)} ～ {w.new_end_s==null?'—':fmtClock(w.new_end_s)}</td></tr>)}</tbody></table></div>}
      </>}
      <h4>新旧订单归属与预计交付对比（含已完成业务）</h4>
      <div className="r28-order-scroll"><table><thead><tr><th>订单</th><th>原车辆</th><th>新车辆</th><th>原预计交付</th><th>新预计交付</th><th>变化</th><th>状态/原因</th></tr></thead><tbody>{currentResult.comparison.order_changes.map(x=><tr key={x.order_id}><td>{x.order_id}</td><td>{x.previous_vehicle_id??'—'}</td><td>{x.next_vehicle_id??'—'}</td><td>{x.previous_delivery_at_s==null?'—':fmtClock(x.previous_delivery_at_s)}</td><td>{x.new_delivery_at_s==null?'—':fmtClock(x.new_delivery_at_s)}</td><td>{x.previous_delivery_at_s!=null&&x.new_delivery_at_s!=null?(x.new_delivery_at_s-x.previous_delivery_at_s===0?'不变':`${x.new_delivery_at_s-x.previous_delivery_at_s>0?'+':''}${x.new_delivery_at_s-x.previous_delivery_at_s} 秒`):'—'}</td><td>{x.status==='completed_before_event'?'异常前已完成':x.status==='unserved'?`未服务：${briefReason(x.unserved_reason_code??'unknown')}`:'后续预计送达'}</td></tr>)}</tbody></table></div>
      <p className="pg-hint">本次为重新计算生成的独立只读预览。若同时有其他计划或数据库变化，请重新求解，不能将本表当成正式执行凭证。</p>
    </>}
  </div>;
}
