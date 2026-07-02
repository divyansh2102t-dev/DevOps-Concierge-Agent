import time
from collections import defaultdict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.database import init_db
from backend.api import chat, settings, auth, training


class SecurityAndRateLimitMiddleware:
    def __init__(self, app):
        self.app = app
        # Allow a maximum burst of 120 requests, refilling at 2 requests per second
        self.limit = 120.0
        self.refill_rate = 2.0  # tokens per second
        self.tokens = defaultdict(lambda: 120.0)
        self.last_update = defaultdict(time.time)

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_ip = client[0] if client else "127.0.0.1"
        
        # Inject HTTP security headers into the response headers list
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                
                security_headers = [
                    (b"x-frame-options", b"DENY"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"content-security-policy", 
                     b"default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: http://localhost:* http://127.0.0.1:*; media-src 'self' data: blob: http://localhost:* http://127.0.0.1:*; connect-src 'self' http://localhost:* ws://localhost:* http://127.0.0.1:* ws://127.0.0.1:* https://*.googleapis.com;")
                ]
                
                for k, v in security_headers:
                    headers.append((k, v))
                message["headers"] = headers
                
            await send(message)

        # Bypass rate limiting completely for local loopback IPs (localhost / 127.0.0.1 / ::1)
        if client_ip in ("127.0.0.1", "::1", "localhost"):
            await self.app(scope, receive, send_with_headers)
            return

        now = time.time()
        # Refill token bucket based on time passed
        elapsed = now - self.last_update[client_ip]
        self.tokens[client_ip] = min(self.limit, self.tokens[client_ip] + elapsed * self.refill_rate)
        self.last_update[client_ip] = now

        # If bucket is empty, reject with 429 Too Many Requests
        if self.tokens[client_ip] < 1.0:
            await self.send_error(send, 429, b"Too Many Requests: Rate Limit Exceeded")
            return

        self.tokens[client_ip] -= 1.0

        await self.app(scope, receive, send_with_headers)

    async def send_error(self, send, status_code, body):
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"text/plain"),
                (b"content-length", str(len(body)).encode())
            ]
        })
        await send({
            "type": "http.response.body",
            "body": body,
            "more_body": False
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="DevOps Concierge Agent", version="1.0.0", lifespan=lifespan)

# Register security and rate limit middleware at lowest ASGI level
app.add_middleware(SecurityAndRateLimitMiddleware)

import os
allowed_origins = [
    "http://localhost:3000", 
    "http://127.0.0.1:3000",
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost"
]
env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    allowed_origins.extend([o.strip() for o in env_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex="https://.*\\.vercel\\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(training.router, prefix="/api/training", tags=["training"])

from fastapi.staticfiles import StaticFiles
import os
media_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_media")
os.makedirs(media_dir, exist_ok=True)
app.mount("/api/media", StaticFiles(directory=media_dir), name="media")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

# Force reload trigger: system prompt creator attribution update - V3


