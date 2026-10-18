
import hashlib
from contextvars import ContextVar
from contextlib import asynccontextmanager

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.transport_security import TransportSecuritySettings

EMAIL = "24f2005969@ds.study.iitm.ac.in"
challenge_header = ContextVar("challenge_header", default=None)

security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False
)

mcp = FastMCP(
    "Exam MCP Server",
    stateless_http=True,
    transport_security=security,
)


@mcp.tool()
async def solve_challenge(ctx: Context) -> str:
    """Hash the challenge from the current HTTP request."""
    challenge = challenge_header.get()

    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    message = f"{challenge}:{EMAIL}"
    return hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]


mcp_app = mcp.streamable_http_app()


class HeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        raw = headers.get(b"x-exam-challenge", b"")
        challenge = raw.decode("ascii") if raw else None

        token = challenge_header.set(challenge)
        try:
            await self.app(scope, receive, send)
        finally:
            challenge_header.reset(token)


mcp_app = HeaderMiddleware(mcp_app)


@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


app = FastAPI(lifespan=lifespan)
app.mount("/", mcp_app)
