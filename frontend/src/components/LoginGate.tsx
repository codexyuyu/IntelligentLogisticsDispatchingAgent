import { useState } from "react";
import { setToken, verifyToken } from "../auth";

export function LoginGate({ onSuccess }: { onSuccess: () => void }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [visible, setVisible] = useState(false);

  async function submit() {
    if (!value.trim()) {
      setError("请输入 API Key");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await verifyToken(value);
      setToken(value);
      onSuccess();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "登录失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <section className="auth-hero">
        <div className="auth-brand">
          <div className="auth-logo">冷</div>
          <div>
            <strong>县域冷链调度</strong>
            <span>仓储与运输协同</span>
          </div>
        </div>
        <div className="auth-copy">
          <span className="auth-kicker">COLD-CHAIN DISPATCH CONSOLE</span>
          <h1>一仓一链，<br />把每一次调度算清楚。</h1>
          <p>仓储作业、冷间时间窗与运输计划在同一张调度单上对齐。</p>
          <ul>
            <li>冷间与库位资源可视化</li>
            <li>运输与仓运联合方案</li>
            <li>异常处置与重排对比</li>
          </ul>
        </div>
        <div className="auth-foot">第一版县域冷链调度界面 · API Key 访问</div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <span className="auth-kicker">API KEY ACCESS</span>
          <h2>进入调度台</h2>
          <p>使用后端分配的 API Key。开发环境示例：<code>dev-operator-token</code>。</p>
          <label htmlFor="api-key">API Key</label>
          <div className="auth-input-row">
            <input
              id="api-key"
              type={visible ? "text" : "password"}
              value={value}
              placeholder="输入 API Key"
              autoFocus
              onChange={(event) => setValue(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void submit();
              }}
            />
            <button type="button" className="auth-ghost" onClick={() => setVisible((v) => !v)}>
              {visible ? "隐藏" : "显示"}
            </button>
          </div>
          <button type="button" className="auth-submit" onClick={submit} disabled={busy}>
            {busy ? "验证中…" : "验证并进入"}
          </button>
          {error ? <div className="auth-error">{error}</div> : null}
          <small>API Key 只保存在本机 localStorage，不写入仓库。</small>
        </div>
      </section>
    </div>
  );
}
