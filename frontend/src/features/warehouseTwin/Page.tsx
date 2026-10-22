import { useMemo, useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import { StatusPill } from '../../components/StatusPill';
import WarehouseTwin3D, { type WarehouseCamera, type WarehouseSelection } from '../../components/WarehouseTwin3D';
import { useApp } from '../../appContext';
import { useSimClock } from '../../hooks/useSimClock';
import { forkliftPose, STAGE_LABELS, warehouseTwinData, type TwinMode, FORKLIFT_IDS } from '../../lib/warehouseTwin';
import { fmtClock } from '../../lib/format';

const SPEEDS = [1, 4, 16, 64];

export default function WarehouseTwinPage(){
  const { snapshot, baselinePlan, anomalyResult } = useApp();
  const plan=anomalyResult?.replanned_plan ?? baselinePlan;
  const [mode,setMode]=useState<TwinMode>('showcase');
  const [camera,setCamera]=useState<WarehouseCamera>('isometric');
  const [showRoof,setShowRoof]=useState(false);
  const [selected,setSelected]=useState<WarehouseSelection|null>({kind:'zone',id:'chilled'});
  const data=useMemo(()=>warehouseTwinData(snapshot,plan,mode),[snapshot,plan,mode]);
  const horizon=Math.max(1800,...data.jobs.map(job=>job.endS));
  const clock=useSimClock(horizon,false);
  const activeJobs=data.jobs.filter((job)=>clock.t >= job.startS && clock.t <= job.endS);
  const completedJobs=data.jobs.filter((job)=>clock.t>=job.endS);
  const currentDetail=useMemo(()=>{
    if(!selected)return {title:'单仓总览',lines:['点击库区、货架、叉车或月台查看详情。']};
    if(selected.kind==='zone'){
      const z=data.zones.find(x=>x.id===selected.id);
      return {title:z?.name??selected.id,lines:[`类型：${z?.temp??'未知'}`,`空间范围：${z?.width??0} × ${z?.depth??0}（示意单位）`, '温度与布局为演示配置，未连接冷库传感器。']};
    }
    if(selected.kind==='rack'){
      const rack=data.racks.find(x=>x.id===selected.id);
      return {title:rack?.id??selected.id,lines:[`温区：${rack?.zone==='frozen'?'冷冻':'冷藏'}`,`结构：${rack?.levels??0} 层 × ${rack?.bays??0} 货位`, `可视化占用率（演示）：${Math.round((rack?.occupied??0)*100)}%`, '库存箱体为演示绘制，不是实时 WMS 库位数据。']};
    }
    if(selected.kind==='forklift'){
      const pose=forkliftPose(selected.id,clock.t,data.jobs,data.racks);
      return {title:selected.id,lines:[`任务状态：${STAGE_LABELS[pose.stage]}`,`当前作业：${pose.job?.id??'无'}`,`关联库位：${pose.job?.rackId??'—'}`,`任务来源：${pose.job?.source==='planned_timing'?'排程时间展示映射':'合成演示事件'}`, '没有接入真实叉车定位或硬件控制。']};
    }
    return {title:selected.id,lines:['冷链装卸月台','叉车将托盘送至月台交接区。','装车动作与运输计划目前是视觉示意，不能据此确认实际已发车。']};
  },[selected,data,clock.t]);
  const canShowPlan=Boolean(plan?.warehouse.operations?.length);
  return <div className="r26-page">
    <SectionHeader title="单仓冷链数字孪生" desc="一座配送中心 · 冷藏/冷冻分区 · 24 组多层货架 · 三辆叉车 · 动态月台作业；与 R25 配送视图分别渲染，避免场景叠加卡顿。"
      actions={<StatusPill tone={mode==='showcase'?'warning':'success'}>{mode==='showcase'?'明确标注：仿真演示':'排程时间映射（非实时监控）'}</StatusPill>} />
    {data.warehouseWarning && <div className="callout callout-warning">{data.warehouseWarning}</div>}
    <div className="r26-hero">
      <div><small>当前业务仓库</small><strong>{data.warehouseId}</strong><span>唯一配送中心 · 内部分区不是独立仓库</span></div>
      <div><small>温控功能区</small><strong>{data.zones.length}</strong><span>含收货、质检、分拣与装车</span></div>
      <div><small>货架阵列</small><strong>{data.racks.length}</strong><span>3 层 × 3 货位 / 架</span></div>
      <div><small>叉车设备</small><strong>{FORKLIFT_IDS.length}</strong><span>独立路径 / 取货 / 交接</span></div>
      <div><small>作业任务</small><strong>{data.jobs.length}</strong><span>{mode==='showcase'?'合成作业事件':'当前 CP-SAT 作业映射'}</span></div>
    </div>
    <div className="r26-toolbar">
      <div className="r26-toolbar-group"><span>数据</span>
        <button className={`btn btn-sm ${mode==='showcase'?'btn-primary':'btn-ghost'}`} onClick={()=>{setMode('showcase');clock.pause();clock.seek(0);}}>完整演示</button>
        <button className={`btn btn-sm ${mode==='plan'?'btn-primary':'btn-ghost'}`} disabled={!canShowPlan} title={canShowPlan?'按当前仓储排程时间展示任务':'请先在联合调度页求解 CP-SAT 仓储排程'} onClick={()=>{setMode('plan');clock.pause();clock.seek(0);}}>按 CP-SAT 时间映射</button>
      </div>
      <div className="r26-toolbar-group"><span>视角</span>
        {([['isometric','剖切俯视'],['top','垂直俯视'],['dock','装车月台']] as const).map(([key,title])=><button key={key} className={`btn btn-sm ${camera===key?'btn-primary':'btn-ghost'}`} onClick={()=>setCamera(key)}>{title}</button>)}
        <button className={`btn btn-sm ${showRoof?'btn-primary':'btn-ghost'}`} onClick={()=>setShowRoof(v=>!v)}>{showRoof?'隐藏屋顶':'显示半透明屋顶'}</button>
      </div>
    </div>
    <div className="r26-scene-layout">
      <div className="r26-scene-panel">
        <div className="r26-overlay"><strong>WH · SINGLE WAREHOUSE</strong><span>{mode==='showcase'?'DEMO REPLAY · NOT WMS TELEMETRY':'CP-SAT TIMING · VISUAL PATH ASSUMPTIONS'}</span></div>
        <WarehouseTwin3D data={data} getTime={clock.getTime} cameraPreset={camera} showRoof={showRoof} selected={selected} onSelect={setSelected} height={590} />
        <div className="r26-scene-hint">左键拖动旋转 · 滚轮缩放 · 右键平移 · 点击货架、库区、叉车、月台查看属性</div>
      </div>
      <aside className="r26-inspector">
        <div className="r26-inspector-title"><small>SCENE INSPECTOR</small><h3>{currentDetail.title}</h3></div>
        <div className="r26-inspector-body">{currentDetail.lines.map((line,i)=><div key={i}>{line}</div>)}</div>
        <div className="r26-inspector-title"><small>ZONE DIRECTORY</small><h3>仓内区域</h3></div>
        <div className="r26-zone-list">{data.zones.map((zone)=><button key={zone.id} className={selected?.kind==='zone'&&selected.id===zone.id?'is-selected':''} onClick={()=>setSelected({kind:'zone',id:zone.id})}><i style={{background:`#${zone.color.toString(16).padStart(6,'0')}`}}/>{zone.name}<small>{zone.temp}</small></button>)}</div>
      </aside>
    </div>
    <div className="panel r26-player">
      <div className="r26-play-top"><div><b>叉车作业时间轴</b><small>{mode==='showcase'?'合成演示计划，支持任意时刻拖动回放':'作业时刻来自当前 CP-SAT；叉车分配与仓内路径是展示映射'}</small></div>
        <div className="r26-player-buttons"><button className="btn btn-primary btn-sm" onClick={clock.toggle}>{clock.playing?'暂停':'播放'}</button><button className="btn btn-ghost btn-sm" onClick={()=>{clock.pause();clock.seek(0);}}>重置</button>
          {SPEEDS.map(s=><button key={s} className={`btn btn-sm ${clock.speed===s?'btn-primary':'btn-ghost'}`} onClick={()=>clock.setSpeed(s)}>{s}×</button>)}
        </div></div>
      <div className="r26-scrub"><span>{fmtClock(clock.t)}</span><input type="range" min="0" max={horizon} step="1" value={Math.round(clock.t)} onChange={e=>clock.seek(Number(e.target.value))} aria-label="拖动仓库作业回放进度条"/><span>{fmtClock(horizon)}</span></div>
      <div className="r26-progress"><span style={{width:`${clock.t/horizon*100}%`}}/></div>
      <div className="r26-vehicle-row">{FORKLIFT_IDS.map(id=>{
        const pose=forkliftPose(id,clock.t,data.jobs,data.racks);
        return <button key={id} className={`r26-forklift-chip ${selected?.id===id?'selected':''}`} onClick={()=>setSelected({kind:'forklift',id})}><strong>{id}</strong><span>{STAGE_LABELS[pose.stage]}</span><small>{pose.job?.rackId??'待命区'}</small></button>;
      })}<div className="r26-work-counter">运行中 <b>{activeJobs.length}</b> 项 / 已完成 <b>{completedJobs.length}</b> 项</div></div>
    </div>
    <div className="panel r26-work-log"><div className="panel-title-row"><div><h3>叉车搬运任务</h3><p>{mode==='showcase'?'用于展示的确定性任务，不写入 PostgreSQL，也不构成真实库存变更':'时间来自当前排程；货位、批次映射、叉车行驶路线仅作可视化示意'}</p></div><span className="soft-badge">{data.jobs.length} 条</span></div>
      <div className="table-wrap"><table><thead><tr><th>任务</th><th>叉车</th><th>库位</th><th>批次</th><th>订单</th><th>开始</th><th>结束</th><th>状态</th></tr></thead><tbody>{data.jobs.map(job=><tr key={job.id} onClick={()=>setSelected({kind:'forklift',id:job.forkliftId})} style={{cursor:'pointer'}}><td>{job.id}</td><td>{job.forkliftId}</td><td>{job.rackId}</td><td>{job.batchId}</td><td>{job.orderId}</td><td>{fmtClock(job.startS)}</td><td>{fmtClock(job.endS)}</td><td>{clock.t>=job.endS?'已完成':clock.t>=job.startS?'进行中':'待执行'}</td></tr>)}</tbody></table></div>
    </div>
    <p className="r26-disclaimer">数据边界：本页面仓库布局、货架占用、叉车模型和任务路线为 R26 展示资产；真实规划模式只采用已计算的作业时间，不声称真实库位坐标、叉车遥测、温度传感或库存落账。历史双仓评测数据仍单独保留，PostgreSQL 实库是否统一须通过独立迁移确认。</p>
  </div>;
}
