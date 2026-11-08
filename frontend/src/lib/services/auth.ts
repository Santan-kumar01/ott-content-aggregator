/**
 * OTT Content Aggregator - Authentication Service
 *
 * Communicates with FastAPI backend auth endpoints:
 * - POST /api/v1/auth/register
 * - POST /api/v1/auth/login (OAuth2 form-encoded)
 * - GET  /api/v1/auth/me (Bearer JWT)
 *
 * Persists JWT securely using Next.js HttpOnly session cookies.
 */

import { api, ApiError } from "@/lib/api";
import type { User, AuthTokens } from "@/types";

export interface RegisterPayload {
  email: string;
  username: string;
  password: string;
}

export interface LoginPayload {
  username: string; // Supports username or email address
  password: string;
}

export interface LoginResult {
  user: User;
  tokens: AuthTokens;
}

export const authService = {
  /**
   * Register a new user account.
   */
  async register(payload: RegisterPayload): Promise<User> {
    const trimmedEmail = payload.email.trim().toLowerCase();
    const trimmedUsername = payload.username.trim();

    if (!trimmedEmail) throw new Error("Email address is required");
    if (!trimmedUsername) throw new Error("Username is required");
    if (!payload.password) throw new Error("Password is required");
    if (payload.password.length < 8) {
      throw new Error("Password must be at least 8 characters");
    }
    if (new TextEncoder().encode(payload.password).length > 72) {
      throw new Error("Password cannot exceed 72 bytes");
    }

    try {
      return await api.post<User>("/api/v1/auth/register", {
        email: trimmedEmail,
        username: trimmedUsername,
        password: payload.password,
      });
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 400 && error.message.toLowerCase().includes("email already registered")) {
          throw new Error("An account with this email address already exists.");
        }
        throw new Error(error.message || "Registration failed. Please check your details.");
      }
      throw new Error("Unable to connect to authentication server. Please ensure the backend is running.");
    }
  },

  /**
   * Log in with email or username and password.
   * On success, sets HttpOnly cookie via /api/auth/session and retrieves current user profile.
   */
  async login(payload: LoginPayload): Promise<LoginResult> {
    const trimmedUsername = payload.username.trim();
    if (!trimmedUsername) throw new Error("Email or username is required");
    if (!payload.password) throw new Error("Password is required");

    const params = new URLSearchParams();
    params.append("username", trimmedUsername);
    params.append("password", payload.password);

    let tokens: AuthTokens;
    try {
      tokens = await api.post<AuthTokens>("/api/v1/auth/login", params);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 401) {
          throw new Error("Incorrect email/username or password. Please try again.");
        }
        if (error.status === 400 && error.message.toLowerCase().includes("inactive")) {
          throw new Error("This account is inactive. Please contact support.");
        }
        throw new Error(error.message || "Authentication failed.");
      }
      throw new Error("Unable to reach authentication service. Please ensure the backend server is running.");
    }

    // Persist token in secure HttpOnly cookie bridge
    try {
      await fetch("/api/auth/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: tokens.access_token }),
      });
    } catch {
      // Session cookie save fallback
    }

    // Fetch user profile
    const user = await this.getCurrentUser(tokens.access_token);

    return { user, tokens };
  },

  /**
   * Retrieve current user profile using JWT token.
   */
  async getCurrentUser(token?: string): Promise<User> {
    try {
      return await api.get<User>("/api/v1/auth/me", {
        token: token ?? null,
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        throw new Error("Session expired or invalid. Please sign in again.");
      }
      throw error;
    }
  },

  /**
   * Read the active session token from the HttpOnly session cookie bridge.
   */
  async getSessionToken(): Promise<string | null> {
    try {
      const response = await fetch("/api/auth/session", { cache: "no-store" });
      if (!response.ok) return null;
      const data = await response.json();
      return data?.token || null;
    } catch {
      return null;
    }
  },

  /**
   * Clear session and log out the user.
   */
  async logout(): Promise<void> {
    try {
      await fetch("/api/auth/session", { method: "DELETE" });
    } catch {
      // Ignored
    }
  },
};

