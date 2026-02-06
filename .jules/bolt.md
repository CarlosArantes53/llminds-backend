# Bolt's Journal

## 2025-01-26 - Missing Indexes on Frequently Filtered Fields
**Learning:** The application allows filtering tickets by status, assignee, and creator, and datasets by status and target model. These fields are not indexed, which will lead to full table scans as data grows.
**Action:** Adding `index=True` to these columns in SQLAlchemy models ensures efficient lookup. This is a high-impact, low-risk optimization for database performance.
