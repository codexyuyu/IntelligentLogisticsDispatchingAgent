// Owner CODEX_FRONTEND: a visible unfinished state, never fake business data.
export default function ModulePlaceholder({title, purpose, owner}: {title:string; purpose:string; owner:string}) {
  return <section className="panel"><span className="tag">待实现</span><h2>{title}</h2><p>{purpose}</p><p className="muted">后端责任：{owner} · 前端：Codex</p></section>;
}
