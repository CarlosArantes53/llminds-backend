## 2026-02-20 - [Async Integration with Google GenAI]
**Learning:** The synchronous `client.models.generate_content` method in the `google-genai` library blocks the event loop in async FastAPI applications, significantly degrading performance under load.
**Action:** Always use the `client.aio` accessor (e.g., `await client.aio.models.generate_content(...)`) for asynchronous operations when integrating with Google GenAI.
