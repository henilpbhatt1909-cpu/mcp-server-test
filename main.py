
import hashlib
from contextvars import ContextVar
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from mcp.server.fastmcp import FastMCP, Context

EMAIL = "24f2005969@ds.study.iitm.ac.in"
challenge_header = ContextVar("challenge_header", default=None)

mcp = FastMCP("Exam MCP Server")


@mcp.tool()
async def solve_challenge(ctx: Context) -> str:
    """Calculate the answer using the current HTTP challenge."""
    challenge = challenge_header.get()

    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    text = f"{challenge}:{EMAIL}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


mcp_app = mcp.streamable_http_app()


class HeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        value = headers.get(b"x-exam-challenge", b"").decode("ascii")
        token = challenge_header.set(value or None)

        try:
            await self.app(scope, receive, send)
        finally:
            challenge_header.reset(token)


mcp_app = HeaderMiddleware(mcp_app)


@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


# The MCP SDK owns the HTTP routes
app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "running"}


app.mount("/", mcp_app)
