"""HTTP request utilities shared across middleware."""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Extract client IP from request.

    Checks X-Real-IP (set by nginx) first, then falls back to the
    direct connection address.  X-Forwarded-For is intentionally
    NOT trusted because it can be spoofed by end-users; nginx sets
    X-Real-IP from ``$remote_addr`` which is the actual TCP peer.
    """
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if hasattr(request.client, "host"):
        return request.client.host

    return "unknown"
