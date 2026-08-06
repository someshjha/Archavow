"""S3 — knowledge upload, chunk, search (embeddings optional)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_upload_markdown_chunks_document(client: TestClient) -> None:
    res = client.post(
        "/api/v1/knowledge/documents",
        json={
            "title": "kafka-mtls.md",
            "source_class": "org",
            "content": (
                "# Kafka mTLS\n\n"
                "All Kafka clients must use mutual TLS in production.\n\n"
                "## Certificates\n\n"
                "Rotate broker certificates every 90 days.\n\n"
                "## Consumer groups\n\n"
                "Prefer sticky assignors for payment processors.\n"
            ),
        },
    )
    assert res.status_code == 201, res.text
    doc = res.json()["data"]
    assert doc["title"] == "kafka-mtls.md"
    assert doc["source_class"] == "org"
    assert doc["chunk_count"] >= 2
    assert doc["status"] in {"ready", "embedded", "keyword_only"}
    assert "content_hash" in doc


def test_list_knowledge_documents(client: TestClient) -> None:
    client.post(
        "/api/v1/knowledge/documents",
        json={
            "title": "aks-baseline.md",
            "source_class": "seed",
            "content": "AKS clusters must enable Azure Policy. Network policies required.",
        },
    )
    client.post(
        "/api/v1/knowledge/documents",
        json={
            "title": "org-kafka.md",
            "source_class": "org",
            "content": "Org Kafka must use mTLS.",
        },
    )
    listed = client.get("/api/v1/knowledge/documents")
    assert listed.status_code == 200
    items = listed.json()["data"]
    # Seed docs are hidden from the default library list
    assert all(d["source_class"] != "seed" for d in items)
    assert any(d["title"] == "org-kafka.md" for d in items)


def test_search_keyword_when_embeddings_none(client: TestClient) -> None:
    # client fixture sets AI_EMBEDDING_PROVIDER=none
    client.post(
        "/api/v1/knowledge/documents",
        json={
            "title": "api-security.md",
            "source_class": "org",
            "content": "Partner APIs must use OAuth2 client credentials. Never ship long-lived API keys.",
        },
    )
    res = client.post(
        "/api/v1/knowledge/search",
        json={"query": "OAuth2 partner APIs", "limit": 5},
    )
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    assert body["retrieval_status"] in {"degraded", "ok", "partial"}
    assert body["hits"]
    assert any("OAuth" in h["text"] or "oauth" in h["text"].lower() for h in body["hits"])
    assert all("document_id" in h and "chunk_id" in h for h in body["hits"])
    assert "citation" in body["hits"][0]


def test_search_empty_corpus(client: TestClient) -> None:
    # Auto-seed may populate industry docs; a nonsense query should not match.
    res = client.post(
        "/api/v1/knowledge/search",
        json={"query": "zzzzxqwertyuniquetoken999", "limit": 5},
    )
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["hits"] == []
    assert body["retrieval_status"] in {"ok", "degraded"}
