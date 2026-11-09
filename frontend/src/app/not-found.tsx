import React from "react";
import Link from "next/link";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Clapperboard, Compass, Home } from "lucide-react";

export default function GlobalNotFound() {
  return (
    <div className="min-h-screen bg-[#07070a] text-zinc-100 flex flex-col selection:bg-purple-600 selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-20 flex items-center justify-center relative overflow-hidden">
        {/* Ambient glow backgrounds */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-purple-600/15 blur-[140px] pointer-events-none rounded-full" />
        <div className="absolute bottom-10 right-1/4 w-72 h-72 bg-indigo-600/10 blur-[100px] pointer-events-none rounded-full" />

        <div className="max-w-md w-full text-center p-8 sm:p-12 rounded-3xl bg-zinc-900/60 border border-white/10 backdrop-blur-xl shadow-2xl shadow-black/80 relative z-10">
          <div className="p-4 rounded-2xl bg-purple-600/20 border border-purple-500/30 mx-auto w-fit mb-6 text-purple-400">
            <Clapperboard className="size-12" />
          </div>

          <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 mb-4 inline-block tracking-wider">
            ERROR 404
          </span>

          <h1 className="text-3xl font-extrabold text-white tracking-tight mb-3">
            Scene Missing
          </h1>

          <p className="text-sm text-zinc-400 mb-8 leading-relaxed">
            The page or feature you were looking for doesn&apos;t exist or may have been relocated in the CineSync catalog.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold text-zinc-300 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 transition-all cursor-pointer"
            >
              <Home className="size-4" />
              <span>Back to Home</span>
            </Link>

            <Link
              href="/discover"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 shadow-lg shadow-purple-600/30 transition-all cursor-pointer"
            >
              <Compass className="size-4" />
              <span>Explore Discover</span>
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}

