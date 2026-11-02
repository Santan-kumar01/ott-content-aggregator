"""Comprehensive unit test suite for QueryParserService and natural-language query parsing."""

import pytest

from src.schemas.query import ParsedQuery
from src.services.query_parser_service import (
    QueryParserService,
    get_query_parser_service,
    parse_catalog_query,
)


@pytest.fixture
def parser() -> QueryParserService:
    return QueryParserService()


# ---------------------------------------------------------------------------
# 1. Primary Required Prompt Examples
# ---------------------------------------------------------------------------


class TestPromptRequiredExamples:
    """Verifies the exact examples mandated by the project specification."""

    def test_show_me_inception(self, parser: QueryParserService):
        result = parser.parse("Show me Inception")
        assert result.search_query == "Inception"
        assert result.cleaned_query == "Inception"
        assert result.genre is None
        assert result.intent == "search"
        assert result.to_catalog_filters() == {"search": "Inception"}

    def test_find_movies_like_interstellar(self, parser: QueryParserService):
        result = parser.parse("Find movies like Interstellar")
        assert result.search_query == "Interstellar"
        assert result.cleaned_query == "Interstellar"
        assert result.is_similarity is True
        assert result.similar_to == "Interstellar"
        assert result.content_type == "movie"
        assert result.intent == "similar"
        # Does not invent unsupported filters for catalog search
        assert result.to_catalog_filters() == {"search": "Interstellar"}

    def test_search_for_breaking_bad(self, parser: QueryParserService):
        result = parser.parse("Search for Breaking Bad")
        assert result.search_query == "Breaking Bad"
        assert result.cleaned_query == "Breaking Bad"
        assert result.genre is None
        assert result.intent == "search"
        assert result.to_catalog_filters() == {"search": "Breaking Bad"}

    def test_i_want_to_watch_the_dark_knight(self, parser: QueryParserService):
        result = parser.parse("I want to watch The Dark Knight")
        assert result.search_query == "The Dark Knight"
        assert result.cleaned_query == "The Dark Knight"
        assert result.genre is None
        assert result.intent == "search"
        assert result.to_catalog_filters() == {"search": "The Dark Knight"}

    def test_find_action_movies(self, parser: QueryParserService):
        result = parser.parse("Find action movies")
        assert result.genre == "Action"
        assert result.content_type == "movie"
        assert result.search_query is None
        assert result.intent == "genre_search"
        assert result.to_catalog_filters() == {"genre": "Action"}


# ---------------------------------------------------------------------------
# 2. Conversational Prefixes and Polite Fillers
# ---------------------------------------------------------------------------


class TestConversationalPrefixes:
    """Verifies stripping of spoken commands, greetings, and polite prefixes."""

    @pytest.mark.parametrize(
        ("query", "expected_title"),
        [
            ("Please find Inception", "Inception"),
            ("Can you find Inception?", "Inception"),
            ("Could you please show me Inception", "Inception"),
            ("Would you show me Inception", "Inception"),
            ("Hey can you search for Inception", "Inception"),
            ("I'd like to watch Inception", "Inception"),
            ("I would like to watch Inception", "Inception"),
            ("Let's watch Inception", "Inception"),
            ("Play Inception", "Inception"),
            ("Watch Inception", "Inception"),
            ("Look for Inception", "Inception"),
            ("Look up Inception", "Inception"),
            ("Bring up Inception", "Inception"),
            ("Get me Inception", "Inception"),
            ("Give me Inception", "Inception"),
            ("Where can I watch Inception?", "Inception"),
            ("Show me the movie Inception", "Inception"),
            ("Show me the film Inception", "Inception"),
            ("Find the movie called Inception", "Inception"),
            ("Search for the movie titled Inception", "Inception"),
            ("Look up the show named Breaking Bad", "Breaking Bad"),
            ("Look up the TV show Breaking Bad", "Breaking Bad"),
            ("Watch the series Breaking Bad", "Breaking Bad"),
        ],
    )
    def test_prefix_stripping_variations(
        self, parser: QueryParserService, query: str, expected_title: str
    ):
        result = parser.parse(query)
        assert result.search_query == expected_title
        assert result.cleaned_query == expected_title


# ---------------------------------------------------------------------------
# 3. Punctuation, Quotes, and Multiword Title Preservation
# ---------------------------------------------------------------------------


