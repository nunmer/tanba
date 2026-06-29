"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

import * as apiClient from "./api";

interface AuthState {
  ready: boolean;
  authed: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(Boolean(apiClient.getAccess()));
    setReady(true);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await apiClient.login(email, password);
    setAuthed(true);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    await apiClient.register(email, password);
    setAuthed(true);
  }, []);

  const logout = useCallback(() => {
    apiClient.clearTokens();
    setAuthed(false);
  }, []);

  return (
    <AuthContext.Provider value={{ ready, authed, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

/** Redirect to /login once we know the user is unauthenticated. */
export function useRequireAuth(): boolean {
  const { ready, authed } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (ready && !authed) router.replace("/login");
  }, [ready, authed, router]);
  return ready && authed;
}
