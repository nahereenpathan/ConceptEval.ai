"""
Frontend ↔ Backend Connection and Problem Library Regression Tests
Verifies CORS preflight, API path routing, query parameter contracts, pagination,
error handling (422, 500), empty library responses, and SQLite canonical resolution.
"""

import pytest
import pytest_asyncio
import httpx
from fastapi import FastAPI
from app.main import app
from app.core.config import settings, _resolve_canonical_sqlite_url


@pytest.mark.asyncio
async def test_cors_preflight_on_problems_endpoint():
    """Verify CORS OPTIONS preflight request for Problem Library from frontend origin."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/v1/problems",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization, content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert response.headers.get("access-control-allow-credentials") == "true"
        allow_methods = response.headers.get("access-control-allow-methods", "")
        assert "GET" in allow_methods
        assert "OPTIONS" in allow_methods


@pytest.mark.asyncio
async def test_cors_ip_origin_preflight():
    """Verify CORS preflight works for 127.0.0.1:5173 origin."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/v1/problems",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization, content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


@pytest.mark.asyncio
async def test_problem_library_real_records_success():
    """Verify exact frontend request returns real database problem records with CORS headers."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/problems?sort_by=created_at&sort_order=desc&page=1&page_size=10&paginate=true",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] > 0
        assert len(data["items"]) > 0
        assert data["page"] == 1
        assert data["page_size"] == 10

        first = data["items"][0]
        assert "id" in first
        assert "slug" in first
        assert "title" in first
        assert "difficulty" in first
        assert "topics" in first


@pytest.mark.asyncio
async def test_problem_library_pagination_and_sorting():
    """Verify pagination and sorting parameters adhere to API contract."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res1 = await client.get("/api/v1/problems?sort_by=title&sort_order=asc&page=1&page_size=5&paginate=true")
        assert res1.status_code == 200
        data1 = res1.json()
        assert len(data1["items"]) <= 5

        res2 = await client.get("/api/v1/problems?sort_by=title&sort_order=asc&page=2&page_size=5&paginate=true")
        assert res2.status_code == 200
        data2 = res2.json()
        if data1["total"] > 5:
            assert data2["page"] == 2
            # Items on page 1 and page 2 must be distinct
            ids_page1 = {item["id"] for item in data1["items"]}
            ids_page2 = {item["id"] for item in data2["items"]}
            assert ids_page1.isdisjoint(ids_page2)


@pytest.mark.asyncio
async def test_problem_library_empty_filter_response():
    """Verify filtering by non-existent term returns HTTP 200 empty library, not an error."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/problems?search=__nonexistent_search_query_99999__&paginate=true",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


@pytest.mark.asyncio
async def test_problem_library_validation_error_422():
    """Verify invalid query parameter returns 422 with structured VALIDATION_ERROR."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/problems?page=0&page_size=10&paginate=true")
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "details" in data["error"]


@pytest.mark.asyncio
async def test_unhandled_exception_returns_500_with_cors():
    """Verify unhandled exceptions return structured JSON, request_id, and preserve CORS headers."""
    @app.get("/api/v1/test-simulated-error")
    async def simulated_error():
        raise RuntimeError("Simulated crash for 500 handler verification")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/test-simulated-error", headers={"Origin": "http://localhost:5173"})
        assert response.status_code == 500
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "message" in data["error"]
        assert "request_id" in data["error"]


def test_sqlite_db_url_resolution():
    """Verify relative SQLite paths resolve to absolute canonical paths."""
    resolved = _resolve_canonical_sqlite_url("sqlite+aiosqlite:///./concept_eval_dev.db")
    assert resolved.startswith("sqlite+aiosqlite:///")
    assert "concept_eval_dev.db" in resolved
    # Non-sqlite URLs must remain untouched
    postgres_url = "postgresql+asyncpg://user:pass@localhost:5432/dbname"
    assert _resolve_canonical_sqlite_url(postgres_url) == postgres_url
