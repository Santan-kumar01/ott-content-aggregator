import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { TitleDetails } from "@/components/movies/TitleDetails";
import {
  fetchTitleById,
  fetchSimilarTitles,
  type EnrichedTitle,
} from "@/lib/services/catalog";
import { Film, ArrowLeft } from "lucide-react";

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { id } = await params;
  const numId = Number(id);

  if (isNaN(numId) || numId <= 0) {
    return { title: "Title Not Found | CineSync OTT" };
  }

  try {
    const title = await fetchTitleById(numId);
    return {
      title: `${title.name} (${title.release_year}) - Stream on ${title.platform} | CineSync OTT`,
      description:
        title.description ||
        `Watch ${title.name} (${title.release_year}) on ${title.platform}. Unified streaming discovery with CineSync.`,
      openGraph: {
        title: `${title.name} (${title.release_year})`,
        description: title.description || undefined,
        images: title.posterUrl ? [{ url: title.posterUrl }] : [],
      },
    };
  } catch {
    return { title: "Title Details | CineSync OTT" };
  }
}

export default async function TitleDetailsPage({ params }: PageProps) {
  const { id } = await params;
  const numId = Number(id);

  if (isNaN(numId) || numId <= 0) {
    return <NotFoundState />;
  }

  let title: EnrichedTitle | null = null;
  let similar: EnrichedTitle[] = [];

  try {
    title = await fetchTitleById(numId);
    similar = await fetchSimilarTitles(numId, title.genre, title.platform, 4);
  } catch {
    return <NotFoundState />;
  }

  return (
    <div className="min-h-screen bg-[#07070a] text-zinc-100 flex flex-col selection:bg-purple-600 selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        <TitleDetails title={title} similarTitles={similar} />
      </main>

      <Footer />
    </div>
  );
}

function NotFoundState() {
  return (
    <div className="min-h-screen bg-[#07070a] text-zinc-100 flex flex-col selection:bg-purple-600 selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-16 flex items-center justify-center">
        <div className="max-w-md w-full text-center p-8 sm:p-12 rounded-3xl bg-zinc-900/40 border border-white/10 backdrop-blur-xl">
          <div className="p-4 rounded-2xl bg-white/5 border border-white/10 mx-auto w-fit mb-5">
            <Film className="size-10 text-purple-400" />
          </div>

          <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-purple-500/10 text-purple-300 border border-purple-500/20 mb-3 inline-block">
            404 NOT FOUND
          </span>

          <h1 className="text-2xl font-bold text-white mb-2">Title Not Found</h1>
          <p className="text-sm text-zinc-400 mb-8 leading-relaxed">
            The movie or series you requested could not be found in the CineSync
            unified streaming catalog.
          </p>

          <Link
            href="/discover"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs sm:text-sm font-semibold shadow-lg shadow-purple-600/30 transition-colors"
          >
            <ArrowLeft className="size-4" />
            <span>Explore All Titles</span>
          </Link>
        </div>
      </main>

      <Footer />
    </div>
  );
}
