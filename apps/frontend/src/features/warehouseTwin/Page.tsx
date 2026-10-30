import { useMemo, useState } from 'react';
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
    if(selected.kind==='evaporator'){
      const frozen=selected.id==='EV-02';
      return {title:`${selected.id} 吊顶冷风机`,lines:[
        `所属温区：${frozen?'冷冻区':'冷藏区'}`,
        '设备连接：未接入 · 演示模型',
        '演示工况：制冷送风；双轴流风扇随回放转动',
        `温区目标（演示配置）：${frozen?'−18°C':'2–8°C'}`,
        '实测温度 / 风机转速 / 功率：未采集',
        '除霜状态 / 故障告警：未知（无设备遥测）',
        '结构：双风机护网、翅片换热器、检修侧盖、接水盘、排水弯管、保温回气管与吊架',
        'COLDLINE 为演示铭牌，非厂家型号或真实设备参数。',
      ]};
    }
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
      return {title:selected.id,lines:[`任务状态：${STAGE_LABELS[pose.stage]}`,`当前作业：${pose.job?.id??'无'}`,`关联库位：${pose.job?.rackId??'—'}`,
        ...(pose.job?[`原任务时间：${fmtClock(pose.job.sourceStartS??pose.job.startS)} — ${fmtClock(pose.job.sourceEndS??pose.job.endS)}`,
          `通道等待：${Math.round(pose.job.startS-(pose.job.sourceStartS??pose.job.startS))} 秒`]:[]),
        `任务来源：${pose.job?.source==='planned_timing'?'排程任务的避让回放':'合成演示事件'}`, '没有接入真实叉车定位或硬件控制。']};
    }
    if(selected.kind==='cargo'){
      const job=data.jobs.find(j=>j.id===selected.id);
      return {title:selected.id,lines:job?[`批次：${job.batchId}`,`订单：${job.orderId}`,`关联库位：${job.rackId}`]:['单件可视化货物','此箱体为演示模型，未绑定实时库存。']};
    }
    if(selected.kind==='charger'){
      return {title:`${selected.id} 叉车充电桩`,lines:['机柜、操作屏、急停按钮、通风格栅与充电线缆。','叉车停回待命位时显示连接线；离开后线缆归位。','状态灯和屏幕为回放演示，未连接真实电池管理系统。']};
    }
    const dockNumber=Number(selected.id.replace('DOCK-',''));
    return {title:`D${String(dockNumber).padStart(2,'0')} 出口`,lines:['开放式装卸出口 · 动力滚筒输送线','叉车卸下托盘后倒车离开，货物沿输送线通过出口。','滚筒和货物随回放时间同步运动；暂停、拖动可检查交接过程。','当前为作业展示动画，不代表实际出库落账或车辆已发车。']};
  },[selected,data,clock.t]);
  const canShowPlan=Boolean(plan?.warehouse.operations?.length);
  return <div className="r26-page">
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
        <button className={`btn btn-sm ${mode==='plan'?'btn-primary':'btn-ghost'}`} disabled={!canShowPlan} title={canShowPlan?'回放当前排程任务，通道冲突会增加演示等待时间，原任务时间保留在详情中':'请先在联合调度页求解 CP-SAT 仓储排程'} onClick={()=>{setMode('plan');clock.pause();clock.seek(0);}}>排程任务回放</button>
      </div>
      <div className="r26-toolbar-group"><span>视角</span>
        {([['isometric','剖切俯视'],['top','垂直俯视'],['dock','装车月台'],['equipment','叉车与充电桩']] as const).map(([key,title])=><button key={key} className={`btn btn-sm ${camera===key?'btn-primary':'btn-ghost'}`} onClick={()=>setCamera(key)}>{title}</button>)}
        <button className={`btn btn-sm ${showRoof?'btn-primary':'btn-ghost'}`} onClick={()=>setShowRoof(v=>!v)}>{showRoof?'隐藏屋顶':'显示半透明屋顶'}</button>
      </div>
    </div>
    <div className="r26-scene-layout">
      <div className="r26-scene-panel">
        <WarehouseTwin3D data={data} getTime={clock.getTime} cameraPreset={camera} showRoof={showRoof} selected={selected} onSelect={setSelected} height={590} />
        <div className="r26-scene-hint">左键拖动旋转 · 滚轮缩放 · 右键平移 · 点击冷风机、货架、库区、叉车、月台查看属性</div>
      </div>
      <aside className="r26-inspector">
        <div className="r26-inspector-title"><small>场景检视</small><h3>{currentDetail.title}</h3></div>
        <div className="r26-inspector-body">{currentDetail.lines.map((line,i)=><div key={i}>{line}</div>)}</div>
        <div className="r26-inspector-title"><small>制冷设备</small><h3>冷风机</h3></div>
          <div className="r26-zone-list">{['EV-01','EV-02'].map((id,i)=><button key={id} className={selected?.kind==='evaporator'&&selected.id===id?'is-selected':''} onClick={()=>setSelected({kind:'evaporator',id})}>{id}<small>{i===0?'冷藏区':'冷冻区'} · 未接入</small></button>)}</div>
          <div className="r26-inspector-title"><small>库区目录</small><h3>仓内区域</h3></div>
        <div className="r26-zone-list">{data.zones.map((zone)=><button key={zone.id} className={selected?.kind==='zone'&&selected.id===zone.id?'is-selected':''} onClick={()=>setSelected({kind:'zone',id:zone.id})}><i style={{background:`#${zone.color.toString(16).padStart(6,'0')}`}}/>{zone.name}<small>{zone.temp}</small></button>)}</div>
      </aside>
    </div>
    <div className="panel r26-player">
      <div className="r26-play-top"><div><b>叉车作业时间轴</b></div>
        <div className="r26-player-buttons"><button className="btn btn-primary btn-sm" onClick={clock.toggle}>{clock.playing?'暂停':'播放'}</button><button className="btn btn-ghost btn-sm" onClick={()=>{clock.pause();clock.seek(0);}}>重置</button>
          {SPEEDS.map(s=><button key={s} className={`btn btn-sm ${clock.speed===s?'btn-primary':'btn-ghost'}`} onClick={()=>clock.setSpeed(s)}>{s}×</button>)}
        </div></div>
      <div className="r26-scrub"><span>{fmtClock(clock.t)}</span><input type="range" min="0" max={horizon} step="1" value={Math.round(clock.t)} onChange={e=>clock.seek(Number(e.target.value))} aria-label="拖动仓库作业回放进度条"/><span>{fmtClock(horizon)}</span></div>
      <div className="r26-vehicle-row">{FORKLIFT_IDS.map(id=>{
        const pose=forkliftPose(id,clock.t,data.jobs,data.racks);
        return <button key={id} className={`r26-forklift-chip ${selected?.id===id?'selected':''}`} onClick={()=>setSelected({kind:'forklift',id})}><strong>{id}</strong><span>{STAGE_LABELS[pose.stage]}</span><small>{pose.job?.rackId??'待命区'}</small></button>;
      })}<div className="r26-work-counter">运行中 <b>{activeJobs.length}</b> 项 / 已完成 <b>{completedJobs.length}</b> 项</div></div>
    </div>
    <div className="panel r26-work-log"><div className="panel-title-row"><div><h3>叉车搬运任务</h3></div><span className="soft-badge">{data.jobs.length} 条</span></div>
      <p>共用通道按预约顺序通行。冲突车辆在停车位等待；下表显示避让后的回放时间，原任务时间可在叉车详情查看。</p>
      <div className="table-wrap"><table><thead><tr><th>任务</th><th>叉车</th><th>库位</th><th>批次</th><th>订单</th><th>开始</th><th>结束</th><th>状态</th></tr></thead><tbody>{data.jobs.map(job=><tr key={job.id} onClick={()=>setSelected({kind:'forklift',id:job.forkliftId})} style={{cursor:'pointer'}}><td>{job.id}</td><td>{job.forkliftId}</td><td>{job.rackId}</td><td>{job.batchId}</td><td>{job.orderId}</td><td>{fmtClock(job.startS)}</td><td>{fmtClock(job.endS)}</td><td>{clock.t>=job.endS?'已完成':clock.t>=job.startS?'进行中':clock.t>=(job.sourceStartS??job.startS)?'等待通道':'待执行'}</td></tr>)}</tbody></table></div>
    </div>
  </div>;
}
