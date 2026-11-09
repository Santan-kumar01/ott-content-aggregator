"use client";

import React, { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  Film,
  Tv,
  Star,
  Play,
  Info,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getVerifiedPoster } from "@/lib/imdb";
import type { Platform, ContentType } from "@/types";

export interface MovieCardProps {
  id: number;
  title: string;
  releaseYear: number;
  genre: string;
  platform: Platform;
  contentType?: ContentType;
  rating?: number;
  description?: string | null;
  posterUrl?: string | null;
  featured?: boolean;
  className?: string;
}

// Platform badge color mappings
const platformColors: Record<
  string,
  { bg: string; text: string; border: string; glow: string }
> = {
  Netflix: {
    bg: "bg-red-600/90",
    text: "text-white",
    border: "border-red-500/40",
    glow: "shadow-red-600/30",
  },
  Prime: {
    bg: "bg-sky-500/90",
    text: "text-white",
    border: "border-sky-400/40",
    glow: "shadow-sky-500/30",
  },
  "Disney+": {
    bg: "bg-blue-600/90",
    text: "text-white",
    border: "border-blue-400/40",
    glow: "shadow-blue-600/30",
  },
  Max: {
    bg: "bg-indigo-600/90",
    text: "text-white",
    border: "border-indigo-400/40",
    glow: "shadow-indigo-600/30",
  },
  "Apple TV+": {
    bg: "bg-zinc-800/90",
    text: "text-zinc-100",
    border: "border-zinc-500/40",
    glow: "shadow-zinc-700/30",
  },
  Hulu: {
    bg: "bg-emerald-500/90",
    text: "text-black font-semibold",
    border: "border-emerald-400/40",
    glow: "shadow-emerald-500/30",
  },
  "Paramount+": {
    bg: "bg-blue-500/90",
    text: "text-white",
    border: "border-blue-400/40",
    glow: "shadow-blue-500/30",
  },
  Peacock: {
    bg: "bg-teal-600/90",
    text: "text-white",
    border: "border-teal-400/40",
    glow: "shadow-teal-600/30",
  },
};

// Genre gradient themes for fallback poster backgrounds
const genreGradients: Record<string, string> = {
  "Sci-Fi": "from-purple-950 via-slate-900 to-indigo-950",
  Action: "from-red-950 via-neutral-900 to-orange-950",
  Drama: "from-blue-950 via-zinc-900 to-slate-950",
  Thriller: "from-emerald-950 via-stone-900 to-cyan-950",
  Horror: "from-rose-950 via-neutral-900 to-black",
  Comedy: "from-amber-950 via-stone-900 to-yellow-950",
  Adventure: "from-cyan-950 via-slate-900 to-emerald-950",
  Crime: "from-slate-950 via-zinc-900 to-neutral-950",
  Animation: "from-violet-950 via-purple-900 to-indigo-950",
};

