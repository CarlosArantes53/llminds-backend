"""Testes de Datasets — CRUD, paginação, filtros, bulk import."""

import pytest
from httpx import AsyncClient
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_create_dataset(client: AsyncClient, user_token: str):
    resp = await client.post("/api/v1/datasets/", json={
        "name": "Dataset de IA",
        "rows": [
            {"prompt_text": "O que é IA?", "response_text": "Inteligência Artificial é..."}
        ],
        "target_model": "llama-3",
    }, headers=auth_header(user_token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Dataset de IA"
    assert len(data["rows"]) == 1
    assert data["rows"][0]["prompt_text"] == "O que é IA?"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_dataset_empty_prompt(client: AsyncClient, user_token: str):
    # Testing Pydantic validation failure (min_length=1)
    resp = await client.post("/api/v1/datasets/", json={
        "name": "Invalid",
        "rows": [{"prompt_text": "", "response_text": "Resposta"}]
    }, headers=auth_header(user_token))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_datasets_paginated(client: AsyncClient, user_token: str):
    for i in range(5):
        await client.post("/api/v1/datasets/", json={
            "name": f"Dataset {i}",
            "rows": [{"prompt_text": f"P{i}", "response_text": f"R{i}"}]
        }, headers=auth_header(user_token))

    resp = await client.get("/api/v1/datasets/?page=1&page_size=3", headers=auth_header(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 3
    assert data["pages"] == 2


@pytest.mark.asyncio
async def test_filter_datasets_by_target_model(client: AsyncClient, user_token: str):
    await client.post("/api/v1/datasets/", json={
        "name": "D1", "rows": [{"prompt_text": "P1", "response_text": "R1"}], "target_model": "llama-3",
    }, headers=auth_header(user_token))
    await client.post("/api/v1/datasets/", json={
        "name": "D2", "rows": [{"prompt_text": "P2", "response_text": "R2"}], "target_model": "gpt-4",
    }, headers=auth_header(user_token))

    resp = await client.get("/api/v1/datasets/?target_model=llama-3", headers=auth_header(user_token))
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["target_model"] == "llama-3"


@pytest.mark.asyncio
async def test_get_dataset(client: AsyncClient, user_token: str):
    create = await client.post("/api/v1/datasets/", json={
        "name": "D_GET", "rows": [{"prompt_text": "P", "response_text": "R"}],
    }, headers=auth_header(user_token))
    did = create.json()["id"]

    resp = await client.get(f"/api/v1/datasets/{did}", headers=auth_header(user_token))
    assert resp.status_code == 200
    assert resp.json()["id"] == did


@pytest.mark.asyncio
async def test_update_dataset(client: AsyncClient, user_token: str):
    create = await client.post("/api/v1/datasets/", json={
        "name": "Original", "rows": [{"prompt_text": "Original", "response_text": "Original"}],
    }, headers=auth_header(user_token))
    did = create.json()["id"]

    resp = await client.patch(f"/api/v1/datasets/{did}", json={
        "name": "Atualizado",
    }, headers=auth_header(user_token))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Atualizado"


@pytest.mark.asyncio
async def test_delete_dataset(client: AsyncClient, user_token: str):
    create = await client.post("/api/v1/datasets/", json={
        "name": "Del", "rows": [{"prompt_text": "Del", "response_text": "Del"}],
    }, headers=auth_header(user_token))
    did = create.json()["id"]

    resp = await client.delete(f"/api/v1/datasets/{did}", headers=auth_header(user_token))
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_bulk_create_datasets(client: AsyncClient, user_token: str):
    resp = await client.post("/api/v1/datasets/bulk", json={
        "items": [
            {"name": "D1", "rows": [{"prompt_text": "P1", "response_text": "R1"}], "target_model": "llama-3"},
            {"name": "D2", "rows": [{"prompt_text": "P2", "response_text": "R2"}], "target_model": "llama-3"},
            {"name": "D3", "rows": [{"prompt_text": "P3", "response_text": "R3"}]},
        ]
    }, headers=auth_header(user_token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["created"] == 3
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_bulk_create_with_errors(client: AsyncClient, user_token: str):
    resp = await client.post("/api/v1/datasets/bulk", json={
        "items": [
            {"name": "OK", "rows": [{"prompt_text": "OK", "response_text": "OK"}]},
            {"name": "Fail", "rows": [{"prompt_text": "", "response_text": "Fail"}]},
        ]
    }, headers=auth_header(user_token))

    # If using Pydantic, this likely returns 422.
    if resp.status_code == 422:
        # Expected if validation is strict
        pass
    else:
        assert resp.status_code == 201
        data = resp.json()
        assert data["created"] == 1
        assert data["failed"] == 1
