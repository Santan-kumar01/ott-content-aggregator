"use client";

import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface PaginationProps {
  currentPage: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export function Pagination({
  currentPage,
  totalItems,
  pageSize,
  onPageChange,
  className,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  if (totalPages <= 1) {
    return null;
  }

  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  // Generate page numbers with ellipsis
  const getPageNumbers = () => {
    const pages: (number | "ellipsis")[] = [];

    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);

      if (currentPage > 3) {
        pages.push("ellipsis");
      }

      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }

      if (currentPage < totalPages - 2) {
        pages.push("ellipsis");
      }

      pages.push(totalPages);
    }

    return pages;
  };

  const pages = getPageNumbers();

  return (
    <div
      className={cn(
        "flex flex-col sm:flex-row items-center justify-between gap-4 py-6 border-t border-white/5",
        className
      )}
    >
      {/* Item Range Count */}
      <div className="text-xs sm:text-sm text-zinc-400 font-medium">
        Showing <span className="text-white font-semibold">{startItem}</span>–
        <span className="text-white font-semibold">{endItem}</span> of{" "}
        <span className="text-white font-semibold">{totalItems}</span> titles
      </div>

      {/* Page Navigation Controls */}
      <div className="flex items-center gap-1.5">
        {/* Previous Button */}
        <button
          type="button"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          aria-label="Previous page"
          className="flex items-center gap-1 px-3 py-2 rounded-xl bg-zinc-900/80 border border-white/10 text-xs sm:text-sm font-medium text-zinc-300 hover:text-white hover:border-white/20 disabled:opacity-40 disabled:pointer-events-none transition-colors focus:outline-none"
        >
          <ChevronLeft className="size-4" />
          <span className="hidden sm:inline">Previous</span>
        </button>

        {/* Page Numbers */}
        <div className="flex items-center gap-1">
          {pages.map((p, idx) => {
            if (p === "ellipsis") {
              return (
                <span
                  key={`ellipsis-${idx}`}
                  className="px-2 py-1 text-zinc-600 text-xs select-none"
                >
                  •••
                </span>
              );
            }

            const isCurrent = p === currentPage;

            return (
              <button
                key={p}
                type="button"
                onClick={() => onPageChange(p)}
                aria-current={isCurrent ? "page" : undefined}
                className={cn(
                  "size-8 sm:size-9 rounded-xl text-xs sm:text-sm font-semibold transition-all focus:outline-none",
                  isCurrent
                    ? "bg-purple-600 text-white shadow-md shadow-purple-600/40 ring-1 ring-purple-400/50"
                    : "bg-zinc-900/60 hover:bg-zinc-800 text-zinc-400 hover:text-white border border-white/5"
                )}
              >
                {p}
              </button>
            );
          })}
        </div>

        {/* Next Button */}
        <button
          type="button"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          aria-label="Next page"
          className="flex items-center gap-1 px-3 py-2 rounded-xl bg-zinc-900/80 border border-white/10 text-xs sm:text-sm font-medium text-zinc-300 hover:text-white hover:border-white/20 disabled:opacity-40 disabled:pointer-events-none transition-colors focus:outline-none"
        >
          <span className="hidden sm:inline">Next</span>
          <ChevronRight className="size-4" />
        </button>
      </div>
    </div>
  );
}

