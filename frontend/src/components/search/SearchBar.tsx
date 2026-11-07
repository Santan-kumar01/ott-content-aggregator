"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Search, X, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  isLoading?: boolean;
  className?: string;
}

export function SearchBar({
  value,
  onChange,
  placeholder = "Search movies, series, genres, or keywords...",
  isLoading = false,
  className,
}: SearchBarProps) {
  const [internalValue, setInternalValue] = useState(value);
  const [prevValue, setPrevValue] = useState(value);

  // Sync internal state if parent value changes externally (official React pattern)
  if (value !== prevValue) {
    setPrevValue(value);
    setInternalValue(value);
  }

  // Debounce user keystrokes by 300ms
  useEffect(() => {
    const handler = setTimeout(() => {
      if (internalValue !== value) {
        onChange(internalValue);
      }
    }, 300);

    return () => clearTimeout(handler);
  }, [internalValue, value, onChange]);

  const handleClear = useCallback(() => {
    setInternalValue("");
    onChange("");
  }, [onChange]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      handleClear();
    } else if (e.key === "Enter") {
      onChange(internalValue);
    }
  };

  return (
    <div
      className={cn(
        "relative flex items-center w-full rounded-2xl bg-zinc-900/80 border border-white/10 hover:border-purple-500/40 focus-within:border-purple-500 focus-within:ring-2 focus-within:ring-purple-500/20 backdrop-blur-xl transition-all shadow-lg shadow-black/40",
        className
      )}
    >
      <div className="absolute left-4 flex items-center pointer-events-none text-zinc-400">
        {isLoading ? (
          <Loader2 className="size-5 animate-spin text-purple-400" />
        ) : (
          <Search className="size-5" />
        )}
      </div>

      <input
        type="text"
        value={internalValue}
        onChange={(e) => setInternalValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        aria-label="Search titles"
        className="w-full bg-transparent pl-12 pr-12 py-3.5 sm:py-4 text-sm sm:text-base text-white placeholder-zinc-500 focus:outline-none"
      />

      {internalValue && (
        <button
          type="button"
          onClick={handleClear}
          aria-label="Clear search input"
          className="absolute right-4 p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors focus:outline-none"
        >
          <X className="size-4" />
        </button>
      )}
    </div>
  );
}
