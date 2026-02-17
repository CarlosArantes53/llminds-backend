## 2024-05-22 - [Optimizing Role-Based Queries]
**Learning:** The `users` table lacked an index on the `role` column, which is frequently used for filtering agents and admins. This causes full table scans in critical paths like ticket assignment.
**Action:** Always verify indexes on columns used for filtering in `WHERE` clauses, especially for low-cardinality fields like roles in large tables. Added `index=True` to `UserModel.role` and created a migration.
