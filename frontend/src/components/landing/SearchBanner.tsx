"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Mic, Sparkles, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchBannerProps {
  className?: string;
  placeholder?: string;
}

const QUICK_TAGS = [
  { label: "Sci-Fi on Netflix", query: "Sci-Fi Netflix" },
  { label: "Christopher Nolan", query: "Christopher Nolan" },
  { label: "Top Rated Shows", query: "Top Rated" },
  { label: "Prime Video Action", query: "Action Prime" },
  { label: "90s Classics", query: "1990s" },
];

export function SearchBanner({
  className,
  placeholder = "Search movies, series, platforms, or try voice queries...",
}: SearchBannerProps) {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) {
      router.push("/discover");
      return;
    }
    router.push(`/discover?search=${encodeURIComponent(searchTerm.trim())}`);
  };

  const handleQuickTag = (query: string) => {
    router.push(`/discover?search=${encodeURIComponent(query)}`);
  };

  return (
    <div className={cn("w-full max-w-4xl mx-auto px-4", className)}>
      {/* Search Container with ambient border glow */}
      <div className="relative p-1 rounded-2xl sm:rounded-3xl bg-gradient-to-r from-purple-500/20 via-pink-500/10 to-indigo-500/20 shadow-2xl shadow-purple-950/40">
        <form
          onSubmit={handleSearch}
          className="relative flex flex-col sm:flex-row items-stretch sm:items-center gap-2 p-2 rounded-[14px] sm:rounded-[22px] bg-zinc-950/90 backdrop-blur-xl border border-white/10"
        >
          {/* Search Icon & Input */}
          <div className="flex-1 flex items-center gap-3 px-3.5 py-2">
            <Search className="size-5 text-zinc-400 shrink-0" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={placeholder}
              className="w-full bg-transparent text-sm sm:text-base text-white placeholder-zinc-500 focus:outline-none"
            />
          </div>

          {/* Voice Search Pill Badge & Submit Button */}
          <div className="flex items-center gap-2 px-1">
            <button
              type="button"
              onClick={() => router.push("/discover?voice=true")}
              title="Natural Language Voice Search powered by Groq Whisper"
              className={cn(
                "hidden sm:flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium",
                "bg-purple-950/60 border border-purple-500/30 text-purple-300 hover:bg-purple-900/60 transition-colors",
                "group cursor-pointer"
              )}
            >
              <Mic className="size-3.5 text-purple-400 group-hover:scale-110 transition-transform animate-pulse" />
              <span>Voice Ready</span>
            </button>

            <button
              type="submit"
              className={cn(
                "flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white",
                "bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 hover:from-purple-500 hover:to-indigo-500",
                "shadow-lg shadow-purple-600/30 transition-all duration-200 active:scale-95 cursor-pointer"
              )}
            >
              <span>Search</span>
              <ArrowRight className="size-4" />
            </button>
          </div>
        </form>
      </div>

      {/* Quick Search Suggestions */}
      <div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-xs text-zinc-400">
        <span className="flex items-center gap-1 text-zinc-500 font-medium">
          <Sparkles className="size-3 text-purple-400" /> Popular:
        </span>
        {QUICK_TAGS.map((tag) => (
          <button
            key={tag.label}
            type="button"
            onClick={() => handleQuickTag(tag.query)}
            className="px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-zinc-300 transition-colors cursor-pointer"
          >
            {tag.label}
          </button>
        ))}
      </div>
    </div>
  );
}

