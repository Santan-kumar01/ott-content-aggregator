"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface MovieCardSkeletonProps {
  className?: string;
}

export function MovieCardSkeleton({ className }: MovieCardSkeletonProps) {
  return (
    <div
      className={cn(
        "flex flex-col rounded-2xl overflow-hidden bg-zinc-900/60 border border-white/5 animate-pulse",
        className
      )}
    >
      {/* Aspect Ratio 2:3 Poster Skeleton */}
      <div className="relative aspect-[2/3] w-full bg-zinc-800/60">
        {/* Top badge skeletons */}
        <div className="absolute top-2.5 inset-x-2.5 flex items-center justify-between">
          <div className="h-5 w-16 rounded-full bg-zinc-700/60" />
          <div className="h-5 w-10 rounded-full bg-zinc-700/60" />
        </div>

        {/* Shimmer effect */}
        <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent -translate-x-full animate-[shimmer_2s_infinite]" />
      </div>

      {/* Card Info Footer Skeleton */}
      <div className="p-3.5 space-y-2.5 bg-zinc-900/80">
        <div className="flex items-center justify-between gap-2">
          <div className="h-3 w-14 rounded bg-zinc-800" />
          <div className="h-3 w-16 rounded bg-zinc-800" />
        </div>
        <div className="h-4 w-4/5 rounded bg-zinc-800" />
      </div>
    </div>
  );
}

