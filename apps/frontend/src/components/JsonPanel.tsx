import { useState } from "react";
import { idempotencyKey, request } from "../api";

type Props = {
  title: string;
  path: string;
  initialBody: string;
  description?: string;
  idempotent?: boolean;
};

export function JsonPanel({ title, path, initialBody, description, idempotent = false }: Props) {
  const [body, setBody] = useState(initialBody);
  const [response, setResponse] = useState<unknown>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    try {
      setBusy(true);
      setError("");
      const headers: Record<string, string> = {};
      if (idempotent) headers["Idempotency-Key"] = idempotencyKey();
      setResponse(
        await request<unknown>(path, { method: "POST", headers, body }),
      );
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h2>{title}</h2>
      {description ? <p className="muted">{description}</p> : null}
      <textarea value={body} onChange={(event) => setBody(event.target.value)} spellCheck={false} />
      <div className="row" style={{ marginTop: "0.5rem" }}>
        <button onClick={submit} disabled={busy}>
          {busy ? "running…" : `POST ${path}`}
        </button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {response ? <pre>{JSON.stringify(response, null, 2)}</pre> : null}
    </section>
  );
}
