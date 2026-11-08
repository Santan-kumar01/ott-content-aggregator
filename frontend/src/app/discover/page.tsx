"use client";

import React, { useState, useEffect, useCallback, useTransition, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { SearchBar } from "@/components/search/SearchBar";
import { FilterPanel, type FilterState } from "@/components/search/FilterPanel";
import { SortControl, type SortByField, type SortOrder } from "@/components/search/SortControl";
import { MovieGrid } from "@/components/movies/MovieGrid";
import { Pagination } from "@/components/search/Pagination";
import {
  fetchPaginatedTitles,
  type EnrichedTitle,
} from "@/lib/services/catalog";
import { VoiceSearchModal } from "@/components/voice/VoiceSearchModal";
import type { ParsedVoiceQuery } from "@/types";
import { Sparkles, Layers, SlidersHorizontal } from "lucide-react";

const PAGE_SIZE = 12;

function DiscoverContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

  // Read initial values from URL query parameters
  const initialSearch = searchParams.get("search") || "";
  const initialGenre = searchParams.get("genre") || "All";
  const initialPlatform = searchParams.get("platform") || "All";
  const initialYear = searchParams.get("year")
    ? Number(searchParams.get("year"))
    : undefined;
  const initialType = (searchParams.get("type") as "all" | "movie" | "show") || "all";
  const initialSortBy = (searchParams.get("sort_by") as SortByField) || "name";
  const initialSortOrder = (searchParams.get("sort_order") as SortOrder) || "asc";
  const initialPage = searchParams.get("page")
    ? Math.max(1, Number(searchParams.get("page")))
    : 1;

  // Local state
  const [search, setSearch] = useState(initialSearch);
  const [filters, setFilters] = useState<FilterState>({
    genre: initialGenre,
    platform: initialPlatform,
    releaseYear: initialYear,
    contentType: initialType,
  });
  const [sortBy, setSortBy] = useState<SortByField>(initialSortBy);
  const [sortOrder, setSortOrder] = useState<SortOrder>(initialSortOrder);
  const [currentPage, setCurrentPage] = useState(initialPage);

  // Data state
  const [titles, setTitles] = useState<EnrichedTitle[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFiltersMobile, setShowFiltersMobile] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [isFallbackMode, setIsFallbackMode] = useState(false);
  const isVoiceParam = searchParams.get("voice") === "true";
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(isVoiceParam);
  const [prevVoiceParam, setPrevVoiceParam] = useState(isVoiceParam);

  if (isVoiceParam !== prevVoiceParam) {
    setPrevVoiceParam(isVoiceParam);
    if (isVoiceParam) {
      setIsVoiceModalOpen(true);
    }
  }

  const handleCloseVoiceModal = useCallback(() => {
    setIsVoiceModalOpen(false);
    if (searchParams.get("voice")) {
      const params = new URLSearchParams(searchParams.toString());
      params.delete("voice");
      const query = params.toString();
      router.replace(`/discover${query ? `?${query}` : ""}`, { scroll: false });
    }
  }, [router, searchParams]);

  // Sync state to URL search parameters
  const updateUrlParams = useCallback(
    (
      newSearch: string,
      newFilters: FilterState,
      newSortBy: SortByField,
      newSortOrder: SortOrder,
      newPage: number
    ) => {
      const params = new URLSearchParams();

      if (newSearch.trim()) params.set("search", newSearch.trim());
      if (newFilters.genre && newFilters.genre !== "All") params.set("genre", newFilters.genre);
      if (newFilters.platform && newFilters.platform !== "All")
        params.set("platform", newFilters.platform);
      if (newFilters.releaseYear !== undefined)
        params.set("year", String(newFilters.releaseYear));
      if (newFilters.contentType && newFilters.contentType !== "all")
        params.set("type", newFilters.contentType);
      if (newSortBy && newSortBy !== "name") params.set("sort_by", newSortBy);
      if (newSortOrder && newSortOrder !== "asc") params.set("sort_order", newSortOrder);
      if (newPage > 1) params.set("page", String(newPage));

      const query = params.toString();
      startTransition(() => {
        router.replace(`/discover${query ? `?${query}` : ""}`, { scroll: false });
      });
    },
    [router]
  );

  // Fetch titles when search, filters, sort, or pagination changes
  useEffect(() => {
    let ignore = false;

    async function execute() {
      const skip = (currentPage - 1) * PAGE_SIZE;

      try {
        const res = await fetchPaginatedTitles({
          search: search.trim() || undefined,
          genre: filters.genre !== "All" ? filters.genre : undefined,
          platform: filters.platform !== "All" ? filters.platform : undefined,
          release_year: filters.releaseYear,
          sort_by: sortBy,
          sort_order: sortOrder,
          skip,
          limit: PAGE_SIZE,
        });

        if (ignore) return;

        let finalItems = res.items;
        let finalTotal = res.total;

        if (filters.contentType && filters.contentType !== "all") {
          finalItems = res.items.filter((i) => i.content_type === filters.contentType);
          finalTotal = finalItems.length;
        }

        setTitles(finalItems);
        setTotalItems(finalTotal);
        setIsFallbackMode(Boolean(res.isFallback));
        setError(null);
      } catch (err) {
        if (ignore) return;
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load titles from the catalog."
        );
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    execute();

    return () => {
      ignore = true;
    };
  }, [currentPage, search, filters, sortBy, sortOrder, reloadKey]);

  // Handlers
  const handleSearchChange = (newSearch: string) => {
    setIsLoading(true);
    setSearch(newSearch);
    setCurrentPage(1);
    updateUrlParams(newSearch, filters, sortBy, sortOrder, 1);
  };

  const handleFilterChange = (newFilters: FilterState) => {
    setIsLoading(true);
    setFilters(newFilters);
    setCurrentPage(1);
    updateUrlParams(search, newFilters, sortBy, sortOrder, 1);
  };

  const handleResetFilters = () => {
    setIsLoading(true);
    const emptyFilters: FilterState = {
      genre: "All",
      platform: "All",
      releaseYear: undefined,
      contentType: "all",
    };
    setSearch("");
    setFilters(emptyFilters);
    setCurrentPage(1);
    updateUrlParams("", emptyFilters, sortBy, sortOrder, 1);
  };

  const handleSortChange = (newSortBy: SortByField, newSortOrder: SortOrder) => {
    setIsLoading(true);
    setSortBy(newSortBy);
    setSortOrder(newSortOrder);
    setCurrentPage(1);
    updateUrlParams(search, filters, newSortBy, newSortOrder, 1);
  };

  const handlePageChange = (page: number) => {
    setIsLoading(true);
    setCurrentPage(page);
    updateUrlParams(search, filters, sortBy, sortOrder, page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleApplyVoiceResults = (
    voiceQuery: string,
    parsed: ParsedVoiceQuery
  ) => {
    setIsLoading(true);

    const newSearch = parsed.cleaned_query || voiceQuery || search;
    const newFilters: FilterState = {
      ...filters,
      genre: parsed.genre || filters.genre,
      platform: parsed.platform || filters.platform,
      releaseYear: parsed.release_year ?? filters.releaseYear,
      contentType: parsed.content_type || filters.contentType,
    };

    setSearch(newSearch);
    setFilters(newFilters);
    setCurrentPage(1);
    updateUrlParams(newSearch, newFilters, sortBy, sortOrder, 1);
  };

  return (
    <div className="min-h-screen bg-[#07070a] text-zinc-100 flex flex-col selection:bg-purple-600 selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        {/* Page Hero Header */}
        <div className="relative mb-8 sm:mb-12 text-center max-w-3xl mx-auto">
          {/* Subtle glow backdrop */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-80 h-36 bg-purple-600/15 blur-3xl pointer-events-none rounded-full" />

          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-semibold mb-4">
            <Sparkles className="size-3.5" />
            <span>Unified Streaming Discovery</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white mb-4">
            Discover Your Next{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-indigo-300 to-purple-400">
              Favourite
            </span>
          </h1>

          <p className="text-sm sm:text-base text-zinc-400 leading-relaxed">
            Explore movies and series across Netflix, Prime Video, Disney+, Max,
            Apple TV+, and more with instant search, intelligent filters, and authentic
            artwork.
          </p>
        </div>

        {/* Search Bar Section */}
        <div className="max-w-2xl mx-auto mb-8">
          <SearchBar
            value={search}
            onChange={handleSearchChange}
            onVoiceClick={() => setIsVoiceModalOpen(true)}
            isLoading={isLoading}
            placeholder="Search titles by name, synopsis, or keywords..."
          />
        </div>

        {/* Controls Layout: Filters + Results Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Desktop Filter Sidebar */}
          <aside className="hidden lg:block lg:col-span-1">
            <div className="sticky top-28 space-y-4">
              <FilterPanel
                filters={filters}
                onChange={handleFilterChange}
                onReset={handleResetFilters}
              />
            </div>
          </aside>

          {/* Main Results Column */}
          <div className="lg:col-span-3 flex flex-col gap-6">
            {/* Mobile Filter Toggle & Sort Row */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-2xl bg-zinc-900/40 border border-white/5 backdrop-blur-md">
              <div className="flex items-center justify-between sm:justify-start gap-3">
                {/* Mobile Filter Toggle Button */}
                <button
                  type="button"
                  onClick={() => setShowFiltersMobile(!showFiltersMobile)}
                  className="lg:hidden flex items-center gap-2 px-3.5 py-2 rounded-xl bg-purple-600/20 border border-purple-500/40 text-purple-300 text-xs font-semibold"
                >
                  <SlidersHorizontal className="size-3.5" />
                  <span>{showFiltersMobile ? "Hide Filters" : "Filter Titles"}</span>
                </button>

                <div className="flex items-center gap-2 text-xs text-zinc-400 font-medium">
                  <Layers className="size-4 text-purple-400" />
                  <span>
                    Found <strong className="text-white font-semibold">{totalItems}</strong>{" "}
                    {totalItems === 1 ? "title" : "titles"}
                  </span>
                </div>
              </div>

              {/* Sort Control */}
              <div className="flex justify-end">
                <SortControl
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onChange={handleSortChange}
                />
              </div>
            </div>

            {/* Mobile Filter Drawer (Visible when toggled on small screens) */}
            {showFiltersMobile && (
              <div className="lg:hidden mb-4 animate-in fade-in slide-in-from-top-2 duration-200">
                <FilterPanel
                  filters={filters}
                  onChange={handleFilterChange}
                  onReset={handleResetFilters}
                />
              </div>
            )}

            {/* Transparent Demo/Fallback Dataset Notice */}
            {isFallbackMode && !isLoading && (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/25 text-amber-200 text-xs">
                <div className="flex items-center gap-2.5">
                  <span className="px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 font-bold uppercase tracking-wider text-[10px] shrink-0 border border-amber-500/30">
                    Demo Preview
                  </span>
                  <span>
                    Displaying verified sample titles with authentic IMDb artwork. Live backend API is currently disconnected.
                  </span>
                </div>
                <span className="text-[11px] font-mono text-amber-400/80 self-end sm:self-auto">
                  Offline Dataset
                </span>
              </div>
            )}

            {/* Movie Grid */}
            <MovieGrid
              titles={titles}
              isLoading={isLoading}
              error={error}
              onRetry={() => {
                setIsLoading(true);
                setReloadKey((k) => k + 1);
              }}
              onResetFilters={handleResetFilters}
              skeletonCount={PAGE_SIZE}
            />

            {/* Pagination Controls */}
            {!isLoading && totalItems > PAGE_SIZE && (
              <Pagination
                currentPage={currentPage}
                totalItems={totalItems}
                pageSize={PAGE_SIZE}
                onPageChange={handlePageChange}
              />
            )}
          </div>
        </div>

        {/* Voice Assisted Search Modal */}
        <VoiceSearchModal
          isOpen={isVoiceModalOpen}
          onClose={handleCloseVoiceModal}
          onApplyResults={handleApplyVoiceResults}
        />
      </main>

      <Footer />
    </div>
  );
}

export default function DiscoverPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#07070a] flex items-center justify-center">
          <div className="size-8 rounded-full border-2 border-purple-500 border-t-transparent animate-spin" />
        </div>
      }
    >
      <DiscoverContent />
    </Suspense>
  );
}
