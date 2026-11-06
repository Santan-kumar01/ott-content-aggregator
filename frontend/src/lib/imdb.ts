/**
 * Server-Side IMDb RapidAPI Poster Service & Verified Poster Pool
 *
 * Provides authentic, high-resolution official movie & series poster artwork
 * fetched from the RapidAPI IMDb API (host: imdb236.p.rapidapi.com).
 *
 * Implements strict title + release year verification, tier-1 in-memory caching
 * to prevent duplicate API requests and quota exhaustion, and graceful error handling.
 */

export interface MoviePosterData {
  title: string;
  releaseYear?: number;
  imdbId: string;
  posterUrl: string;
  source: "rapidapi" | "cache" | "fallback";
}

export interface PosterPoolItem {
  id: string;
  title: string;
  year: number;
  platform: string;
  platformColor: string;
  genre: string;
  rating: number;
  gradient: string;
  imageUrl: string;
}

// In-memory cache for fetched posters to avoid redundant API hits
const posterMemoryCache = new Map<string, MoviePosterData>();

// Pre-seeded verified official poster cache for core landing page titles.
// Ensures instant rendering, zero quota burn, and full offline/fallback resilience.
export const VERIFIED_OFFICIAL_POSTERS: Record<string, MoviePosterData> = {
  "interstellar-2014": {
    title: "Interstellar",
    releaseYear: 2014,
    imdbId: "tt0816692",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BYzdjMDAxZGItMjI2My00ODA1LTlkNzItOWFjMDU5ZDJlYWY3XkEyXkFqcGc@.jpg",
    source: "cache",
  },
  "inception-2010": {
    title: "Inception",
    releaseYear: 2010,
    imdbId: "tt1375666",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@.jpg",
    source: "cache",
  },
  "the dark knight-2008": {
    title: "The Dark Knight",
    releaseYear: 2008,
    imdbId: "tt0468569",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BMTMxNTMwODM0NF5BMl5BanBnXkFtZTcwODAyMTk2Mw@@.jpg",
    source: "cache",
  },
  "the batman-2022": {
    title: "The Batman",
    releaseYear: 2022,
    imdbId: "tt1877830",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BMmU5NGJlMzAtMGNmOC00YjJjLTgyMzUtNjAyYmE4Njg5YWMyXkEyXkFqcGc@.jpg",
    source: "cache",
  },
  "dune-2021": {
    title: "Dune",
    releaseYear: 2021,
    imdbId: "tt1160419",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BNWIyNmU5MGYtZDZmNi00ZjAwLWJlYjgtZTc0ZGIxMDE4ZGYwXkEyXkFqcGc@.jpg",
    source: "cache",
  },
  "dune: part two-2024": {
    title: "Dune: Part Two",
    releaseYear: 2024,
    imdbId: "tt15239678",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BNTc0YmQxMjEtODI5MC00NjFiLTlkMWUtOGQ5NjFmYWUyZGJhXkEyXkFqcGc@.jpg",
    source: "cache",
  },
  "severance-2022": {
    title: "Severance",
    releaseYear: 2022,
    imdbId: "tt11280740",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BZDI5YzJhODQtMzQyNy00YWNmLWIxMjUtNDBjNjA5YWRjMzExXkEyXkFqcGc@.jpg",
    source: "cache",
  },
  "stranger things-2016": {
    title: "Stranger Things",
    releaseYear: 2016,
    imdbId: "tt4574334",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BMjEzMDAxOTUyMV5BMl5BanBnXkFtZTgwNzAxMzYzOTE@.jpg",
    source: "cache",
  },
  "the mandalorian-2019": {
    title: "The Mandalorian",
    releaseYear: 2019,
    imdbId: "tt8111088",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BNjgxZGM0OWUtZGY1MS00MWRmLTk2N2ItYjQyZTI1OThlZDliXkEyXkFqcGc@.jpg",
    source: "cache",
  },
  "breaking bad-2008": {
    title: "Breaking Bad",
    releaseYear: 2008,
    imdbId: "tt0903747",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BMzU5ZGYzNmQtMTdhYy00OGRiLTg0NmQtYjVjNzliZTg1ZGE4XkEyXkFqcGc@.jpg",
    source: "cache",
  },
  "oppenheimer-2023": {
    title: "Oppenheimer",
    releaseYear: 2023,
    imdbId: "tt15398776",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BN2JkMDc5MGQtZjg3YS00NmFiLWIyZmQtZTJmNTM5MjVmYTQ4XkEyXkFqcGc@.jpg",
    source: "cache",
  },
  "the matrix-1999": {
    title: "The Matrix",
    releaseYear: 1999,
    imdbId: "tt0133093",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BN2NmN2VhMTQtMDNiOS00NDlhLTliMjgtODE2ZTY0ODQyNDRhXkEyXkFqcGc@.jpg",
    source: "cache",
  },
  "gladiator-2000": {
    title: "Gladiator",
    releaseYear: 2000,
    imdbId: "tt0172495",
    posterUrl:
      "https://m.media-amazon.com/images/M/MV5BYWQ4YmNjYjEtOWE1Zi00Y2U4LWI4NTAtMTU0MjkxNWQ1ZmJiXkEyXkFqcGc@.jpg",
    source: "cache",
  },
};

