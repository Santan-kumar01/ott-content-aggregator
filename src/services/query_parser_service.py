"""Natural-language catalog query parser service.

Performs fast, deterministic parsing of natural-language and transcribed voice queries
for catalog search. Normalizes conversational prefixes, extracts search keywords,
detects genres, platforms, release years, and similarity intent without calling an LLM.
"""

import logging
import re
from typing import Any

from src.schemas.query import ParsedQuery

logger = logging.getLogger("src.services.query_parser_service")

# ---------------------------------------------------------------------------
# Canonical Genre Mappings
# ---------------------------------------------------------------------------

GENRE_MAP: dict[str, str] = {
    "action": "Action",
    "adventure": "Adventure",
    "adventures": "Adventure",
    "animation": "Animation",
    "animated": "Animation",
    "anime": "Animation",
    "cartoon": "Animation",
    "cartoons": "Animation",
    "biography": "Biography",
    "biographical": "Biography",
    "biopic": "Biography",
    "biopics": "Biography",
    "comedy": "Comedy",
    "comedies": "Comedy",
    "crime": "Crime",
    "documentary": "Documentary",
    "documentaries": "Documentary",
    "docuseries": "Documentary",
    "drama": "Drama",
    "dramas": "Drama",
    "family": "Family",
    "fantasy": "Fantasy",
    "horror": "Horror",
    "music": "Music",
    "musical": "Music",
    "musicals": "Music",
    "mystery": "Mystery",
    "mysteries": "Mystery",
    "romance": "Romance",
    "romantic": "Romance",
    "rom-com": "Romance",
    "romcom": "Romance",
    "sci-fi": "Sci-Fi",
    "scifi": "Sci-Fi",
    "sci fi": "Sci-Fi",
    "science fiction": "Sci-Fi",
    "thriller": "Thriller",
    "thrillers": "Thriller",
    "western": "Western",
    "westerns": "Western",
}

# ---------------------------------------------------------------------------
# Known Protected Titles (never strip command words or prefixes)
# ---------------------------------------------------------------------------

KNOWN_PROTECTED_TITLES: frozenset[str] = frozenset(
    {
        "find me guilty",
        "search party",
        "showgirls",
        "watchmen",
        "play misty for me",
        "get out",
        "get shorty",
        "look who's talking",
        "bring it on",
        "open your eyes",
        "her",
        "up",
        "it",
        "us",
        "them",
        "you",
        "seven",
        "se7en",
        "speed",
        "1917",
        "1984",
        "2001: a space odyssey",
        "blade runner 2049",
        "the dark knight",
        "the godfather",
        "the wire",
        "the matrix",
        "a quiet place",
        "to kill a mockingbird",
    }
)

# ---------------------------------------------------------------------------
# Platform Mappings
# ---------------------------------------------------------------------------

PLATFORM_MAP: dict[str, str] = {
    "netflix": "Netflix",
    "prime": "Prime",
    "prime video": "Prime",
    "amazon prime": "Prime",
    "disney+": "Disney+",
    "disney plus": "Disney+",
    "disney": "Disney+",
    "hulu": "Hulu",
    "hbo max": "HBO Max",
    "hbo": "HBO Max",
    "max": "Max",
    "apple tv": "Apple TV",
    "apple tv+": "Apple TV",
    "peacock": "Peacock",
    "paramount+": "Paramount+",
    "paramount plus": "Paramount+",
}

# ---------------------------------------------------------------------------
# Regular Expressions for Deterministic Parsing
# ---------------------------------------------------------------------------

# Trailing platform specification (e.g., "... on Netflix")
PLATFORM_SUFFIX_REGEX = re.compile(
    r"\s+(?:on|via|streaming on)\s+(netflix|prime(?:\s+video)?|amazon\s+prime|disney\+?|disney\s+plus|hulu|hbo\s+max|max|apple\s+tv\+?|peacock|paramount\+?|paramount\s+plus)$",
    re.IGNORECASE,
)

