from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agv-fleet")

# 가짜 데이터. 나중에 ROS 2 토픽으로 교체할 부분
ROBOTS = {
    "agv-01": {"battery": 24, "state": "IDLE", "pose": {"x": 1.0, "y": 2.0}},
    "agv-02": {"battery": 85, "state": "NAVIGATING", "pose": {"x": 5.5, "y": 0.8}},
}
LOCATIONS = {"charger": {"x": 0.0, "y": 0.0}, "zone_b": {"x": 8.0, "y": 3.0}}
MAP_BOUNDS = {"x_min": -1.0, "x_max": 10.0, "y_min": -1.0, "y_max": 5.0}


@mcp.tool()
def get_robot_status(robot_id: str) -> dict:
    """Get battery percentage, navigation state and pose of an AGV (e.g. agv-01)."""
    if robot_id not in ROBOTS:
        return {"error": f"unknown robot: {robot_id}"}
    return {"robot_id": robot_id, **ROBOTS[robot_id]}


@mcp.tool()
def list_locations() -> dict:
    """List named locations on the SLAM map with their x, y coordinates in meters."""
    return LOCATIONS


@mcp.tool()
def send_nav_goal(robot_id: str, x: float, y: float) -> dict:
    """Send a navigation goal (map frame, meters) to an AGV. Validated before sending."""
    robot = ROBOTS.get(robot_id)
    if robot is None:
        return {"accepted": False, "reason": "unknown robot"}
    # LLM 판단과 무관하게 코드로 검증하는 안전 레이어
    b = MAP_BOUNDS
    if not (b["x_min"] <= x <= b["x_max"] and b["y_min"] <= y <= b["y_max"]):
        return {"accepted": False, "reason": "goal outside map bounds"}
    if robot["battery"] < 30:
        return {"accepted": False, "reason": "battery below 30%"}
    if robot["state"] != "IDLE":
        return {"accepted": False, "reason": f"robot is {robot['state']}"}
    return {"accepted": True, "robot_id": robot_id, "goal": {"x": x, "y": y}}

import json
from pathlib import Path

MEMORY_FILE = Path("agv_memory.json")


def _load_memory() -> list:
    if MEMORY_FILE.exists():
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    return []


@mcp.tool()
def save_note(robot_id: str, note: str) -> dict:
    """Save an operational note about an AGV (e.g. a recurring fault location) for future sessions."""
    notes = _load_memory()
    notes.append({"robot_id": robot_id, "note": note})
    notes = notes[-50:]  # 메모리도 무한히 키우지 않기
    MEMORY_FILE.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True, "total_notes": len(notes)}


@mcp.tool()
def read_notes(robot_id: str) -> dict:
    """Read saved operational notes for an AGV. Check this before planning a task."""
    notes = [n for n in _load_memory() if n["robot_id"] == robot_id]
    return {"robot_id": robot_id, "notes": notes[-10:]}  # 최근 10개만 = 적시 로딩

@mcp.resource(
    "agv://robots",
    mime_type="application/json"
)
def list_robots() -> list[str]:
    """등록된 AGV id 목록 (자동완성용)."""
    return list(ROBOTS.keys())


@mcp.resource(
    "agv://robots/{robot_id}",
    mime_type="application/json"
)
def fetch_robot(robot_id: str) -> dict:
    """특정 AGV의 현재 상태."""
    if robot_id not in ROBOTS:
        raise ValueError(f"Robot with id {robot_id} not found")
    return {"robot_id": robot_id, **ROBOTS[robot_id]}


@mcp.resource(
    "agv://map",
    mime_type="application/json"
)
def map_info() -> dict:
    """SLAM 맵 경계와 등록된 지점."""
    return {"bounds": MAP_BOUNDS, "locations": LOCATIONS}

if __name__ == "__main__":
    mcp.run()  # stdio 방식