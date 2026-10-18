import asyncio
import hashlib
import secrets

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


URL = "http://127.0.0.1:8000/mcp"
EMAIL = "24f2005969@ds.study.iitm.ac.in"


async def main():
    for i in range(5):
        challenge = secrets.token_hex(16)
        expected = hashlib.sha256(
            f"{challenge}:{EMAIL}".encode("utf-8")
        ).hexdigest()[:16]

        headers = {"X-Exam-Challenge": challenge}

        async with streamablehttp_client(
            URL, headers=headers
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.list_tools()
                names = [tool.name for tool in result.tools]
                assert names == ["solve_challenge"], names

                result = await session.call_tool(
                    "solve_challenge", {}
                )

                assert len(result.content) == 1
                assert result.content[0].type == "text"
                actual = result.content[0].text

                assert actual == expected, (
                    f"Expected {expected}, got {actual}"
                )

                print(f"Test {i + 1}: PASS - {actual}")


asyncio.run(main())
