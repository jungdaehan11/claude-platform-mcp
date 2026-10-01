import asyncio
from mcp_client import MCPClient


async def main():
    async with MCPClient() as mcp:
        print("=== 직접 리소스 ===")
        for r in await mcp.list_resources():
            print(f"- {r.uri} ({r.mimeType})")

        print("\n=== 템플릿 ===")
        for t in await mcp.list_resource_templates():
            print(f"- {t.uriTemplate}")

        # JSON이 딕셔너리로 파싱돼서 바로 접근 가능
        robots = await mcp.read_resource("agv://robots")
        print(f"\n등록된 로봇: {robots}")

        map_info = await mcp.read_resource("agv://map")
        bounds = map_info["bounds"]
        print(f"맵 범위: x {bounds['x_min']}~{bounds['x_max']}, y {bounds['y_min']}~{bounds['y_max']}")

        # 템플릿 리소스를 로봇마다 읽기
        for robot_id in robots:
            status = await mcp.read_resource(f"agv://robots/{robot_id}")
            mark = "🔋" if status["battery"] >= 30 else "⚠️"
            print(f"{mark} {robot_id}: {status['battery']}% / {status['state']}")


asyncio.run(main())