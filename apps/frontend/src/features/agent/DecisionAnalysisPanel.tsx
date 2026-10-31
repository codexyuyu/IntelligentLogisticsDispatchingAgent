import { useEffect, useState } from 'react';
import { request } from '../../api';
import './decision-analysis.css';
import '../stageB/defense-evidence.css';
import { short } from '../stageB/api';

export type DecisionAnalysis = {
  analysis_id: string; target_type: 'dispatch_task' | 'incident'; target_id: string;
  run_id: string; question: string; reply: string; model: string | null;
  status: 'model_success' | 'model_unavailable' | 'model_failed';
  error_code: string | null;
  tool_trace: { name: string; ok: boolean; source: string }[];
  recommendation: string | null;
  evidence: Record<string, unknown>; created_at: string;
};

const pending = new Map<string, Promise<DecisionAnalysis | null>>();
const recommendationLabels: Record<string, string> = {
  not_approvable: '候选校验不通过，不建议批准',
  insufficient_comparison: '缺少可核对的方案对比，请人工核实',
  keep_original: '未证明候选优于简单顺延，建议保留原方案',
  review_candidate: '有计算得到的改善，可进一步人工审核',
};
const toolNames: Record<string, string> = {
  get_checked_dispatch_task: '读取已校验的调度任务',
  get_solver_candidate_metrics: '读取 OR-Tools 候选指标',
  get_simulation_incident: '读取模拟异常记录',
  analyze_incident_impact: '核对受影响订单与延误',
  compare_incident_strategies: '核对顺延与候选对比',
  deepseek_decision_explanation: 'DeepSeek 分析和回答',
};