# Explicit release year specification (e.g., "... released in 2021", "... from 2020", "... (2019)")
RELEASE_YEAR_SUFFIX_REGEX = re.compile(
    r"(?:\s+\((19\d\d|20\d\d)\)|\s+(?:released\s+in|from\s+the\s+year|from|in)\s+(19\d\d|20\d\d))$",
    re.IGNORECASE,
)

# Similarity query pattern (e.g., "Find movies like Interstellar", "Shows like Breaking Bad")
SIMILARITY_REGEX = re.compile(
    r"^(?:(?:please\s+)?(?:can\s+you\s+|could\s+you\s+|would\s+you\s+)?(?:show\s+me|find|search\s+for|look\s+for|play|watch|recommend|suggest|give\s+me)\s+)?"
    r"(?:(?:the|any|some)\s+)?"
    r"(?:([a-zA-Z\-]+(?:\s+[a-zA-Z\-]+)?)\s+)?"
    r"(?:(movies?|films?|shows?|series|tv\s+shows?|titles?|something|anything))\s+"
    r"(?:like|similar\s+to)\s+(.+)$",
    re.IGNORECASE,
)

# Direct similarity without media noun (e.g., "similar to Interstellar", "like Inception")
SIMILARITY_DIRECT_REGEX = re.compile(
    r"^(?:(?:please\s+)?(?:can\s+you\s+|could\s+you\s+|would\s+you\s+)?(?:show\s+me|find|search\s+for|look\s+for|play|watch|recommend|suggest|give\s+me)\s+)?"
    r"(?:similar\s+to|like)\s+(.+)$",
    re.IGNORECASE,
)

# Conversational command prefix pattern
COMMAND_PREFIX_REGEX = re.compile(
    r"^(?:"
    r"(?:please\s+|can\s+you\s+|could\s+you\s+|would\s+you\s+|will\s+you\s+|hey\s+|hello\s+|hi\s+)*"
    r"(?:"
    r"show\s+me|"
    r"show|"
    r"search\s+for|"
    r"search|"
    r"find\s+me|"
    r"find|"
    r"look\s+for|"
    r"look\s+up|"
    r"i\s+want\s+to\s+watch|"
    r"i'd\s+like\s+to\s+watch|"
    r"i\s+would\s+like\s+to\s+watch|"
    r"let's\s+watch|"
    r"watch|"
    r"play|"
    r"bring\s+up|"
    r"get\s+me|"
    r"give\s+me|"
    r"open|"
    r"display|"
    r"where\s+can\s+i\s+watch|"
    r"where\s+to\s+watch|"
    r"put\s+on"
    r")\s+"
    r"(?:"
    r"(?:the|a|an)\s+(?:movie|film|show|series|tv\s+show|tv\s+series|season|episode)\s+|"
    r"(?:movies|films|shows|series|titles)\s+|"
    r"(?:movie|film|show|series)\s+"
    r")?"
    r"(?:called\s+|titled\s+|named\s+)?"
    r")",
    re.IGNORECASE,
)

# Pure genre pattern (e.g., "action movies", "comedy", "sci-fi shows")
MEDIA_SUFFIX_REGEX = re.compile(
    r"\s+(?:movies?|shows?|films?|series|tv\s+shows?|content|titles?|stuff)$",
    re.IGNORECASE,
)
LEADING_ARTICLE_REGEX = re.compile(
    r"^(?:the|any|some)\s+",
    re.IGNORECASE,
)

# Genre phrase pattern (e.g., "movies in the action genre", "comedy genre")
GENRE_PHRASE_REGEX = re.compile(
    r"^(?:(?:movies?|shows?|films?|series)\s+)?(?:in\s+the\s+|of\s+the\s+)?([a-zA-Z\-]+(?:\s+[a-zA-Z\-]+)?)\s+genre$",
    re.IGNORECASE,
)

# Genre + Media Descriptor + Title (e.g., "action movie Die Hard", "comedy show Friends")
GENRE_MEDIA_TITLE_REGEX = re.compile(
    r"^([a-zA-Z\-]+(?:\s+[a-zA-Z\-]+)?)\s+(movie|film|show|series|tv\s+show)\s+(?:called\s+|titled\s+|named\s+)?(.+)$",
    re.IGNORECASE,
)

