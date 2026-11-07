"use client";

import React from "react";
import { Filter, RotateCcw, X, Tv, Film } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Platform } from "@/types";

export interface FilterState {
  genre: string;
  platform: string;
  releaseYear?: number;
  contentType?: "all" | "movie" | "show";
}

interface FilterPanelProps {
  filters: FilterState;
  onChange: (updated: FilterState) => void;
  onReset: () => void;
  className?: string;
}

export const GENRE_OPTIONS = [
  "All",
  "Action",
  "Sci-Fi",
  "Drama",
  "Thriller",
  "Comedy",
  "Adventure",
  "Crime",
  "Animation",
  "Horror",
];

export const PLATFORM_OPTIONS: (Platform | "All")[] = [
  "All",
  "Netflix",
  "Prime",
  "Disney+",
  "Max",
  "Apple TV+",
  "Hulu",
  "Paramount+",
  "Peacock",
];

export const YEAR_OPTIONS: { label: string; value?: number }[] = [
  { label: "All Years", value: undefined },
  { label: "2024", value: 2024 },
  { label: "2023", value: 2023 },
  { label: "2022", value: 2022 },
  { label: "2021", value: 2021 },
  { label: "2020", value: 2020 },
  { label: "2019", value: 2019 },
  { label: "2018", value: 2018 },
  { label: "2016", value: 2016 },
  { label: "2014", value: 2014 },
  { label: "2010", value: 2010 },
  { label: "2008", value: 2008 },
  { label: "2000", value: 2000 },
  { label: "1999", value: 1999 },
];

