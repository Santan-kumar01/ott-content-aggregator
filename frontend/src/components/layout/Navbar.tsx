"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Clapperboard,
  Search,
  Mic,
  Menu,
  X,
  ArrowRight,
  LogOut,
  ChevronDown,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";

const NAV_LINKS = [
  { label: "Home", href: "/" },
  { label: "Discover", href: "/discover" },
  { label: "Movies", href: "/discover?type=movie" },
  { label: "Series", href: "/discover?type=show" },
  { label: "Platforms", href: "/#platforms" },
  { label: "Features", href: "/#features" },
];

function DesktopNavLinks() {
  const pathname = usePathname();

  return (
    <nav className="hidden md:flex items-center gap-1 lg:gap-2">
      {NAV_LINKS.map((link) => {
        const isActive =
          link.href === "/"
            ? pathname === "/"
            : pathname?.startsWith(link.href);

        return (
          <Link
            key={link.label}
            href={link.href}
            className={cn(
              "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
              isActive
                ? "text-white bg-white/10"
                : "text-zinc-400 hover:text-white hover:bg-white/5"
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

function MobileNavLinks({ onNavigate }: { onNavigate: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col space-y-1">
      {NAV_LINKS.map((link) => {
        const isActive =
          link.href === "/"
            ? pathname === "/"
            : pathname?.startsWith(link.href);

        return (
          <Link
            key={link.label}
            href={link.href}
            onClick={onNavigate}
            className={cn(
              "px-3 py-2 rounded-lg text-sm font-medium transition-colors",
              isActive
                ? "text-white bg-white/10 font-semibold"
                : "text-zinc-300 hover:text-white hover:bg-white/5"
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

function FallbackDesktopNavLinks() {
  return (
    <nav className="hidden md:flex items-center gap-1 lg:gap-2">
      {NAV_LINKS.map((link) => (
        <Link
          key={link.label}
          href={link.href}
          className="px-3 py-1.5 rounded-lg text-sm font-medium text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}

function FallbackMobileNavLinks({ onNavigate }: { onNavigate: () => void }) {
  return (
    <nav className="flex flex-col space-y-1">
      {NAV_LINKS.map((link) => (
        <Link
          key={link.label}
          href={link.href}
          onClick={onNavigate}
          className="px-3 py-2 rounded-lg text-sm font-medium text-zinc-300 hover:text-white hover:bg-white/5 transition-colors"
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setUserDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 w-full transition-all duration-300",
        scrolled
          ? "bg-zinc-950/85 backdrop-blur-xl border-b border-white/10 shadow-lg shadow-black/40"
          : "bg-transparent border-b border-white/5"
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 sm:h-20">
          {/* Brand Logo */}
          <Link
            href="/"
            className="flex items-center gap-2.5 group focus:outline-none"
          >
            <div className="relative p-2 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 shadow-md shadow-purple-600/30 group-hover:scale-105 transition-transform">
              <Clapperboard className="size-5 text-white" />
              <div className="absolute inset-0 rounded-xl bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>

            <div className="flex flex-col">
              <span className="font-extrabold text-base sm:text-lg tracking-tight text-white flex items-center gap-1.5">
                CineSync
                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  OTT
                </span>
              </span>
              <span className="text-[10px] text-zinc-400 font-medium tracking-wide hidden sm:block">
                Unified Streaming Aggregator
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links wrapped in Suspense */}
          <Suspense fallback={<FallbackDesktopNavLinks />}>
            <DesktopNavLinks />
          </Suspense>

          {/* Desktop Right Actions */}
          <div className="hidden md:flex items-center gap-2.5">
            <Link
              href="/discover"
              className="p-2 rounded-xl text-zinc-400 hover:text-white hover:bg-white/5 border border-transparent hover:border-white/10 transition-colors"
              title="Search Catalog"
            >
              <Search className="size-4" />
            </Link>

            <Link
              href="/discover?voice=true"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-purple-950/60 border border-purple-500/30 text-purple-300 hover:bg-purple-900/60 transition-colors"
              title="Voice Search"
            >
              <Mic className="size-3.5 text-purple-400" />
              <span>Voice</span>
            </Link>

            {/* Auth Actions */}
            {isAuthenticated && user ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  type="button"
                  onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-white transition-all cursor-pointer"
                  aria-expanded={userDropdownOpen}
                >
                  <div className="size-6 rounded-lg bg-gradient-to-tr from-purple-500 to-indigo-500 flex items-center justify-center text-[11px] font-bold text-white shadow-sm">
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <span className="max-w-[110px] truncate">{user.username}</span>
                  <ChevronDown className="size-3 text-zinc-400" />
                </button>

                {userDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-56 rounded-xl bg-zinc-900/95 border border-white/10 p-2 shadow-2xl backdrop-blur-xl z-50 animate-in fade-in zoom-in-95">
                    <div className="px-3 py-2 border-b border-white/5">
                      <p className="text-xs font-semibold text-white truncate">
                        {user.username}
                      </p>
                      <p className="text-[11px] text-zinc-400 truncate">
                        {user.email}
                      </p>
                      {user.is_superuser && (
                        <span className="inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-500/20 text-purple-300 border border-purple-500/30">
                          Admin
                        </span>
                      )}
                    </div>

                    <div className="py-1">
                      <Link
                        href="/discover"
                        onClick={() => setUserDropdownOpen(false)}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs text-zinc-300 hover:text-white hover:bg-white/5 transition-colors"
                      >
                        <Clapperboard className="size-3.5 text-purple-400" />
                        <span>Discover Catalog</span>
                      </Link>
                      <div className="flex items-center justify-between px-3 py-1.5 rounded-lg text-xs text-zinc-400 opacity-60">
                        <div className="flex items-center gap-2">
                          <Sparkles className="size-3.5 text-zinc-500" />
                          <span>Watchlist</span>
                        </div>
                        <span className="text-[10px] text-zinc-500 font-mono">Soon</span>
                      </div>
                    </div>

                    <div className="pt-1 border-t border-white/5">
                      <button
                        type="button"
                        onClick={async () => {
                          setUserDropdownOpen(false);
                          await logout();
                        }}
                        className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors cursor-pointer text-left"
                      >
                        <LogOut className="size-3.5" />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/login"
                  className="px-3 py-1.5 rounded-xl text-xs font-semibold text-zinc-300 hover:text-white hover:bg-white/5 transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  className={cn(
                    "inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-white",
                    "bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 hover:from-purple-500 hover:to-indigo-500",
                    "shadow-md shadow-purple-600/30 hover:shadow-purple-600/50 transition-all cursor-pointer"
                  )}
                >
                  <span>Get Started</span>
                  <ArrowRight className="size-3" />
                </Link>
              </div>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden items-center gap-2">
            <Link
              href="/discover"
              className="p-2 rounded-lg text-zinc-400 hover:text-white"
              aria-label="Discover"
            >
              <Search className="size-5" />
            </Link>

            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 focus:outline-none"
              aria-label="Toggle mobile menu"
            >
              {mobileMenuOpen ? (
                <X className="size-6 text-white" />
              ) : (
                <Menu className="size-6 text-white" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-white/10 bg-zinc-950/95 backdrop-blur-2xl px-4 pt-3 pb-6 space-y-4">
          <Suspense
            fallback={
              <FallbackMobileNavLinks onNavigate={() => setMobileMenuOpen(false)} />
            }
          >
            <MobileNavLinks onNavigate={() => setMobileMenuOpen(false)} />
          </Suspense>

          <div className="pt-3 border-t border-white/10 flex flex-col gap-2">
            <Link
              href="/discover?voice=true"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold bg-purple-950/70 border border-purple-500/30 text-purple-300"
            >
              <Mic className="size-4 text-purple-400" />
              <span>Voice Assisted Search</span>
            </Link>

            {isAuthenticated && user ? (
              <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-2">
                <div className="flex items-center gap-2.5">
                  <div className="size-8 rounded-lg bg-gradient-to-tr from-purple-500 to-indigo-500 flex items-center justify-center text-xs font-bold text-white shadow-sm">
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-white truncate">
                      {user.username}
                    </p>
                    <p className="text-[11px] text-zinc-400 truncate">
                      {user.email}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={async () => {
                    setMobileMenuOpen(false);
                    await logout();
                  }}
                  className="w-full mt-2 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-medium text-red-400 bg-red-500/10 hover:bg-red-500/20 transition-colors"
                >
                  <LogOut className="size-3.5" />
                  <span>Sign Out</span>
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2 pt-1">
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center justify-center py-2.5 px-3 rounded-xl text-xs font-semibold text-zinc-300 bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center justify-center py-2.5 px-3 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-purple-600 to-indigo-600 shadow-md shadow-purple-600/30"
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