export default function DecisionAnalysisPanel({ kind, targetId, runId, parser }: {
  kind: 'dispatch_task' | 'incident'; targetId: string; runId?: string; parser?: 'deepseek_tool_call' | 'rule_based';
}) {
  const [analysis, setAnalysis] = useState<DecisionAnalysis | null>(null);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const base = kind === 'dispatch_task'
    ? `/agents/dispatch-tasks/${encodeURIComponent(targetId)}/ai-analysis`
    : `/agents/runs/${encodeURIComponent(runId ?? '')}/incidents/${encodeURIComponent(targetId)}/ai-analysis`;

  useEffect(() => {
    let active = true;
    setAnalysis(null); setError(''); setLoading(true);
    // Deduplicate initial auto-analysis on React StrictMode remounts; after refresh,
    // GET checks the persisted audit before any external model call.
    let promise = pending.get(base);
    if (!promise) {
      promise = request<DecisionAnalysis | null>(base).then(existing => existing ?? request<DecisionAnalysis>(base, {
        method: 'POST', body: JSON.stringify({ question: '' }),
      }));
      pending.set(base, promise);
      void promise.finally(() => { if (pending.get(base) === promise) pending.delete(base); }).catch(() => {});
    }
    void promise.then(result => { if (active) setAnalysis(result); })
      .catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'AI 分析请求失败'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [base]);

  async function ask(text: string) {
    if (loading) return;
    setLoading(true); setError('');
    try {
      const result = await request<DecisionAnalysis>(base, {
        method: 'POST', body: JSON.stringify({ question: text }),
      });
      setAnalysis(result); setQuestion('');
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'AI 分析请求失败'); }
    finally { setLoading(false); }
  }

  return <section className="decision-ai-panel" aria-label="AI 决策分析">
    <div className="decision-ai-heading">
      <h4>AI Agent 决策分析</h4>
      <span className="decision-ai-state" role="status">{loading ? '正在读取证据并分析…' : analysis?.status === 'model_success'
        ? `DeepSeek 已回答 · ${analysis.model ?? '模型'}` : analysis?.status === 'model_unavailable'
          ? '未调用模型 · API Key 未配置' : analysis?.status === 'model_failed'
            ? '模型调用失败 · 保留算法结果' : '尚无分析'}</span>
    </div>
    <div className="defense-proof" style={{margin: 0}} aria-label="AI 决策证据链">
      <div className="defense-heading"><div><span className="defense-eyebrow">可核对证据 · 非演示伪造</span><h4>AI 如何参与了本次调度？</h4></div>
        <span className={`defense-verdict ${analysis?.status === 'model_success' ? 'positive' : ''}`}>
          {loading ? '正在核验证据' : analysis?.status === 'model_success' ? '本次 DeepSeek 已完成解释' : '本次无可确认模型解释'}</span></div>
      <div className="defense-steps">
        <div className="defense-step"><strong>① 业务意图 / 事实读取</strong>
          <span className="defense-step-state">{kind === 'incident' ? '异常事实来自后端模拟记录'
            : parser === 'deepseek_tool_call' ? 'DeepSeek 已解析调度意图'
              : parser === 'rule_based' ? '规则解析 · 非 AI 识别' : '读取已有调度任务'}</span>
          <small>{kind === 'incident' ? '已登记的异常、延误和受影响订单为数据源' : '意图解析与模型解释是两种独立能力，来源分别记录'}</small></div>
        <div className="defense-step"><strong>② OR-Tools / 业务校验</strong><span className="defense-step-state">求解与可行性不由语言模型决定</span>
          <small>成本、里程、时效、校验结果由求解器和仿真评估计算，DeepSeek 只能解释</small></div>
        <div className="defense-step"><strong>③ DeepSeek 解释 / 人工审批</strong><span className="defense-step-state">{analysis?.status === 'model_success' ? '真实模型回答已留审计' : '模型回答未确认'}</span>
          <small>模型分析不自动执行审批；操作员单独确认是否采用候选方案</small></div>
      </div>
      {analysis && <>
        <p className="defense-provenance"><strong>审计：</strong>{short(analysis.analysis_id)} · <strong>关联运行：</strong>{short(analysis.run_id)} · <strong>模型：</strong>{analysis.status === 'model_success' ? analysis.model ?? '已调用（型号未返回）' : '不可确认'} · <strong>工具：</strong>{analysis.tool_trace.filter(x => x.ok).length}/{analysis.tool_trace.length} 成功</p>
        <div className="defense-mini-trace">{analysis.tool_trace.map((tool, i) => <span key={`${tool.name}-${i}`}>{tool.ok ? '✓' : '✕'} {toolNames[tool.name] ?? tool.name}</span>)}</div>
      </>}
      {!analysis && !loading && <p className="muted">暂无已保存的模型审计；界面不会伪造工具调用或 AI 解释。</p>}
    </div>
    <p className="muted">系统先只读核对订单、求解及异常指标，再交给模型解释。模型不能修改候选路线、替代人工审批或控制真实车辆。</p>
    {analysis?.recommendation && <p className="decision-rule">业务规则判断：{recommendationLabels[analysis.recommendation] ?? analysis.recommendation}（不是 AI 审批）</p>}
    {analysis?.status === 'model_success' && <div className="decision-ai-reply" style={{ whiteSpace: 'pre-wrap' }}>
      <strong>DeepSeek 回答</strong><p>{analysis.reply}</p>
    </div>}
    {analysis?.status !== 'model_success' && !loading && <p className="muted">当前仅展示调度算法和服务端真实证据；没有可确认的 AI 解释。请检查服务器 DEEPSEEK_API_KEY 配置后重试。</p>}
    {analysis && <details><summary>实际工具与数据来源（{analysis.tool_trace.length}）</summary>
      <ol className="decision-ai-trace">{analysis.tool_trace.map((t, i) => <li key={`${t.name}-${i}`}>
        {toolNames[t.name] ?? t.name} · {t.ok ? '成功' : '未成功'} · {t.source}
      </li>)}</ol>
      <details><summary>本次 AI 收到的业务证据</summary><pre>{JSON.stringify(analysis.evidence, null, 2)}</pre></details>
    </details>}
    <form className="decision-ai-followup" onSubmit={event => { event.preventDefault(); if (question.trim()) void ask(question.trim()); }}>
      <label htmlFor={`decision-ai-q-${kind}`}>继续追问当前候选方案</label>
      <textarea id={`decision-ai-q-${kind}`} value={question} maxLength={500} rows={2}
        onChange={event => setQuestion(event.target.value)} placeholder="为什么建议保留原方案？哪些订单可能迟到？" />
      <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
        <button type="submit" className="btn btn-primary btn-sm" disabled={loading || !question.trim()}>询问 DeepSeek</button>
        {analysis?.status !== 'model_success' && <button type="button" className="btn btn-ghost btn-sm" disabled={loading} onClick={() => void ask('请基于当前候选的真实指标解释方案及风险。')}>重新请求 AI 分析</button>}
      </div>
    </form>
    {error && <p className="callout callout-error" role="alert">{error}</p>}
  </section>;
}
