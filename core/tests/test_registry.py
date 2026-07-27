import pytest
from core.tools.registry import ToolRegistry, ToolDef, ToolResult, get_tool_registry


def test_tool_result_success():
    r = ToolResult(success=True, output="ok")
    assert r.success is True
    assert str(r) == "ok"


def test_tool_result_failure():
    r = ToolResult(success=False, output="", error="fail")
    assert r.success is False
    assert str(r) == "fail"


def test_tool_registry_register():
    reg = ToolRegistry()
    tool = ToolDef(name="TEST", icon="T", description="test", risk_level="auto", fn=lambda a, p: "ok")
    reg.register(tool)
    assert "TEST" in reg.names()


def test_tool_registry_get():
    reg = ToolRegistry()
    tool = ToolDef(name="TEST", icon="T", description="test", risk_level="auto", fn=lambda a, p: "ok")
    reg.register(tool)
    assert reg.get("TEST") is not None
    assert reg.get("test") is not None
    assert reg.get("UNKNOWN") is None


def test_tool_registry_execute():
    reg = ToolRegistry()
    tool = ToolDef(name="TEST", icon="T", description="test", risk_level="auto", fn=lambda a, p: f"executed {a.get('x')}")
    reg.register(tool)
    result = reg.execute("TEST", {"x": "hello"}, "/tmp")
    assert result.success is True
    assert "executed hello" in result.output


def test_tool_registry_execute_unknown():
    reg = ToolRegistry()
    result = reg.execute("UNKNOWN", {}, "/tmp")
    assert result.success is False
    assert "Unknown tool" in result.error


def test_tool_registry_risk_level():
    reg = ToolRegistry()
    tool = ToolDef(name="TEST", icon="T", description="test", risk_level="confirm", fn=lambda a, p: "ok")
    reg.register(tool)
    assert reg.risk_level_for("TEST") == "confirm"


def test_tool_registry_risk_level_run_command():
    reg = ToolRegistry()
    tool = ToolDef(name="RUN_COMMAND", icon="⚡", description="run", risk_level="confirm", fn=lambda a, p: "ok")
    reg.register(tool)
    assert reg.risk_level_for("RUN_COMMAND", {"cmd": "ls"}) == "auto"
    assert reg.risk_level_for("RUN_COMMAND", {"cmd": "rm -rf /"}) == "review"


def test_get_tool_registry():
    reg = get_tool_registry()
    assert "READ_FILE" in reg.names()
    assert "WRITE_FILE" in reg.names()
    assert "GREP" in reg.names()
    assert "RUN_COMMAND" in reg.names()
    assert len(reg.names()) >= 15
