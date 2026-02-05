# Backend — Clean Architecture + FastAPI (Etapas 1–3)

## Arquitetura

```
backend/
├── docker-compose.yml
├── alembic.ini
├── alembic/versions/0001_initial_tables.py
├── pytest.ini
├── app/
│   ├── main.py                          # Entry + middleware + lifespan
│   ├── seed.py                          # ★ Seed admin inicial
│   ├── domain/                          # Camada de Domínio
│   │   ├── events/                      #   DomainEvent, AggregateRoot
│   │   ├── shared/value_objects.py      #   Milestone VO, Email VO
│   │   └── systems/{users,tickets,datasets}/
│   ├── application/                     # Camada de Aplicação
│   │   ├── dtos/                        #   Commands, Queries, Results
│   │   ├── shared/                      #   UoW, EventDispatcher, AuditHandlers
│   │   └── systems/{users,tickets,datasets}/use_cases.py
│   ├── infrastructure/                  # Camada de Infraestrutura
│   │   ├── config/settings.py
│   │   ├── database/{session,models}.py
│   │   └── systems/                     #   Repos concretos (filtros, count, bulk)
│   └── presentation/                    # ★ Camada de Apresentação (Etapa 3)
│       ├── middleware/
│       │   ├── exception_handlers.py    #   Global error handling
│       │   └── request_id.py            #   X-Request-ID + logging
│       └── api/v1/
│           ├── router.py                #   4 sub-routers com tags
│           ├── schemas.py               #   Enums, Pagination, Filters, Bulk, AuditLog
│           ├── deps.py                  #   JWT (access+refresh), RBAC, DI factories
│           └── endpoints/
│               ├── auth.py              #   ★ register, login, refresh, change-pw, me
│               ├── users.py             #   CRUD admin + audit logs
│               ├── tickets.py           #   CRUD + pagination + filters + milestones
│               └── datasets.py          #   CRUD + pagination + filters + bulk + audit
└── tests/
    ├── conftest.py                      # SQLite in-memory, fixtures, auth helpers
    ├── test_auth.py                     # 8 testes
    ├── test_tickets.py                  # 11 testes
    ├── test_datasets.py                 # 8 testes
    └── test_users.py                    # 6 testes
```

## O que a Etapa 3 adicionou

| Feature                    | Detalhes                                                    |
|----------------------------|-------------------------------------------------------------|
| **Auth separada**          | `/api/v1/auth/` — register, login, refresh, change-password, me |
| **Refresh Token**          | JWT refresh com 7 dias de validade                          |
| **Global Error Handling**  | Exception handlers para AuthorizationError, ValueError, 500 |
| **Request ID**             | X-Request-ID em cada request + log de tempo de execução     |
| **Paginação**              | `PaginatedResponse<T>` com total, page, pages               |
| **Filtros — Tickets**      | status, assigned_to, created_by, search (ilike no título)   |
| **Filtros — Datasets**     | status, target_model                                        |
| **Bulk Import**            | `POST /datasets/bulk` — até 1000 itens por request          |
| **Audit Log Endpoints**    | `GET /users/{id}/audit-logs`, `GET /datasets/{id}/audit-logs` |
| **Seed Admin**             | `python -m app.seed` — cria admin inicial                   |
| **Testes de Integração**   | 33 testes com pytest + httpx + SQLite in-memory             |
| **Swagger Documentado**    | Tags com emojis, descriptions, examples em schemas          |
| **Active User Guard**      | `get_current_active_user` — bloqueia usuários inativos      |
| **Health Check com DB**    | `/health` — verifica conectividade com Postgres             |

## Setup Rápido

```bash
# 1. Subir Postgres + pgAdmin
docker compose up -d

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Aplicar migração
alembic upgrade head

# 4. Seed admin
python -m app.seed

# 5. Rodar servidor
uvicorn app.main:app --reload --port 8000

# 6. Rodar testes
pytest -v
```

## Endpoints API v1

### 🔐 Autenticação (`/api/v1/auth`)
| Método | Rota               | Auth? | Descrição                     |
|--------|--------------------|-------|-------------------------------|
| POST   | /register          | ✗     | Criar conta                   |
| POST   | /login             | ✗     | Login → access + refresh      |
| POST   | /refresh           | ✗     | Renovar access token          |
| POST   | /change-password   | ✓     | Alterar senha                 |
| GET    | /me                | ✓     | Perfil autenticado            |

### 👤 Usuários (`/api/v1/users`)
| Método | Rota                    | Role  | Descrição              |
|--------|-------------------------|-------|------------------------|
| GET    | /                       | admin | Listar todos           |
| GET    | /{id}                   | admin | Detalhe                |
| PATCH  | /{id}                   | self/admin | Atualizar         |
| DELETE | /{id}                   | admin | Remover                |
| GET    | /{id}/audit-logs        | admin | Audit logs             |

### 🎫 Tickets (`/api/v1/tickets`)
| Método | Rota                         | Descrição                          |
|--------|------------------------------|------------------------------------|
| POST   | /                            | Criar                              |
| GET    | /?page&status&search&...     | Listar (paginado + filtros)        |
| GET    | /{id}                        | Detalhe                            |
| PATCH  | /{id}                        | Atualizar                          |
| DELETE | /{id}                        | Remover                            |
| POST   | /{id}/transition             | Transição de status                |
| POST   | /{id}/milestones             | Adicionar milestone                |
| POST   | /{id}/milestones/complete    | Completar milestone                |

### 🧠 Datasets LLM (`/api/v1/datasets`)
| Método | Rota                    | Descrição                          |
|--------|-------------------------|------------------------------------|
| POST   | /                       | Inserir par prompt/response        |
| GET    | /?page&status&target... | Listar (paginado + filtros)        |
| GET    | /{id}                   | Detalhe                            |
| PATCH  | /{id}                   | Atualizar                          |
| DELETE | /{id}                   | Remover                            |
| POST   | /bulk                   | ★ Import em lote (até 1000)        |
| GET    | /{id}/audit-logs        | Audit logs                         |

## Acessos

- **Swagger:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **pgAdmin:** http://localhost:5050
- **Admin padrão:** admin / admin123 (após `python -m app.seed`)
