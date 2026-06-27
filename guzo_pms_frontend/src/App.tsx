import { useEffect, useState, type ReactNode } from "react";
import {
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import PmsShell from "./layout/PmsShell";
import LoginPage from "./auth/LoginPage";
import { canAccessPath, getDefaultPath } from "./auth/accessControl";
import {
  clearStoredSession,
  loadStoredSession,
  saveStoredSession,
} from "./auth/sessionStorage";
import { pmsCompatibilityRoutes, pmsWorkflowRoutes } from "./routes/pmsRoutes";
import { fetchCurrentUser, logoutPmsUser } from "./services/authService";
import { DEV_AUTH_FALLBACK } from "./config/pms";
import type { UserSession } from "./types/pms";

function LoginRoute({
  session,
  onLogin,
}: {
  session: UserSession | null;
  onLogin: (session: UserSession) => void;
}) {
  const navigate = useNavigate();

  if (session) {
    return <Navigate to={getDefaultPath(session)} replace />;
  }

  function handleLogin(nextSession: UserSession) {
    onLogin(nextSession);
    navigate(getDefaultPath(nextSession), { replace: true });
  }

  return <LoginPage onLogin={handleLogin} />;
}

function ProtectedRoute({
  session,
  children,
}: {
  session: UserSession | null;
  children: ReactNode;
}) {
  const location = useLocation();

  if (!session) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (!canAccessPath(session, location.pathname)) {
    return <Navigate to={getDefaultPath(session)} replace />;
  }

  return <>{children}</>;
}

export default function App() {
  const [session, setSession] = useState<UserSession | null>(() =>
    loadStoredSession()
  );

  useEffect(() => {
    let cancelled = false;
    async function hydrateAuthenticatedUser() {
      const stored = loadStoredSession();
      if (!stored?.access_token) {
        if (stored && !DEV_AUTH_FALLBACK) {
          clearStoredSession();
          setSession(null);
        }
        return;
      }
      try {
        const user = await fetchCurrentUser();
        if (!cancelled) {
          const nextSession = {
            ...user,
            access_token: stored.access_token,
            expires_at: stored.expires_at,
          };
          saveStoredSession(nextSession);
          setSession(nextSession);
        }
      } catch {
        if (!cancelled) {
          clearStoredSession();
          setSession(null);
        }
      }
    }
    hydrateAuthenticatedUser();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleLogin(nextSession: UserSession) {
    saveStoredSession(nextSession);
    setSession(nextSession);
  }

  async function handleLogout() {
    if (session?.access_token) {
      try {
        await logoutPmsUser();
      } catch {
        // Client-side token clearing is the logout behavior for JWT auth.
      }
    }
    clearStoredSession();
    setSession(null);
  }

  return (
    session ? (
    <PmsShell session={session} onLogout={handleLogout}>
      <Routes>
        <Route
          path="/"
          element={<Navigate to={getDefaultPath(session)} replace />}
        />
        <Route
          path="/login"
          element={<LoginRoute session={session} onLogin={handleLogin} />}
        />
        {[...pmsWorkflowRoutes, ...pmsCompatibilityRoutes].map((route) => (
          <Route
            key={route.path}
            path={route.path}
            element={
              <ProtectedRoute session={session}>{route.element}</ProtectedRoute>
            }
          />
        ))}
        <Route
          path="*"
          element={<Navigate to={getDefaultPath(session)} replace />}
        />
      </Routes>
    </PmsShell>
    ) : (
      <Routes>
        <Route
          path="/login"
          element={<LoginRoute session={session} onLogin={handleLogin} />}
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  );
}
