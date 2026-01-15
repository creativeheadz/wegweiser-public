import os
import json
import asyncio
import sys


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENT_CORE_PATH = os.path.join(REPO_ROOT, "installerFiles", "Linux", "Agent")
if AGENT_CORE_PATH not in sys.path:
    sys.path.insert(0, AGENT_CORE_PATH)

from core.tool_manager import ToolManager


def test_tool_manager_boolean_and_list_parameters(monkeypatch, tmp_path):
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    tm = ToolManager(str(base_dir), "example.com")

    async def fake_get_tool_executable(self, tool_name):  # type: ignore[unused-argument]
        return "/fake/loki_wrapper.py"

    # Avoid real downloads/unpacking
    monkeypatch.setattr(ToolManager, "get_tool_executable", fake_get_tool_executable)

    calls: dict = {}

    async def fake_create_subprocess_exec(*cmd, **kwargs):  # type: ignore[unused-argument]
        calls["command"] = list(cmd)

        class DummyProc:
            returncode = 0

            async def communicate(self_inner):  # type: ignore[unused-argument]
                return b"", b""

        return DummyProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    result = asyncio.run(
        tm.run_tool("loki", {"test": True, "quick": False, "paths": ["/foo", "/bar"]})
    )

    assert result["status"] == "success"
    cmd = calls["command"]
    # command structure: [python_exe, entry_point_path, ...args]
    args = cmd[2:]
    assert "--test" in args
    assert "--quick" not in args
    # List parameter should appear as repeated flags
    assert args.count("--paths") == 2
    assert "/foo" in args and "/bar" in args


def test_loki_snippet_processes_pending_job(monkeypatch, tmp_path):
    base_dir = tmp_path / "wegweiser"
    config_dir = base_dir / "Config"
    logs_dir = base_dir / "Logs"
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    agent_config = {
        "deviceuuid": "00000000-0000-0000-0000-000000000001",
        "serverAddr": "app.wegweiser.tech",
    }
    (config_dir / "agent.config").write_text(json.dumps(agent_config))

    queue_path = config_dir / "loki_queue.json"
    queue_data = {
        "version": 1,
        "jobs": [
            {"id": "job-1", "parameters": {"test": True}, "status": "pending"},
        ],
    }
    queue_path.write_text(json.dumps(queue_data))

    monkeypatch.setenv("WEGWEISER_BASE_DIR", str(base_dir))

    import importlib.util

    loki_path = os.path.join(REPO_ROOT, "snippets", "unSigned", "Loki.py")
    spec = importlib.util.spec_from_file_location("test_loki_snippet", loki_path)
    assert spec and spec.loader
    Loki = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(Loki)  # type: ignore[attr-defined]

    calls: dict = {}

    class DummyToolManager:
        def __init__(self, base_dir_arg, server_url):  # type: ignore[unused-argument]
            calls["base_dir"] = base_dir_arg
            calls["server_url"] = server_url

        async def run_tool(self, tool_name, parameters):  # type: ignore[unused-argument]
            calls["tool_name"] = tool_name
            calls["parameters"] = parameters
            return {"status": "success", "stdout": "", "stderr": "", "returncode": 0}

    monkeypatch.setattr(Loki, "ToolManager", DummyToolManager)

    Loki.deploy_and_run_loki()

    updated_queue = json.loads(queue_path.read_text())
    job = updated_queue["jobs"][0]
    assert job["id"] == "job-1"
    assert job["status"] == "completed"
    assert "updated_at" in job

    assert calls["tool_name"] == "loki"
    assert calls["parameters"] == {"test": True}

