import { useState } from 'react';
import { getToken } from './auth/storage';
import { RegisterForm } from './components/RegisterForm';
import { LoginForm } from './components/LoginForm';

/**
 * Possible application views.
 *
 * - "register": unauthenticated, showing the registration form
 * - "login":    unauthenticated, showing the login form
 * - "app":      authenticated (token is present in storage)
 *
 * PR3 will replace the "app" branch with the real Profile screen.
 */
type View = 'register' | 'login' | 'app';

function resolveInitialView(): View {
  // If a token is already in memory (e.g., from a same-session navigation),
  // start directly in the authenticated area.
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

  if (view === 'login') {
    return (
      <LoginForm
        onSuccess={() => setView('app')}
        onGoToRegister={() => setView('register')}
      />
    );
  }

  // "app" view — authenticated area placeholder.
  // The real Profile screen (GET /api/auth/me) will be wired in PR3.
  return (
    <div className="app-shell">
      <header className="app-topbar">
        <span className="app-topbar__title">Perfil Usuario</span>
      </header>
      <main className="app-content" data-testid="authenticated-area">
        <p>Logged in. Profile screen coming in PR3.</p>
      </main>
    </div>
  );
}

export default App;
