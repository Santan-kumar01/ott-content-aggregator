/**
 * OTT Content Aggregator - Catalog Service
 *
 * Interfaces with backend endpoints:
 * - GET /api/v1/titles/paginated
 * - GET /api/v1/titles/{id}
 * - GET /api/v1/titles
 *
 * Enriches titles with verified IMDb poster artwork, handles sorting/filtering,
 * and provides robust fallback support when the backend or database is offline.
 */

import { api, ApiError } from "@/lib/api";
import { getVerifiedPoster } from "@/lib/imdb";
import type { Title, PaginatedTitles, TitleFilterParams, Platform } from "@/types";

// Enriched Title with display attributes
export interface EnrichedTitle extends Title {
  posterUrl: string | null;
  rating?: number;
}

export interface EnrichedPaginatedTitles {
  items: EnrichedTitle[];
  total: number;
  skip: number;
  limit: number;
  has_next: boolean;
  isFallback?: boolean;
}

// Comprehensive seed dataset matching FastAPI Title model
export const FALLBACK_CATALOG: EnrichedTitle[] = [
  {
    id: 1,
    name: "Interstellar",
    description: "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival as Earth faces catastrophic famine.",
    content_type: "movie",
    release_year: 2014,
    genre: "Sci-Fi",
    platform: "Prime",
    created_at: "2024-01-01T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BYzdjMDAxZGItMjI2My00ODA1LTlkNzItOWFjMDU5ZDJlYWY3XkEyXkFqcGc@.jpg",
    rating: 8.7,
  },
  {
    id: 2,
    name: "Inception",
    description: "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
    content_type: "movie",
    release_year: 2010,
    genre: "Sci-Fi",
    platform: "Netflix",
    created_at: "2024-01-02T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@.jpg",
    rating: 8.8,
  },
  {
    id: 3,
    name: "The Dark Knight",
    description: "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.",
    content_type: "movie",
    release_year: 2008,
    genre: "Action",
    platform: "Max",
    created_at: "2024-01-03T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BMTMxNTMwODM0NF5BMl5BanBnXkFtZTcwODAyMTk2Mw@@.jpg",
    rating: 9.0,
  },
  {
    id: 4,
    name: "The Batman",
    description: "When a sadistic serial killer begins murdering key political figures in Gotham, Batman is forced to investigate the city's hidden corruption and question his family's involvement.",
    content_type: "movie",
    release_year: 2022,
    genre: "Action",
    platform: "Max",
    created_at: "2024-01-04T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BMmU5NGJlMzAtMGNmOC00YjJjLTgyMzUtNjAyYmE4Njg5YWMyXkEyXkFqcGc@.jpg",
    rating: 7.8,
  },
  {
    id: 5,
    name: "Dune: Part Two",
    description: "Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family, facing a choice between love and the fate of the universe.",
    content_type: "movie",
    release_year: 2024,
    genre: "Adventure",
    platform: "Max",
    created_at: "2024-01-05T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BNTc0YmQxMjEtODI5MC00NjFiLTlkMWUtOGQ5NjFmYWUyZGJhXkEyXkFqcGc@.jpg",
    rating: 8.6,
  },
  {
    id: 6,
    name: "Dune",
    description: "A noble family becomes embroiled in a war for control over the galaxy's most valuable asset while its heir becomes troubled by visions of a dark future.",
    content_type: "movie",
    release_year: 2021,
    genre: "Sci-Fi",
    platform: "Max",
    created_at: "2024-01-06T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BNWIyNmU5MGYtZDZmNi00ZjAwLWJlYjgtZTc0ZGIxMDE4ZGYwXkEyXkFqcGc@.jpg",
    rating: 8.0,
  },
  {
    id: 7,
    name: "Severance",
    description: "Mark leads a team of office workers whose memories have been surgically divided between their work and personal lives. When a mysterious colleague appears outside of work, it begins a journey to discover the truth.",
    content_type: "show",
    release_year: 2022,
    genre: "Thriller",
    platform: "Apple TV+",
    created_at: "2024-01-07T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BZDI5YzJhODQtMzQyNy00YWNmLWIxMjUtNDBjNjA5YWRjMzExXkEyXkFqcGc@.jpg",
    rating: 8.7,
  },
  {
    id: 8,
    name: "Stranger Things",
    description: "When a young boy vanishes, a small town uncovers a mystery involving secret experiments, terrifying supernatural forces and one strange little girl.",
    content_type: "show",
    release_year: 2016,
    genre: "Sci-Fi",
    platform: "Netflix",
    created_at: "2024-01-08T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BMjEzMDAxOTUyMV5BMl5BanBnXkFtZTgwNzAxMzYzOTE@.jpg",
    rating: 8.7,
  },
  {
    id: 9,
    name: "The Mandalorian",
    description: "The travels of a lone bounty hunter in the outer reaches of the galaxy, far from the authority of the New Republic.",
    content_type: "show",
    release_year: 2019,
    genre: "Action",
    platform: "Disney+",
    created_at: "2024-01-09T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BNjgxZGM0OWUtZGY1MS00MWRmLTk2N2ItYjQyZTI1OThlZDliXkEyXkFqcGc@.jpg",
    rating: 8.6,
  },
  {
    id: 10,
    name: "Breaking Bad",
    description: "A chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing and selling methamphetamine with a former student in order to secure his family's financial future.",
    content_type: "show",
    release_year: 2008,
    genre: "Drama",
    platform: "Netflix",
    created_at: "2024-01-10T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BMzU5ZGYzNmQtMTdhYy00OGRiLTg0NmQtYjVjNzliZTg1ZGE4XkEyXkFqcGc@.jpg",
    rating: 9.5,
  },
  {
    id: 11,
    name: "Oppenheimer",
    description: "The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb during World War II.",
    content_type: "movie",
    release_year: 2023,
    genre: "Drama",
    platform: "Prime",
    created_at: "2024-01-11T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BN2JkMDc5MGQtZjg3YS00NmFiLWIyZmQtZTJmNTM5MjVmYTQ4XkEyXkFqcGc@.jpg",
    rating: 8.9,
  },
  {
    id: 12,
    name: "The Matrix",
    description: "When a beautiful stranger leads computer hacker Neo to a forbidding underworld, he discovers the shocking truth--the life he knows is the elaborate deception of an evil cyber-intelligence.",
    content_type: "movie",
    release_year: 1999,
    genre: "Sci-Fi",
    platform: "Max",
    created_at: "2024-01-12T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BN2NmN2VhMTQtMDNiOS00NDlhLTliMjgtODE2ZTY0ODQyNDRhXkEyXkFqcGc@.jpg",
    rating: 8.7,
  },
  {
    id: 13,
    name: "Gladiator",
    description: "A former Roman General sets out to exact vengeance against the corrupt emperor who murdered his family and sent him into slavery.",
    content_type: "movie",
    release_year: 2000,
    genre: "Action",
    platform: "Paramount+",
    created_at: "2024-01-13T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BYWQ4YmNjYjEtOWE1Zi00Y2U4LWI4NTAtMTU0MjkxNWQ1ZmJiXkEyXkFqcGc@.jpg",
    rating: 8.5,
  },
  {
    id: 14,
    name: "Shogun",
    description: "When a mysterious European ship is found marooned in a nearby fishing village, Lord Toranaga discovers secrets that could tip the scales of power and devastate his formidable enemies.",
    content_type: "show",
    release_year: 2024,
    genre: "Drama",
    platform: "Hulu",
    created_at: "2024-01-14T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BYTJlNmI0MmYtMzkxZi00ZmY0LWJjMjAtYTkwYjVjZDE5MmY4XkEyXkFqcGc@.jpg",
    rating: 8.8,
  },
  {
    id: 15,
    name: "Succession",
    description: "The Roy family is known for controlling the biggest media and entertainment company in the world. However, their world changes when their aging father steps down from the company.",
    content_type: "show",
    release_year: 2018,
    genre: "Drama",
    platform: "Max",
    created_at: "2024-01-15T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BNmU4M2YzMzktZGU3Yi00NzgxLTk5NDQtZThmY2Y5YWY0YWRmXkEyXkFqcGc@.jpg",
    rating: 8.9,
  },
  {
    id: 16,
    name: "Ted Lasso",
    description: "American college football coach Ted Lasso heads to London to manage AFC Richmond, a struggling English Premier League football team.",
    content_type: "show",
    release_year: 2020,
    genre: "Comedy",
    platform: "Apple TV+",
    created_at: "2024-01-16T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BMTdmMDdhNDEtZGI4MS00ODU5LWIyZjctOTM5NDY3Y2FmNTg5XkEyXkFqcGc@.jpg",
    rating: 8.8,
  },
  {
    id: 17,
    name: "The Bear",
    description: "A young fine-dining chef returns home to Chicago to run his family's Italian beef sandwich shop after a tragic suicide in his family.",
    content_type: "show",
    release_year: 2022,
    genre: "Comedy",
    platform: "Hulu",
    created_at: "2024-01-17T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BN2E2YmM1NTktMmJkMy00ZDJlLTk5ZjgtYzVkY2YxMDFhNGJmXkEyXkFqcGc@.jpg",
    rating: 8.6,
  },
  {
    id: 18,
    name: "Spider-Man: Across the Spider-Verse",
    description: "Miles Morales catapults across the Multiverse, where he encounters a team of Spider-People charged with protecting its very existence.",
    content_type: "movie",
    release_year: 2023,
    genre: "Action",
    platform: "Netflix",
    created_at: "2024-01-18T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BMzI0NmVkMjEtYmY4MS00ZDMxLTlkZmEtMzU3MzAxZjc1NWZhXkEyXkFqcGc@.jpg",
    rating: 8.7,
  },
  {
    id: 19,
    name: "The Last of Us",
    description: "After a global pandemic destroys civilization, a hardened survivor takes charge of a 14-year-old girl who may be humanity's last hope.",
    content_type: "show",
    release_year: 2023,
    genre: "Action",
    platform: "Max",
    created_at: "2024-01-19T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BYzA2Nzk5M2EtNWY4Yi00ZDY4LThkZTgtYjhhNzc4MmY0NjA2XkEyXkFqcGc@.jpg",
    rating: 8.8,
  },
  {
    id: 20,
    name: "Arcane",
    description: "Set in utopian Piltover and the oppressed underground of Zaun, the story follows the origins of two iconic League of Legends champions-and the power that will tear them apart.",
    content_type: "show",
    release_year: 2021,
    genre: "Animation",
    platform: "Netflix",
    created_at: "2024-01-20T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BYTc1NjQ3NjgtNDVhNC00MTUzLTlkMmQtMjVlNGVkZDA4M2NjXkEyXkFqcGc@.jpg",
    rating: 9.0,
  },
  {
    id: 21,
    name: "The Boys",
    description: "A fun and irreverent take on what happens when superheroes-who are as popular as celebrities, as influential as politicians, and as revered as gods-abuse their superpowers rather than use them for good.",
    content_type: "show",
    release_year: 2019,
    genre: "Action",
    platform: "Prime",
    created_at: "2024-01-21T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BODQ0MWQ0ODgtMmU1Yi00N2EzLWExNmQtOWVhMWU3OTNmYjM1XkEyXkFqcGc@.jpg",
    rating: 8.7,
  },
  {
    id: 22,
    name: "Avengers: Endgame",
    description: "After the devastating events of Avengers: Infinity War, the universe is in ruins. With the help of remaining allies, the Avengers assemble once more in order to reverse Thanos' actions.",
    content_type: "movie",
    release_year: 2019,
    genre: "Action",
    platform: "Disney+",
    created_at: "2024-01-22T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BMTc5MDE2ODcwNV5BMl5BanBnXkFtZTgwMzI2NzQ2NzM@.jpg",
    rating: 8.4,
  },
  {
    id: 23,
    name: "Loki",
    description: "The mercurial villain Loki resumes his role as the God of Mischief in a new series that takes place after the events of 'Avengers: Endgame'.",
    content_type: "show",
    release_year: 2021,
    genre: "Action",
    platform: "Disney+",
    created_at: "2024-01-23T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BN2E2YmM1NTktMmJkMy00ZDJlLTk5ZjgtYzVkY2YxMDFhNGJmXkEyXkFqcGc@.jpg",
    rating: 8.2,
  },
  {
    id: 24,
    name: "Yellowstone",
    description: "A ranching family in Montana faces off against others encroaching on their land.",
    content_type: "show",
    release_year: 2018,
    genre: "Drama",
    platform: "Peacock",
    created_at: "2024-01-24T00:00:00Z",
    posterUrl: "https://m.media-amazon.com/images/M/MV5BZTI4Y2Q1MGQtYjE3Yy00N2VkLTg5NWYtZDUxMTNmNjc2NTYxXkEyXkFqcGc@.jpg",
    rating: 8.7,
  },
];

