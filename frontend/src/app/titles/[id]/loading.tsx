import React from "react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";

export default function Loading() {
  return (
    <div className="min-h-screen bg-[#07070a] text-zinc-100 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 sm:py-12 animate-pulse">
        {/* Back Link Skeleton */}
        <div className="h-8 w-32 rounded-xl bg-zinc-800/60 mb-6" />

        {/* Hero Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 lg:gap-12 items-start mb-16">
          <div className="md:col-span-4 lg:col-span-4">
            <div className="aspect-[2/3] w-full max-w-sm mx-auto rounded-3xl bg-zinc-800/60 border border-white/5" />
          </div>

          <div className="md:col-span-8 lg:col-span-8 space-y-4">
            <div className="flex gap-2">
              <div className="h-6 w-24 rounded-full bg-zinc-800/80" />
              <div className="h-6 w-16 rounded-full bg-zinc-800/80" />
              <div className="h-6 w-20 rounded-full bg-zinc-800/80" />
            </div>

            <div className="h-12 w-3/4 rounded-2xl bg-zinc-800" />
            <div className="h-5 w-48 rounded bg-zinc-800/60" />

            <div className="flex gap-3 pt-4">
              <div className="h-12 w-40 rounded-2xl bg-purple-900/30" />
              <div className="h-12 w-32 rounded-2xl bg-zinc-800/60" />
            </div>

            <div className="h-32 rounded-3xl bg-zinc-900/60 border border-white/5 mt-6" />
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}

