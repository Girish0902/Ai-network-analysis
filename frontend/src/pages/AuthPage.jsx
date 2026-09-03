import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth.jsx";
import { useToast, errorMessage } from "../lib/toast.jsx";
import { Button, Input } from "../components/ui.jsx";
import { Spinner } from "../App.jsx";

const USERNAME_PATTERN = "^[a-zA-Z0-9_.-]+$";

export default function AuthPage({ mode }) {
  const { login, signup } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();
  const isLogin = mode === "login";

  const [form, setForm] = useState({
    username_or_email: "",
    password: "",
    username: "",
    email: "",
    badge_number: "",
    confirm: "",
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  function setField(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((e) => ({ ...e, [key]: undefined }));
  }

  function validate() {
    const next = {};
    if (isLogin) {
      if (form.username_or_email.trim().length < 3)
        next.username_or_email = "Enter your username or email (at least 3 characters).";
      if (!form.password) next.password = "Enter your password.";
    } else {
      const username = form.username.trim();
      if (username.length < 3 || !new RegExp(USERNAME_PATTERN).test(username))
        next.username = "Username must be 3+ characters using letters, digits, dot, dash or underscore.";
      const email = form.email.trim();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) next.email = "Enter a valid email address, e.g. name@police.in.";
      if (form.badge_number.trim().length < 3) next.badge_number = "Enter your official badge number (3+ characters).";
      if (form.password.length < 8) next.password = "Password must be at least 8 characters.";
      if (form.confirm !== form.password) next.confirm = "Passwords do not match.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      if (isLogin) {
        await login(form.username_or_email.trim(), form.password);
        push("Signed in successfully.", "success");
      } else {
        await signup({
          username: form.username.trim(),
          email: form.email.trim(),
          password: form.password,
          badge_number: form.badge_number.trim(),
        });
        push("Account created. Welcome, investigator.", "success");
      }
      navigate("/", { replace: true });
    } catch (error) {
      push(errorMessage(error), "error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-stretch">
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between bg-gradient-to-br from-slate-950 via-indigo-950 to-sky-950 p-10">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center text-xl font-bold text-white shadow-lg">
            AI
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-100">Investigation Intelligence Platform</p>
            <p className="text-xs text-slate-400">Collect &middot; Organize &middot; Connect &middot; Explore &middot; Explain &middot; Report</p>
          </div>
        </div>
        <div className="space-y-6">
          <p className="text-3xl font-bold leading-tight text-slate-100">
            Evidence-grounding investigation for authorized criminal-justice teams.
          </p>
          <ul className="space-y-3 text-sm text-slate-300">
            <li className="flex gap-3 items-start">
              <span className="mt-1 h-1.5 w-1.5 rounded-full bg-sky-400 shrink-0" />
              Secure ingestion with SHA-256 fingerprinting and an immutable, tamper-evident audit trail.
            </li>
            <li className="flex gap-3 items-start">
              <span className="mt-1 h-1.5 w-1.5 rounded-full bg-sky-400 shrink-0" />
              Role-based access control with case-level authorization approvals.
            </li>
            <li className="flex gap-3 items-start">
              <span className="mt-1 h-1.5 w-1.5 rounded-full bg-sky-400 shrink-0" />
              Document routing and evidence processing into a schema-versioned, provenance-bound payload.
            </li>
          </ul>
        </div>
        <p className="text-[11px] text-slate-500">
          Prototype workspace &middot; do not upload real, sensitive or classified data during demonstration.
        </p>
      </div>

      <div className="flex-1 flex items-center justify-center bg-slate-950 px-4 py-10">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-6 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center text-xl font-bold text-white">
              AI
            </div>
            <p className="text-lg font-semibold">Investigation Intelligence</p>
          </div>

          <h1 className="text-2xl font-bold text-slate-100">
            {isLogin ? "Sign in to your workspace" : "Create an investigator account"}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {isLogin
              ? "Use your official username or email."
              : "A default INVESTIGATOR role is created. Administrators cannot self-register."}
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            {isLogin ? (
              <>
                <Input
                  label="Username or email"
                  placeholder="inv_ravi"
                  autoComplete="username"
                  value={form.username_or_email}
                  onChange={(e) => setField("username_or_email", e.target.value)}
                  error={errors.username_or_email}
                />
                <Input
                  label="Password"
                  type="password"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  value={form.password}
                  onChange={(e) => setField("password", e.target.value)}
                  error={errors.password}
                />
              </>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Username"
                    placeholder="inv_ravi"
                    autoComplete="username"
                    value={form.username}
                    onChange={(e) => setField("username", e.target.value)}
                    error={errors.username}
                  />
                  <Input
                    label="Badge number"
                    placeholder="2026-CID-01842"
                    autoComplete="off"
                    value={form.badge_number}
                    onChange={(e) => setField("badge_number", e.target.value)}
                    error={errors.badge_number}
                  />
                </div>
                <Input
                  label="Official email"
                  type="email"
                  placeholder="ravi@police.in"
                  autoComplete="email"
                  value={form.email}
                  onChange={(e) => setField("email", e.target.value)}
                  error={errors.email}
                />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Password"
                    type="password"
                    placeholder="Minimum 8 characters"
                    autoComplete="new-password"
                    value={form.password}
                    onChange={(e) => setField("password", e.target.value)}
                    error={errors.password}
                  />
                  <Input
                    label="Confirm password"
                    type="password"
                    placeholder="Repeat password"
                    autoComplete="new-password"
                    value={form.confirm}
                    onChange={(e) => setField("confirm", e.target.value)}
                    error={errors.confirm}
                  />
                </div>
              </>
            )}

            <Button type="submit" size="lg" className="w-full" disabled={submitting}>
              {submitting && <Spinner size="sm" />}
              {isLogin ? "Sign in" : "Create account"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-400">
            {isLogin ? (
              <>
                No account yet?{" "}
                <Link to="/signup" className="font-semibold text-sky-400 hover:text-sky-300">
                  Register as investigator
                </Link>
              </>
            ) : (
              <>
                Already registered?{" "}
                <Link to="/login" className="font-semibold text-sky-400 hover:text-sky-300">
                  Sign in
                </Link>
              </>
            )}
          </p>

          <div className="mt-8 rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-xs text-slate-400">
            <p className="font-medium text-slate-300 mb-1">Demo credentials</p>
            <p>
              Admin &mdash; <code className="text-sky-300">superadmin</code> (password from backend{" "}
              <code className="text-slate-300">.env</code>, seeded <code className="text-slate-300">ADMIN_PASSWORD</code>).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}