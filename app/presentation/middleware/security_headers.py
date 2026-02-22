from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # X-Frame-Options: DENY
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options: nosniff
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection: 1; mode=block
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy: strict-origin-when-cross-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Strict-Transport-Security (HSTS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content-Security-Policy (CSP)
        # Allow images from self, data:, and typical CDN sources for Swagger UI
        # Allow scripts and styles from self and 'unsafe-inline' (needed for Swagger UI)
        # Note: 'unsafe-inline' weakens CSP but is required for Swagger UI without nonce/hash
        csp = (
            "default-src 'self'; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;"
        )
        response.headers["Content-Security-Policy"] = csp

        # Permissions-Policy
        # Disable geolocation, microphone, camera by default
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response