export function MovieCard({
  id,
  title,
  releaseYear,
  genre,
  platform,
  contentType = "movie",
  rating,
  description,
  posterUrl,
  featured = false,
  className,
}: MovieCardProps) {
  const [imageError, setImageError] = useState(false);

  // Fallback to verified IMDb poster if not directly passed
  const effectivePoster =
    posterUrl || getVerifiedPoster(title, releaseYear) || null;

  const platformStyle = platformColors[platform] || {
    bg: "bg-purple-600/90",
    text: "text-white",
    border: "border-purple-400/40",
    glow: "shadow-purple-600/30",
  };

  const gradientBg =
    genreGradients[genre] || "from-purple-950 via-neutral-900 to-indigo-950";

  return (
    <div
      data-title-id={id}
      className={cn(
        "group relative flex flex-col rounded-2xl overflow-hidden",
        "bg-zinc-900/80 border border-white/10 hover:border-purple-500/50",
        "transition-all duration-300 ease-out",
        "hover:-translate-y-1.5 hover:shadow-2xl hover:shadow-purple-950/40",
        featured && "ring-1 ring-purple-500/40",
        className
      )}
    >
      {/* Clickable Card Area leading to details */}
      <Link
        href={`/titles/${id}`}
        aria-label={`View details for ${title} (${releaseYear})`}
        className="block relative aspect-[2/3] w-full overflow-hidden bg-zinc-950 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-inset"
      >
        {effectivePoster && !imageError ? (
          <Image
            src={effectivePoster}
            alt={title}
            fill
            unoptimized
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 20vw"
            className="object-cover object-center transition-transform duration-500 ease-out group-hover:scale-105"
            onError={() => setImageError(true)}
          />
        ) : (
          /* Resilient Artistic Fallback Poster */
          <div
            className={cn(
              "absolute inset-0 bg-gradient-to-br flex flex-col justify-between p-4",
              gradientBg
            )}
          >
            {/* Background geometric pattern */}
            <div className="absolute inset-0 opacity-15 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-white/20 via-transparent to-transparent pointer-events-none" />

            {/* Top decorative element */}
            <div className="flex items-center justify-between text-zinc-500 text-xs">
              <span className="font-mono tracking-widest uppercase">
                {genre}
              </span>
              <Sparkles className="size-3.5 text-purple-400/50" />
            </div>

            {/* Middle artwork representation */}
            <div className="flex flex-col items-center justify-center my-auto text-center px-2 py-4">
              <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md mb-3 shadow-inner">
                {contentType === "show" ? (
                  <Tv className="size-7 text-purple-300" />
                ) : (
                  <Film className="size-7 text-purple-300" />
                )}
              </div>
              <h3 className="font-bold text-white text-base sm:text-lg leading-snug line-clamp-2 drop-shadow-md">
                {title}
              </h3>
              <p className="text-xs text-zinc-400 mt-1 font-medium">
                {releaseYear}
              </p>
            </div>

            {/* Bottom Platform Watermark */}
            <div className="text-right text-[10px] tracking-wider uppercase text-zinc-500/80 font-semibold">
              Available on {platform}
            </div>
          </div>
        )}

        {/* Top Badges: Platform (Left) & Rating (Right) */}
        <div className="absolute top-2.5 inset-x-2.5 flex items-center justify-between z-10 pointer-events-none">
          <span
            className={cn(
              "px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wide backdrop-blur-md border shadow-sm",
              platformStyle.bg,
              platformStyle.text,
              platformStyle.border,
              platformStyle.glow
            )}
          >
            {platform}
          </span>

          {typeof rating === "number" && rating > 0 && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-black/75 border border-white/15 text-amber-300 backdrop-blur-md">
              <Star className="size-3 fill-amber-400 text-amber-400" />
              <span>{rating.toFixed(1)}</span>
            </span>
          )}
        </div>

        {/* Hover Action Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-4 z-20">
          <div className="flex items-center gap-2 mb-2">
            <span className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-600/30 transition-colors">
              <Play className="size-3.5 fill-current" />
              <span>View Details</span>
            </span>
            <span
              className="p-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-white transition-colors"
              title="Details"
            >
              <Info className="size-4" />
            </span>
          </div>
          {description && (
            <p className="text-[11px] text-zinc-300 line-clamp-2 leading-relaxed">
              {description}
            </p>
          )}
        </div>
      </Link>

      {/* Card Metadata Footer */}
      <div className="p-3.5 flex flex-col justify-between flex-1 bg-zinc-900/70 backdrop-blur-sm border-t border-white/5">
        <div>
          <div className="flex items-center justify-between gap-2 text-[11px] text-zinc-400 mb-1">
            <span className="font-medium text-zinc-300">{genre}</span>
            <span className="flex items-center gap-1 text-zinc-500 font-mono">
              {contentType === "show" ? "Series" : "Movie"} • {releaseYear}
            </span>
          </div>

          <Link
            href={`/titles/${id}`}
            className="group-hover:text-purple-300 transition-colors focus:outline-none focus-visible:underline"
          >
            <h4
              className="text-sm font-semibold text-white tracking-tight line-clamp-1"
              title={title}
            >
              {title}
            </h4>
          </Link>
        </div>
      </div>
    </div>
  );
}
