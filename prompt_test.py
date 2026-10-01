import asyncio
from mcp_client import MCPClient


async def main():
    async with MCPClient() as mcp:
        print("=== 사용 가능한 프롬프트 ===")
        for p in await mcp.list_prompts():
            args = [a.name for a in (p.arguments or [])]
            print(f"/{p.name} {args} — {p.description}")

        print("\n=== 보간 결과 ===")
        messages = await mcp.get_prompt("diagnose_robot", {"robot_id": "agv-01"})
        for m in messages:
            print(f"[{m.role}]\n{m.content.text}")


asyncio.run(main())