"use client";

import React from "react";
import { SearchX, RotateCcw, AlertCircle } from "lucide-react";
import { MovieCard } from "./MovieCard";
import { MovieCardSkeleton } from "./MovieCardSkeleton";
import type { EnrichedTitle } from "@/lib/services/catalog";
import { cn } from "@/lib/utils";

interface MovieGridProps {
  titles: EnrichedTitle[];
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onResetFilters?: () => void;
  skeletonCount?: number;
  className?: string;
}

export function MovieGrid({
  titles,
  isLoading = false,
  error = null,
  onRetry,
  onResetFilters,
  skeletonCount = 12,
  className,
}: MovieGridProps) {
  // 1. Loading State
  if (isLoading) {
    return (
      <div
        className={cn(
          "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 sm:gap-6",
          className
        )}
      >
        {Array.from({ length: skeletonCount }).map((_, idx) => (
          <MovieCardSkeleton key={`skeleton-${idx}`} />
        ))}
      </div>
    );
  }

  // 2. Error State
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center rounded-3xl bg-red-950/20 border border-red-500/20 backdrop-blur-xl my-6">
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 mb-4">
          <AlertCircle className="size-8 text-red-400" />
        </div>
        <h3 className="text-lg font-bold text-white mb-2">Unable to Load Catalog</h3>
        <p className="text-sm text-zinc-400 max-w-md mb-6">{error}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-600/30 transition-colors"
          >
            <RotateCcw className="size-4" />
            <span>Try Again</span>
          </button>
        )}
      </div>
    );
  }

  // 3. Empty State
  if (titles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 sm:p-16 text-center rounded-3xl bg-zinc-900/40 border border-white/5 backdrop-blur-xl my-6">
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10 mb-4">
          <SearchX className="size-10 text-purple-400" />
        </div>
        <h3 className="text-xl font-bold text-white mb-2">No Titles Found</h3>
        <p className="text-sm text-zinc-400 max-w-md mb-6">
          We couldn&apos;t find any movies or series matching your current search,
          genre, platform or year filters.
        </p>
        {onResetFilters && (
          <button
            type="button"
            onClick={onResetFilters}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-600/30 transition-colors"
          >
            <RotateCcw className="size-4" />
            <span>Reset All Filters</span>
          </button>
        )}
      </div>
    );
  }

  // 4. Populated Grid
  return (
    <div
      className={cn(
        "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 sm:gap-6",
        className
      )}
    >
      {titles.map((title) => (
        <MovieCard
          key={title.id}
          id={title.id}
          title={title.name}
          releaseYear={title.release_year}
          genre={title.genre}
          platform={title.platform}
          contentType={title.content_type}
          rating={title.rating}
          description={title.description}
          posterUrl={title.posterUrl}
        />
      ))}
    </div>
  );
}
