import { useEffect, useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import { pgRequest } from '../postgres/api';

type Source = 'single_warehouse_demo' | 'verified_postgres';
type Mode = 'deepseek_tool_calling' | 'direct_algorithm_fallback_not_ai';
type ToolEvidence = { tool:string;status:string;error?:string;[field:string]:unknown };
type Artifact = { kind:'workflow'|'exception';payload:Record<string,unknown> };
type Response = { mode:Mode; answer:string; calls:ToolEvidence[];artifact:Artifact|null;model?:string };
type Turn = { role:'user'|'assistant';content:string;result?:Response };
type Status = { configured:boolean;model:string;provider:string;mode:string };
const examples = [
  '请读取当前订单和车辆情况，告诉我现在有哪些调度资源。',
  '请对今天的20个订单执行仓储与运输联合调度，列出车辆分配和校验结果。',
  '假设一辆正在配送的车辆发生故障，请实际调用异常重调度，并说明受影响的订单。',
  '如果配送车辆延误15分钟，请检查配送时间窗并重新分析后续任务。',
];
const feedbackLabel:Record<string,string> = {
  get_business_status:'业务状态查询', generate_joint_plan:'联合调度求解', simulate_exception:'异常事件重调度',
};
const sourceLabel:Record<Source,string> = {
  single_warehouse_demo:'内置单仓合成场景 · 无需数据库数据',
  verified_postgres:'PostgreSQL R30-A 数据 · 需要本机数据库',
};

export default function AgentPage() {
  const [source,setSource] = useState<Source>('single_warehouse_demo');
  const [zone,setZone] = useState<'chilled'|'frozen'>('chilled');
  const [status,setStatus] = useState<Status|null>(null);
  const [statusError,setStatusError] = useState('');
  const [input,setInput] = useState(examples[1]);
  const [turns,setTurns] = useState<Turn[]>([]);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [selected,setSelected] = useState<Response|null>(null);
  useEffect(()=>{void pgRequest<Status>('/r30c/status').then(s=>{setStatus(s);setStatusError('');}).catch(e=>setStatusError(e instanceof Error?e.message:'R30-C 服务不可访问'));},[]);

  const options = { source, temperature_zone:zone,budget_ms:60000 };
  async function send(message=input){
    const cleaned=message.trim();if(!cleaned||busy)return;
    const prior = turns.slice(-6).map(x=>({role:x.role,content:x.content}));
    setError('');setInput('');setBusy(true);
    setTurns(old=>[...old,{role:'user',content:cleaned}]);
    try{
      const result=await pgRequest<Response>('/r30c/chat',{...options,message:cleaned,history:prior});
      setTurns(old=>[...old,{role:'assistant',content:result.answer,result}]);
      setSelected(result);
    }catch(e){
      const reason=e instanceof Error?e.message:'未知网络错误';
      setError(reason);
      setTurns(old=>[...old,{role:'assistant',content:`本次 AI 调用未成功：${reason}。这不是算法已执行的证明；可以尝试下方“直接调用算法”演示入口。`}]);
    }finally{setBusy(false);}
  }
  async function quick(action:'get_business_status'|'generate_joint_plan'|'simulate_exception'){
    if(busy)return;
    setBusy(true);setError('');
    const label=feedbackLabel[action];
    setTurns(old=>[...old,{role:'user',content:`[手动执行 · 非 AI] ${label}`}]);
    try{
      const result=await pgRequest<Response>('/r30c/quick',{...options,action,
        event_type:'vehicle_breakdown',delay_s:900});
      setTurns(old=>[...old,{role:'assistant',content:`${label}已调用真实后端。当前是直接运行算法的降级演示，不代表 DeepSeek 已经完成推理。`,result}]);
      setSelected(result);
    }catch(e){
      const reason=e instanceof Error?e.message:'未知网络错误';
      setError(reason);
      setTurns(old=>[...old,{role:'assistant',content:`${label}失败：${reason}`}]);
    }finally{setBusy(false);}
  }
  function openReplay(artifact:Artifact){
    const payload=artifact.kind==='exception' ? artifact.payload.baseline : artifact.payload;
    if(!payload || typeof payload!=='object' || !('snapshot' in payload)||!('plan' in payload)){
      setError('结果缺少原方案快照，无法进入回放');return;
    }
    try{
      sessionStorage.setItem('r30c-replay-transfer',JSON.stringify({
        workflow:payload,exception:artifact.kind==='exception'?artifact.payload:null,source,zone,
      }));
      window.dispatchEvent(new CustomEvent('twin:navigate',{detail:'closedLoop'}));
    }catch(e){setError('浏览器无法暂存此次演示数据：'+(e instanceof Error?e.message:String(e)));}
  }
  function exportJson(){
    if(!selected)return;
    const blob=new Blob([JSON.stringify(selected,null,2)],{type:'application/json;charset=utf-8'});
    const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;
    a.download='R30C_agent_readonly_evidence.json';a.click();URL.revokeObjectURL(url);
  }
  return <div className="r30c-root">
    <SectionHeader title="调度助手" desc="自然语言理解 → 受限工具调用 → 原有 CP-SAT / OR-Tools 求解 → 独立校验 → 数字孪生回放。真实算法与合成场景来源明确区分。" />
    <div className="pg-warning"><b>安全边界：</b>DeepSeek 仅能调用限定的查询、联合调度和异常预览工具；不执行 SQL、不自动确认方案、不修改订单库存。PostgreSQL 中的 R30-A 数据可能为合成演示数据；示意道路不是实际导航。</div>
    <div className="panel r30c-settings">
      <div className="panel-title-row"><h3>AI 服务与调度数据</h3><span className={'soft-badge '+(status?.configured?'':'')}>{status?.configured ? `DeepSeek ${status.model} · 已配置密钥` : 'DeepSeek 尚未配置 / 连接异常'}</span></div>
      <div className="pg-form r27-fields">
        <label>选择业务来源<select value={source} disabled={busy} onChange={e=>{setSource(e.target.value as Source);setSelected(null);setTurns([]);}}>{(Object.keys(sourceLabel) as Source[]).map(x=><option key={x} value={x}>{sourceLabel[x]}</option>)}</select></label>
        {source==='verified_postgres'&&<label>温区<select value={zone} disabled={busy} onChange={e=>setZone(e.target.value as 'chilled'|'frozen')}><option value="chilled">冷藏</option><option value="frozen">冷冻</option></select></label>}
      </div>
      <p className="pg-hint">{statusError||'模型密钥只在 FastAPI 后端读取，不传入浏览器。自然语言调用失败时，直接运行算法的按钮依然可用。'}</p>
    </div>
    <div className="r30c-grid">
      <div className="panel r30c-conversation">
        <div className="panel-title-row"><h3>智能对话</h3><span className="soft-badge">DeepSeek Function Calling</span></div>
        <div className="r30c-messages" aria-live="polite">
          {turns.length===0&&<div className="r30c-blank">在下方输入调度需求。AI 会调用后端工具，执行记录会显示在右侧。组会建议先演示“20 单联合调度”，再演示“车辆故障”。</div>}
          {turns.map((x,i)=><div key={i} className={'r30c-message '+(x.role==='user'?'mine':'assistant')}>
            <span className="r30c-speaker">{x.role==='user'?'用户':'调度智能体'}</span>
            <p>{x.content}</p>
            {x.result&&<button className="btn btn-ghost btn-sm" onClick={()=>setSelected(x.result!)}>查看本轮工具结果</button>}
          </div>)}
          {busy&&<div className="r30c-wait">正在等待模型 / 后端调度求解，可能需要数十秒…</div>}
        </div>
        <div className="r30c-ask">
          <textarea value={input} maxLength={1800} rows={3} placeholder="例如：请为 20 个订单生成仓运调度方案" onChange={e=>setInput(e.target.value)}
            onKeyDown={e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();void send();}}}/>
          <button className="btn btn-primary" disabled={busy||!input.trim()||!status?.configured} onClick={()=>void send()}>{busy?'正在计算…':'发送给 DeepSeek'}</button>
        </div>
        {error&&<p className="pg-error" role="alert">{error}</p>}
      </div>
      <div className="r30c-side">
        <div className="panel">
          <h3>组会演示指令</h3>
          <p className="pg-hint">点击示例填充聊天输入，再按“发送给 DeepSeek”。</p>
          {examples.map((text,i)=><button className="r30c-example" disabled={busy} key={i} onClick={()=>setInput(text)}><strong>0{i+1}</strong>{text}</button>)}
        </div>
        <div className="panel">
          <h3>演示保底 · 直接调用真实算法</h3>
          <p className="pg-hint">模型 API 暂时不可用时使用。这里不会假装是 AI 推理，仍会调用现有后端。</p>
          <div className="r30c-fallback">
            <button className="btn btn-ghost btn-sm" disabled={busy} onClick={()=>void quick('get_business_status')}>只读查询</button>
            <button className="btn btn-ghost btn-sm" disabled={busy} onClick={()=>void quick('generate_joint_plan')}>真实联合调度</button>
            <button className="btn btn-ghost btn-sm" disabled={busy} onClick={()=>void quick('simulate_exception')}>车辆故障预览</button>
          </div>
        </div>
        <div className="panel">
          <div className="panel-title-row"><h3>后端工具执行记录</h3><span className="soft-badge">只读校验</span></div>
          {(!selected||!selected.calls.length)&&<p className="pg-hint">当前暂无实际工具执行证据。AI 文字不等于求解已完成。</p>}
          {selected?.calls.map((t,i)=><div key={i} className="r30c-call">
            <div><strong>{feedbackLabel[t.tool]||t.tool}</strong><span>{t.status==='failed'?'调用失败':t.status==='verified_readonly'?'已求解并通过核验':'只读查询'}</span></div>
            {t.error&&<p className="pg-error">{t.error}</p>}
            {t.tool==='generate_joint_plan'&&t.status==='verified_readonly'&&<p>订单 {String(t.planned_delivery_count)}/{String(t.order_count)} · 求解车辆 {String(t.vehicle_route_count)} · 仓储任务 {String(t.operations)} · R28 {String(t.r28_reconciliation)}</p>}
            {t.tool==='simulate_exception'&&t.status==='verified_readonly'&&<p>已完成 {String(t.delivered_before_event)} · 异常后预计可交付 {String(t.forecast_delivered_total)} · 未服务 {String(t.unserved_total)} · 后缀校验 {String(t.validation)}{t.impact_counts&&typeof t.impact_counts==='object'?` · 影响订单 ${String((t.impact_counts as Record<string,unknown>).affected_orders)}`:''}</p>}
            {t.tool==='get_business_status'&&t.status==='read_only'&&<p>订单 {String(t.orders)} · 车辆 {String(t.vehicles)} · 未执行求解</p>}
          </div>)}
          {selected?.artifact&&<div className="r30c-result-actions"><button className="btn btn-primary" onClick={()=>openReplay(selected.artifact!)}>打开现有 3D 仓运回放</button><button className="btn btn-ghost" onClick={exportJson}>导出方案与证据 JSON</button></div>}
          {selected&&<p className="pg-hint">执行模式：{selected.mode==='deepseek_tool_calling'?'DeepSeek 模型请求':'人工快捷操作（未使用 AI）'}。本次预览未写数据库。</p>}
        </div>
      </div>
    </div>
  </div>;
}
