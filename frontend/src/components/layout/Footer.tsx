import React from "react";
import Link from "next/link";
import { Clapperboard } from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full border-t border-white/10 bg-zinc-950/90 text-zinc-400 text-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14 sm:py-16">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-10">
          {/* Brand & Mission Statement */}
          <div className="md:col-span-2 space-y-4">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="p-2 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 shadow-md shadow-purple-600/30">
                <Clapperboard className="size-5 text-white" />
              </div>
              <span className="font-extrabold text-lg tracking-tight text-white flex items-center gap-1.5">
                CineSync
                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  OTT
                </span>
              </span>
            </Link>

            <p className="text-zinc-400 text-xs sm:text-sm leading-relaxed max-w-sm">
              The unified entertainment discovery engine. Seamlessly index,
              search, and stream titles across Netflix, Prime Video, Disney+,
              Max, and Apple TV+ with AI-driven voice intelligence.
            </p>

            <div className="pt-2 flex items-center gap-2 text-xs text-zinc-500">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Backend API operational with Redis cache active</span>
            </div>
          </div>

          {/* Column 1: Discovery */}
          <div className="space-y-3">
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-white">
              Discover
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link
                  href="/discover"
                  className="hover:text-white transition-colors"
                >
                  All Titles
                </Link>
              </li>
              <li>
                <Link
                  href="/discover?type=movie"
                  className="hover:text-white transition-colors"
                >
                  Movies Catalog
                </Link>
              </li>
              <li>
                <Link
                  href="/discover?type=show"
                  className="hover:text-white transition-colors"
                >
                  TV Series
                </Link>
              </li>
              <li>
                <Link
                  href="/discover?sort_by=release_year&sort_order=desc"
                  className="hover:text-white transition-colors"
                >
                  Latest Releases
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 2: Supported Platforms */}
          <div className="space-y-3">
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-white">
              Platforms
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link
                  href="/discover?platform=Netflix"
                  className="hover:text-white transition-colors"
                >
                  Netflix
                </Link>
              </li>
              <li>
                <Link
                  href="/discover?platform=Prime"
                  className="hover:text-white transition-colors"
                >
                  Prime Video
                </Link>
              </li>
              <li>
                <Link
                  href="/discover?platform=Disney%2B"
                  className="hover:text-white transition-colors"
                >
                  Disney+
                </Link>
              </li>
              <li>
                <Link
                  href="/discover?platform=Max"
                  className="hover:text-white transition-colors"
                >
                  Max (HBO)
                </Link>
              </li>
              <li>
                <Link
                  href="/discover?platform=Apple%20TV%2B"
                  className="hover:text-white transition-colors"
                >
                  Apple TV+
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 3: Features & Architecture */}
          <div className="space-y-3">
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-white">
              Technology
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <span className="text-zinc-400">Groq Whisper Transcription</span>
              </li>
              <li>
                <span className="text-zinc-400">Natural Language Intent NLP</span>
              </li>
              <li>
                <span className="text-zinc-400">Redis Invalidation Caching</span>
              </li>
              <li>
                <span className="text-zinc-400">FastAPI Async Architecture</span>
              </li>
              <li>
                <span className="text-zinc-400">Next.js 16 + Tailwind CSS</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 pt-8 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-zinc-500">
          <p>
            © 2026 OTT Content Aggregator • Built for Axlero Internship
          </p>

          <div className="flex items-center gap-1.5 text-zinc-500">
            <span>Powered by</span>
            <span className="text-zinc-400 font-semibold">FastAPI</span>
            <span>&amp;</span>
            <span className="text-zinc-400 font-semibold">Next.js</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

