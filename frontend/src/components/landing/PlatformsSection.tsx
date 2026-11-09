"use client";

import React from "react";
import Link from "next/link";
import { ArrowUpRight, PlaySquare } from "lucide-react";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { cn } from "@/lib/utils";

interface PlatformInfo {
  name: string;
  queryParam: string;
  tagline: string;
  titleCount: string;
  brandColor: string;
  badgeBg: string;
  borderHover: string;
  glow: string;
}

const PLATFORMS: PlatformInfo[] = [
  {
    name: "Netflix",
    queryParam: "Netflix",
    tagline: "Global Blockbusters & Originals",
    titleCount: "4,500+ Titles",
    brandColor: "text-red-500",
    badgeBg: "bg-red-600/15 border-red-500/30 text-red-400",
    borderHover: "hover:border-red-500/50 hover:shadow-red-600/20",
    glow: "from-red-600/10",
  },
  {
    name: "Prime Video",
    queryParam: "Prime",
    tagline: "Exclusive Series & Box Office Hits",
    titleCount: "3,800+ Titles",
    brandColor: "text-sky-400",
    badgeBg: "bg-sky-500/15 border-sky-400/30 text-sky-300",
    borderHover: "hover:border-sky-400/50 hover:shadow-sky-500/20",
    glow: "from-sky-500/10",
  },
  {
    name: "Disney+",
    queryParam: "Disney+",
    tagline: "Marvel, Star Wars, Pixar & Disney",
    titleCount: "2,200+ Titles",
    brandColor: "text-blue-400",
    badgeBg: "bg-blue-600/15 border-blue-400/30 text-blue-300",
    borderHover: "hover:border-blue-400/50 hover:shadow-blue-600/20",
    glow: "from-blue-600/10",
  },
  {
    name: "Max",
    queryParam: "Max",
    tagline: "HBO Prestige, Warner Bros & DC",
    titleCount: "2,900+ Titles",
    brandColor: "text-indigo-400",
    badgeBg: "bg-indigo-600/15 border-indigo-400/30 text-indigo-300",
    borderHover: "hover:border-indigo-400/50 hover:shadow-indigo-600/20",
    glow: "from-indigo-600/10",
  },
  {
    name: "Apple TV+",
    queryParam: "Apple TV+",
    tagline: "Award-Winning Premium Originals",
    titleCount: "600+ Titles",
    brandColor: "text-zinc-200",
    badgeBg: "bg-zinc-700/20 border-zinc-500/30 text-zinc-200",
    borderHover: "hover:border-zinc-400/50 hover:shadow-zinc-500/20",
    glow: "from-zinc-400/10",
  },
  {
    name: "Paramount+",
    queryParam: "Paramount+",
    tagline: "Live Sports, Trek & Paramount Films",
    titleCount: "1,800+ Titles",
    brandColor: "text-blue-300",
    badgeBg: "bg-blue-500/15 border-blue-300/30 text-blue-200",
    borderHover: "hover:border-blue-300/50 hover:shadow-blue-400/20",
    glow: "from-blue-500/10",
  },
  {
    name: "Hulu",
    queryParam: "Hulu",
    tagline: "Next-Day TV & Acclaimed Dramas",
    titleCount: "2,400+ Titles",
    brandColor: "text-emerald-400",
    badgeBg: "bg-emerald-500/15 border-emerald-400/30 text-emerald-300",
    borderHover: "hover:border-emerald-400/50 hover:shadow-emerald-500/20",
    glow: "from-emerald-500/10",
  },
  {
    name: "Peacock",
    queryParam: "Peacock",
    tagline: "NBCUniversal Classics & Live Events",
    titleCount: "1,500+ Titles",
    brandColor: "text-teal-400",
    badgeBg: "bg-teal-500/15 border-teal-400/30 text-teal-300",
    borderHover: "hover:border-teal-400/50 hover:shadow-teal-500/20",
    glow: "from-teal-500/10",
  },
];

export function PlatformsSection({ className }: { className?: string }) {
  return (
    <section
      id="platforms"
      className={cn("py-20 sm:py-28 relative overflow-hidden", className)}
    >
      {/* Background ambient gradient */}
      <div className="absolute inset-0 bg-radial-gradient from-purple-950/15 via-transparent to-transparent pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <SectionHeading
          badge="SUPPORTED ECOSYSTEM"
          badgeIcon={<PlaySquare className="size-3.5 text-purple-400" />}
          title="All Your Favorite Services,"
          highlight="Unified in One Hub"
          description="Never switch between different streaming apps to find what to watch. We index catalogs across every major provider in real-time."
          centered
        />

        {/* Platforms Grid */}
        <div className="mt-14 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {PLATFORMS.map((platform) => (
            <Link
              key={platform.name}
              href={`/discover?platform=${encodeURIComponent(platform.queryParam)}`}
              className={cn(
                "group relative p-5 rounded-2xl",
                "bg-zinc-950/60 backdrop-blur-md border border-white/10",
                "transition-all duration-300 ease-out",
                "hover:-translate-y-1 hover:shadow-xl",
                platform.borderHover
              )}
            >
              {/* Subtle top glow highlight */}
              <div
                className={cn(
                  "absolute inset-x-0 top-0 h-1 rounded-t-2xl bg-gradient-to-r opacity-0 group-hover:opacity-100 transition-opacity",
                  platform.glow,
                  "to-transparent"
                )}
              />

              <div className="flex items-start justify-between">
                {/* Platform Badge */}
                <div
                  className={cn(
                    "px-3 py-1 rounded-xl text-xs font-bold border backdrop-blur-md",
                    platform.badgeBg
                  )}
                >
                  {platform.name}
                </div>

                <div className="p-1.5 rounded-lg bg-white/5 text-zinc-500 group-hover:text-white group-hover:bg-white/10 transition-colors">
                  <ArrowUpRight className="size-4" />
                </div>
              </div>

              <div className="mt-6">
                <h3 className="text-lg font-bold text-white tracking-tight group-hover:text-purple-300 transition-colors">
                  {platform.name}
                </h3>
                <p className="text-xs text-zinc-400 mt-1 line-clamp-1">
                  {platform.tagline}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-xs font-mono text-zinc-500">
                <span className="text-purple-300/80 font-medium">
                  {platform.titleCount}
                </span>
                <span className="group-hover:translate-x-0.5 transition-transform text-zinc-400">
                  Explore →
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