class TestPunctuationAndComplexTitles:
    """Verifies preservation of internal punctuation and multiword titles."""

    def test_spider_man_no_way_home(self, parser: QueryParserService):
        result = parser.parse("Please play Spider-Man: No Way Home.")
        assert result.search_query == "Spider-Man: No Way Home"
        assert result.cleaned_query == "Spider-Man: No Way Home"

    def test_dont_look_up(self, parser: QueryParserService):
        result = parser.parse("Show me Don't Look Up!")
        assert result.search_query == "Don't Look Up"

    def test_avengers_endgame(self, parser: QueryParserService):
        result = parser.parse("I want to watch Avengers: Endgame?")
        assert result.search_query == "Avengers: Endgame"

    def test_fast_and_furious(self, parser: QueryParserService):
        result = parser.parse("Find Fast & Furious")
        assert result.search_query == "Fast & Furious"

    def test_mission_impossible_fallout(self, parser: QueryParserService):
        result = parser.parse("Search for Mission: Impossible - Fallout")
        assert result.search_query == "Mission: Impossible - Fallout"

    def test_wall_e(self, parser: QueryParserService):
        result = parser.parse("Play Wall-E")
        assert result.search_query == "Wall-E"

    def test_face_off(self, parser: QueryParserService):
        result = parser.parse("Find Face/Off")
        assert result.search_query == "Face/Off"

    def test_quoted_title(self, parser: QueryParserService):
        result = parser.parse('Search for "Interstellar"')
        assert result.search_query == "Interstellar"

    def test_single_quoted_title(self, parser: QueryParserService):
        result = parser.parse("Show me 'The Dark Knight'")
        assert result.search_query == "The Dark Knight"

    def test_curly_quoted_title(self, parser: QueryParserService):
        result = parser.parse("Watch “Inception”")
        assert result.search_query == "Inception"


# ---------------------------------------------------------------------------
# 4. Ambiguous and Single-Word Titles (No False Stripping)
# ---------------------------------------------------------------------------


class TestAmbiguousAndSingleWordTitles:
    """Verifies titles starting with command words or single short words are preserved."""

    def test_find_me_guilty_direct(self, parser: QueryParserService):
        result = parser.parse("Find Me Guilty")
        assert result.search_query == "Find Me Guilty"
        assert result.cleaned_query == "Find Me Guilty"

    def test_find_me_guilty_with_prefix(self, parser: QueryParserService):
        result = parser.parse("Please find Find Me Guilty")
        assert result.search_query == "Find Me Guilty"

    def test_search_party(self, parser: QueryParserService):
        result = parser.parse("Search Party")
        assert result.search_query == "Search Party"

    def test_watchmen(self, parser: QueryParserService):
        result = parser.parse("Watchmen")
        assert result.search_query == "Watchmen"

    def test_showgirls(self, parser: QueryParserService):
        result = parser.parse("Showgirls")
        assert result.search_query == "Showgirls"

    def test_play_misty_for_me(self, parser: QueryParserService):
        result = parser.parse("Play Misty for Me")
        assert result.search_query == "Play Misty for Me"

    def test_get_out(self, parser: QueryParserService):
        result = parser.parse("Get Out")
        assert result.search_query == "Get Out"

    def test_up_pixar(self, parser: QueryParserService):
        result = parser.parse("Up")
        assert result.search_query == "Up"

    def test_show_me_up(self, parser: QueryParserService):
        result = parser.parse("Show me Up")
        assert result.search_query == "Up"

    def test_her(self, parser: QueryParserService):
        result = parser.parse("Her")
        assert result.search_query == "Her"

    def test_watch_her(self, parser: QueryParserService):
        result = parser.parse("Watch Her")
        assert result.search_query == "Her"

    def test_it(self, parser: QueryParserService):
        result = parser.parse("It")
        assert result.search_query == "It"

    def test_1917(self, parser: QueryParserService):
        result = parser.parse("1917")
        assert result.search_query == "1917"

    def test_blade_runner_2049(self, parser: QueryParserService):
        result = parser.parse("Blade Runner 2049")
        assert result.search_query == "Blade Runner 2049"


# ---------------------------------------------------------------------------
# 5. Titles Containing Genre Words (Not Erroneously Split)
# ---------------------------------------------------------------------------


