# Anthropic Academy 학습 정리

> Claude Platform 101 (2026.09 수료) + Model Context Protocol 소개
> 실습 저장소: `claude-platform-101`

---

## 목차

1. [Claude Platform 101](#1-claude-platform-101)
2. [Model Context Protocol](#2-model-context-protocol)
3. [Claude ↔ Gemini 대응표](#3-claude--gemini-대응표)
4. [퀴즈 핵심 포인트](#4-퀴즈-핵심-포인트)
5. [실습 파일 맵](#5-실습-파일-맵)
6. [AGV 프로젝트 적용 설계](#6-agv-프로젝트-적용-설계)
7. [실행 중 겪은 문제와 해결](#7-실행-중-겪은-문제와-해결)

---

# 1. Claude Platform 101

## 1-1. 첫 API 호출

`messages.create`에 넘기는 **필수 세 가지**:

| 매개변수 | 뜻 |
|---|---|
| `model` | 어떤 모델이 요청을 처리할지 |
| `max_tokens` | 응답 길이 상한 |
| `messages` | `role`(user/assistant)과 `content`의 목록 |

```python
response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1024,
    system="You are a terse senior code reviewer.",  # 선택 사항
    messages=[{"role": "user", "content": "..."}],
)

for block in response.content:   # 문자열이 아니라 블록 배열
    if block.type == "text":
        print(block.text)
```

- `system`은 **선택**. 페르소나와 규칙을 지정하는 자리
- 응답 `content`는 **블록 배열** → 반복문으로 `type` 확인 (text, tool_use, thinking 등이 섞일 수 있음)
- API 키는 `messages.create`의 인자가 아니라 **클라이언트 생성 시 환경변수**에서 읽힘
- 키는 `.env`에 두고 `.gitignore`에 반드시 등록

## 1-2. 도구(Tool)와 에이전트 루프

도구 = **이름 + 설명 + 입력 스키마(JSON)**. `tools` 배열로 전달한다.

> **최重要 원칙: 모델은 도구를 실행하지 않는다. 내 코드가 실행한다.**

### 루프 구조

1. 도구 목록과 함께 메시지 전송
2. `stop_reason == "tool_use"` → 응답에서 도구 요청을 꺼내 **내 코드가 실행**
3. 결과를 `tool_result`(+ `tool_use_id`)로 다시 전송
4. `stop_reason == "end_turn"`이 될 때까지 반복

### 기억할 점

- **설명(description)이 품질을 좌우**한다. 에이전트가 도구를 못 쓰거나 잘못 쓰는 가장 큰 원인이 모호한 설명
- 도구를 추가하려면 배열에 스키마 추가 + 디스패치(switch/if)에 분기 추가
- **툴 러너**(SDK 베타): 함수만 넘기면 스키마 생성과 루프를 SDK가 대신 처리
- 무한 반복 방지를 위해 **최대 턴 수 제한**을 두는 것이 안전

## 1-3. 확장적 사고 (Extended thinking)

최종 답변 전에 단계별로 추론하게 하는 기능.

- Opus 5에서는 **적응형(adaptive)**이고 기본 활성화 — 모델이 언제 얼마나 생각할지 스스로 결정
- 사고량 조절: `output_config`의 `effort` → `low` / `medium` / `high`(기본) / `xhigh` / `max`
- ⚠️ **`effort`는 `thinking` 블록이 아니라 `output_config` 안에 들어간다** (시험 함정)
- `thinking={"type": "adaptive", "display": "summarized"}` → 추론 요약을 응답에 포함

| 쓸 때 | 끌 때 |
|---|---|
| 수학, 다단계 논리 | 단순 분류 |
| 코드 디버깅 | 정보 추출 |
| 규제·규정 분석 | 정형화된 변환 작업 |
| 트레이드오프 비교 | → 지연과 비용만 증가 |

## 1-4. 서버 도구 vs 클라이언트 도구

| 종류 | 스키마 정의 | 실행 위치 | 에이전트 루프 |
|---|---|---|---|
| 사용자 정의 도구 | 내가 작성 | 내 코드 | **필요** |
| **서버 도구** | Anthropic | **Anthropic 서버** | **불필요** |
| 클라이언트 도구 | Anthropic(스키마 제공) | 내 코드 | 필요 |

- **서버 도구**: 웹 검색(`web_search`), 코드 실행(`code_execution`), 웹 페치
  - 선언만 하면 **결과가 같은 응답 안에** 들어옴. `stop_reason` 분기도, 결과 재전송도 없음
  - 새 블록 타입: `server_tool_use`, 코드 실행 결과 블록
- **클라이언트 도구**: memory, bash — 스키마는 Anthropic이 게시, 실행은 내 쪽

> 코드 실행 도구의 가치: LLM이 암산하면 틀릴 수 있는 계산을 **코드로 돌려 정확하게** 만든다.

## 1-5. 스킬 (Skills)

작업 절차·형식·톤을 담은 **폴더(`SKILL.md` 포함)**를 한 번 업로드하고 ID로 참조한다.

```python
container={"skills": [{"type": "custom", "skill_id": skill.id, "version": "latest"}]}
tools=[{"type": "code_execution_...", "name": "code_execution"}]   # 필수
```

- 스킬은 `container.skills` **배열** → 한 요청에 여러 개 연결 가능
- **코드 실행 도구가 반드시 활성화**되어야 함 (스킬이 그 컨테이너 안에서 실행됨)
- 이제 정식 기능이라 **베타 헤더 불필요**
- 핵심 효과: **사용자 프롬프트는 한 줄, 절차는 스킬에** → 팀 전체 산출물 형식 표준화

## 1-6. 컨텍스트 관리 4패턴

**컨텍스트 = 매 호출마다 모델에 들어가는 전부**: 시스템 메시지, 메시지 기록, 도구 정의와 결과, 파일·스킬, 사고 블록.
창(window)은 한정되어 있고 넣은 만큼 비용이 든다 → **모두가 아니라 적절한 것을 넣는 것**이 목표.

| 패턴 | 해결하는 문제 | 성격 |
|---|---|---|
| **1. 적시 로딩(Just-in-time)** | 비용, 창 크기 | **설계 패턴** (API 기능 아님) |
| **2. 서버 측 압축(Compact)** | 긴 대화로 창 초과 | API 기능, 베타 |
| **3. 프롬프트 캐싱** | 반복 호출 비용 | API 기능 |
| **4. 메모리 도구** | 세션 간 상태 없음 | API 기능 |

- **적시 로딩**: 전체 데이터를 미리 넣지 말고, 필요할 때 도구로 가져오게 한다
- **압축**: `context_management`의 `edits`에 `compact_...` 타입 → 임계값 넘으면 **자동** 요약
- **캐싱**: 시스템 프롬프트, 도구 정의, 긴 문서 등 **안정적인 부분**을 표시해 재사용
- **메모리**: 모델은 도구로 읽고 쓰기만 하고, **저장소 백엔드는 클라이언트가 구현**

> 각 패턴은 서로 다른 실패 모드를 해결한다. 내가 겪는 문제에 맞는 패턴을 고를 것.

## 1-7. 관리형 에이전트 (Managed Agents)

**구성 요소 4개 (순서대로)**

| 요소 | 뜻 |
|---|---|
| **에이전트** | 모델 + 시스템 프롬프트 + 도구 세트 — **재사용 가능** |
| **환경** | 실행 장소(클라우드/자체 호스팅), 네트워크 설정 |
| **세션** | 특정 환경에서의 **1회 실행 = 작업 단위** |
| **이벤트** | 오가는 메시지, 도구 호출, 결과, 답변 |

- `while` 루프를 돌리는 대신 **이벤트를 보내고 이벤트를 읽는다**
- ⚠️ **스트림을 먼저 열고 → 시작 메시지 전송.** 스트림은 열린 뒤의 이벤트만 전달한다 (시험 함정)
- `events`는 **복수형 배열**
- 주요 이벤트: `agent.message`(텍스트), `agent.tool_use`(도구 선택), `session.status_idle`(완료)
- 번들 도구 세트(`agent_toolset_...`)로 파일/bash/웹 도구를 직접 정의 없이 사용
- **적합**: 장기 실행, 샌드박스 작업, 백그라운드 작업
- **부적합**: 빠른 단일 질의, 모든 도구 호출을 검사해야 하는 경우, 최저 비용 대량 분류

---

# 2. Model Context Protocol

## 2-1. MCP란

**모델이 외부 도구·데이터에 접속하는 방식을 정한 공개 표준(프로토콜).**
프로그램이 아니라 "약속"이다. USB-C처럼, 한 번 만든 서버를 여러 모델·앱이 같은 방식으로 쓴다.

- MCP 이전: 모델마다 전용 도구 코드를 따로 작성
- MCP 이후: 도구를 **MCP 서버 하나로** 만들면 Claude, Gemini, Claude Code 등이 모두 연결
- 핵심 가치: **MCP가 없으면 모든 연동 코드를 직접 작성하고 유지보수해야 한다**

```
[모델] ←→ [MCP 클라이언트] ←→ [MCP 서버] ←→ [실제 시스템]
                              ↑ 서버 쪽만 바꾸면 바깥은 그대로
```

## 2-2. 세 가지 기본 요소(Primitives)

| 기둥 | 성격 | HTTP 비유 | **누가 시작하는가** |
|---|---|---|---|
| **Tools** | 행동을 수행 | POST | **모델**이 판단 |
| **Resources** | 데이터를 제공 | GET | **앱 코드**가 요청 |
| **Prompts** | 질문·워크플로 템플릿 | — | **사용자**가 선택(`/명령`) |

> 퀴즈 핵심: "사용자가 버튼을 눌러 워크플로를 시작" → **Prompts** (사용자가 시점을 제어하므로)

## 2-3. 서버 구현

```python
from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("DocumentMCP", log_level="ERROR")
```

### Tools — 데코레이터 + 타입 힌트

```python
@mcp.tool(
    name="read_doc_contents",
    description="Read the contents of a document and return it as a string."
)
def read_document(
    doc_id: str = Field(description="Id of the document to read")
):
    ...
```

- JSON 스키마를 직접 쓰지 않는다. **타입 힌트 + `Field(description=...)`**로 SDK가 자동 생성
- `Field` 설명은 모델이 **각 인자에 뭘 넣을지** 판단하는 근거 → 단위·좌표계 등을 꼭 명시

### Resources — 두 종류

```python
@mcp.resource("docs://documents", mime_type="application/json")
def list_docs() -> list[str]:                       # 직접(static)
    return list(docs.keys())

@mcp.resource("docs://documents/{doc_id}", mime_type="text/plain")
def fetch_doc(doc_id: str) -> str:                  # 템플릿
    return docs[doc_id]
```

- **직접 리소스**: 고정 URI, 변하지 않는 목록 등
- **템플릿 리소스**: URI에 `{}` 자리표시자 → SDK가 파싱해 함수 인자로 전달
- `mime_type`은 클라이언트에게 주는 힌트: `application/json`, `text/plain`, `application/pdf`
- **반환값 직렬화는 SDK가 처리** → JSON 문자열로 변환할 필요 없음
- 요청/응답: `ReadResourceRequest` → `ReadResourceResult`

### Prompts

```python
@mcp.prompt(name="diagnose_robot", description="...")
def diagnose_robot(robot_id: str = Field(description="...")) -> str:
    return f"{robot_id}의 상태를 점검해줘. ..."
```

- 사용자가 `/명령`으로 고르면 서버가 **완성된 메시지**를 반환 (인자 보간)
- 긴 지시문을 사용자가 매번 타이핑할 필요가 없어짐

## 2-4. 클라이언트 구현

대부분의 프로젝트는 **클라이언트 또는 서버 중 하나만** 만든다. 학습용으로는 둘 다 만든다.

구성:
- **Client Session** — SDK가 제공하는 실제 연결
- **MCP Client** — 세션을 감싸 **정리(cleanup)를 자동화**하는 내 클래스

```python
async def list_tools(self) -> list[types.Tool]:
    return (await self.session().list_tools()).tools

async def call_tool(self, tool_name, tool_input) -> types.CallToolResult | None:
    return await self.session().call_tool(tool_name, tool_input)

async def read_resource(self, uri: str) -> Any:
    result = await self.session().read_resource(AnyUrl(uri))
    resource = result.contents[0]
    if isinstance(resource, types.TextResourceContents):
        if resource.mimeType == "application/json":
            return json.loads(resource.text)      # MIME 타입으로 파싱 분기
    return resource.text

async def list_prompts(self) -> list[types.Prompt]:
    return (await self.session().list_prompts()).prompts

async def get_prompt(self, prompt_name, args: dict[str, str]):
    return (await self.session().get_prompt(prompt_name, args)).messages
```

- 메시지 타입: 도구 목록 조회는 **`ListToolsRequest`**, 도구 실행은 `CallToolRequest`
- `read_resource`는 `contents[0]`을 꺼내고 **MIME 타입에 따라** 파싱 방식을 나눈다
- 세션은 **생명주기 관리가 필요** → `AsyncExitStack` + `async with`로 감싸면 정리가 자동

## 2-5. 테스트 방법

- **MCP Inspector**: `mcp dev server.py` → 브라우저에서 Connect → Tools/Resources/Prompts 탭에서 클릭으로 실행 (Node.js 필요)
- **직접 만든 CLI**: 도구 목록을 읽어 번호로 고르고 인자를 입력받아 실행 — Node 없이 동작, 모델 호출 0회
- 모델 없이 **서버만 단독 검증**할 수 있다는 게 핵심. 특히 안전 검증 로직 테스트에 유용

---

# 3. Claude ↔ Gemini 대응표

실습을 Gemini 무료 티어로 진행하면서 정리한 대조표.

| 개념 | Claude | Gemini |
|---|---|---|
| 응답 본문 | `response.content` (블록 배열) | `response.text` |
| 도구 요청 신호 | `stop_reason == "tool_use"` | `response.function_calls` 존재 |
| 종료 신호 | `stop_reason == "end_turn"` | `function_calls` 없음 |
| 도구 결과 전달 | `tool_result` + `tool_use_id` | `Part.from_function_response` |
| 자동 도구 실행 | 툴 러너(toolRunner) | 자동 함수 호출(AFC) + `chat.send_message` |
| 사고 기능 | `thinking` + `output_config.effort` | `thinking_config.thinking_level` |
| 사고 내용 보기 | `display: "summarized"` | `include_thoughts=True` |
| 웹 검색 | `web_search` 서버 도구 | `google_search` 도구 (무료 티어 제한) |
| 코드 실행 | `code_execution` 서버 도구 | `code_execution` 도구 |
| 스킬 | `container.skills` | 없음 → `SKILL.md`를 시스템 지시로 주입해 대체 |
| 관리형 에이전트 | `agents` / `environments` / `sessions` | 없음 |
| MCP | 네이티브 지원 | SDK 연동 가능(실험적), 수동 루프로 우회 |

**비용 구조 구분**

| 항목 | 성격 |
|---|---|
| claude.ai 구독(Pro 등) | 채팅 앱 사용 권한. **코드에서 API 호출에는 못 씀** |
| Claude API 크레딧 | **선불 충전**. 충전액 이상 지출되지 않음 |
| Gemini API | 무료 티어 존재(RPM/TPM/RPD 제한), 유료는 **후불** → 예산 알림 필수 |

---

# 4. 퀴즈 핵심 포인트

- 도구를 실제로 실행하는 주체 → **내 코드** (모델은 요청만 생성)
- `messages.create` 필수 3가지 → **model, max_tokens, messages** (API 키·system은 아님)
- 확장적 사고의 `effort` 위치 → **`output_config` 안**
- 관리형 에이전트가 적합한 곳 → **장기 실행, 샌드박스, 백그라운드 작업**
- 관리형 에이전트 순서 → 에이전트 → 환경 → 세션 → 이벤트, **스트림 먼저 열고 메시지 전송**
- 컨텍스트 관리가 중요한 이유 → **창은 한정적이고 넣은 만큼 비용이 든다**
- Claude Code에서 Claude API 작업용 내장 스킬 → **`/claude-api`**
- MCP 도구 목록 조회 메시지 → **`ListToolsRequest`** (실행은 `CallToolRequest`)
- 사용자가 버튼으로 워크플로 시작 → **Prompts**
- `docs://documents/{doc_id}`처럼 ID가 바뀌는 리소스 → **템플릿 리소스**
- MCP가 없을 때의 문제 → **모든 연동 도구 코드를 직접 작성·유지보수해야 함**

---

# 5. 실습 파일 맵

| 파일 | 다룬 개념 | API |
|---|---|---|
| `main.py` / `claude_main.py` | 첫 API 호출, 시스템 프롬프트, 응답 블록 | Gemini / Claude |
| `agent.py` | 도구 정의 + 에이전트 루프 **직접 구현** | Gemini |
| `agent_auto.py` | 자동 함수 호출(툴 러너 대응) | Gemini |
| `thinking.py` | 사고 수준 low/high 비교, 생각 토큰 측정 | Gemini |
| `server_tools.py` | 서버 도구(코드 실행, 웹 검색) | Gemini |
| `skill_report.py` + `agv-report-skill/SKILL.md` | 스킬 방식 — 절차를 파일로 분리 | Gemini |
| `managed_agent.py` | 관리형 에이전트(에이전트/환경/세션/이벤트) | Claude |
| `agv_mcp_server.py` | MCP 서버 — Tools / Resources / Prompts + 안전 검증 + 메모리 | — |
| `mcp_client.py` | MCP 클라이언트 클래스(세션 정리 자동화) | — |
| `mcp_list.py` | 도구 목록 조회 | — |
| `inspector_cli.py` | Inspector 대체 CLI 테스트 도구 | — |
| `resource_test.py` | 리소스 조회 + MIME 기반 파싱 | — |
| `prompt_test.py` | 프롬프트 목록 + 인자 보간 | — |
| `memory_test.py` | 세션 간 지속 메모리 | — |
| `mcp_agent.py` | 모델 ↔ MCP 서버 연결 에이전트 루프 | Gemini |

---

# 6. AGV 프로젝트 적용 설계

## 6-1. 구조

```
[사용자]  Claude Code / 관제 앱
    │  "충전소로 보내줘", "왜 멈췄어?"
    ▼
[LLM 에이전트]
    │  MCP
    ▼
[amr_mcp_server]  ← rclpy 노드 겸 MCP 서버
    │  ROS 2 토픽 / 서비스 / 액션
    ▼
[기존 스택]  slam_toolbox · Nav2 · 라이다 드라이버 · 모터 제어
```

## 6-2. 도구 설계안

| 구분 | 도구 | 내부 동작 |
|---|---|---|
| 조회 | `get_robot_pose` | `/amcl_pose` 또는 TF(`map→base_link`) |
| 조회 | `get_battery` | `/battery_state` |
| 조회 | `get_scan_summary` | `/scan` 요약(전방 최소거리, 유효 포인트 비율) |
| 조회 | `get_map_info` | `/map` 해상도·크기·원점 |
| 조회 | `get_last_nav_error` | Nav2 액션 결과 코드 |
| 명령 | `send_nav_goal(x, y, yaw)` | **검증 후** Nav2 `navigate_to_pose` |
| 명령 | `save_map(name)` | 맵 저장 서비스 |

## 6-3. 설계 원칙 (면접 설명용)

1. **실시간 제어 루프에 LLM을 넣지 않는다.**
   SLAM·장애물 회피는 수십 Hz로 동작해야 하지만 API 호출은 수 초가 걸리고 실패(429/503)할 수 있다.
   LLM은 배차 판단, 로그 분석 같은 **상위 레이어**에만 사용한다.

2. **명령 도구는 서버 코드에서 검증한다.**
   맵 범위, 코스트맵 점유, 배터리, 로봇 상태를 코드로 확인한 뒤에만 Nav2로 전달.
   E-stop과 collision monitor는 LLM과 무관하게 항상 동작한다.

3. **조회와 명령을 분리한다.**
   API 수준 필터링(모델에게 안 보여주기)과 서버 수준 검증(보여줘도 실행 안 하기)은 **방어 층이 다르므로 둘 다** 적용.

4. **원시 센서 데이터를 컨텍스트에 넣지 않는다.**
   라이다 스캔은 한 번에 수백 개 값 → 서버에서 요약해 도구로 전달.
   전체 데이터가 필요한 관제 화면은 **리소스**로 따로 받는다.

5. **외부 API 장애에 대비한다.**
   LLM 응답 실패 시 규칙 기반 배차로 넘어가는 대체 경로(fallback)를 둔다.

## 6-4. 검증된 사례 (실습에서 실제로 발생)

- **사례 1 — 모델 판단보다 서버 검증이 우선**
  모델이 배터리 24%임을 조회해 알고도 `send_nav_goal`을 호출했고,
  서버가 `battery below 30%`로 거절 → 안전 레이어가 코드에 있어야 하는 이유를 실증.

- **사례 2 — 규칙 자체의 설계 버그**
  "배터리 30% 미만 출발 금지" 규칙 때문에 **충전소로도 못 가는** 모순 발생.
  LLM 프롬프트가 아니라 **서버 규칙에 충전소 예외**를 추가해 해결.

## 6-5. 배치(deployment) 계획

| 단계 | MCP 서버 위치 | 전송 방식 |
|---|---|---|
| 개발 | PC | stdio |
| 실로봇 테스트 | PC (Wi-Fi로 Pi의 토픽 구독) | stdio |
| 배포 | Pi 탑재 | HTTP + 토큰 인증, 네트워크 범위 제한 |

**전원 관련 확인 사항 (Pi 5)**
- Pi 5 권장 전원은 5V 5A. 5A를 못 받으면 **USB 출력 전류가 제한**되어 USB 라이다가 불안정할 수 있음
- 확인: `vcgencmd get_throttled` (0x0이면 정상), `vcgencmd pmic_read_adc EXT5V_V`
- 대응: 전원 공급형 USB 허브 / 5V 5A 전원 또는 DC-DC 컨버터 / 모터 전원은 반드시 분리
- 라이다 전원이 먼저 끊기는 상황 대비 → `/scan` 타임아웃 감지 시 정지 로직 필요

---

# 7. 실행 중 겪은 문제와 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `Activate.ps1` 보안 오류 | PowerShell 실행 정책 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| 패키지가 전역에 설치됨 | 가상환경 미활성화 상태로 `pip install` | `(.venv)` 표시 확인 후 재설치, `pip show`의 `Location` 검증 |
| `401 authentication_error` | `.env` 키에 `sk-ant-`가 중복 입력됨 | 키 앞부분·길이만 출력해 점검 후 수정 |
| `429 RESOURCE_EXHAUSTED` | 무료 티어 한도(RPD 20 등) 초과 | 경량 모델 사용, 호출 횟수 절약, 한도 대시보드 확인 |
| `503 UNAVAILABLE` | 서버 혼잡(5xx = 서버 측) | 지수적 대기 재시도 구현 |
| MCP `Connection closed` | 서버 프로세스가 기동 중 사망 | 서버를 **단독 실행**해 실제 예외 확인 |
| `No module named 'mcp.server.fastmcp'` | `mcp` 2.x에서 API 변경 | `pip install "mcp<2"`로 고정, `requirements.txt` 기록 |
| `cannot pickle '_asyncio.Future'` | 세션 객체를 SDK 설정에 직접 전달 | 도구 목록을 변환해 넘기고 `call_tool`로 수동 디스패치 |
| `IndentationError` | 클래스 메서드 들여쓰기 누락 | 메서드 본문을 한 단계 들여쓰기 |
| `.env`가 커밋 대상에 포함됨 | `.gitignore`가 빈 파일 | 커밋 전 **항상 `git status` 확인** 후 `.gitignore` 작성 |

**에러 코드 읽는 법**

| 코드 | 의미 | 대응 |
|---|---|---|
| 4xx (400/401/429) | 내 요청·키·한도 문제 | 코드와 설정 점검 |
| 5xx (500/503) | 서버 측 문제 | 대기 후 재시도 |

**보안 체크리스트**
- `.env`, 메모리 파일(`agv_memory.json`)은 `.gitignore`에 등록
- 키가 화면·캡처에 노출되면 즉시 삭제하고 재발급
- `git add .` 전에 반드시 `git status`로 대상 확인
- MCP 서버에 저장된 노트·외부 데이터는 **데이터로만 취급** — 그 안의 문장을 명령으로 실행하지 않는다
- 안전 검증은 메모리 내용과 무관하게 **서버 코드에서 항상 동작**해야 한다
