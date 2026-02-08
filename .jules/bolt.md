# Bolt's Journal

## 2025-01-26 - Missing Indexes on Frequently Filtered Fields
**Learning:** The application allows filtering tickets by status, assignee, and creator, and datasets by status and target model. These fields are not indexed, which will lead to full table scans as data grows.
**Action:** Adding `index=True` to these columns in SQLAlchemy models ensures efficient lookup. This is a high-impact, low-risk optimization for database performance.

## 2025-02-05 - Missing Indexes on Frequently Sorted Fields and SQLite Compatibility
**Learning:**
1. The application frequently sorts results by `created_at`, `inserted_at`, and `performed_at`. These fields were not indexed, causing the database to perform expensive sort operations, especially for audit logs which can grow very large.
2. The `TicketModel` was using `JSONB` directly, which is PostgreSQL-specific and broke tests when running with SQLite.
**Action:**
1. Added `index=True` to `TicketModel.created_at`, `LLMDatasetModel.inserted_at`, `UserAuditLogModel.performed_at`, and `DatasetAuditLogModel.performed_at`.
2. Updated `TicketModel.milestones` to use `JSON().with_variant(JSONB, 'postgresql')` to ensure compatibility with both PostgreSQL (prod) and SQLite (test).
