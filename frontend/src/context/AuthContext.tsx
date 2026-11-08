"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
} from "react";
import { authService, type LoginPayload, type RegisterPayload } from "@/lib/services/auth";
import type { User } from "@/types";

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize session on mount by checking HttpOnly cookie bridge
  useEffect(() => {
    let isMounted = true;

    async function initAuth() {
      try {
        const savedToken = await authService.getSessionToken();
        if (!savedToken) {
          if (isMounted) {
            setUser(null);
            setToken(null);
            setIsLoading(false);
          }
          return;
        }

        if (isMounted) {
          setToken(savedToken);
        }

        try {
          const profile = await authService.getCurrentUser(savedToken);
          if (isMounted) {
            setUser(profile);
          }
        } catch {
          // Token expired or invalid
          if (isMounted) {
            setUser(null);
            setToken(null);
          }
          await authService.logout();
        }
      } catch {
        if (isMounted) {
          setUser(null);
          setToken(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    initAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    setIsLoading(true);
    try {
      const result = await authService.login(payload);
      setUser(result.user);
      setToken(result.tokens.access_token);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    return await authService.register(payload);
  }, []);

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await authService.logout();
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    if (!token) return;
    try {
      const profile = await authService.getCurrentUser(token);
      setUser(profile);
    } catch {
      // Session invalid
      setUser(null);
      setToken(null);
    }
  }, [token]);

  const value = useMemo(
    () => ({
      user,
      token,
      isAuthenticated: !!user,
      isLoading,
      login,
      register,
      logout,
      refreshProfile,
    }),
    [user, token, isLoading, login, register, logout, refreshProfile]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

