import { useCallback, useEffect, useState } from "react";
import { api, Exchange, onExchange, Todo } from "./api";
import AddTodo from "./components/AddTodo";
import TodoList from "./components/TodoList";
import RequestInspector from "./components/RequestInspector";

const POLL_MS = 5000;

function loadName(): string {
  try {
    return localStorage.getItem("author") ?? "";
  } catch {
    return "";
  }
}

export default function App() {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [author, setAuthor] = useState(loadName);
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [polling, setPolling] = useState(true);
  const [showBackground, setShowBackground] = useState(false);

  // Record every HTTP exchange for the inspector (newest first, keep 50).
  useEffect(() => onExchange((e) => setExchanges((prev) => [e, ...prev].slice(0, 50))), []);

  const refresh = useCallback(async (background = false) => {
    try {
      setTodos(await api.list(background));
      setLoaded(true);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!polling) return;
    const timer = setInterval(() => refresh(true), POLL_MS);
    return () => clearInterval(timer);
  }, [polling, refresh]);

  // Run an action, then re-read the list so everyone sees the server's truth.
  const act = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
    await refresh(true);
  };

  const saveName = (name: string) => {
    setAuthor(name);
    try {
      localStorage.setItem("author", name);
    } catch {
      /* private mode etc. */
    }
  };

  return (
    <div className="layout">
      <main className="board">
        <header>
          <h1>Class To-Do Board</h1>
          <p className="subtitle">
            Everyone in the room shares this list. Every click is an HTTP request to a server, which
            talks to a database.
          </p>
        </header>

        <label className="name">
          Your name
          <input
            value={author}
            maxLength={40}
            placeholder="optional"
            onChange={(e) => saveName(e.target.value)}
          />
        </label>

        <AddTodo onAdd={(title) => act(() => api.create(title, author))} />

        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}

        {!loaded && !error ? (
          <p className="muted">Loading from the server…</p>
        ) : (
          <TodoList
            todos={todos}
            onToggle={(t) => act(() => api.toggle(t))}
            onRename={(t, title) => act(() => api.rename(t, title))}
            onDelete={(t) => act(() => api.remove(t))}
          />
        )}
      </main>

      <RequestInspector
        exchanges={showBackground ? exchanges : exchanges.filter((e) => !e.background)}
        polling={polling}
        setPolling={setPolling}
        showBackground={showBackground}
        setShowBackground={setShowBackground}
        onClear={() => setExchanges([])}
      />
    </div>
  );
}
