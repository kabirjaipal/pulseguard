import time
import hashlib
from fastapi import Request, HTTPException, status
from app.core.redis_client import redis_client

class RateLimiter:
    """
    A custom Redis-backed fixed-window rate limiter.
    
    Can be used as a FastAPI dependency:
    Depends(RateLimiter(requests_limit=10, window_seconds=60, scope="login"))
    """
    def __init__(self, requests_limit: int, window_seconds: int = 60, scope: str = "global"):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.scope = scope

    def __call__(self, request: Request):
        # 1. Identify the user/session
        # If the Authorization header is present with a Bearer token, we use a hash of the token.
        # Otherwise, we fallback to the client's IP address.
        identifier = None
        auth_header = request.headers.get("authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                # Hash the token so we don't save raw tokens in Redis
                token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
                identifier = f"token:{token_hash}"
            except Exception:
                pass
                
        if not identifier:
            identifier = f"ip:{request.client.host if request.client else 'unknown'}"

        # 2. Determine the time window bucket
        now = int(time.time())
        window_bucket = now // self.window_seconds
        
        # 3. Create the unique Redis key for this limit
        redis_key = f"ratelimit:{self.scope}:{identifier}:{window_bucket}"

        try:
            # Atomically increment the count in Redis
            current_requests = redis_client.incr(redis_key)

            # If this is the first request in the current window bucket, set TTL
            if current_requests == 1:
                # Add 5 seconds buffer to the expire TTL to prevent race conditions
                redis_client.expire(redis_key, self.window_seconds + 5)

            # If client exceeded their limit, raise HTTP 429
            if current_requests > self.requests_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )
        except HTTPException:
            raise
        except Exception as e:
            # Bypass rate limiter if Redis is offline/erroring to keep service available
            print(f"Rate limiting engine connection error: {str(e)}")
