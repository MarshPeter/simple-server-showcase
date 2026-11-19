import { FormEvent, useState } from "react";

export default function AddTodo({ onAdd }: { onAdd: (title: string) => Promise<void> }) {
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setBusy(true);
    await onAdd(title);
    setTitle("");
    setBusy(false);
  };

  return (
    <form className="add" onSubmit={submit}>
      <input
        value={title}
        maxLength={200}
        placeholder="What needs doing?"
        aria-label="New to-do"
        onChange={(e) => setTitle(e.target.value)}
      />
      <button type="submit" className="primary" disabled={busy || !title.trim()}>
        Add
      </button>
    </form>
  );
}
