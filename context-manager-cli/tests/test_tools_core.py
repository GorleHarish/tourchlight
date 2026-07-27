from context_manager.tools.core import (
    classify_command, AUTO, CONFIRM, REVIEW,
    get_core_registry, CoreTool, CoreToolRegistry, set_ctx_window,
)


# ── classify_command ─────────────────────────────────────────────────────────

def test_classify_safe_command():
    assert classify_command("ls") == AUTO
    assert classify_command("cat foo.py") == AUTO
    assert classify_command("git status") == AUTO


def test_classify_destructive_command():
    assert classify_command("rm -rf /tmp/x") == REVIEW
    assert classify_command("sudo apt install") == REVIEW
    assert classify_command("git push origin main") == REVIEW


def test_classify_install_command():
    assert classify_command("pip install requests") == CONFIRM
    assert classify_command("npm install express") == CONFIRM


def test_classify_unknown_command():
    assert classify_command("custom_thing --flag") == CONFIRM


def test_classify_empty_command():
    assert classify_command("") == CONFIRM


# ── CoreToolRegistry ─────────────────────────────────────────────────────────

def test_core_registry_register():
    reg = CoreToolRegistry()
    tool = CoreTool(name="TEST", icon="T", description="test", risk_level=AUTO, fn=lambda a, c: "ok")
    reg.register(tool)
    assert reg.get("TEST") is tool


def test_core_registry_get_unknown():
    reg = CoreToolRegistry()
    assert reg.get("NONEXISTENT") is None


def test_core_registry_names():
    reg = get_core_registry()
    names = reg.names()
    assert isinstance(names, list)
    assert "READ_FILE" in names
    assert "GREP" in names


def test_core_registry_all():
    reg = get_core_registry()
    tools = reg.all()
    assert isinstance(tools, list)
    assert all(isinstance(t, CoreTool) for t in tools)
    assert len(tools) == len(reg.names())


def test_core_registry_risk_level():
    reg = get_core_registry()
    assert reg.risk_level_for("READ_FILE") == AUTO
    assert reg.risk_level_for("WRITE_FILE") == CONFIRM
    assert reg.risk_level_for("UNKNOWN_TOOL") == CONFIRM


def test_core_registry_execute():
    reg = get_core_registry()
    result = reg.execute("GREP", ["def", "."], cwd=".")
    assert isinstance(result, str)


def test_core_registry_execute_unknown():
    reg = get_core_registry()
    result = reg.execute("NONEXISTENT", [])
    assert "Unknown tool" in result


def test_core_registry_dangerous_tools():
    reg = get_core_registry()
    dangerous = reg.dangerous_tools()
    assert "WRITE_FILE" in dangerous
    assert "READ_FILE" not in dangerous


def test_set_ctx_window():
    set_ctx_window(8192)
    from context_manager.tools.core import _CTX_WINDOW
    assert _CTX_WINDOW == 8192