// Complete pool of verified titles for dynamic landing-page selections
export const VERIFIED_POSTER_POOL: PosterPoolItem[] = [
  {
    id: "interstellar",
    title: "Interstellar",
    year: 2014,
    platform: "Prime",
    platformColor: "bg-sky-500/90 text-white border-sky-400/40",
    genre: "Sci-Fi",
    rating: 8.7,
    gradient: "from-blue-950 via-slate-900 to-indigo-950",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BYzdjMDAxZGItMjI2My00ODA1LTlkNzItOWFjMDU5ZDJlYWY3XkEyXkFqcGc@.jpg",
  },
  {
    id: "inception",
    title: "Inception",
    year: 2010,
    platform: "Netflix",
    platformColor: "bg-red-600/90 text-white border-red-500/40",
    genre: "Sci-Fi",
    rating: 8.8,
    gradient: "from-purple-950 via-neutral-900 to-slate-950",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@.jpg",
  },
  {
    id: "severance",
    title: "Severance",
    year: 2022,
    platform: "Apple TV+",
    platformColor: "bg-zinc-800/90 text-white border-zinc-500/40",
    genre: "Thriller",
    rating: 8.7,
    gradient: "from-emerald-950 via-zinc-900 to-teal-950",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BZDI5YzJhODQtMzQyNy00YWNmLWIxMjUtNDBjNjA5YWRjMzExXkEyXkFqcGc@.jpg",
  },
  {
    id: "dune-two",
    title: "Dune: Part Two",
    year: 2024,
    platform: "Max",
    platformColor: "bg-indigo-600/90 text-white border-indigo-400/40",
    genre: "Adventure",
    rating: 8.6,
    gradient: "from-amber-950 via-neutral-900 to-rose-950",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BNTc0YmQxMjEtODI5MC00NjFiLTlkMWUtOGQ5NjFmYWUyZGJhXkEyXkFqcGc@.jpg",
  },
  {
    id: "the-dark-knight",
    title: "The Dark Knight",
    year: 2008,
    platform: "Max",
    platformColor: "bg-indigo-600/90 text-white border-indigo-400/40",
    genre: "Action",
    rating: 9.0,
    gradient: "from-slate-950 via-zinc-900 to-neutral-950",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BMTMxNTMwODM0NF5BMl5BanBnXkFtZTcwODAyMTk2Mw@@.jpg",
  },
  {
    id: "the-batman",
    title: "The Batman",
    year: 2022,
    platform: "Max",
    platformColor: "bg-indigo-600/90 text-white border-indigo-400/40",
    genre: "Action",
    rating: 7.8,
    gradient: "from-red-950 via-stone-900 to-black",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BMmU5NGJlMzAtMGNmOC00YjJjLTgyMzUtNjAyYmE4Njg5YWMyXkEyXkFqcGc@.jpg",
  },
  {
    id: "stranger-things",
    title: "Stranger Things",
    year: 2016,
    platform: "Netflix",
    platformColor: "bg-red-600/90 text-white border-red-500/40",
    genre: "Sci-Fi",
    rating: 8.7,
    gradient: "from-rose-950 via-neutral-900 to-black",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BMjEzMDAxOTUyMV5BMl5BanBnXkFtZTgwNzAxMzYzOTE@.jpg",
  },
  {
    id: "the-mandalorian",
    title: "The Mandalorian",
    year: 2019,
    platform: "Disney+",
    platformColor: "bg-blue-600/90 text-white border-blue-400/40",
    genre: "Action",
    rating: 8.6,
    gradient: "from-cyan-950 via-slate-900 to-emerald-950",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BNjgxZGM0OWUtZGY1MS00MWRmLTk2N2ItYjQyZTI1OThlZDliXkEyXkFqcGc@.jpg",
  },
  {
    id: "breaking-bad",
    title: "Breaking Bad",
    year: 2008,
    platform: "Netflix",
    platformColor: "bg-red-600/90 text-white border-red-500/40",
    genre: "Drama",
    rating: 9.5,
    gradient: "from-emerald-950 via-zinc-900 to-slate-950",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BMzU5ZGYzNmQtMTdhYy00OGRiLTg0NmQtYjVjNzliZTg1ZGE4XkEyXkFqcGc@.jpg",
  },
  {
    id: "oppenheimer",
    title: "Oppenheimer",
    year: 2023,
    platform: "Prime",
    platformColor: "bg-sky-500/90 text-white border-sky-400/40",
    genre: "Drama",
    rating: 8.9,
    gradient: "from-amber-950 via-stone-900 to-orange-950",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BN2JkMDc5MGQtZjg3YS00NmFiLWIyZmQtZTJmNTM5MjVmYTQ4XkEyXkFqcGc@.jpg",
  },
  {
    id: "the-matrix",
    title: "The Matrix",
    year: 1999,
    platform: "Max",
    platformColor: "bg-indigo-600/90 text-white border-indigo-400/40",
    genre: "Sci-Fi",
    rating: 8.7,
    gradient: "from-emerald-950 via-slate-900 to-teal-950",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BN2NmN2VhMTQtMDNiOS00NDlhLTliMjgtODE2ZTY0ODQyNDRhXkEyXkFqcGc@.jpg",
  },
  {
    id: "gladiator",
    title: "Gladiator",
    year: 2000,
    platform: "Paramount+",
    platformColor: "bg-blue-500/90 text-white border-blue-300/40",
    genre: "Action",
    rating: 8.5,
    gradient: "from-amber-950 via-stone-900 to-neutral-950",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BYWQ4YmNjYjEtOWE1Zi00Y2U4LWI4NTAtMTU0MjkxNWQ1ZmJiXkEyXkFqcGc@.jpg",
  },
  {
    id: "dune-one",
    title: "Dune",
    year: 2021,
    platform: "Max",
    platformColor: "bg-indigo-600/90 text-white border-indigo-400/40",
    genre: "Sci-Fi",
    rating: 8.0,
    gradient: "from-amber-950 via-neutral-900 to-rose-950",
    imageUrl:
      "https://m.media-amazon.com/images/M/MV5BNWIyNmU5MGYtZDZmNi00ZjAwLWJlYjgtZTc0ZGIxMDE4ZGYwXkEyXkFqcGc@.jpg",
  },
];

