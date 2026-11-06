"use client";

import React from "react";
import Link from "next/link";
import {
  Sparkles,
  ArrowRight,
  Mic,
  Clapperboard,
} from "lucide-react";
import { FloatingPosters } from "@/components/landing/FloatingPosters";
import { cn } from "@/lib/utils";

export function HeroSection({ className }: { className?: string }) {
  return (
    <section
      className={cn(
        "relative pt-8 sm:pt-14 pb-16 sm:pb-24 overflow-hidden",
        className
      )}
    >
      {/* Cinematic Ambient Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[500px] pointer-events-none overflow-hidden">
        <div className="absolute top-[-100px] left-1/4 w-[500px] h-[400px] rounded-full bg-purple-600/15 blur-[120px]" />
        <div className="absolute top-[-50px] right-1/4 w-[450px] h-[350px] rounded-full bg-indigo-600/15 blur-[120px]" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-8 items-center">
          {/* Left Column: Headline, CTAs, Metrics (Cols 7 on LG) */}
          <div className="lg:col-span-7 flex flex-col items-center lg:items-start text-center lg:text-left space-y-6">
            {/* Pill Badge */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider border border-purple-500/30 bg-purple-950/40 text-purple-300 backdrop-blur-md shadow-inner shadow-purple-500/10">
              <Sparkles className="size-3.5 text-purple-400" />
              <span>Next-Gen Streaming Intelligence</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black tracking-tight text-white leading-[1.1]">
              Stream Smarter.{" "}
              <span className="block mt-1 sm:mt-2 bg-gradient-to-r from-purple-400 via-pink-400 to-indigo-300 bg-clip-text text-transparent">
                Every Platform. One Unified Hub.
              </span>
            </h1>

            {/* Subtitle Description */}
            <p className="text-sm sm:text-base lg:text-lg text-zinc-400 max-w-xl leading-relaxed">
              Never waste 20 minutes wondering what to watch or which app has
              it. Search titles, track real-time availability across Netflix,
              Prime, Disney+, and Max, or find matches using AI voice
              prompts.
            </p>

            {/* CTA Buttons */}
            <div className="pt-2 flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
              <Link
                href="/discover"
                className={cn(
                  "w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl text-sm font-semibold text-white",
                  "bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 hover:from-purple-500 hover:to-indigo-500",
                  "shadow-xl shadow-purple-600/30 hover:shadow-purple-600/50 transition-all cursor-pointer active:scale-95"
                )}
              >
                <Clapperboard className="size-4" />
                <span>Explore Catalog</span>
                <ArrowRight className="size-4" />
              </Link>

              <Link
                href="/discover?voice=true"
                className={cn(
                  "w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl text-sm font-semibold",
                  "bg-zinc-900/80 hover:bg-zinc-800/90 text-zinc-200 hover:text-white border border-white/10 hover:border-purple-500/40",
                  "backdrop-blur-md transition-all cursor-pointer"
                )}
              >
                <Mic className="size-4 text-purple-400" />
                <span>Try Voice Search</span>
              </Link>
            </div>

            {/* Key Stats Bar */}
            <div className="pt-6 border-t border-white/10 w-full grid grid-cols-3 gap-4 text-center lg:text-left">
              <div>
                <div className="text-xl sm:text-2xl font-black text-white tracking-tight">
                  10,000+
                </div>
                <div className="text-[11px] sm:text-xs text-zinc-500 font-medium">
                  Indexed Titles
                </div>
              </div>

              <div>
                <div className="text-xl sm:text-2xl font-black text-purple-400 tracking-tight">
                  8+
                </div>
                <div className="text-[11px] sm:text-xs text-zinc-500 font-medium">
                  Top Platforms
                </div>
              </div>

              <div>
                <div className="text-xl sm:text-2xl font-black text-white tracking-tight">
                  &lt;10ms
                </div>
                <div className="text-[11px] sm:text-xs text-zinc-500 font-medium">
                  Redis Speed
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: 3D Floating Posters (Cols 5 on LG) */}
          <div className="lg:col-span-5 w-full flex items-center justify-center">
            <FloatingPosters />
          </div>
        </div>
      </div>
    </section>
  );
}

