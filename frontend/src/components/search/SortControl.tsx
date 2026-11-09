"use client";

import React from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";

export type SortByField = "name" | "release_year" | "created_at";
export type SortOrder = "asc" | "desc";

interface SortControlProps {
  sortBy: SortByField;
  sortOrder: SortOrder;
  onChange: (sortBy: SortByField, sortOrder: SortOrder) => void;
  className?: string;
}

const SORT_OPTIONS: { label: string; value: SortByField }[] = [
  { label: "Title Name", value: "name" },
  { label: "Release Year", value: "release_year" },
  { label: "Date Added", value: "created_at" },
];

export function SortControl({
  sortBy,
  sortOrder,
  onChange,
  className,
}: SortControlProps) {
  const toggleOrder = () => {
    onChange(sortBy, sortOrder === "asc" ? "desc" : "asc");
  };

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="relative flex items-center">
        <label htmlFor="sort-by-select" className="sr-only">
          Sort catalog by
        </label>
        <div className="absolute left-3 pointer-events-none text-zinc-400">
          <ArrowUpDown className="size-3.5" />
        </div>

        <select
          id="sort-by-select"
          value={sortBy}
          onChange={(e) => onChange(e.target.value as SortByField, sortOrder)}
          className="appearance-none pl-9 pr-8 py-2 rounded-xl bg-zinc-900/80 border border-white/10 text-xs sm:text-sm text-zinc-200 hover:text-white hover:border-white/20 focus:outline-none focus:border-purple-500 transition-colors cursor-pointer"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-zinc-950 text-white">
              Sort by: {opt.label}
            </option>
          ))}
        </select>
        <div className="absolute right-3 pointer-events-none text-zinc-400 text-[10px]">
          ▼
        </div>
      </div>

      <button
        type="button"
        onClick={toggleOrder}
        aria-label={`Sort order: currently ${
          sortOrder === "asc" ? "ascending" : "descending"
        }`}
        title={`Switch to ${sortOrder === "asc" ? "descending" : "ascending"}`}
        className="flex items-center gap-1 px-3 py-2 rounded-xl bg-zinc-900/80 border border-white/10 hover:border-white/20 text-xs text-zinc-300 hover:text-white transition-colors focus:outline-none"
      >
        {sortOrder === "asc" ? (
          <>
            <ArrowUp className="size-3.5 text-purple-400" />
            <span className="hidden sm:inline font-medium">Asc</span>
          </>
        ) : (
          <>
            <ArrowDown className="size-3.5 text-purple-400" />
            <span className="hidden sm:inline font-medium">Desc</span>
          </>
        )}
      </button>
    </div>
  );
}