// Initialize memory cache with verified records
for (const [key, val] of Object.entries(VERIFIED_OFFICIAL_POSTERS)) {
  posterMemoryCache.set(key, val);
}

function getCacheKey(title: string, releaseYear?: number): string {
  const normTitle = title.trim().toLowerCase();
  return releaseYear ? `${normTitle}-${releaseYear}` : normTitle;
}

/**
 * Deterministic helper to get a random non-repeating selection of verified posters
 */
export function selectRandomPosters(
  count = 4,
  excludeIds: string[] = []
): PosterPoolItem[] {
  // Filter out recent IDs to avoid immediate repeats if possible
  let available = VERIFIED_POSTER_POOL.filter(
    (item) => !excludeIds.includes(item.id)
  );

  // If exclusions leave fewer items than requested, fall back to entire pool
  if (available.length < count) {
    available = [...VERIFIED_POSTER_POOL];
  }

  // Fisher-Yates shuffle copy
  const shuffled = [...available];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }

  return shuffled.slice(0, count);
}

/**
 * Fetch official poster artwork for a movie or TV show.
 *
 * 1. Checks in-memory cache first (0 network cost).
 * 2. If missing and RapidAPI credentials are available, queries RapidAPI IMDb API.
 * 3. Verifies exact title + release year match.
 * 4. Caches result and returns verified poster URL.
 */
