"use client";

import React, { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  ArrowLeft,
  Star,
  Play,
  Film,
  Tv,
  Calendar,
  Share2,
  Bookmark,
  Check,
  ExternalLink,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { MovieCard } from "./MovieCard";
import type { EnrichedTitle } from "@/lib/services/catalog";

interface TitleDetailsProps {
  title: EnrichedTitle;
  similarTitles?: EnrichedTitle[];
}

const platformColors: Record<
  string,
  { bg: string; text: string; border: string; glow: string }
> = {
  Netflix: {
    bg: "bg-red-600/90",
    text: "text-white",
    border: "border-red-500/40",
    glow: "shadow-red-600/40",
  },
  Prime: {
    bg: "bg-sky-500/90",
    text: "text-white",
    border: "border-sky-400/40",
    glow: "shadow-sky-500/40",
  },
  "Disney+": {
    bg: "bg-blue-600/90",
    text: "text-white",
    border: "border-blue-400/40",
    glow: "shadow-blue-600/40",
  },
  Max: {
    bg: "bg-indigo-600/90",
    text: "text-white",
    border: "border-indigo-400/40",
    glow: "shadow-indigo-600/40",
  },
  "Apple TV+": {
    bg: "bg-zinc-800/90",
    text: "text-zinc-100",
    border: "border-zinc-500/40",
    glow: "shadow-zinc-700/40",
  },
  Hulu: {
    bg: "bg-emerald-500/90",
    text: "text-black font-semibold",
    border: "border-emerald-400/40",
    glow: "shadow-emerald-500/40",
  },
  "Paramount+": {
    bg: "bg-blue-500/90",
    text: "text-white",
    border: "border-blue-400/40",
    glow: "shadow-blue-500/40",
  },
  Peacock: {
    bg: "bg-teal-600/90",
    text: "text-white",
    border: "border-teal-400/40",
    glow: "shadow-teal-600/40",
  },
};

export function TitleDetails({ title, similarTitles = [] }: TitleDetailsProps) {
  const [imageError, setImageError] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  const platformStyle = platformColors[title.platform] || {
    bg: "bg-purple-600/90",
    text: "text-white",
    border: "border-purple-400/40",
    glow: "shadow-purple-600/40",
  };

  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard?.writeText(window.location.href);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  return (
    <div className="relative">
      {/* Background Ambient Backdrop */}
      {title.posterUrl && !imageError && (
        <div className="absolute top-0 inset-x-0 h-96 overflow-hidden pointer-events-none opacity-20 -z-10">
          <Image
            src={title.posterUrl}
            alt=""
            fill
            priority
            unoptimized
            className="object-cover object-top blur-3xl scale-125"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-[#07070a]/40 via-[#07070a]/90 to-[#07070a]" />
        </div>
      )}

      {/* Navigation Breadcrumb / Back Link */}
      <div className="mb-6">
        <Link
          href="/discover"
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs sm:text-sm text-zinc-300 hover:text-white transition-colors"
        >
          <ArrowLeft className="size-4" />
          <span>Back to Discover</span>
        </Link>
      </div>

      {/* Title Hero Container */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 lg:gap-12 items-start mb-16">
        {/* Left: 2:3 Poster Art */}
        <div className="md:col-span-4 lg:col-span-4">
          <div className="relative aspect-[2/3] w-full max-w-sm mx-auto rounded-3xl overflow-hidden bg-zinc-900 border border-white/15 shadow-2xl shadow-purple-950/50">
            {title.posterUrl && !imageError ? (
              <Image
                src={title.posterUrl}
                alt={title.name}
                fill
                priority
                unoptimized
                sizes="(max-width: 768px) 100vw, 350px"
                className="object-cover object-center"
                onError={() => setImageError(true)}
              />
            ) : (
              <div className="absolute inset-0 bg-gradient-to-br from-purple-950 via-slate-900 to-indigo-950 flex flex-col items-center justify-center p-6 text-center">
                {title.content_type === "show" ? (
                  <Tv className="size-16 text-purple-400 mb-4" />
                ) : (
                  <Film className="size-16 text-purple-400 mb-4" />
                )}
                <h3 className="font-bold text-xl text-white mb-2">{title.name}</h3>
                <p className="text-xs text-zinc-400">{title.release_year}</p>
              </div>
            )}

            {/* Platform Tag */}
            <div className="absolute top-4 left-4 z-10">
              <span
                className={cn(
                  "px-3 py-1 rounded-full text-xs font-bold tracking-wide backdrop-blur-md border shadow-lg",
                  platformStyle.bg,
                  platformStyle.text,
                  platformStyle.border,
                  platformStyle.glow
                )}
              >
                {title.platform}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Detailed Metadata & Actions */}
        <div className="md:col-span-8 lg:col-span-8 flex flex-col justify-start">
          {/* Top Badges */}
          <div className="flex flex-wrap items-center gap-2.5 mb-3">
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 text-zinc-200 border border-white/10 backdrop-blur-md">
              {title.content_type === "show" ? (
                <>
                  <Tv className="size-3.5 text-purple-400" />
                  <span>TV Series</span>
                </>
              ) : (
                <>
                  <Film className="size-3.5 text-purple-400" />
                  <span>Feature Film</span>
                </>
              )}
            </span>

            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 text-zinc-200 border border-white/10 backdrop-blur-md">
              <Calendar className="size-3.5 text-purple-400" />
              <span>{title.release_year}</span>
            </span>

            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/15 text-purple-300 border border-purple-500/30">
              {title.genre}
            </span>

            {typeof title.rating === "number" && title.rating > 0 && (
              <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                <Star className="size-3.5 fill-amber-400 text-amber-400" />
                <span>{title.rating.toFixed(1)} IMDb</span>
              </span>
            )}
          </div>

          {/* Title Header */}
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-white mb-4 leading-tight">
            {title.name}
          </h1>

          {/* Platform Availability Notice */}
          <div className="flex flex-wrap items-center gap-2 text-xs sm:text-sm text-zinc-400 mb-6">
            <span className="font-medium text-zinc-300">Cataloged Platform:</span>
            <span className="font-semibold text-white px-2 py-0.5 rounded-md bg-white/10">
              {title.platform}
            </span>
            <span className="text-zinc-600 hidden sm:inline">•</span>
            <span className="text-zinc-500 text-xs">
              Direct provider streaming subject to provider subscription
            </span>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center gap-3.5 mb-8">
            <a
              href={`https://www.google.com/search?q=stream+${encodeURIComponent(
                title.name
              )}+${encodeURIComponent(title.platform)}`}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                "inline-flex items-center gap-2 px-5 py-3.5 rounded-2xl text-xs sm:text-sm font-bold text-white",
                "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500",
                "shadow-lg shadow-purple-600/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
              )}
            >
              <ExternalLink className="size-4" />
              <span>Find on {title.platform} (Web Search)</span>
            </a>

            <div
              className="inline-flex items-center gap-2 px-4 py-3.5 rounded-2xl text-xs sm:text-sm font-medium bg-white/5 text-zinc-400 border border-white/10 select-none cursor-default"
              title="Watchlist persistence is scheduled for Phase 4 user authentication release"
            >
              <Bookmark className="size-4 text-zinc-500" />
              <span>Watchlist</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-zinc-800 text-zinc-400 border border-white/5">
                Coming Soon
              </span>
            </div>

            <button
              type="button"
              onClick={handleShare}
              className="inline-flex items-center gap-2 px-4 py-3.5 rounded-2xl text-sm font-semibold bg-white/5 hover:bg-white/10 text-zinc-300 hover:text-white border border-white/10 transition-colors"
              title="Share title"
            >
              {copiedLink ? (
                <>
                  <Check className="size-4 text-emerald-400" />
                  <span className="text-emerald-400">Copied!</span>
                </>
              ) : (
                <>
                  <Share2 className="size-4" />
                  <span>Share</span>
                </>
              )}
            </button>
          </div>

          {/* Synopsis */}
          <div className="p-6 rounded-3xl bg-zinc-900/60 border border-white/10 backdrop-blur-xl mb-8">
            <h2 className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-3">
              Synopsis & Storyline
            </h2>
            <p className="text-sm sm:text-base text-zinc-200 leading-relaxed">
              {title.description ||
                "No synopsis is currently available for this title in the aggregator catalog."}
            </p>
          </div>

          {/* Key Title Details Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-5 rounded-3xl bg-zinc-900/40 border border-white/5">
            <div>
              <span className="block text-[11px] font-medium text-zinc-500 uppercase tracking-wider mb-1">
                Format
              </span>
              <span className="text-sm font-semibold text-white">
                {title.content_type === "show" ? "TV Series" : "Movie"}
              </span>
            </div>

            <div>
              <span className="block text-[11px] font-medium text-zinc-500 uppercase tracking-wider mb-1">
                Genre
              </span>
              <span className="text-sm font-semibold text-white">{title.genre}</span>
            </div>

            <div>
              <span className="block text-[11px] font-medium text-zinc-500 uppercase tracking-wider mb-1">
                Release Year
              </span>
              <span className="text-sm font-semibold text-white">
                {title.release_year}
              </span>
            </div>

            <div>
              <span className="block text-[11px] font-medium text-zinc-500 uppercase tracking-wider mb-1">
                Catalog Ref
              </span>
              <span className="text-sm font-mono font-semibold text-purple-300">
                #OTT-{String(title.id).padStart(4, "0")}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Similar Titles Section */}
      {similarTitles.length > 0 && (
        <div className="pt-8 border-t border-white/10">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                More in {title.genre}
              </h3>
              <p className="text-xs sm:text-sm text-zinc-400 mt-1">
                Recommended titles curated from the same genre and streaming platforms
              </p>
            </div>

            <Link
              href={`/discover?genre=${encodeURIComponent(title.genre)}`}
              className="text-xs font-semibold text-purple-400 hover:text-purple-300 transition-colors"
            >
              Explore all {title.genre} →
            </Link>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 sm:gap-6">
            {similarTitles.map((sim) => (
              <MovieCard
                key={sim.id}
                id={sim.id}
                title={sim.name}
                releaseYear={sim.release_year}
                genre={sim.genre}
                platform={sim.platform}
                contentType={sim.content_type}
                rating={sim.rating}
                description={sim.description}
                posterUrl={sim.posterUrl}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