export function FilterPanel({
  filters,
  onChange,
  onReset,
  className,
}: FilterPanelProps) {
  const activeCount = [
    filters.genre && filters.genre !== "All",
    filters.platform && filters.platform !== "All",
    filters.releaseYear !== undefined,
    filters.contentType && filters.contentType !== "all",
  ].filter(Boolean).length;

  return (
    <div
      className={cn(
        "flex flex-col gap-5 p-5 rounded-3xl bg-zinc-900/60 border border-white/10 backdrop-blur-xl",
        className
      )}
    >
      {/* Header with Active Badges & Reset CTA */}
      <div className="flex items-center justify-between flex-wrap gap-3 pb-3 border-b border-white/5">
        <div className="flex items-center gap-2 text-white">
          <Filter className="size-4 text-purple-400" />
          <span className="text-sm font-semibold tracking-wide">Filters</span>
          {activeCount > 0 && (
            <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-purple-600/30 text-purple-300 border border-purple-500/40">
              {activeCount} active
            </span>
          )}
        </div>

        {activeCount > 0 && (
          <button
            type="button"
            onClick={onReset}
            className="flex items-center gap-1.5 text-xs font-medium text-zinc-400 hover:text-white transition-colors focus:outline-none"
          >
            <RotateCcw className="size-3.5" />
            <span>Reset Filters</span>
          </button>
        )}
      </div>

      {/* Row 1: Content Type Pills */}
      <div>
        <label className="block text-xs font-medium text-zinc-400 mb-2 uppercase tracking-wider">
          Format
        </label>
        <div className="flex flex-wrap gap-2">
          {[
            { label: "All Formats", value: "all", icon: null },
            { label: "Movies", value: "movie", icon: Film },
            { label: "Series", value: "show", icon: Tv },
          ].map((item) => {
            const isSelected = (filters.contentType || "all") === item.value;
            const Icon = item.icon;
            return (
              <button
                key={item.value}
                type="button"
                onClick={() =>
                  onChange({
                    ...filters,
                    contentType: item.value as "all" | "movie" | "show",
                  })
                }
                className={cn(
                  "flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all focus:outline-none",
                  isSelected
                    ? "bg-purple-600 text-white shadow-md shadow-purple-600/30 ring-1 ring-purple-400/50"
                    : "bg-white/5 hover:bg-white/10 text-zinc-300 border border-white/5"
                )}
              >
                {Icon && <Icon className="size-3.5" />}
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Row 2: Streaming Platform Chips */}
      <div>
        <label className="block text-xs font-medium text-zinc-400 mb-2 uppercase tracking-wider">
          Streaming Platform
        </label>
        <div className="flex flex-wrap gap-2">
          {PLATFORM_OPTIONS.map((plat) => {
            const isSelected =
              plat === "All"
                ? !filters.platform || filters.platform === "All"
                : filters.platform === plat;

            return (
              <button
                key={plat}
                type="button"
                onClick={() =>
                  onChange({
                    ...filters,
                    platform: plat === "All" ? "All" : plat,
                  })
                }
                className={cn(
                  "px-3 py-1.5 rounded-xl text-xs font-medium transition-all focus:outline-none",
                  isSelected
                    ? "bg-white text-zinc-950 font-semibold shadow-md shadow-white/10 ring-1 ring-white"
                    : "bg-white/5 hover:bg-white/10 text-zinc-300 border border-white/5"
                )}
              >
                {plat}
              </button>
            );
          })}
        </div>
      </div>

      {/* Row 3: Genres & Release Year Dropdowns/Pills */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Genre Selector */}
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-2 uppercase tracking-wider">
            Genre
          </label>
          <div className="relative">
            <select
              value={filters.genre || "All"}
              onChange={(e) =>
                onChange({
                  ...filters,
                  genre: e.target.value,
                })
              }
              className="w-full appearance-none rounded-xl bg-zinc-800/80 border border-white/10 px-3.5 py-2.5 text-xs sm:text-sm text-white focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-colors"
            >
              {GENRE_OPTIONS.map((g) => (
                <option key={g} value={g} className="bg-zinc-900 text-white">
                  {g === "All" ? "All Genres" : g}
                </option>
              ))}
            </select>
            <div className="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-400 text-xs">
              ▼
            </div>
          </div>
        </div>

        {/* Release Year Selector */}
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-2 uppercase tracking-wider">
            Release Year
          </label>
          <div className="relative">
            <select
              value={filters.releaseYear !== undefined ? String(filters.releaseYear) : ""}
              onChange={(e) =>
                onChange({
                  ...filters,
                  releaseYear: e.target.value ? Number(e.target.value) : undefined,
                })
              }
              className="w-full appearance-none rounded-xl bg-zinc-800/80 border border-white/10 px-3.5 py-2.5 text-xs sm:text-sm text-white focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-colors"
            >
              {YEAR_OPTIONS.map((y) => (
                <option
                  key={y.label}
                  value={y.value !== undefined ? String(y.value) : ""}
                  className="bg-zinc-900 text-white"
                >
                  {y.label}
                </option>
              ))}
            </select>
            <div className="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-400 text-xs">
              ▼
            </div>
          </div>
        </div>
      </div>

      {/* Active Filter Tags */}
      {activeCount > 0 && (
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-white/5">
          <span className="text-[11px] text-zinc-500 font-medium">Applied:</span>

          {filters.genre && filters.genre !== "All" && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-purple-500/10 text-purple-300 border border-purple-500/30">
              <span>Genre: {filters.genre}</span>
              <button
                type="button"
                onClick={() => onChange({ ...filters, genre: "All" })}
                className="hover:text-white"
              >
                <X className="size-3" />
              </button>
            </span>
          )}

          {filters.platform && filters.platform !== "All" && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-purple-500/10 text-purple-300 border border-purple-500/30">
              <span>Platform: {filters.platform}</span>
              <button
                type="button"
                onClick={() => onChange({ ...filters, platform: "All" })}
                className="hover:text-white"
              >
                <X className="size-3" />
              </button>
            </span>
          )}

          {filters.releaseYear !== undefined && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-purple-500/10 text-purple-300 border border-purple-500/30">
              <span>Year: {filters.releaseYear}</span>
              <button
                type="button"
                onClick={() => onChange({ ...filters, releaseYear: undefined })}
                className="hover:text-white"
              >
                <X className="size-3" />
              </button>
            </span>
          )}

          {filters.contentType && filters.contentType !== "all" && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-purple-500/10 text-purple-300 border border-purple-500/30">
              <span>Format: {filters.contentType === "show" ? "Series" : "Movie"}</span>
              <button
                type="button"
                onClick={() => onChange({ ...filters, contentType: "all" })}
                className="hover:text-white"
              >
                <X className="size-3" />
              </button>
            </span>
          )}
        </div>
      )}
    </div>
  );
}

