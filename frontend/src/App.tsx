import { useState } from 'react';
import { getToken, clearToken } from './auth/storage';
import { RegisterForm } from './components/RegisterForm';
import { LoginForm } from './components/LoginForm';
import { Profile } from './components/Profile';

/**
 * Possible application views.
 *
 * - "register": unauthenticated, showing the registration form
 * - "login":    unauthenticated, showing the login form
 * - "app":      authenticated (token is present in storage)
 */
type View = 'register' | 'login' | 'app';

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

  if (view === 'login') {
    return (
      <LoginForm
        onSuccess={() => setView('app')}
        onGoToRegister={() => setView('register')}
      />
    );
  }

  // "app" view — authenticated area with Profile + ChangePasswordForm.
  return (
    <Profile
      onLogout={() => {
        clearToken();
        setView('login');
      }}
    />
  );
}

export default App;
