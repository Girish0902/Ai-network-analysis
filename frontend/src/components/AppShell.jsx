import { NavLink, useNavigate } from "react-router-dom";
import { useAuth, isAdmin } from "../lib/auth.jsx";
import { formatDate } from "../lib/format.js";

const navLinkClass = ({ isActive }) =>
  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    isActive
      ? "bg-sky-500/10 text-sky-300 ring-1 ring-inset ring-sky-500/30"
      : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
  }`;

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  const admin = isAdmin(user);

  return (
    <div className="min-h-screen flex">
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-950/60">
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center text-lg font-bold text-white shadow">
              AI
            </div>
            <div className="leading-tight">
              <p className="text-sm font-semibold text-slate-100">Investigation</p>
              <p className="text-[11px] text-slate-500">Intelligence Platform</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          <NavLink to="/" end className={navLinkClass}>
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
            </svg>
            Dashboard
          </NavLink>
          {admin && (
            <NavLink to="/admin/approvals" className={navLinkClass}>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Access Approvals
            </NavLink>
          )}
        </nav>
        <div className="border-t border-slate-800 px-5 py-4">
          <div className="mb-3">
            <p className="text-sm font-medium text-slate-200 truncate">{user?.username}</p>
            <p className="text-xs text-slate-500 truncate">
              {user?.badge_number} &middot; {user?.role}
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="w-full rounded-lg border border-slate-700 px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 transition-colors"
          >
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex-1 flex min-w-0 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-slate-800 bg-slate-950/40 px-4 md:px-8 py-3 backdrop-blur">
          <div className="flex items-center gap-3 md:hidden">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center text-sm font-bold text-white">
              AI
            </div>
            <p className="text-sm font-semibold">Investigation</p>
          </div>
          <div className="hidden md:flex items-center gap-2 text-xs text-slate-500">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
            </svg>
            Secure workspace &middot; authenticated session
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300 ring-1 ring-inset ring-emerald-500/20">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Connected
            </span>
            <button
              onClick={handleLogout}
              className="md:hidden rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800"
            >
              Sign out
            </button>
          </div>
        </header>

        <main className="flex-1 px-4 md:px-8 py-6 md:py-8 overflow-y-auto">{children}</main>

        <footer className="border-t border-slate-800/70 px-4 md:px-8 py-3 text-[11px] text-slate-600">
          AI-Assisted Criminal Investigation &amp; Intelligence Platform &middot; Authorization-based access only. Joined{" "}
          {formatDate(user?.created_at)}.
        </footer>
      </div>
    </div>
  );
}