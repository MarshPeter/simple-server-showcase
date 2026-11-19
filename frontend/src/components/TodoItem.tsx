import { FormEvent, useState } from "react";
import { Todo } from "../api";

type Props = {
  todo: Todo;
  onToggle: (t: Todo) => void;
  onRename: (t: Todo, title: string) => void;
  onDelete: (t: Todo) => void;
};

export default function TodoItem({ todo, onToggle, onRename, onDelete }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(todo.title);

  const save = (e: FormEvent) => {
    e.preventDefault();
    setEditing(false);
    if (draft.trim() && draft.trim() !== todo.title) onRename(todo, draft);
  };

  return (
    <li className={todo.done ? "todo done" : "todo"}>
      <input
        type="checkbox"
        checked={todo.done}
        aria-label={todo.done ? "Mark not done" : "Mark done"}
        onChange={() => onToggle(todo)}
      />

      {editing ? (
        <form className="edit" onSubmit={save}>
          <input autoFocus value={draft} maxLength={200} onChange={(e) => setDraft(e.target.value)} onBlur={save} />
        </form>
      ) : (
        <div className="text">
          <span className="title">{todo.title}</span>
          <span className="meta">
            #{todo.id}
            {todo.author ? ` · by ${todo.author}` : ""}
          </span>
        </div>
      )}

      <div className="actions">
        <button
          onClick={() => {
            setDraft(todo.title);
            setEditing(true);
          }}
          title="Update the title"
        >
          Edit
        </button>
        <button onClick={() => onDelete(todo)} title="Delete this to-do">
          Delete
        </button>
      </div>
    </li>
  );
}
