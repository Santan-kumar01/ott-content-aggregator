/**
 * OTT Content Aggregator - Shared Frontend Type Definitions
 *
 * Aligned with backend schemas from FastAPI models:
 * - Title and PaginatedTitleRead
 * - User and Token
 * - VoiceSearchResponse and QueryIntent
 */

export type ContentType = "movie" | "show";

export type Platform =
  | "Netflix"
  | "Prime"
  | "Disney+"
  | "Max"
  | "Apple TV+"
  | "Hulu"
  | "Paramount+"
  | "Peacock"
  | string;

export interface Title {
  id: number;
  name: string;
  description?: string | null;
  content_type: ContentType;
  release_year: number;
  genre: string;
  platform: Platform;
  created_at: string;
}

export interface PaginatedTitles {
  items: Title[];
  total: number;
  skip: number;
  limit: number;
  has_next: boolean;
}

export interface TitleFilterParams {
  genre?: string;
  platform?: string;
  search?: string;
  release_year?: number;
  sort_by?: "name" | "release_year" | "created_at";
  sort_order?: "asc" | "desc";
  skip?: number;
  limit?: number;
}

export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
}

export interface ParsedVoiceQuery {
  search_query?: string | null;
  cleaned_query: string;
  genre?: string | null;
  platform?: string | null;
  release_year?: number | null;
  content_type?: ContentType | null;
  intent: "search" | "filter" | "similarity" | "empty";
  confidence?: number;
}

export interface VoiceSearchResponse {
  transcription: string;
  parsed_query: ParsedVoiceQuery;
  titles: Title[];
  count: number;
  total: number;
}

