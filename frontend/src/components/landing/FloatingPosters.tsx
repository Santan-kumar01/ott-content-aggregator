"use client";

import React, { useState, useSyncExternalStore } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { Star, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  VERIFIED_POSTER_POOL,
  selectRandomPosters,
  type PosterPoolItem,
} from "@/lib/imdb";

// In-memory client snapshot cache for the current session/page view
let clientPostersSnapshot: PosterPoolItem[] | null = null;

function getClientSnapshot(): PosterPoolItem[] {
  if (clientPostersSnapshot) {
    return clientPostersSnapshot;
  }

  try {
    // Check previous exclusions from session and local storage
    const sessionPrev = sessionStorage.getItem("cine_prev_posters");
    const localPrev = localStorage.getItem("cine_last_posters");
    const prevIds: string[] = [];

    if (sessionPrev) {
      prevIds.push(...JSON.parse(sessionPrev));
    } else if (localPrev) {
      prevIds.push(...JSON.parse(localPrev));
    }

    const selected = selectRandomPosters(4, prevIds);

    if (selected && selected.length === 4) {
      clientPostersSnapshot = selected;
      const newIds = selected.map((p) => p.id);
      sessionStorage.setItem("cine_prev_posters", JSON.stringify(newIds));
      localStorage.setItem("cine_last_posters", JSON.stringify(newIds));
      return clientPostersSnapshot;
    }
  } catch {
    // Fallback gracefully if storage is restricted
  }

  clientPostersSnapshot = VERIFIED_POSTER_POOL.slice(0, 4);
  return clientPostersSnapshot;
}

function getServerSnapshot(): PosterPoolItem[] {
  return VERIFIED_POSTER_POOL.slice(0, 4);
}

const emptySubscribe = () => () => {};

export function FloatingPosters({ className }: { className?: string }) {
  // Use React 19 useSyncExternalStore to avoid hydration mismatch and setState-in-effect warnings
  const posters = useSyncExternalStore(
    emptySubscribe,
    getClientSnapshot,
    getServerSnapshot
  );

  const leftCard = posters[0] || VERIFIED_POSTER_POOL[0];
  const rightCard = posters[1] || VERIFIED_POSTER_POOL[1];
  const backCard = posters[2] || VERIFIED_POSTER_POOL[2];
  const centerCard = posters[3] || VERIFIED_POSTER_POOL[3];

  return (
    <div
      className={cn(
        "relative w-full max-w-[540px] h-[400px] sm:h-[460px] lg:h-[500px] mx-auto",
        "flex items-center justify-center perspective-1500 select-none",
        className
      )}
    >
      {/* Ambient Radial Lighting Behind Posters */}
      <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
        <div className="w-72 h-72 sm:w-96 sm:h-96 rounded-full bg-gradient-to-tr from-purple-600/25 via-indigo-500/20 to-cyan-500/15 blur-3xl animate-pulse-glow" />
      </div>

      {/* Floating Card 1: Left Background */}
      <motion.div
        key={`left-${leftCard.id}`}
        initial={{ opacity: 1, rotateY: 16, rotateZ: -5 }}
        animate={{
          opacity: 1,
          y: [-8, 8, -8],
          rotateY: 16,
          rotateZ: -5,
        }}
        transition={{
          y: { duration: 6, repeat: Infinity, ease: "easeInOut" },
          opacity: { duration: 0.3 },
        }}
        whileHover={{
          scale: 1.05,
          rotateY: 8,
          zIndex: 30,
          transition: { duration: 0.2 },
        }}
        className={cn(
          "absolute -left-2 sm:left-4 top-12 sm:top-14 w-[160px] sm:w-[190px] aspect-[2/3]",
          "rounded-2xl overflow-hidden shadow-2xl shadow-black/80 border border-white/15",
          "cursor-pointer z-10 hidden sm:block backdrop-blur-md"
        )}
      >
        <PosterCardContent item={leftCard} />
      </motion.div>

      {/* Floating Card 2: Right Background */}
      <motion.div
        key={`right-${rightCard.id}`}
        initial={{ opacity: 1, rotateY: -16, rotateZ: 5 }}
        animate={{
          opacity: 1,
          y: [10, -10, 10],
          rotateY: -16,
          rotateZ: 5,
        }}
        transition={{
          y: { duration: 7, repeat: Infinity, ease: "easeInOut", delay: 0.8 },
          opacity: { duration: 0.3 },
        }}
        whileHover={{
          scale: 1.05,
          rotateY: -8,
          zIndex: 30,
          transition: { duration: 0.2 },
        }}
        className={cn(
          "absolute -right-2 sm:right-4 top-8 sm:top-10 w-[160px] sm:w-[190px] aspect-[2/3]",
          "rounded-2xl overflow-hidden shadow-2xl shadow-black/80 border border-white/15",
          "cursor-pointer z-10 hidden sm:block backdrop-blur-md"
        )}
      >
        <PosterCardContent item={rightCard} />
      </motion.div>

      {/* Floating Card 3: Deep Back Accent */}
      <motion.div
        key={`back-${backCard.id}`}
        initial={{ opacity: 0.7, scale: 0.88 }}
        animate={{
          opacity: 0.7,
          y: [-4, 6, -4],
          scale: 0.88,
        }}
        transition={{
          y: { duration: 8, repeat: Infinity, ease: "easeInOut", delay: 1.5 },
        }}
        className={cn(
          "absolute top-2 w-[170px] sm:w-[200px] aspect-[2/3]",
          "rounded-2xl overflow-hidden shadow-2xl shadow-black/90 border border-white/10",
          "z-0 pointer-events-none opacity-60 filter blur-[0.5px]"
        )}
      >
        <PosterCardContent item={backCard} />
      </motion.div>

      {/* Floating Card 4: Foreground Centerpiece (NO PLAY BUTTON OVERLAY) */}
      <motion.div
        key={`center-${centerCard.id}`}
        initial={{ opacity: 1, scale: 1 }}
        animate={{
          opacity: 1,
          scale: 1,
          y: [0, -10, 0],
          rotateX: [0, 2, 0],
        }}
        transition={{
          y: { duration: 5.5, repeat: Infinity, ease: "easeInOut" },
          rotateX: { duration: 5.5, repeat: Infinity, ease: "easeInOut" },
          opacity: { duration: 0.3 },
        }}
        whileHover={{
          scale: 1.04,
          translateY: -8,
          transition: { duration: 0.25 },
        }}
        className={cn(
          "relative w-[210px] sm:w-[240px] aspect-[2/3]",
          "rounded-2xl overflow-hidden shadow-2xl shadow-purple-950/60 border border-purple-500/40",
          "cursor-pointer z-20 ring-1 ring-white/20 group"
        )}
      >
        <PosterCardContent item={centerCard} isCenter />
      </motion.div>
    </div>
  );
}

