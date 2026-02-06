import time
from collections import defaultdict
from fastapi import HTTPException, Request, status

class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using a sliding window.
    NOTE: In production with multiple workers, use Redis.
    """
    def __init__(self, requests: int, window: int):
        self.requests = requests
        self.window = window
        self.clients = defaultdict(list)

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Prevent memory leak: purge if too many clients
        if len(self.clients) > 10000:
            self.clients.clear()

        # Clean up old requests
        self.clients[client_ip] = [
            req_time for req_time in self.clients[client_ip]
            if now - req_time < self.window
        ]

        if len(self.clients[client_ip]) >= self.requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
            )

        self.clients[client_ip].append(now)

    def reset(self):
        """Reset internal storage (useful for tests)."""
        self.clients.clear()