class TestTitlesContainingGenreWords:
    """Verifies that titles with embedded genre words aren't wrongly parsed as genre filters."""

    def test_action_jackson(self, parser: QueryParserService):
        result = parser.parse("Action Jackson")
        assert result.search_query == "Action Jackson"
        assert result.genre is None

    def test_show_me_action_jackson(self, parser: QueryParserService):
        result = parser.parse("Show me Action Jackson")
        assert result.search_query == "Action Jackson"
        assert result.genre is None

    def test_crime_and_punishment(self, parser: QueryParserService):
        result = parser.parse("Crime and Punishment")
        assert result.search_query == "Crime and Punishment"
        assert result.genre is None


# ---------------------------------------------------------------------------
# 6. Genre Recognition and Normalization
# ---------------------------------------------------------------------------


class TestGenreRecognition:
    """Verifies genre matching, synonyms, and catalog filter generation."""

    @pytest.mark.parametrize(
        ("query", "expected_genre"),
        [
            ("action", "Action"),
            ("action movies", "Action"),
            ("find action movies", "Action"),
            ("comedy", "Comedy"),
            ("show me comedy", "Comedy"),
            ("comedy shows", "Comedy"),
            ("sci-fi", "Sci-Fi"),
            ("scifi", "Sci-Fi"),
            ("sci fi", "Sci-Fi"),
            ("science fiction movies", "Sci-Fi"),
            ("find sci-fi movies", "Sci-Fi"),
            ("drama", "Drama"),
            ("find drama series", "Drama"),
            ("horror films", "Horror"),
            ("animated movies", "Animation"),
            ("animation", "Animation"),
            ("cartoons", "Animation"),
            ("documentaries", "Documentary"),
            ("find documentary films", "Documentary"),
            ("romance", "Romance"),
            ("romantic movies", "Romance"),
            ("thriller", "Thriller"),
            ("thrillers", "Thriller"),
            ("mystery", "Mystery"),
            ("fantasy", "Fantasy"),
            ("adventure", "Adventure"),
            ("western movies", "Western"),
            ("movies in the drama genre", "Drama"),
        ],
    )
    def test_genre_queries(
        self, parser: QueryParserService, query: str, expected_genre: str
    ):
        result = parser.parse(query)
        assert result.genre == expected_genre
        assert result.search_query is None
        assert result.intent == "genre_search"
        assert result.to_catalog_filters() == {"genre": expected_genre}


# ---------------------------------------------------------------------------
# 7. Genre Combined with Title
# ---------------------------------------------------------------------------


class TestGenreCombinedWithTitle:
    """Verifies queries specifying both genre and title."""

    def test_action_movie_die_hard(self, parser: QueryParserService):
        result = parser.parse("Find action movie Die Hard")
        assert result.genre == "Action"
        assert result.search_query == "Die Hard"
        assert result.content_type == "movie"
        assert result.to_catalog_filters() == {"genre": "Action", "search": "Die Hard"}

    def test_comedy_show_friends(self, parser: QueryParserService):
        result = parser.parse("Show me comedy show Friends")
        assert result.genre == "Comedy"
        assert result.search_query == "Friends"
        assert result.content_type == "show"
        assert result.to_catalog_filters() == {"genre": "Comedy", "search": "Friends"}


# ---------------------------------------------------------------------------
# 8. Similarity Queries
# ---------------------------------------------------------------------------


class TestSimilarityQueries:
    """Verifies similarity recommendation intent extraction."""

    def test_shows_like_breaking_bad(self, parser: QueryParserService):
        result = parser.parse("Shows like Breaking Bad")
        assert result.search_query == "Breaking Bad"
        assert result.is_similarity is True
        assert result.similar_to == "Breaking Bad"
        assert result.content_type == "show"
        assert result.intent == "similar"

    def test_similar_to_the_matrix(self, parser: QueryParserService):
        result = parser.parse("Find movies similar to The Matrix")
        assert result.search_query == "The Matrix"
        assert result.is_similarity is True
        assert result.similar_to == "The Matrix"
        assert result.content_type == "movie"

    def test_sci_fi_movies_like_interstellar(self, parser: QueryParserService):
        result = parser.parse("Find sci-fi movies like Interstellar")
        assert result.search_query == "Interstellar"
        assert result.genre == "Sci-Fi"
        assert result.is_similarity is True
        assert result.similar_to == "Interstellar"
        assert result.content_type == "movie"
        assert result.to_catalog_filters() == {
            "search": "Interstellar",
            "genre": "Sci-Fi",
        }