function PosterCardContent({
  item,
  isCenter = false,
}: {
  item: PosterPoolItem;
  isCenter?: boolean;
}) {
  const [imageError, setImageError] = useState(false);

  return (
    <div
      className={cn(
        "relative w-full h-full flex flex-col justify-between overflow-hidden text-white",
        "bg-gradient-to-b",
        item.gradient
      )}
    >
      {/* Official Poster Artwork Image */}
      {item.imageUrl && !imageError && (
        <Image
          src={item.imageUrl}
          alt={item.title}
          fill
          sizes={isCenter ? "240px" : "190px"}
          className="object-cover object-center transition-transform duration-500 ease-out group-hover:scale-105"
          onError={() => setImageError(true)}
          priority={isCenter}
        />
      )}

      {/* Cinematic Gradient Overlays for High Contrast & Artwork Visibility */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/25 to-black/60 pointer-events-none" />

      {/* Top Header: Platform Badge + Rating */}
      <div className="relative z-10 p-3 sm:p-3.5 flex items-center justify-between gap-1">
        <span
          className={cn(
            "px-2.5 py-0.5 rounded-full text-[10px] sm:text-[11px] font-bold tracking-wide border shadow-sm backdrop-blur-md",
            item.platformColor
          )}
        >
          {item.platform}
        </span>

        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] sm:text-[11px] font-semibold bg-black/75 border border-white/20 text-amber-300 backdrop-blur-md">
          <Star className="size-2.5 sm:size-3 fill-amber-400 text-amber-400" />
          <span>{item.rating}</span>
        </span>
      </div>

      {/* Bottom Metadata & Sub-tag */}
      <div className="relative z-10 p-3 sm:p-3.5 pt-0 mt-auto">
        <h4 className="font-extrabold text-sm sm:text-base leading-tight tracking-tight text-white drop-shadow-lg line-clamp-1">
          {item.title}
        </h4>
        <div className="flex items-center gap-1.5 text-[10px] sm:text-[11px] text-zinc-300 mt-0.5 font-medium">
          <span>{item.genre}</span>
          <span>•</span>
          <span>{item.year}</span>
        </div>

        <div className="flex items-center justify-between text-[9px] sm:text-[10px] text-zinc-400 font-mono pt-2 mt-2 border-t border-white/15">
          <span className="flex items-center gap-1 text-purple-300">
            <Sparkles className="size-2.5" /> Unified Stream
          </span>
          <span className="uppercase tracking-wider">HD 4K</span>
        </div>
      </div>
    </div>
  );
}
