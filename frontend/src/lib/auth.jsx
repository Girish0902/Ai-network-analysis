import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch } from "./api.js";

const TOKEN_KEY = "investigation.token";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function hydrate() {
      const stored = localStorage.getItem(TOKEN_KEY);
      if (!stored) {
        setLoading(false);
        return;
      }
      try {
        const me = await apiFetch("/api/v1/auth/me", { token: stored });
        if (!cancelled) {
          setToken(stored);
          setUser(me);
        }
      } catch {
        localStorage.removeItem(TOKEN_KEY);
        if (!cancelled) {
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    hydrate();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = async (usernameOrEmail, password) => {
    const data = await apiFetch("/api/v1/auth/login", {
      method: "POST",
      body: { username_or_email: usernameOrEmail, password },
    });
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setToken(data.access_token);
    const me = await apiFetch("/api/v1/auth/me", { token: data.access_token });
    setUser(me);
    return me;
  };

  const signup = async (payload) => {
    const created = await apiFetch("/api/v1/auth/signup", {
      method: "POST",
      body: payload,
    });
    const data = await apiFetch("/api/v1/auth/login", {
      method: "POST",
      body: { username_or_email: payload.email, password: payload.password },
    });
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setToken(data.access_token);
    setUser(created);
    return created;
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({ token, user, loading, login, signup, logout }),
    [token, user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function isAdmin(user) {
  return user?.role === "ADMIN";
}