import React from "react";
import Link from "next/link";
import { Clapperboard, ArrowRight, Sparkles, Mic } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { HeroSection } from "@/components/landing/HeroSection";
import { SearchBanner } from "@/components/landing/SearchBanner";
import { PlatformsSection } from "@/components/landing/PlatformsSection";
import { FeaturedSection } from "@/components/landing/FeaturedSection";
import { FeaturesSection } from "@/components/landing/FeaturesSection";
import { VoiceDemoSection } from "@/components/landing/VoiceDemoSection";
import { cn } from "@/lib/utils";

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col bg-[#07070a] text-white selection:bg-purple-600 selection:text-white">
      {/* Navigation Header */}
      <Navbar />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col">
        {/* 1. Hero Section with 3D Floating Posters */}
        <HeroSection />

        {/* 2. Interactive Search Banner & Quick Tags */}
        <div className="relative z-20 -mt-6 sm:-mt-8 mb-8 sm:mb-14">
          <SearchBanner />
        </div>

        {/* 3. Supported Platforms Showcase */}
        <PlatformsSection />

        {/* 4. Curated Featured & Trending Titles */}
        <FeaturedSection />

        {/* 5. Core Architectural & Feature Pillars */}
        <FeaturesSection />

        {/* 6. AI Voice Pipeline Interactive Demonstration */}
        <VoiceDemoSection />

        {/* 7. Final Conversion Call-to-Action Banner */}
        <section className="py-20 sm:py-28 relative overflow-hidden">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="relative p-8 sm:p-14 rounded-3xl bg-gradient-to-b from-purple-950/40 via-zinc-950/80 to-zinc-950 border border-purple-500/30 backdrop-blur-2xl shadow-2xl shadow-purple-950/50 text-center overflow-hidden">
              {/* Ambient radial glow inside banner */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-48 bg-purple-600/25 blur-3xl pointer-events-none" />

              <div className="relative z-10 space-y-6 max-w-2xl mx-auto">
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider bg-white/5 border border-white/10 text-purple-300">
                  <Sparkles className="size-3.5 text-purple-400" />
                  <span>Start Streaming Smarter</span>
                </div>

                <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white tracking-tight leading-tight">
                  Ready to Stop Searching and Start Watching?
                </h2>

                <p className="text-sm sm:text-base text-zinc-400 leading-relaxed">
                  Join thousands of film buffs and binge-watchers who discover
                  their next favorite movie in seconds across every platform.
                </p>

                <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
                  <Link
                    href="/discover"
                    className={cn(
                      "w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl text-sm font-semibold text-white",
                      "bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 hover:from-purple-500 hover:to-indigo-500",
                      "shadow-xl shadow-purple-600/40 transition-all cursor-pointer active:scale-95"
                    )}
                  >
                    <Clapperboard className="size-4" />
                    <span>Launch Aggregator Catalog</span>
                    <ArrowRight className="size-4" />
                  </Link>

                  <Link
                    href="/discover?voice=true"
                    className={cn(
                      "w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl text-sm font-semibold",
                      "bg-white/5 hover:bg-white/10 text-white border border-white/10 hover:border-white/20 transition-all cursor-pointer"
                    )}
                  >
                    <Mic className="size-4 text-purple-400" />
                    <span>Voice Search Demo</span>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}
