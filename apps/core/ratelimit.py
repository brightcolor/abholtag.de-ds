"""Small cache based rate limiter (sliding window approximation)."""

import hashlib

from django.conf import settings
from django.core.cache import cache


def client_key(request) -> str:
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
        "REMOTE_ADDR", ""
    )
    return hashlib.sha256(ip.encode()).hexdigest()[:24]


def is_rate_limited(request, bucket: str) -> bool:
    limit, window = settings.RATE_LIMITS.get(bucket, (60, 60))
    key = f"rl:{bucket}:{client_key(request)}"
    try:
        current = cache.get_or_set(key, 0, timeout=window)
        current = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)
        current = 1
    return current > limit