/**
 * Enriches a raw Title from FastAPI with authentic poster art and rating
 */
export function enrichTitle(title: Title): EnrichedTitle {
  // Check predefined verified cache first
  const verifiedPoster = getVerifiedPoster(title.name, title.release_year);

  // Check fallback pool for matching rating / poster
  const matched = FALLBACK_CATALOG.find(
    (f) =>
      f.name.toLowerCase() === title.name.toLowerCase() &&
      f.release_year === title.release_year
  );

  return {
    ...title,
    posterUrl: verifiedPoster || matched?.posterUrl || null,
    rating: matched?.rating ?? undefined,
  };
}

/**
 * Fetch paginated titles from FastAPI backend with query filters.
 * Falls back transparently to client dataset if the backend is offline.
 */
export async function fetchPaginatedTitles(
  params: TitleFilterParams = {}
): Promise<EnrichedPaginatedTitles> {
  const {
    genre,
    platform,
    search,
    release_year,
    sort_by,
    sort_order = "asc",
    skip = 0,
    limit = 20,
  } = params;

  const queryParams: Record<string, string | number> = {
    skip,
    limit,
    sort_order,
  };

  if (genre && genre !== "All") queryParams.genre = genre;
  if (platform && platform !== "All") queryParams.platform = platform;
  if (search && search.trim()) queryParams.search = search.trim();
  if (release_year) queryParams.release_year = release_year;
  if (sort_by) queryParams.sort_by = sort_by;

  try {
    const rawData = await api.get<PaginatedTitles>("/api/v1/titles/paginated", {
      params: queryParams,
    });

    if (rawData && Array.isArray(rawData.items)) {
      return {
        items: rawData.items.map(enrichTitle),
        total: rawData.total,
        skip: rawData.skip,
        limit: rawData.limit,
        has_next: rawData.has_next,
        isFallback: false,
      };
    }
  } catch (error) {
    console.warn(
      "[CatalogService] Backend unavailable, using local verified dataset:",
      error instanceof Error ? error.message : error
    );
  }

  // Fallback filtering & sorting implementation
  return filterAndPaginateFallback(params);
}

