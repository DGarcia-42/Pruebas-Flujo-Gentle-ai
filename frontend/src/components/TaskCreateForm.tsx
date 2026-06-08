import { useState } from 'react';
import type { FormEvent } from 'react';
import { createTask } from '../api/client';
import type { ApiError } from '../api/client';

interface Props {
  /** Called after a task is successfully created. */
  onTaskCreated: () => void;
}

export function TaskCreateForm({ onTaskCreated }: Props) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErrorMsg(null);
    setLoading(true);

    try {
      await createTask({
        title,
        ...(description ? { description } : {}),
        ...(dueDate ? { due_date: dueDate } : {}),
      });

      // Clear fields on success
      setTitle('');
      setDescription('');
      setDueDate('');

      onTaskCreated();
    } catch (err) {
      const apiErr = err as ApiError;
      setErrorMsg(apiErr.detail ?? 'Failed to create task');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="profile-card" aria-label="Create a task" style={{ marginBottom: 'var(--space-6)' }}>
      <h2 className="profile-card__heading">New task</h2>

      <form onSubmit={handleSubmit} noValidate>
        <div className="form-group">
          <label htmlFor="task-title-input" className="form-label">
            Title <span aria-hidden="true">*</span>
          </label>
          <input
            id="task-title-input"
            data-testid="task-title"
            type="text"
            className="form-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            disabled={loading}
            placeholder="Task title"
          />
        </div>

        <div className="form-group">
          <label htmlFor="task-description-input" className="form-label">
            Description
          </label>
          <input
            id="task-description-input"
            data-testid="task-description"
            type="text"
            className="form-input"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={loading}
            placeholder="Optional description"
          />
        </div>

        <div className="form-group">
          <label htmlFor="task-due-date-input" className="form-label">
            Due date
          </label>
          <input
            id="task-due-date-input"
            data-testid="task-due-date"
            type="date"
            className="form-input"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            disabled={loading}
          />
        </div>

        {errorMsg && (
          <p data-testid="task-error" className="message-error">
            {errorMsg}
          </p>
        )}

        <button
          type="submit"
          data-testid="task-submit"
          className="btn-primary"
          disabled={loading || !title.trim()}
        >
          {loading ? 'Creating…' : 'Create task'}
        </button>
      </form>
    </section>
  );
}