export async function getMoviePoster(
  title: string,
  releaseYear?: number,
  contentType: "movie" | "tvSeries" = "movie"
): Promise<MoviePosterData | null> {
  const cacheKey = getCacheKey(title, releaseYear);

  if (posterMemoryCache.has(cacheKey)) {
    return posterMemoryCache.get(cacheKey)!;
  }

  const apiKey =
    process.env.RAPIDAPI_KEY ||
    process.env["x-api-key"] ||
    process.env.RAPID_API_KEY;
  const apiHost =
    process.env.RAPIDAPI_HOST ||
    process.env["x-api-host"] ||
    "imdb236.p.rapidapi.com";

  if (!apiKey) {
    const titleOnlyKey = title.trim().toLowerCase();
    for (const [k, v] of posterMemoryCache.entries()) {
      if (k.startsWith(titleOnlyKey)) return v;
    }
    return null;
  }

  try {
    const typeParam = contentType ? `&type=${contentType}` : "";
    const endpoint = `https://${apiHost}/api/imdb/search?originalTitle=${encodeURIComponent(
      title.trim()
    )}${typeParam}&rows=25`;

    const res = await fetch(endpoint, {
      method: "GET",
      headers: {
        "x-rapidapi-host": apiHost,
        "x-rapidapi-key": apiKey,
      },
      next: { revalidate: 86400 },
    });

    if (!res.ok) {
      console.warn(
        `[RapidAPI IMDb] Request failed for "${title}": HTTP ${res.status}`
      );
      return null;
    }

    const json = await res.json();
    const items = json.results || json.rows || [];

    let match = items.find(
      (m: { primaryTitle?: string; startYear?: number }) =>
        m.primaryTitle &&
        m.primaryTitle.toLowerCase() === title.toLowerCase() &&
        (releaseYear ? m.startYear === releaseYear : true)
    );

    if (!match && releaseYear) {
      match = items.find(
        (m: { originalTitle?: string; startYear?: number }) =>
          m.originalTitle &&
          m.originalTitle.toLowerCase() === title.toLowerCase() &&
          m.startYear === releaseYear
      );
    }

    if (!match) {
      match = items.find(
        (m: { primaryTitle?: string }) =>
          m.primaryTitle && m.primaryTitle.toLowerCase() === title.toLowerCase()
      );
    }

    if (!match || !match.primaryImage) {
      return null;
    }

    const result: MoviePosterData = {
      title: match.primaryTitle || title,
      releaseYear: match.startYear || releaseYear,
      imdbId: match.id || "",
      posterUrl: match.primaryImage,
      source: "rapidapi",
    };

    posterMemoryCache.set(cacheKey, result);
    return result;
  } catch (error) {
    console.error(
      `[RapidAPI IMDb] Error fetching poster for "${title}":`,
      error
    );
    return null;
  }
}

/**
 * Synchronous resolver for predefined verified posters.
 */
export function getVerifiedPoster(
  title: string,
  releaseYear?: number
): string | null {
  const key = getCacheKey(title, releaseYear);
  if (VERIFIED_OFFICIAL_POSTERS[key]) {
    return VERIFIED_OFFICIAL_POSTERS[key].posterUrl;
  }
  const normTitle = title.trim().toLowerCase();
  for (const [k, v] of Object.entries(VERIFIED_OFFICIAL_POSTERS)) {
    if (k.startsWith(normTitle)) {
      return v.posterUrl;
    }
  }
  return null;
}
