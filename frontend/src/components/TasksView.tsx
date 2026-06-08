import { useState, useEffect } from 'react';
import { listTasks } from '../api/client';
import type { Task, ApiError } from '../api/client';
import { TaskCreateForm } from './TaskCreateForm';
import { TaskList } from './TaskList';

/**
 * Container component for the tasks view.
 *
 * - Fetches the task list on mount via GET /api/tasks.
 * - Re-fetches after a task is successfully created (no manual reload).
 * - Passes tasks down to TaskList (presentational).
 * - Passes onTaskCreated callback down to TaskCreateForm.
 */
export function TasksView() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  function fetchTasks() {
    setLoadError(null);
    listTasks()
      .then((data) => {
        if (data) setTasks(data);
      })
      .catch((err: ApiError) => {
        setLoadError(err.detail ?? 'Failed to load tasks');
      });
  }

  useEffect(() => {
    fetchTasks();
  }, []);

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <span className="app-topbar__title">Tasks</span>
      </header>

      <main className="app-content">
        <TaskCreateForm onTaskCreated={fetchTasks} />

        {loadError ? (
          <p className="message-error" data-testid="tasks-load-error">
            {loadError}
          </p>
        ) : (
          <TaskList tasks={tasks} />
        )}
      </main>
    </div>
  );
}
