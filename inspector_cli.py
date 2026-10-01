import asyncio
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(command=sys.executable, args=["agv_mcp_server.py"])


def _print_result(result):
    for block in result.content:
        text = getattr(block, "text", None)
        if text is None:
            continue
        try:  # JSON이면 보기 좋게
            print(json.dumps(json.loads(text), ensure_ascii=False, indent=2))
        except (json.JSONDecodeError, TypeError):
            print(text)


async def main():
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools

            while True:
                print("\n=== AGV MCP 도구 ===")
                for i, t in enumerate(tools, 1):
                    print(f"{i}. {t.name} — {t.description}")
                print("0. 종료")

                choice = input("\n번호 선택: ").strip()
                if choice == "0":
                    break
                if not choice.isdigit() or not (1 <= int(choice) <= len(tools)):
                    print("잘못된 번호입니다.")
                    continue

                tool = tools[int(choice) - 1]
                schema = tool.inputSchema
                props = schema.get("properties", {})
                required = schema.get("required", list(props))

                # 매개변수 입력받기
                args = {}
                for name, spec in props.items():
                    desc = spec.get("description", "")
                    hint = f" ({desc})" if desc else ""
                    raw = input(f"  {name}{hint} [{spec.get('type','string')}]: ").strip()
                    if raw == "" and name not in required:
                        continue
                    if spec.get("type") == "number":
                        try:
                            args[name] = float(raw)
                        except ValueError:
                            print("  숫자를 입력하세요.")
                            args = None
                            break
                    elif spec.get("type") == "integer":
                        args[name] = int(raw)
                    else:
                        args[name] = raw

                if args is None:
                    continue

                print(f"\n--- {tool.name}({args}) ---")
                try:
                    _print_result(await session.call_tool(tool.name, args))
                except Exception as e:
                    print(f"[에러] {e}")


asyncio.run(main())