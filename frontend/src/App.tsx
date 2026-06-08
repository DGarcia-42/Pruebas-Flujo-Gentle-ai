import { useState } from 'react';
import { getToken, clearToken } from './auth/storage';
import { RegisterForm } from './components/RegisterForm';
import { LoginForm } from './components/LoginForm';
import { Profile } from './components/Profile';
import { TasksView } from './components/TasksView';

/**
 * Possible application views.
 *
 * - "register": unauthenticated, showing the registration form
 * - "login":    unauthenticated, showing the login form
 * - "app":      authenticated (token is present in storage)
 * - "tasks":    task list + creation form (no auth required)
 */
type View = 'register' | 'login' | 'app' | 'tasks';

function resolveInitialView(): View {
  return getToken() ? 'app' : 'login';
}

function App() {
  const [view, setView] = useState<View>(resolveInitialView);

  if (view === 'register') {
    return (
      <RegisterForm
        onSuccess={() => setView('login')}
      />
    );
  }

  if (view === 'tasks') {
    return <TasksView onBack={() => setView(getToken() ? 'app' : 'login')} />;
  }

  if (view === 'login') {
    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', padding: 'var(--space-3) var(--space-6)' }}>
          <button
            type="button"
            className="topbar-action"
            data-testid="nav-tasks"
            onClick={() => setView('tasks')}
          >
            Tasks
          </button>
        </div>
        <LoginForm
          onSuccess={() => setView('app')}
          onGoToRegister={() => setView('register')}
        />
      </div>
    );
  }

  // "app" view — authenticated area with Profile + ChangePasswordForm.
  return (
    <Profile
      onLogout={() => {
        clearToken();
        setView('login');
      }}
      onGoToTasks={() => setView('tasks')}
    />
  );
}

export default App;