/**
 * Client-side filter and pagination engine for offline mode
 */
function filterAndPaginateFallback(
  params: TitleFilterParams
): EnrichedPaginatedTitles {
  const {
    genre,
    platform,
    search,
    release_year,
    sort_by = "name",
    sort_order = "asc",
    skip = 0,
    limit = 20,
  } = params;

  let filtered = [...FALLBACK_CATALOG];

  if (genre && genre !== "All") {
    filtered = filtered.filter(
      (item) => item.genre.toLowerCase() === genre.toLowerCase()
    );
  }

  if (platform && platform !== "All") {
    filtered = filtered.filter(
      (item) => item.platform.toLowerCase() === platform.toLowerCase()
    );
  }

  if (search && search.trim()) {
    const query = search.trim().toLowerCase();
    filtered = filtered.filter(
      (item) =>
        item.name.toLowerCase().includes(query) ||
        (item.description && item.description.toLowerCase().includes(query))
    );
  }

  if (release_year) {
    filtered = filtered.filter((item) => item.release_year === release_year);
  }

  // Sort
  filtered.sort((a, b) => {
    let comp = 0;
    if (sort_by === "name") {
      comp = a.name.localeCompare(b.name);
    } else if (sort_by === "release_year") {
      comp = a.release_year - b.release_year;
    } else if (sort_by === "created_at") {
      comp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    }
    return sort_order === "desc" ? -comp : comp;
  });

  const total = filtered.length;
  const items = filtered.slice(skip, skip + limit);
  const has_next = skip + limit < total;

  return {
    items,
    total,
    skip,
    limit,
    has_next,
    isFallback: true,
  };
}

