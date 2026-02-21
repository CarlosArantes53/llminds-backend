## 2026-02-21 - Composite indexes for ordered relationships
**Learning:** SQLAlchemy relationships with `order_by` (like `order_by="DatasetRowModel.order"`) do not automatically ensure the sorting is efficient. Without an index on the sort column (and the foreign key), the database performs a scan and sort operation which is O(N log N) or worse, instead of O(1) or O(N) with an index scan.
**Action:** Always check relationships with `order_by` and ensure there is a composite index on `(foreign_key, sort_column)` to optimize retrieval and `MAX` queries.
