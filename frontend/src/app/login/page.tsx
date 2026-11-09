"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { useAuth } from "@/context/AuthContext";
import {
  Clapperboard,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ShieldCheck,
} from "lucide-react";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect") || "/discover";
  const justRegistered = searchParams.get("registered") === "true";
  const prefillEmail = searchParams.get("email") || "";

  const { login } = useAuth();

  const [username, setUsername] = useState(prefillEmail);
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(
    justRegistered ? "Account created successfully! Please sign in." : null
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const cleanUsername = username.trim();
    if (!cleanUsername) {
      setErrorMessage("Please enter your email or username.");
      return;
    }
    if (!password) {
      setErrorMessage("Please enter your password.");
      return;
    }

    setIsLoading(true);

    try {
      await login({
        username: cleanUsername,
        password,
      });

      setSuccessMessage("Authenticated successfully! Redirecting...");
      setTimeout(() => {
        router.push(redirectUrl);
      }, 400);
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Authentication failed. Please verify your credentials."
      );
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2.5 p-2 rounded-2xl bg-white/5 border border-white/10 hover:border-purple-500/40 transition-all mb-4 group"
        >
          <div className="p-2 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 shadow-md shadow-purple-600/30 group-hover:scale-105 transition-transform">
            <Clapperboard className="size-5 text-white" />
          </div>
          <span className="font-extrabold text-base tracking-tight text-white pr-2">
            CineSync <span className="text-purple-400 font-mono text-xs">OTT</span>
          </span>
        </Link>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          Welcome back
        </h1>
        <p className="text-sm text-zinc-400 mt-2">
          Sign in to access synchronized streaming catalogs and custom preferences.
        </p>
      </div>

      {/* Card Form */}
      <div className="relative rounded-2xl bg-zinc-900/80 border border-white/10 p-6 sm:p-8 backdrop-blur-xl shadow-2xl shadow-black/60">
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 w-48 h-20 bg-purple-500/10 blur-2xl rounded-full pointer-events-none" />

        {/* Alerts */}
        {errorMessage && (
          <div className="mb-5 p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs sm:text-sm flex items-start gap-2.5 animate-in fade-in">
            <AlertCircle className="size-4 text-red-400 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium leading-relaxed">{errorMessage}</div>
          </div>
        )}

        {successMessage && (
          <div className="mb-5 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs sm:text-sm flex items-start gap-2.5 animate-in fade-in">
            <CheckCircle2 className="size-4 text-emerald-400 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium leading-relaxed">{successMessage}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Username / Email */}
          <div>
            <label className="block text-xs font-semibold text-zinc-300 mb-1.5">
              Email or Username
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-500">
                <Mail className="size-4" />
              </div>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="you@example.com or username"
                required
                disabled={isLoading}
                autoComplete="username"
                className="w-full pl-10 pr-3.5 py-2.5 bg-zinc-950/70 border border-white/10 rounded-xl text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500/70 focus:ring-1 focus:ring-purple-500/50 transition-all disabled:opacity-50"
              />
            </div>
          </div>

          {/* Password */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-zinc-300">
                Password
              </label>
              <span className="text-[11px] text-zinc-500">
                Encrypted via OAuth2 Bearer
              </span>
            </div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-500">
                <Lock className="size-4" />
              </div>
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={isLoading}
                autoComplete="current-password"
                className="w-full pl-10 pr-10 py-2.5 bg-zinc-950/70 border border-white/10 rounded-xl text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500/70 focus:ring-1 focus:ring-purple-500/50 transition-all disabled:opacity-50 font-mono tracking-tight"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-zinc-400 hover:text-white transition-colors"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-2 py-3 px-4 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 hover:from-purple-500 hover:to-indigo-500 active:scale-[0.99] transition-all shadow-lg shadow-purple-600/30 flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
          >
            {isLoading ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                <span>Signing In...</span>
              </>
            ) : (
              <>
                <span>Sign In to CineSync</span>
                <ArrowRight className="size-4" />
              </>
            )}
          </button>
        </form>

        {/* Security badge */}
        <div className="mt-6 pt-5 border-t border-white/5 flex items-center justify-center gap-2 text-zinc-500 text-xs">
          <ShieldCheck className="size-4 text-emerald-400" />
          <span>Stateless JWT authentication with secure HttpOnly cookie persistence</span>
        </div>
      </div>

      {/* Switch to Register */}
      <div className="mt-6 text-center text-sm text-zinc-400">
        Don&apos;t have an account yet?{" "}
        <Link
          href={`/register?redirect=${encodeURIComponent(redirectUrl)}`}
          className="text-purple-400 hover:text-purple-300 font-semibold underline underline-offset-4 transition-colors"
        >
          Create account here
        </Link>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-screen flex flex-col bg-zinc-950 text-white selection:bg-purple-600 selection:text-white">
      <Navbar />

      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 py-12 relative overflow-hidden">
        {/* Ambient glow backgrounds */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-purple-600/10 blur-[140px] pointer-events-none rounded-full" />
        <div className="absolute bottom-10 right-10 w-96 h-96 bg-indigo-600/5 blur-[120px] pointer-events-none rounded-full" />

        <Suspense
          fallback={
            <div className="flex items-center justify-center py-20 text-zinc-500">
              <Loader2 className="size-6 animate-spin text-purple-400" />
            </div>
          }
        >
          <LoginForm />
        </Suspense>
      </main>

      <Footer />
    </div>
  );
}

