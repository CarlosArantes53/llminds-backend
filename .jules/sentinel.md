## 2024-03-24 - Privilege Escalation via Mass Assignment
**Vulnerability:** A standard user could register as an admin by including `"role": "admin"` in the JSON payload of the `/register` endpoint.
**Learning:** The Pydantic model `UserCreate` included the `role` field, which was then directly passed to the use case. Even though it defaulted to `user`, the API client could override it.
**Prevention:** Remove sensitive fields (like `role`, `is_active`, `id`) from public-facing Pydantic schemas (DTOs). Always use dedicated DTOs for creation vs internal representation.
