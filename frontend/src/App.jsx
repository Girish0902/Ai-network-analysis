import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./lib/auth.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import CaseWorkspace from "./pages/CaseWorkspace.jsx";
import AdminApprovals from "./pages/AdminApprovals.jsx";
import AppShell from "./components/AppShell.jsx";

function Protected({ children }) {
  const { token, loading } = useAuth();
  if (loading) return <FullPageLoader />;
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

function GuestOnly({ children }) {
  const { token, loading } = useAuth();
  if (loading) return <FullPageLoader />;
  if (token) return <Navigate to="/" replace />;
  return children;
}

function FullPageLoader() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4">
      <Spinner size="lg" />
      <p className="text-sm text-slate-400">Loading secure session&hellip;</p>
    </div>
  );
}

export function Spinner({ size = "md" }) {
  const dim = size === "lg" ? "h-8 w-8" : size === "sm" ? "h-4 w-4" : "h-5 w-5";
  return (
    <span
      className={`inline-block ${dim} border-2 border-slate-600 border-t-sky-400 rounded-full animate-spin`}
    />
  );
}

export function RequireRole({ role, children }) {
  const { user } = useAuth();
  if (user?.role !== role) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const { token } = useAuth();
  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<GuestOnly><AuthPage mode="login" /></GuestOnly>} />
        <Route path="/signup" element={<GuestOnly><AuthPage mode="signup" /></GuestOnly>} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Protected><Dashboard /></Protected>} />
        <Route path="/cases/:caseId" element={<Protected><CaseWorkspace /></Protected>} />
        <Route
          path="/admin/approvals"
          element={<Protected><RequireRole role="ADMIN"><AdminApprovals /></RequireRole></Protected>}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}