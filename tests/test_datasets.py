"""Testes de Datasets — CRUD, paginação, filtros, bulk import."""

import pytest
from httpx import AsyncClient
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_create_dataset(client: AsyncClient, user_token: str):
    resp = await client.post("/api/v1/datasets/", json={
        "prompt_text": "O que é IA?",
        "response_text": "Inteligência Artificial é...",
        "target_model": "llama-3",
    }, headers=auth_header(user_token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["prompt_text"] == "O que é IA?"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_dataset_empty_prompt(client: AsyncClient, user_token: str):
    resp = await client.post("/api/v1/datasets/", json={
        "prompt_text": "   ",
        "response_text": "Resposta",
    }, headers=auth_header(user_token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_datasets_paginated(client: AsyncClient, user_token: str):
    for i in range(5):
        await client.post("/api/v1/datasets/", json={
            "prompt_text": f"Pergunta {i}",
            "response_text": f"Resposta {i}",
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
        "prompt_text": "P1", "response_text": "R1", "target_model": "llama-3",
    }, headers=auth_header(user_token))
    await client.post("/api/v1/datasets/", json={
        "prompt_text": "P2", "response_text": "R2", "target_model": "gpt-4",
    }, headers=auth_header(user_token))

    resp = await client.get("/api/v1/datasets/?target_model=llama-3", headers=auth_header(user_token))
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["target_model"] == "llama-3"


@pytest.mark.asyncio
async def test_get_dataset(client: AsyncClient, user_token: str):
    create = await client.post("/api/v1/datasets/", json={
        "prompt_text": "P", "response_text": "R",
    }, headers=auth_header(user_token))
    did = create.json()["id"]

    resp = await client.get(f"/api/v1/datasets/{did}", headers=auth_header(user_token))
    assert resp.status_code == 200
    assert resp.json()["id"] == did


@pytest.mark.asyncio
async def test_update_dataset(client: AsyncClient, user_token: str):
    create = await client.post("/api/v1/datasets/", json={
        "prompt_text": "Original", "response_text": "Original",
    }, headers=auth_header(user_token))
    did = create.json()["id"]

    resp = await client.patch(f"/api/v1/datasets/{did}", json={
        "prompt_text": "Atualizado",
    }, headers=auth_header(user_token))
    assert resp.status_code == 200
    assert resp.json()["prompt_text"] == "Atualizado"


@pytest.mark.asyncio
async def test_delete_dataset(client: AsyncClient, user_token: str):
    create = await client.post("/api/v1/datasets/", json={
        "prompt_text": "Del", "response_text": "Del",
    }, headers=auth_header(user_token))
    did = create.json()["id"]

    resp = await client.delete(f"/api/v1/datasets/{did}", headers=auth_header(user_token))
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_bulk_create_datasets(client: AsyncClient, user_token: str):
    resp = await client.post("/api/v1/datasets/bulk", json={
        "items": [
            {"prompt_text": "P1", "response_text": "R1", "target_model": "llama-3"},
            {"prompt_text": "P2", "response_text": "R2", "target_model": "llama-3"},
            {"prompt_text": "P3", "response_text": "R3"},
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
            {"prompt_text": "OK", "response_text": "OK"},
            {"prompt_text": "   ", "response_text": "Fail"},  # prompt vazio
        ]
    }, headers=auth_header(user_token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["created"] == 1
    assert data["failed"] == 1
    assert len(data["errors"]) == 1