/**
 * Fetch a single title by its numeric ID
 */
export async function fetchTitleById(id: number): Promise<EnrichedTitle> {
  try {
    const raw = await api.get<Title>(`/api/v1/titles/${id}`);
    if (raw && raw.id) {
      return enrichTitle(raw);
    }
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      // If server explicitly returned 404, check fallback
      const fallbackItem = FALLBACK_CATALOG.find((t) => t.id === id);
      if (fallbackItem) return fallbackItem;
      throw error;
    }
    console.warn(
      `[CatalogService] Backend request failed for title ${id}, checking fallback pool:`,
      error instanceof Error ? error.message : error
    );
  }

  // Check fallback pool
  const found = FALLBACK_CATALOG.find((t) => t.id === id);
  if (found) {
    return found;
  }

  throw new ApiError(404, "Title not found");
}

/**
 * Fetch similar titles based on genre or platform
 */
export async function fetchSimilarTitles(
  currentId: number,
  genre?: string,
  platform?: Platform,
  limit = 4
): Promise<EnrichedTitle[]> {
  try {
    const res = await fetchPaginatedTitles({
      genre: genre || undefined,
      limit: 10,
    });
    return res.items
      .filter((t) => t.id !== currentId)
      .slice(0, limit);
  } catch {
    return FALLBACK_CATALOG.filter((t) => t.id !== currentId && t.genre === genre).slice(0, limit);
  }
}
