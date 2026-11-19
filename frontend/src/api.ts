// A thin wrapper around fetch() that also records every request/response
// so the "Under the hood" panel can show students what actually happened.

export type Todo = {
  id: number;
  title: string;
  done: boolean;
  author: string | null;
  created_at: string;
  updated_at: string;
};

type Method = "GET" | "POST" | "PATCH" | "DELETE";

// What the student did, in plain words, e.g. { action: "Create", subject: "Do Dishes" }
export type Label = { action: string; subject: string };

export type Exchange = {
  id: number;
  label: Label;
  requestBody?: unknown;
  ok: boolean;
  responseBody?: unknown;
  ms: number;
  background: boolean; // automatic refresh, not a click
};

type Listener = (e: Exchange) => void;
const listeners = new Set<Listener>();
let nextId = 1;

export function onExchange(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

async function request<T>(
  method: Method,
  url: string,
  label: Label,
  body?: unknown,
  background = false,
): Promise<T> {
  const started = performance.now();
  let ok = false;
  let responseBody: unknown;

  try {
    const res = await fetch(url, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    ok = res.ok;
    const text = await res.text();
    try {
      responseBody = text ? JSON.parse(text) : undefined;
    } catch {
      responseBody = text;
    }
  } catch {
    responseBody = { error: "Couldn't reach the server" };
  }

  const exchange: Exchange = {
    id: nextId++,
    label,
    requestBody: body,
    ok,
    responseBody,
    ms: Math.round(performance.now() - started),
    background,
  };
  listeners.forEach((fn) => fn(exchange));

  if (!ok) {
    throw new Error((responseBody as { error?: string } | undefined)?.error ?? "Something went wrong");
  }
  return responseBody as T;
}

export const api = {
  list: (background = false) =>
    request<Todo[]>("GET", "/api/todos", { action: "Load", subject: "the to-do list" }, undefined, background),

  create: (title: string, author: string) =>
    request<Todo>("POST", "/api/todos", { action: "Create", subject: title.trim() }, {
      title,
      author: author || undefined,
    }),

  rename: (todo: Todo, title: string) =>
    request<Todo>("PATCH", `/api/todos/${todo.id}`, { action: "Edit", subject: `${todo.title} to ${title.trim()}` }, {
      title,
    }),

  toggle: (todo: Todo) =>
    request<Todo>("PATCH", `/api/todos/${todo.id}`, { action: "Update", subject: todo.title }, {
      done: !todo.done,
    }),

  remove: (todo: Todo) =>
    request<void>("DELETE", `/api/todos/${todo.id}`, { action: "Remove", subject: todo.title }),
};
