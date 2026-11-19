import { Exchange } from "../api";

function Json({ value, empty }: { value: unknown; empty: string }) {
  if (value === undefined) return <em className="muted">{empty}</em>;
  return <pre className="json">{typeof value === "string" ? value : JSON.stringify(value, null, 2)}</pre>;
}

function ExchangeCard({ e, open }: { e: Exchange; open: boolean }) {
  return (
    <details className={e.ok ? "exchange" : "exchange failed"} open={open}>
      <summary>
        <span className="label">
          <strong className={`action ${e.label.action.toLowerCase()}`}>{e.label.action}:</strong>{" "}
          {e.label.subject}
        </span>
        <span className="ms">{e.ms} ms</span>
      </summary>

      <div className="steps">
        <div className="step">
          <h4>Sent to the server</h4>
          <Json value={e.requestBody} empty="Nothing. The browser just asked for the list." />
        </div>

        <div className="step">
          <h4>{e.ok ? "Received from the server" : "The server said no"}</h4>
          <Json value={e.responseBody} empty="Nothing. The server just confirmed it worked." />
        </div>
      </div>
    </details>
  );
}

type Props = {
  exchanges: Exchange[];
  polling: boolean;
  setPolling: (v: boolean) => void;
  showBackground: boolean;
  setShowBackground: (v: boolean) => void;
  onClear: () => void;
};

export default function RequestInspector(p: Props) {
  return (
    <aside className="inspector">
      <div className="inspector-head">
        <h2>Under the hood</h2>
        <button onClick={p.onClear}>Clear</button>
      </div>
      <div className="toggles">
        <label>
          <input type="checkbox" checked={p.polling} onChange={(e) => p.setPolling(e.target.checked)} />
          Auto-refresh every 5s
        </label>
        <label>
          <input
            type="checkbox"
            checked={p.showBackground}
            onChange={(e) => p.setShowBackground(e.target.checked)}
          />
          Show auto-refreshes
        </label>
      </div>

      {p.exchanges.length === 0 ? (
        <p className="muted">Do something on the board to see what travels to the server and back.</p>
      ) : (
        p.exchanges.map((e, i) => <ExchangeCard key={e.id} e={e} open={i === 0} />)
      )}
    </aside>
  );
}
