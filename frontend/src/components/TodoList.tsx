import { Todo } from "../api";
import TodoItem from "./TodoItem";

type Props = {
  todos: Todo[];
  onToggle: (t: Todo) => void;
  onRename: (t: Todo, title: string) => void;
  onDelete: (t: Todo) => void;
};

export default function TodoList({ todos, onToggle, onRename, onDelete }: Props) {
  if (todos.length === 0) {
    return <p className="muted empty">The board is empty. Add the first to-do!</p>;
  }
  return (
    <ul className="todos">
      {todos.map((t) => (
        <TodoItem key={t.id} todo={t} onToggle={onToggle} onRename={onRename} onDelete={onDelete} />
      ))}
    </ul>
  );
}