# ---------------------------------------------------------------------------
# 9. Streaming Platform Extraction
# ---------------------------------------------------------------------------


class TestPlatformExtraction:
    """Verifies platform filter extraction for catalog compatibility."""

    def test_watch_on_netflix(self, parser: QueryParserService):
        result = parser.parse("Watch Inception on Netflix")
        assert result.search_query == "Inception"
        assert result.platform == "Netflix"
        assert result.to_catalog_filters() == {
            "search": "Inception",
            "platform": "Netflix",
        }

    def test_find_on_prime(self, parser: QueryParserService):
        result = parser.parse("Find Interstellar on Prime Video")
        assert result.search_query == "Interstellar"
        assert result.platform == "Prime"

    def test_show_on_disney_plus(self, parser: QueryParserService):
        result = parser.parse("Play The Mandalorian on Disney+")
        assert result.search_query == "The Mandalorian"
        assert result.platform == "Disney+"


# ---------------------------------------------------------------------------
# 10. Release Year Extraction
# ---------------------------------------------------------------------------


class TestReleaseYearExtraction:
    """Verifies release year filter extraction when explicitly requested."""

    def test_released_in_year(self, parser: QueryParserService):
        result = parser.parse("Find Inception released in 2010")
        assert result.search_query == "Inception"
        assert result.release_year == 2010
        assert result.to_catalog_filters() == {
            "search": "Inception",
            "release_year": 2010,
        }

    def test_year_in_parentheses(self, parser: QueryParserService):
        result = parser.parse("The Dark Knight (2008)")
        assert result.search_query == "The Dark Knight"
        assert result.release_year == 2008

    def test_movies_from_year(self, parser: QueryParserService):
        result = parser.parse("Find movies from 2020")
        assert result.release_year == 2020
        assert result.content_type == "movie"
        assert result.to_catalog_filters() == {"release_year": 2020}


# ---------------------------------------------------------------------------
# 11. Edge Cases & Robustness
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Verifies empty strings, pure whitespace, and malformed inputs."""

    def test_empty_string(self, parser: QueryParserService):
        result = parser.parse("")
        assert result.search_query is None
        assert result.cleaned_query == ""
        assert result.intent == "empty"
        assert result.to_catalog_filters() == {}

    def test_whitespace_only(self, parser: QueryParserService):
        result = parser.parse("   \t\n  ")
        assert result.search_query is None
        assert result.cleaned_query == ""
        assert result.intent == "empty"
        assert result.to_catalog_filters() == {}

    def test_none_input(self, parser: QueryParserService):
        result = parser.parse(None)
        assert result.search_query is None
        assert result.cleaned_query == ""
        assert result.intent == "empty"
        assert result.to_catalog_filters() == {}

    def test_punctuation_only(self, parser: QueryParserService):
        result = parser.parse("...???!!!")
        assert result.search_query is None
        assert result.cleaned_query == ""
        assert result.intent == "empty"
        assert result.to_catalog_filters() == {}

    def test_excessive_whitespace_collapsed(self, parser: QueryParserService):
        result = parser.parse("Show    me     Inception    now   ")
        assert "Inception" in (result.search_query or "")

    def test_generic_browse_movies(self, parser: QueryParserService):
        result = parser.parse("Show me movies")
        assert result.search_query is None
        assert result.content_type == "movie"
        assert result.intent == "browse"
        assert result.to_catalog_filters() == {}

    def test_frozen_model_immutability(self, parser: QueryParserService):
        result = parser.parse("Inception")
        with pytest.raises(Exception):
            result.search_query = "Something Else"  # type: ignore


# ---------------------------------------------------------------------------
# 12. Service Convenience Providers
# ---------------------------------------------------------------------------


class TestServiceProviders:
    """Verifies dependency provider and module-level helper."""

    def test_get_query_parser_service_singleton(self):
        svc1 = get_query_parser_service()
        svc2 = get_query_parser_service()
        assert svc1 is svc2
        assert isinstance(svc1, QueryParserService)

    def test_parse_catalog_query_helper(self):
        result = parse_catalog_query("Show me Inception")
        assert isinstance(result, ParsedQuery)
        assert result.search_query == "Inception"

