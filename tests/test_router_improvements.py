"""Tests for router keyword improvements B2.1-B2.5."""

import asyncio

from rag.router import RetrievalRouter, Strategy


def test_recent_keywords_ru_and_en():
    r = RetrievalRouter(layer="test_router")
    # RU keywords
    assert r._is_recent_query("это важно")
    assert r._is_recent_query("почему так")
    assert r._is_recent_query("как сделать")
    assert r._is_recent_query("только что")
    assert r._is_recent_query("ранее было")
    assert r._is_recent_query("сейчас")
    assert r._is_recent_query("вчера")
    assert r._is_recent_query("утром")
    # EN keywords
    assert r._is_recent_query("this is important")
    assert r._is_recent_query("why did you")
    assert r._is_recent_query("how come")
    assert r._is_recent_query("earlier today")
    assert r._is_recent_query("just now")
    assert r._is_recent_query("again")
    assert r._is_recent_query("yesterday")
    assert r._is_recent_query("recently")
    # Negative
    assert not r._is_recent_query("architecture design patterns")


def test_wiki_keywords_ru_and_en():
    r = RetrievalRouter(layer="test_router")
    # RU
    assert r._is_wiki_query("документация по API")
    assert r._is_wiki_query("руководство по настройке")
    assert r._is_wiki_query("гайд по Docker")
    # EN
    assert r._is_wiki_query("tutorial for beginners")
    assert r._is_wiki_query("how to configure Redis")
    assert r._is_wiki_query("guide to deployment")
    assert r._is_wiki_query("manual setup")
    assert r._is_wiki_query("rtfm")
    assert r._is_wiki_query("wiki page")
    assert r._is_wiki_query("documentation")


def test_graph_keywords_ru_and_en():
    r = RetrievalRouter(layer="test_router")
    # RU
    assert r._is_graph_query("связи между модулями")
    assert r._is_graph_query("взаимосвязь событий")
    assert r._is_graph_query("зависит от конфига")
    # EN
    assert r._is_graph_query("depends on Redis")
    assert r._is_graph_query("linked to previous decision")
    assert r._is_graph_query("follows from analysis")
    assert r._is_graph_query("error_pattern in logs")


def test_entity_extraction_preserves_short_non_stopwords():
    r = RetrievalRouter(layer="test_router")
    # Real tech entities should pass (not in stopwords)
    entities = r._extract_entities("Use Redis with Docker and Kubernetes")
    assert "redis" in entities
    assert "docker" in entities
    assert "kubernetes" in entities


def test_entity_extraction_filters_stopwords():
    r = RetrievalRouter(layer="test_router")
    # Stopwords should be filtered
    entities = r._extract_entities("the ai ml js ts db")
    assert "ai" not in entities  # ai is in stopwords
    assert "ml" not in entities
    assert "js" not in entities
    assert "db" not in entities
    # But real entities should pass
    entities = r._extract_entities("Use Redis with Python")
    assert "redis" in entities
    assert "python" in entities


def test_flat_keywords_merges_ru_en():
    r = RetrievalRouter(layer="test_router")
    recent = r._flat_keywords("recent")
    # Should contain both RU and EN
    assert "это" in recent
    assert "this" in recent
    assert "вчера" in recent
    assert "yesterday" in recent


def test_route_returns_strategy():
    r = RetrievalRouter(layer="test_router")

    async def t():
        # Recent query should route to L1_BUFFER
        result = await r.route("это", recent_context=[{"test": True}])
        assert result.strategy == Strategy.L1_BUFFER

        # Wiki query should route to WIKI (or SEMANTIC if no results)
        result = await r.route("tutorial for Python")
        assert result.strategy in (Strategy.WIKI, Strategy.SEMANTIC)

    asyncio.run(t())
