import type { Task } from '../api/client';

interface Props {
  tasks: Task[];
}

/**
 * Returns today's date as an ISO 8601 string (YYYY-MM-DD).
 *
 * Uses lexicographic ISO comparison — not Date subtraction — to avoid
 * UTC-midnight parse ambiguity (design decision #3).
 */
function todayISO(): string {
  return new Date().toISOString().split('T')[0];
}

/**
 * A task is overdue when:
 *   - due_date is not null
 *   - due_date < today (lexicographic ISO compare)
 *   - status is not 'done'
 */
function isOverdue(task: Task): boolean {
  return (
    task.due_date !== null &&
    task.due_date < todayISO() &&
    task.status !== 'done'
  );
}

export function TaskList({ tasks }: Props) {
  if (tasks.length === 0) {
    return (
      <p
        style={{ color: 'var(--color-ink-muted)', fontSize: 'var(--font-size-sm)' }}
        data-testid="task-list-empty"
      >
        No tasks yet.
      </p>
    );
  }

  return (
    <ul className="task-list" data-testid="task-list">
      {tasks.map((task) => {
        const overdue = isOverdue(task);
        return (
          <li key={task.id} className="task-item" data-testid="task-item">
            <div className="task-item__header">
              <span className="task-item__title">{task.title}</span>
              {overdue && (
                <span className="badge-overdue" data-testid="badge-overdue" role="status">
                  Overdue
                </span>
              )}
            </div>

            {task.description && (
              <p className="task-item__description">{task.description}</p>
            )}

            {task.due_date && (
              <p className="task-item__meta" data-testid="task-due-date-display">
                Due: {new Date(`${task.due_date}T12:00:00`).toLocaleDateString()}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
