import asyncio
from mcp_client import MCPClient


async def main():
    async with MCPClient() as mcp:
        session = mcp.session()

        res = await session.list_resources()
        print("=== 직접 리소스 ===")
        for r in res.resources:
            print(f"- {r.uri} ({r.mimeType})")

        tpl = await session.list_resource_templates()
        print("\n=== 템플릿 리소스 ===")
        for t in tpl.resourceTemplates:
            print(f"- {t.uriTemplate}")

        print("\n=== 읽기 ===")
        for uri in ["agv://robots", "agv://map", "agv://robots/agv-01"]:
            result = await session.read_resource(uri)
            print(f"[{uri}]\n{result.contents[0].text}\n")


asyncio.run(main())