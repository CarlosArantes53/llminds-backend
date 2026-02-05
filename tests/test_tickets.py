"""Testes de Tickets — CRUD, paginação, filtros, state machine, milestones."""

import pytest
from httpx import AsyncClient
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_create_ticket(client: AsyncClient, user_token: str):
    resp = await client.post("/api/v1/tickets/", json={
        "title": "Bug no login",
        "description": "Erro 500 ao logar com Google",
    }, headers=auth_header(user_token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Bug no login"
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_list_tickets_paginated(client: AsyncClient, user_token: str):
    # Cria 3 tickets
    for i in range(3):
        await client.post("/api/v1/tickets/", json={
            "title": f"Ticket {i}",
        }, headers=auth_header(user_token))

    resp = await client.get("/api/v1/tickets/?page=1&page_size=2", headers=auth_header(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_filter_tickets_by_status(client: AsyncClient, user_token: str):
    await client.post("/api/v1/tickets/", json={"title": "Open ticket"}, headers=auth_header(user_token))

    resp = await client.get("/api/v1/tickets/?status=open", headers=auth_header(user_token))
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    resp2 = await client.get("/api/v1/tickets/?status=done", headers=auth_header(user_token))
    assert resp2.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_tickets(client: AsyncClient, user_token: str):
    await client.post("/api/v1/tickets/", json={"title": "Implementar OAuth"}, headers=auth_header(user_token))
    await client.post("/api/v1/tickets/", json={"title": "Fix CSS"}, headers=auth_header(user_token))

    resp = await client.get("/api/v1/tickets/?search=OAuth", headers=auth_header(user_token))
    assert resp.json()["total"] == 1
    assert "OAuth" in resp.json()["items"][0]["title"]


@pytest.mark.asyncio
async def test_get_ticket(client: AsyncClient, user_token: str):
    create = await client.post("/api/v1/tickets/", json={"title": "Detalhe"}, headers=auth_header(user_token))
    tid = create.json()["id"]

    resp = await client.get(f"/api/v1/tickets/{tid}", headers=auth_header(user_token))
    assert resp.status_code == 200
    assert resp.json()["id"] == tid


@pytest.mark.asyncio
async def test_get_ticket_not_found(client: AsyncClient, user_token: str):
    resp = await client.get("/api/v1/tickets/99999", headers=auth_header(user_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_ticket(client: AsyncClient, user_token: str):
    create = await client.post("/api/v1/tickets/", json={"title": "Original"}, headers=auth_header(user_token))
    tid = create.json()["id"]

    resp = await client.patch(f"/api/v1/tickets/{tid}", json={"title": "Atualizado"}, headers=auth_header(user_token))
    assert resp.status_code == 200
    assert resp.json()["title"] == "Atualizado"


@pytest.mark.asyncio
async def test_transition_ticket(client: AsyncClient, user_token: str):
    create = await client.post("/api/v1/tickets/", json={"title": "Transition test"}, headers=auth_header(user_token))
    tid = create.json()["id"]

    # open → in_progress (válido)
    resp = await client.post(f"/api/v1/tickets/{tid}/transition", json={"status": "in_progress"}, headers=auth_header(user_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"

    # in_progress → done (válido)
    resp2 = await client.post(f"/api/v1/tickets/{tid}/transition", json={"status": "done"}, headers=auth_header(user_token))
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "done"


@pytest.mark.asyncio
async def test_invalid_transition(client: AsyncClient, user_token: str):
    create = await client.post("/api/v1/tickets/", json={"title": "Invalid"}, headers=auth_header(user_token))
    tid = create.json()["id"]

    # open → done (inválido)
    resp = await client.post(f"/api/v1/tickets/{tid}/transition", json={"status": "done"}, headers=auth_header(user_token))
    assert resp.status_code == 400
    assert "inválida" in resp.json()["detail"].lower() or "Transição" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_and_complete_milestone(client: AsyncClient, user_token: str):
    create = await client.post("/api/v1/tickets/", json={"title": "Milestone test"}, headers=auth_header(user_token))
    tid = create.json()["id"]

    # Adicionar milestone
    resp = await client.post(f"/api/v1/tickets/{tid}/milestones", json={
        "title": "Deploy staging",
        "due_date": "2026-06-01T00:00:00",
    }, headers=auth_header(user_token))
    assert resp.status_code == 201
    assert len(resp.json()["milestones"]) == 1
    assert resp.json()["milestones"][0]["title"] == "Deploy staging"
    assert resp.json()["milestones"][0]["completed"] is False

    # Completar
    resp2 = await client.post(f"/api/v1/tickets/{tid}/milestones/complete", json={
        "milestone_index": 0,
    }, headers=auth_header(user_token))
    assert resp2.status_code == 200
    assert resp2.json()["milestones"][0]["completed"] is True


@pytest.mark.asyncio
async def test_delete_ticket(client: AsyncClient, user_token: str):
    create = await client.post("/api/v1/tickets/", json={"title": "To delete"}, headers=auth_header(user_token))
    tid = create.json()["id"]

    resp = await client.delete(f"/api/v1/tickets/{tid}", headers=auth_header(user_token))
    assert resp.status_code == 204

    resp2 = await client.get(f"/api/v1/tickets/{tid}", headers=auth_header(user_token))
    assert resp2.status_code == 404
