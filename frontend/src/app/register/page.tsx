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
  User as UserIcon,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ShieldCheck,
} from "lucide-react";

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect") || "/discover";

  const { register, login } = useAuth();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    // Client-side validations
    const cleanUsername = username.trim();
    const cleanEmail = email.trim().toLowerCase();

    if (!cleanUsername) {
      setErrorMessage("Please enter a username or full name.");
      return;
    }
    if (cleanUsername.length < 2 || cleanUsername.length > 50) {
      setErrorMessage("Username must be between 2 and 50 characters.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!cleanEmail || !emailRegex.test(cleanEmail)) {
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    if (!password) {
      setErrorMessage("Please enter a password.");
      return;
    }
    if (password.length < 8) {
      setErrorMessage("Password must be at least 8 characters long.");
      return;
    }
    if (new TextEncoder().encode(password).length > 72) {
      setErrorMessage("Password cannot exceed 72 bytes.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match. Please verify.");
      return;
    }

    setIsLoading(true);

    try {
      // 1. Call registration endpoint
      await register({
        username: cleanUsername,
        email: cleanEmail,
        password,
      });

      setSuccessMessage("Account created successfully! Signing you in...");

      // 2. Automatically log the new user in
      try {
        await login({
          username: cleanEmail,
          password,
        });
        router.push(redirectUrl);
      } catch {
        // If auto-login fails, redirect to login page with prefill
        router.push(`/login?registered=true&email=${encodeURIComponent(cleanEmail)}`);
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Registration failed. Please check your information and try again."
      );
    } finally {
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
          Create your account
        </h1>
        <p className="text-sm text-zinc-400 mt-2">
          Join CineSync to explore verified catalogs across all major OTT platforms.
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
          {/* Username */}
          <div>
            <label className="block text-xs font-semibold text-zinc-300 mb-1.5">
              Username or Full Name
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-500">
                <UserIcon className="size-4" />
              </div>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. Alex Rivera"
                required
                disabled={isLoading}
                autoComplete="name"
                className="w-full pl-10 pr-3.5 py-2.5 bg-zinc-950/70 border border-white/10 rounded-xl text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500/70 focus:ring-1 focus:ring-purple-500/50 transition-all disabled:opacity-50"
              />
            </div>
          </div>

          {/* Email */}
          <div>
            <label className="block text-xs font-semibold text-zinc-300 mb-1.5">
              Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-500">
                <Mail className="size-4" />
              </div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                disabled={isLoading}
                autoComplete="email"
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
              <span className="text-[11px] text-zinc-500 font-mono">Min. 8 characters</span>
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
                autoComplete="new-password"
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

          {/* Confirm Password */}
          <div>
            <label className="block text-xs font-semibold text-zinc-300 mb-1.5">
              Confirm Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-500">
                <Lock className="size-4" />
              </div>
              <input
                type={showConfirmPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={isLoading}
                autoComplete="new-password"
                className="w-full pl-10 pr-10 py-2.5 bg-zinc-950/70 border border-white/10 rounded-xl text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500/70 focus:ring-1 focus:ring-purple-500/50 transition-all disabled:opacity-50 font-mono tracking-tight"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-zinc-400 hover:text-white transition-colors"
                aria-label={showConfirmPassword ? "Hide confirmed password" : "Show confirmed password"}
              >
                {showConfirmPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
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
                <span>Creating Account...</span>
              </>
            ) : (
              <>
                <span>Complete Registration</span>
                <ArrowRight className="size-4" />
              </>
            )}
          </button>
        </form>

        {/* Security badge */}
        <div className="mt-6 pt-5 border-t border-white/5 flex items-center justify-center gap-2 text-zinc-500 text-xs">
          <ShieldCheck className="size-4 text-emerald-400" />
          <span>Passkeys & passwords secured with Argon2 / bcrypt encryption</span>
        </div>
      </div>

      {/* Switch to Login */}
      <div className="mt-6 text-center text-sm text-zinc-400">
        Already have a CineSync account?{" "}
        <Link
          href={`/login?redirect=${encodeURIComponent(redirectUrl)}`}
          className="text-purple-400 hover:text-purple-300 font-semibold underline underline-offset-4 transition-colors"
        >
          Sign in here
        </Link>
      </div>
    </div>
  );
}

export default function RegisterPage() {
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
          <RegisterForm />
        </Suspense>
      </main>

      <Footer />
    </div>
  );
}

