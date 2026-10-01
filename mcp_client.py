import sys
import json
from typing import Any
from pydantic import AnyUrl
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client


class MCPClient:
    """MCP 서버 연결과 세션 정리를 감싸는 클래스."""

    def __init__(self, command: str = sys.executable, args: list[str] | None = None):
        self._params = StdioServerParameters(
            command=command,
            args=args or ["agv_mcp_server.py"],
        )
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None

    async def __aenter__(self):
        read, write = await self._stack.enter_async_context(stdio_client(self._params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc_info):
        await self._stack.aclose()
        self._session = None

    def session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("세션이 없습니다. async with 블록 안에서 사용하세요.")
        return self._session

    async def list_tools(self) -> list[types.Tool]:
        result = await self.session().list_tools()
        return result.tools

    async def call_tool(self, tool_name: str, tool_input: dict) -> types.CallToolResult:
        return await self.session().call_tool(tool_name, tool_input)

    async def read_resource(self, uri: str) -> Any:
        result = await self.session().read_resource(AnyUrl(uri))
        resource = result.contents[0]

        if isinstance(resource, types.TextResourceContents):
            if resource.mimeType == "application/json":
                return json.loads(resource.text)

        return resource.text

    async def list_resources(self) -> list[types.Resource]:
        result = await self.session().list_resources()
        return result.resources

    async def list_resource_templates(self) -> list[types.ResourceTemplate]:
        result = await self.session().list_resourceTemplates() \
            if hasattr(self.session(), "list_resourceTemplates") \
            else await self.session().list_resource_templates()
        return result.resourceTemplates


# 직접 실행하면 간단한 테스트
if __name__ == "__main__":
    import asyncio

    async def _test():
        async with MCPClient() as client:
            for tool in await client.list_tools():
                print(f"- {tool.name}: {tool.description}")
                for name, spec in tool.inputSchema.get("properties", {}).items():
                    desc = spec.get("description", "")
                    print(f"    {name} ({spec.get('type')}) {desc}")

            result = await client.call_tool("get_robot_status", {"robot_id": "agv-01"})
            print("\n[테스트 호출]", result.content[0].text)

    asyncio.run(_test())