# Trailing voice recognition punctuation (. ? ! , ; :)
TRAILING_PUNCTUATION_REGEX = re.compile(r"[\.\?\!\,\;]+$")


class QueryParserService:
    """Service that deterministically normalizes and parses catalog queries."""

    def parse(self, query: str | None) -> ParsedQuery:
        """Parse a natural language or voice query into structured catalog search parameters.

        Args:
            query: The raw string query (from voice transcription or user input).

        Returns:
            A ParsedQuery instance containing cleaned query text, search parameters,
            detected genre, platform, release year, content type, and intent.
        """
        if query is None:
            return self._empty_result("")

        raw = query
        text = raw.strip()
        if not text:
            return self._empty_result(raw)

        # 1. Clean outer quotes and trailing sentence punctuation
        text = self._strip_outer_quotes_and_punctuation(text)
        if not text:
            return self._empty_result(raw)

        # 2. Check for known protected titles immediately (e.g., "Find Me Guilty", "Up", "Her")
        lowered = text.lower()
        if lowered in KNOWN_PROTECTED_TITLES:
            return ParsedQuery(
                raw_query=raw,
                cleaned_query=text,
                search_query=text,
                genre=None,
                platform=None,
                release_year=None,
                content_type=None,
                is_similarity=False,
                similar_to=None,
                intent="search",
            )

        # 3. Detect and extract trailing streaming platform (e.g., "on Netflix")
        platform = None
        plat_match = PLATFORM_SUFFIX_REGEX.search(text)
        if plat_match:
            plat_key = plat_match.group(1).lower().strip()
            platform = PLATFORM_MAP.get(plat_key, plat_match.group(1).title())
            trimmed = text[: plat_match.start()].strip()
            if trimmed:
                text = trimmed

        # 4. Detect and extract release year (e.g., "released in 2021", "from 2020", "(2019)")
        release_year = None
        year_match = RELEASE_YEAR_SUFFIX_REGEX.search(text)
        if year_match:
            matched_year = year_match.group(1) or year_match.group(2)
            preceding = text[: year_match.start()].strip()
            if preceding:
                release_year = int(matched_year)
                text = preceding

        # 5. Check for similarity intent ("Find movies like Interstellar", "Shows like Breaking Bad")
        sim_result = self._check_similarity(raw, text, platform, release_year)
        if sim_result is not None:
            return sim_result

        # 6. Detect content type from initial phrasing
        content_type = self._detect_content_type(text)

        # 7. Strip conversational command prefix
        cleaned_text = self._strip_command_prefix(text)

        # If prefix stripping reduced the string to empty, keep the original text
        if not cleaned_text:
            cleaned_text = text

        # Re-check protected titles after command prefix strip (e.g. "Please find Find Me Guilty")
        if cleaned_text.lower() in KNOWN_PROTECTED_TITLES:
            return ParsedQuery(
                raw_query=raw,
                cleaned_query=cleaned_text,
                search_query=cleaned_text,
                genre=None,
                platform=platform,
                release_year=release_year,
                content_type=content_type,
                is_similarity=False,
                similar_to=None,
                intent="search",
            )

        # 8. Check for genre patterns in the remaining query
        # 8A. Pure genre search (e.g. "action movies", "find action movies", "comedy", "sci-fi")
        genre_result = self._check_pure_genre(
            raw, cleaned_text, platform, release_year, content_type
        )
        if genre_result is not None:
            return genre_result

        # 8B. Genre + Media + Title (e.g. "action movie Die Hard", "comedy show Friends")
        genre_title_result = self._check_genre_and_title(
            raw, cleaned_text, platform, release_year, content_type
        )
        if genre_title_result is not None:
            return genre_title_result

        # 8C. Generic media-only search (e.g. "show me movies", "watch shows")
        if cleaned_text.lower() in {
            "movie",
            "movies",
            "film",
            "films",
            "show",
            "shows",
            "series",
            "tv show",
            "tv shows",
            "titles",
        }:
            detected_type = (
                "movie"
                if cleaned_text.lower() in {"movie", "movies", "film", "films"}
                else "show"
            )
            return ParsedQuery(
                raw_query=raw,
                cleaned_query=cleaned_text,
                search_query=None,
                genre=None,
                platform=platform,
                release_year=release_year,
                content_type=detected_type,
                is_similarity=False,
                similar_to=None,
                intent="browse",
            )

        # 8D. Default title search (preserves full title, multiword titles, and punctuation)
        return ParsedQuery(
            raw_query=raw,
            cleaned_query=cleaned_text,
            search_query=cleaned_text,
            genre=None,
            platform=platform,
            release_year=release_year,
            content_type=content_type,
            is_similarity=False,
            similar_to=None,
            intent="search",
        )

    # -----------------------------------------------------------------------
    # Helper Methods
    # -----------------------------------------------------------------------

    def _empty_result(self, raw_query: str) -> ParsedQuery:
        return ParsedQuery(
            raw_query=raw_query,
            cleaned_query="",
            search_query=None,
            genre=None,
            platform=None,
            release_year=None,
            content_type=None,
            is_similarity=False,
            similar_to=None,
            intent="empty",
        )

    def _strip_outer_quotes_and_punctuation(self, text: str) -> str:
        text = text.strip("\"'“”‘’")
        text = TRAILING_PUNCTUATION_REGEX.sub("", text).strip()
        text = text.strip("\"'“”‘’")
        # Collapse internal multiple whitespace
        return re.sub(r"\s+", " ", text)

    def _detect_content_type(self, text: str) -> str | None:
        lowered = text.lower()
        # Avoid false matching of the command verb "show" or "show me" at the start
        text_without_show_verb = re.sub(
            r"^(?:(?:please\s+)?(?:can\s+you\s+|could\s+you\s+)?show(?:\s+me)?\s+)",
            "",
            lowered,
        ).strip()
        if re.search(r"\b(?:movies?|films?)\b", text_without_show_verb):
            return "movie"
        if re.search(
            r"\b(?:shows|series|tv\s+shows?|(?:the|a|an|tv|[a-z\-]+)\s+show)\b",
            text_without_show_verb,
        ):
            return "show"
        return None

    def _check_similarity(
        self,
        raw: str,
        text: str,
        platform: str | None,
        release_year: int | None,
    ) -> ParsedQuery | None:
        # Pattern 1: [prefix] [genre] [media] like [target]
        sim_match = SIMILARITY_REGEX.match(text)
        if sim_match:
            genre_candidate = sim_match.group(1)
            media_candidate = sim_match.group(2)
            target = sim_match.group(3).strip()
            target = self._strip_outer_quotes_and_punctuation(target)

            genre = None
            if genre_candidate and genre_candidate.lower() in GENRE_MAP:
                genre = GENRE_MAP[genre_candidate.lower()]

            content_type = None
            if media_candidate:
                if any(m in media_candidate.lower() for m in ["movie", "film"]):
                    content_type = "movie"
                elif any(
                    s in media_candidate.lower() for s in ["show", "series", "tv"]
                ):
                    content_type = "show"

            return ParsedQuery(
                raw_query=raw,
                cleaned_query=target,
                search_query=target,
                genre=genre,
                platform=platform,
                release_year=release_year,
                content_type=content_type,
                is_similarity=True,
                similar_to=target,
                intent="similar",
            )

        # Pattern 2: [prefix] similar to / like [target]
        direct_match = SIMILARITY_DIRECT_REGEX.match(text)
        if direct_match:
            target = direct_match.group(1).strip()
            target = self._strip_outer_quotes_and_punctuation(target)
            return ParsedQuery(
                raw_query=raw,
                cleaned_query=target,
                search_query=target,
                genre=None,
                platform=platform,
                release_year=release_year,
                content_type=None,
                is_similarity=True,
                similar_to=target,
                intent="similar",
            )

        return None

    def _strip_command_prefix(self, text: str) -> str:
        match = COMMAND_PREFIX_REGEX.match(text)
        if match:
            candidate = text[match.end() :].strip()
            candidate = self._strip_outer_quotes_and_punctuation(candidate)
            if candidate:
                return candidate
        return text

    def _check_pure_genre(
        self,
        raw: str,
        text: str,
        platform: str | None,
        release_year: int | None,
        existing_content_type: str | None,
    ) -> ParsedQuery | None:
        # Check phrase like "movies in the action genre" or "action genre"
        phrase_match = GENRE_PHRASE_REGEX.match(text)
        if phrase_match:
            candidate = phrase_match.group(1).lower().strip()
            if candidate in GENRE_MAP:
                canonical = GENRE_MAP[candidate]
                return ParsedQuery(
                    raw_query=raw,
                    cleaned_query=canonical,
                    search_query=None,
                    genre=canonical,
                    platform=platform,
                    release_year=release_year,
                    content_type=existing_content_type or "movie",
                    is_similarity=False,
                    similar_to=None,
                    intent="genre_search",
                )

        # Check pure genre by removing optional leading articles and trailing media nouns
        normalized = LEADING_ARTICLE_REGEX.sub("", text).strip()
        media_match = MEDIA_SUFFIX_REGEX.search(normalized)
        candidate = normalized
        detected_type = existing_content_type

        if media_match:
            media_word = media_match.group(0).lower().strip()
            if any(m in media_word for m in ["movie", "film"]):
                detected_type = detected_type or "movie"
            elif any(s in media_word for s in ["show", "series", "tv"]):
                detected_type = detected_type or "show"
            candidate = normalized[: media_match.start()].strip()

        candidate_key = candidate.lower().strip()
        if candidate_key in GENRE_MAP:
            canonical = GENRE_MAP[candidate_key]
            return ParsedQuery(
                raw_query=raw,
                cleaned_query=canonical,
                search_query=None,
                genre=canonical,
                platform=platform,
                release_year=release_year,
                content_type=detected_type,
                is_similarity=False,
                similar_to=None,
                intent="genre_search",
            )

        return None

    def _check_genre_and_title(
        self,
        raw: str,
        text: str,
        platform: str | None,
        release_year: int | None,
        existing_content_type: str | None,
    ) -> ParsedQuery | None:
        match = GENRE_MEDIA_TITLE_REGEX.match(text)
        if match:
            genre_candidate = match.group(1).lower().strip()
            media_candidate = match.group(2).lower().strip()
            title_candidate = match.group(3).strip()
            title_candidate = self._strip_outer_quotes_and_punctuation(title_candidate)

            if genre_candidate in GENRE_MAP and title_candidate:
                canonical_genre = GENRE_MAP[genre_candidate]
                content_type = existing_content_type
                if any(m in media_candidate for m in ["movie", "film"]):
                    content_type = "movie"
                elif any(s in media_candidate for s in ["show", "series", "tv"]):
                    content_type = "show"

                return ParsedQuery(
                    raw_query=raw,
                    cleaned_query=title_candidate,
                    search_query=title_candidate,
                    genre=canonical_genre,
                    platform=platform,
                    release_year=release_year,
                    content_type=content_type,
                    is_similarity=False,
                    similar_to=None,
                    intent="search",
                )

        return None


# ---------------------------------------------------------------------------
# Module-level Providers and Convenience Helpers
# ---------------------------------------------------------------------------

_default_query_parser: QueryParserService | None = None


def get_query_parser_service() -> QueryParserService:
    """Dependency provider for QueryParserService."""
    global _default_query_parser
    if _default_query_parser is None:
        _default_query_parser = QueryParserService()
    return _default_query_parser


def parse_catalog_query(
    query: str | None,
    service: QueryParserService | None = None,
) -> ParsedQuery:
    """Convenience helper to parse a catalog query with default or provided service."""
    svc = service or get_query_parser_service()
    return svc.parse(query)
