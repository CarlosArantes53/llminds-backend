## 2026-02-18 - [Missing Index on Low Cardinality Enum]
**Learning:** `UserModel.role` is frequently used to filter users (e.g., listing agents) but lacks an index. In PostgreSQL, this causes full table scans on the `users` table. Adding an index on `role` optimizes queries for specific roles, especially when the role distribution is skewed (few agents, many users).
**Action:** When defining role-based access control with database filtering, ensure the role column is indexed if it's used in WHERE clauses, even if it's an enum with low cardinality (if filtered value is rare).
