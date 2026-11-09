"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Sparkles, ArrowRight, Clapperboard } from "lucide-react";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { MovieCard } from "@/components/movies/MovieCard";
import { cn } from "@/lib/utils";
import type { ContentType, Platform } from "@/types";

interface FeaturedMovie {
  id: number;
  title: string;
  releaseYear: number;
  genre: string;
  platform: Platform;
  contentType: ContentType;
  rating: number;
  description: string;
  posterUrl?: string;
  featured?: boolean;
}

const FEATURED_TITLES: FeaturedMovie[] = [
  {
    id: 1,
    title: "Inception",
    releaseYear: 2010,
    genre: "Sci-Fi",
    platform: "Netflix",
    contentType: "movie",
    rating: 8.8,
    description:
      "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea.",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@.jpg",
    featured: true,
  },
  {
    id: 2,
    title: "Interstellar",
    releaseYear: 2014,
    genre: "Sci-Fi",
    platform: "Prime",
    contentType: "movie",
    rating: 8.7,
    description:
      "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival across distant galaxies.",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BYzdjMDAxZGItMjI2My00ODA1LTlkNzItOWFjMDU5ZDJlYWY3XkEyXkFqcGc@.jpg",
  },
  {
    id: 3,
    title: "The Dark Knight",
    releaseYear: 2008,
    genre: "Action",
    platform: "Max",
    contentType: "movie",
    rating: 9.0,
    description:
      "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest tests.",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BMTMxNTMwODM0NF5BMl5BanBnXkFtZTcwODAyMTk2Mw@@.jpg",
    featured: true,
  },
  {
    id: 4,
    title: "The Batman",
    releaseYear: 2022,
    genre: "Action",
    platform: "Max",
    contentType: "movie",
    rating: 7.8,
    description:
      "When a sadistic serial killer begins murdering key political figures in Gotham, the Batman is forced to investigate the city's hidden corruption.",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BMmU5NGJlMzAtMGNmOC00YjJjLTgyMzUtNjAyYmE4Njg5YWMyXkEyXkFqcGc@.jpg",
  },
  {
    id: 5,
    title: "Severance",
    releaseYear: 2022,
    genre: "Drama",
    platform: "Apple TV+",
    contentType: "show",
    rating: 8.7,
    description:
      "Mark leads a team of office workers whose memories have been surgically divided between their work and personal lives.",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BZDI5YzJhODQtMzQyNy00YWNmLWIxMjUtNDBjNjA5YWRjMzExXkEyXkFqcGc@.jpg",
  },
  {
    id: 6,
    title: "Stranger Things",
    releaseYear: 2016,
    genre: "Sci-Fi",
    platform: "Netflix",
    contentType: "show",
    rating: 8.7,
    description:
      "When a young boy vanishes, a small town uncovers a mystery involving secret experiments, terrifying supernatural forces and one strange little girl.",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BMjEzMDAxOTUyMV5BMl5BanBnXkFtZTgwNzAxMzYzOTE@.jpg",
  },
  {
    id: 7,
    title: "Dune: Part Two",
    releaseYear: 2024,
    genre: "Sci-Fi",
    platform: "Max",
    contentType: "movie",
    rating: 8.6,
    description:
      "Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BNTc0YmQxMjEtODI5MC00NjFiLTlkMWUtOGQ5NjFmYWUyZGJhXkEyXkFqcGc@.jpg",
  },
  {
    id: 8,
    title: "The Mandalorian",
    releaseYear: 2019,
    genre: "Action",
    platform: "Disney+",
    contentType: "show",
    rating: 8.6,
    description:
      "The travels of a lone bounty hunter in the outer reaches of the galaxy, far from the authority of the New Republic.",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BNjgxZGM0OWUtZGY1MS00MWRmLTk2N2ItYjQyZTI1OThlZDliXkEyXkFqcGc@.jpg",
  },
  {
    id: 9,
    title: "Breaking Bad",
    releaseYear: 2008,
    genre: "Drama",
    platform: "Netflix",
    contentType: "show",
    rating: 9.5,
    description:
      "A chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing and selling methamphetamine with a former student.",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BMzU5ZGYzNmQtMTdhYy00OGRiLTg0NmQtYjVjNzliZTg1ZGE4XkEyXkFqcGc@.jpg",
  },
];

const FILTER_TABS = ["All", "Movies", "TV Shows", "Sci-Fi", "Action", "Drama"];

export function FeaturedSection({ className }: { className?: string }) {
  const [activeTab, setActiveTab] = useState("All");

  const filteredTitles = FEATURED_TITLES.filter((item) => {
    if (activeTab === "All") return true;
    if (activeTab === "Movies") return item.contentType === "movie";
    if (activeTab === "TV Shows") return item.contentType === "show";
    return item.genre.toLowerCase() === activeTab.toLowerCase();
  });

  return (
    <section
      id="featured"
      className={cn("py-20 sm:py-28 relative overflow-hidden", className)}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-12">
          <SectionHeading
            badge="CURATED SPOTLIGHT"
            badgeIcon={<Sparkles className="size-3.5 text-purple-400" />}
            title="Trending & Top-Rated"
            highlight="Across Platforms"
            description="Explore critically acclaimed titles aggregated from top streaming services with verified ratings and instant availability."
            centered={false}
          />

          {/* Interactive Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5 p-1 rounded-2xl bg-zinc-950/80 border border-white/10 backdrop-blur-md self-start md:self-auto">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={cn(
                  "px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 cursor-pointer",
                  activeTab === tab
                    ? "bg-purple-600 text-white shadow-md shadow-purple-600/30"
                    : "text-zinc-400 hover:text-white hover:bg-white/5"
                )}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Movie Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
          {filteredTitles.map((title) => (
            <MovieCard
              key={title.id}
              id={title.id}
              title={title.title}
              releaseYear={title.releaseYear}
              genre={title.genre}
              platform={title.platform}
              contentType={title.contentType}
              rating={title.rating}
              description={title.description}
              posterUrl={title.posterUrl}
              featured={title.featured}
            />
          ))}
        </div>

        {/* Bottom Discover CTA */}
        <div className="mt-14 text-center">
          <Link
            href="/discover"
            className={cn(
              "inline-flex items-center gap-2.5 px-6 py-3.5 rounded-2xl font-semibold text-sm",
              "bg-zinc-900 hover:bg-zinc-800 border border-white/15 hover:border-purple-500/40 text-white",
              "shadow-lg hover:shadow-purple-950/40 transition-all duration-200 group"
            )}
          >
            <Clapperboard className="size-4 text-purple-400" />
            <span>Explore Full Aggregated Catalog (10,000+ Titles)</span>
            <ArrowRight className="size-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </div>
    </section>
  );
}

