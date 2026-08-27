"""Inspector pane mixin: telemetry stats, token budget gauges, task trees, and system health."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.markup import escape
from rich.text import Text
from textual import events, on, work
from textual.widgets import Button, Select, Static

from core.memory.manager import TieredMemory
from core.tools.task_helpers import get_workspace_task_status_summary
from rlm_optimized.config import CTX_SIZE, is_port_in_use
from rlm_optimized.tui_widgets.command_palette import PromptTextArea
from rlm_optimized.tui_widgets.file_tree import GitFileTree
from rlm_optimized.tui_widgets.format import (
    build_plan_overview_text,
    build_plan_text,
    build_skills_overview_text,
    build_task_checklist_text,
    import_skill_file,
)
from rlm_optimized.tui_widgets.modals import ShortcutsHelpModal, SkillUploadModal
from rlm_optimized.tui_widgets.status_bar import StatusBar


class InspectorManagerMixin:
    """Mixin providing live telemetry, sidebar inspector metrics, and context budget breakdown."""

    def _build_system_health_text(self) -> str:
        cpu_pct = 0
        ram_pct = 0
        ram_detail = ""

        try:
            import psutil

            cpu_val = psutil.cpu_percent(interval=None)
            cpu_pct = min(100, max(0, int(round(cpu_val))))

            vm = psutil.virtual_memory()
            ram_pct = min(100, max(0, int(round(vm.percent))))
            used_gb = vm.used / (1024**3)
            total_gb = vm.total / (1024**3)
            ram_detail = f" ({used_gb:.1f}/{total_gb:.1f} GB)"
        except Exception:
            try:
                load1, _, _ = os.getloadavg()
                cpu_count = os.cpu_count() or 1
                cpu_pct = min(100, int((load1 / cpu_count) * 100))
            except Exception:
                cpu_pct = 0

            try:
                import time as _t
                now_sys = _t.time()
                if now_sys - getattr(self, "_vm_stat_ts", 0.0) < 5.0 and hasattr(self, "_vm_stat_ram_pct"):
                    ram_pct = self._vm_stat_ram_pct
                else:
                    import subprocess

                    p = subprocess.run(
                        ["vm_stat"], capture_output=True, text=True, timeout=2
                    )
                    lines = p.stdout.splitlines()
                    pages = {}
                    for line in lines[1:]:
                        parts = line.split(":")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val = int(parts[1].strip().rstrip("."))
                            pages[key] = val
                    page_size = 4096
                    free = (
                        pages.get("Pages free", 0) + pages.get("Pages speculative", 0)
                    ) * page_size
                    active = pages.get("Pages active", 0) * page_size
                    wired = pages.get("Pages wired down", 0) * page_size
                    compressed = pages.get("Pages occupied by compressor", 0) * page_size
                    used = active + wired + compressed
                    total = used + free + (pages.get("Pages inactive", 0) * page_size)
                    ram_pct = int((used / total) * 100) if total > 0 else 0
                    self._vm_stat_ts = now_sys
                    self._vm_stat_ram_pct = ram_pct
            except Exception:
                ram_pct = 0

        # Context Token Calculation
        tokens_est = self._live_context_tokens()

        ctx_max = CTX_SIZE
        ctx_pct = min(100, int((tokens_est / ctx_max) * 100)) if ctx_max > 0 else 0

        tps_val = getattr(self, "_live_tps", 0.0)
        lat_val = getattr(self, "_live_latency_ms", 0.0)

        tps_str = (
            f"{tps_val:.1f}"
            if tps_val > 0
            else ("0.0" if not self._is_running else "calculating...")
        )
        lat_str = (
            f"{int(lat_val)}ms"
            if lat_val > 0
            else ("0ms" if not self._is_running else "--")
        )

        is_engine_ready = self.engine_port <= 0 or getattr(
            self, "_last_server_online", False
        )
        status_badge = (
            "[bold green]● ENGINE READY[/bold green]"
            if is_engine_ready
            else "[bold red]○ ENGINE OFFLINE (Port 1234)[/bold red]"
        )

        speedometer = (
            f"[bold cyan]⚡ INFERENCE SPEEDOMETER[/bold cyan]  {status_badge}\n"
            f"[bold green]SPEED: {tps_str} t/s[/bold green] [dim](Latency: {lat_str})[/dim]\n"
        )

        bar_width = 14
        filled = min(bar_width, int(round((ctx_pct / 100.0) * bar_width)))
        hatch_active = "█" * filled
        hatch_free = "░" * (bar_width - filled)
        bar = f"{hatch_active}{hatch_free}"

        ctx_color = "green" if ctx_pct < 50 else "yellow" if ctx_pct < 75 else "red"

        memory_block = (
            f"[bold cyan]🧠 CONTEXT MEMORY USAGE[/bold cyan]\n"
            f"[bold {ctx_color}]{tokens_est:,} / {ctx_max:,} TOKENS[/bold {ctx_color}] [bold yellow]({ctx_pct}%)[/bold yellow]\n"
            f"[{bar}]"
        )

        return f"{speedometer}\n{memory_block}"

    def _is_goal_mode(self) -> bool:
        mode = getattr(self.engine, "execution_mode", "chat")
        if hasattr(mode, "value"):
            mode = mode.value
        return str(mode).lower() == "goal"

    def _build_plan_overview_text(self) -> str:
        import time as _t
        now = _t.time()
        if now - getattr(self, "_plan_overview_ts", 0.0) < 2.0 and hasattr(self, "_plan_overview_cache"):
            return self._plan_overview_cache
        project_root = getattr(self.engine, "project_root", os.getcwd())
        res = build_plan_overview_text(project_root, self._is_goal_mode(), mode=self._get_current_mode_val())
        self._plan_overview_ts = now
        self._plan_overview_cache = res
        return res

    def _build_task_checklist_text(self) -> str:
        import time as _t
        now = _t.time()
        if now - getattr(self, "_task_checklist_ts", 0.0) < 2.0 and hasattr(self, "_task_checklist_cache"):
            return self._task_checklist_cache
        project_root = getattr(self.engine, "project_root", os.getcwd())
        res = build_task_checklist_text(project_root, self._is_goal_mode())
        self._task_checklist_ts = now
        self._task_checklist_cache = res
        return res

    def _build_plan_text(self) -> str:
        import time as _t
        now = _t.time()
        if now - getattr(self, "_plan_text_ts", 0.0) < 2.0 and hasattr(self, "_plan_text_cache"):
            return self._plan_text_cache
        project_root = getattr(self.engine, "project_root", os.getcwd())
        res = build_plan_text(project_root, self._is_goal_mode(), mode=self._get_current_mode_val())
        self._plan_text_ts = now
        self._plan_text_cache = res
        return res

    def _build_skills_text(self, reload: bool = False) -> str:
        import time as _t
        now = _t.time()
        if not reload and now - getattr(self, "_skills_text_ts", 0.0) < 2.0 and hasattr(self, "_skills_text_cache"):
            return self._skills_text_cache
        project_root = getattr(self.engine, "project_root", os.getcwd())
        res = build_skills_overview_text(project_root, reload=reload)
        self._skills_text_ts = now
        self._skills_text_cache = res
        return res

    def _build_context_progress_text(self) -> str:
        tokens_est = self._live_context_tokens()

        ctx_max = CTX_SIZE
        pct = min(100, int((tokens_est / ctx_max) * 100)) if ctx_max > 0 else 0
        bar_width = 24
        filled = min(bar_width, int(round((pct / 100.0) * bar_width)))
        bar = "█" * filled + "░" * (bar_width - filled)

        state_str = getattr(self, "_agent_state", "READY")

        tps_val = getattr(self, "_live_tps", 0.0)
        tps_str = (
            f"{tps_val:.1f} t/s"
            if tps_val > 0
            else ("0.0 t/s" if not self._is_running else "t/s...")
        )

        return (
            f"[bold cyan]> SYSTEM:[/] [bold green]{state_str}[/bold green]  │  "
            f"[bold cyan]LIFECYCLE:[/] [bold green]⚡ ADAPTIVE[/bold green]  │  "
            f"[bold cyan]CONTEXT:[/] [{bar}] [bold yellow]{pct}%[/bold yellow] [dim]({tokens_est:,}/{ctx_max:,})[/dim]  │  "
            f"[bold cyan]SPEED:[/] [bold green]⚡ {tps_str}[/bold green]"
        )

    def _build_meta_text(self) -> str:
        mem = getattr(self.engine, "_memory", None)
        tokens_est = self._live_context_tokens()

        server_status_str = getattr(self, "engine_server_status", "● Active")
        if (
            "Offline" in server_status_str
            or "Error" in server_status_str
            or "404" in server_status_str
        ):
            server_status_str = f"[bold red]{escape(server_status_str)}[/bold red]"
        else:
            server_status_str = f"[bold green]{escape(server_status_str)}[/bold green]"

        mem_line = ""
        if mem and hasattr(mem, "messages"):
            mem_line = f"[bold]Messages:[/] {len(mem.messages)}\n"

        return (
            f"[bold]Engine Server:[/] {server_status_str}\n"
            f"[bold]Provider:[/] [cyan]{escape(self.provider_name)}[/]\n"
            f"[bold]Model:[/] [magenta]{escape(self.model_name)}[/]\n"
            f"[bold]Context:[/] {CTX_SIZE:,} tokens\n"
            f"[bold]LLM Calls:[/] {self.engine._total_llm_calls}\n"
            f"[bold]Live Tokens:[/] {tokens_est:,} / {CTX_SIZE:,}\n"
            f"[bold]Depth Limit:[/] {self.engine.max_depth}\n"
            f"{mem_line}"
        ).strip()

    def update_sidebar_meta(self) -> None:
        try:
            shp = self.query_one("#system-health-panel")
            shp.update(self._build_system_health_text())
        except Exception:
            pass
        try:
            cmb = self.query_one("#context-meter-bar")
            cmb.update(self._build_context_progress_text())
        except Exception:
            pass
        try:
            po = self.query_one("#plan-overview-panel", Static)
            po.update(self._build_plan_overview_text())
        except Exception:
            pass
        try:
            pt = self.query_one("#task-checklist-panel", Static)
            pt.update(self._build_task_checklist_text())
        except Exception:
            pass
        try:
            pp = self.query_one("#plan-panel", Static)
            pp.update(self._build_plan_text())
        except Exception:
            pass
        try:
            sp = self.query_one("#skills-list-panel", Static)
            sp.update(self._build_skills_text())
        except Exception:
            pass
        try:
            mb = self.query_one("#input-model-badge", Button)
            mb.label = f"🤖 {self.model_name} ▾"
        except Exception:
            pass
        try:
            tps_val = getattr(self, "_live_tps", 0.0)
            lat_val = getattr(self, "_live_latency_ms", 0.0)
            tps_str = (
                f"{tps_val:.1f} t/s"
                if tps_val > 0
                else ("idle" if not self._is_running else "calculating...")
            )
            lat_str = (
                f"{int(lat_val)}ms"
                if lat_val > 0
                else ("0ms" if not self._is_running else "--")
            )

            self.query_one("#hud-epoch").update(f"TPS: {tps_str}")
            self.query_one("#hud-reverts").update(f"LATENCY: {lat_str}")
        except Exception:
            pass
        try:
            label = self._get_active_mode_label()
            mtb = self.query_one("#mode-toggle-btn", Button)
            mtb.label = f"MODE: {label}"
            mtb.remove_class("mode-badge-chat")
            mtb.remove_class("mode-badge-goal")
            mtb.remove_class("mode-badge-plan")
            mtb.remove_class("mode-badge-unified")
            mtb.remove_class("mode-badge-code")
            if "CODE" in label:
                mtb.add_class("mode-badge-code")
            elif "GOAL" in label:
                mtb.add_class("mode-badge-goal")
            elif "PLAN" in label:
                mtb.add_class("mode-badge-plan")
            elif "UNIFIED" in label:
                mtb.add_class("mode-badge-unified")
            else:
                mtb.add_class("mode-badge-chat")

        except Exception:
            pass

        try:
            msd = self.query_one("#mode-select-dropdown", Select)
            curr_val = self._get_current_mode_val()
            if msd.value != curr_val:
                msd.value = curr_val
        except Exception:
            pass

    def action_show_help(self) -> None:
        self.push_screen(ShortcutsHelpModal())

    @on(Button.Pressed, "#help-btn")
    def on_help_pressed(self) -> None:
        self.action_show_help()

    @on(Button.Pressed, "#upload-skill-btn")
    def on_upload_skill_pressed(self) -> None:
        project_root = getattr(self.engine, "project_root", os.getcwd())

        def on_modal_result(result: Optional[dict]) -> None:
            if not result or not result.get("source_path"):
                return
            src = result["source_path"]
            custom = result.get("custom_name")
            ok, msg = import_skill_file(src, custom_name=custom, workspace_root=project_root)
            try:
                status_widget = self.query_one("#skills-status-msg", Static)
                if ok:
                    status_widget.update(f"[bold green]✓ {escape(msg)}[/bold green]")
                    self.notify(msg, title="Skill Imported", severity="information")
                else:
                    status_widget.update(f"[bold red]✗ {escape(msg)}[/bold red]")
                    self.notify(msg, title="Import Failed", severity="error")
            except Exception:
                pass

            try:
                sp = self.query_one("#skills-list-panel", Static)
                sp.update(self._build_skills_text(reload=True))
            except Exception:
                pass

        self.push_screen(SkillUploadModal(workspace_root=project_root), on_modal_result)

    @on(Button.Pressed, "#refresh-skills-btn")
    def on_refresh_skills_pressed(self) -> None:
        try:
            sp = self.query_one("#skills-list-panel", Static)
            sp.update(self._build_skills_text(reload=True))
            status_widget = self.query_one("#skills-status-msg", Static)
            status_widget.update("[bold cyan]✓ Refreshed skill registry[/bold cyan]")
            self.notify("Skill list refreshed", title="Skills", severity="information")
        except Exception:
            pass

    @on(Button.Pressed, "#input-model-badge")
    def on_model_badge_clicked(self) -> None:
        self.action_select_model()

    @on(Button.Pressed, "#wipe-context-btn, #agent-wipe-btn")
    def on_wipe_context_btn_clicked(self) -> None:
        self.action_wipe_session()

    @on(Button.Pressed, "#compact-btn, #health-compact-btn, #agent-compact-btn")
    def on_compact_btn_clicked(self) -> None:
        self.action_compact_context()

    @on(Button.Pressed, "#mode-toggle-btn, #mode-select-btn")
    def on_mode_toggle_pressed(self) -> None:
        self.action_select_mode()

    @on(Button.Pressed, "#toggle-breakdown-btn")
    def on_toggle_breakdown_btn(self, event: Button.Pressed) -> None:
        event.stop()
        self._show_ctx_breakdown = not getattr(self, "_show_ctx_breakdown", False)
        btn = self.query_one("#toggle-breakdown-btn", Button)
        try:
            bd_widget = self.query_one("#agent-tab-ctx-breakdown", Static)
            if self._show_ctx_breakdown:
                btn.label = "▾ Breakdown"
                bd_widget.display = True
                breakdown_text = self._context_section_breakdown()
                bd_widget.update(breakdown_text)
            else:
                btn.label = "▸ Breakdown"
                bd_widget.display = False
                bd_widget.update("")
        except Exception:
            pass

    @on(Button.Pressed, ".nav-dock-btn")
    def on_dock_btn_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        for b in self.query(".nav-dock-btn"):
            b.remove_class("nav-dock-btn-active")
        event.button.add_class("nav-dock-btn-active")
        if btn_id == "dock-btn-shell":
            try:
                self.set_focus(self.query_one("#user-input"))
            except Exception:
                pass
        elif btn_id == "dock-btn-context":
            self.action_toggle_sidebar()
        elif btn_id == "dock-btn-goal":
            self.action_select_mode()
        elif btn_id == "dock-btn-sys":
            self.action_toggle_status_modal()

    def update_status_bar(self) -> None:
        """Consolidated Phase-4 status bar (state · model · context gauge · tps · tokens · errors · git)."""
        try:
            bar = self.query_one("#status-bar", StatusBar)
        except Exception:
            return
        tokens, ctx_max, pct = self._context_usage()
        try:
            server_online = is_port_in_use(self.engine_port)
        except Exception:
            server_online = False
        errors = sum(
            1
            for ev in getattr(self, "_agent_events", [])
            if ev.get("state") == "TOOL_DENIED"
            or "ERROR" in str(ev.get("state", "")).upper()
        )
        task_prog = ""
        try:
            from core.tools.task_helpers import get_workspace_task_status_summary

            tsummary = get_workspace_task_status_summary(self.project_root)
            tot = tsummary.get("total_count", 0)
            comp = tsummary.get("completed_count", 0)
            cur = tsummary.get("current_task")
            if tot > 0:
                c_desc = (
                    cur["description"][:25] + "..."
                    if cur and len(cur["description"]) > 25
                    else (cur["description"] if cur else "")
                )
                task_prog = f"{comp}/{tot} {c_desc}".strip()
        except Exception:  # noqa: BLE001, S110
            pass

        bar.update_status(
            state=getattr(self, "_agent_state", "IDLE"),
            model=self.model_name,
            pct=pct,
            tokens=tokens,
            ctx_max=ctx_max,
            tps=getattr(self, "_live_tps", 0.0),
            errors=errors,
            branch=self._git_branch(),
            port=self.engine_port,
            server_online=server_online,
            is_running=getattr(self, "_is_running", False),
            task_progress=task_prog,
        )

        # Keep Agent tab context bar in sync
        try:
            self.update_agent_tab_context()
        except Exception:
            pass

    def _live_context_tokens(self) -> int:
        """Committed memory tokens plus in-flight streamed tokens for the context gauge.

        Memory only receives a message once the full LLM response is parsed, so the
        streamed tokens are added on top here to make the gauge climb during generation.
        """
        mem = getattr(self.engine, "_memory", None)
        if mem and hasattr(mem, "total_tokens") and isinstance(mem.total_tokens, (int, float)) and mem.total_tokens > 0:
            base = int(mem.total_tokens)
        else:
            calls = getattr(self.engine, "_total_llm_calls", 0)
            base = int(calls) * 450 if calls else 0
        return base + getattr(self, "_stream_token_count", 0)

    def _context_section_breakdown(self) -> str:
        """Estimate per-section token usage and return a Rich markup string.

        Sections estimated:
          System Prompt  — base phase prompt + tool syntax suffix
          Scratchpad/L0  — L0 working memory (task matrix, errors, decisions)
          Flashlight     — AST beam (0 if disabled / no recent query)
          Chat History   — all user+assistant messages in active context window
          Pins           — pinned file slices
          Streaming      — in-flight tokens being generated right now

        Returns compact multi-line Rich markup suitable for a narrow sidebar.
        """
        ctx_max = CTX_SIZE
        if ctx_max <= 0:
            return "[dim]N/A[/dim]"

        import time as _t
        now = _t.monotonic()
        cached_static = getattr(self, "_ctx_breakdown_cache", None)
        cached_ts = getattr(self, "_ctx_breakdown_cache_ts", 0.0)
        stream_tok = getattr(self, "_stream_token_count", 0)
        SPARK_WIDTH = 8

        if cached_static is not None and (now - cached_ts) < 2.0:
            if stream_tok > 0:
                pct = min(100.0, (stream_tok / ctx_max) * 100)
                filled = min(SPARK_WIDTH, round((pct / 100.0) * SPARK_WIDTH))
                spark = "▪" * filled + "·" * (SPARK_WIDTH - filled)
                stream_row = (
                    f"[dim]{'Streaming':<10}[/dim] "
                    f"[yellow]{spark}[/yellow] "
                    f"[bold]{stream_tok:>5,}[/bold] "
                    f"[dim]{pct:>4.1f}%[/dim]"
                )
                return cached_static + "\n" + stream_row
            return cached_static

        # ── Estimate each section (O(1) in memory) ───────────────────────────
        mem = getattr(self.engine, "_memory", None)

        # 1. System prompt: rough estimate based on phase
        phase = getattr(self.engine, "_current_phase", "code")
        _SYSTEM_SIZES = {"chat": 900, "plan": 1100, "code": 1050, "goal": 1000, "troubleshoot": 950}
        system_tok = _SYSTEM_SIZES.get(phase, 1000) + 300

        # 2. Scratchpad / L0 — fast memory estimate
        scratchpad_tok = getattr(mem, "_estimate_l0_tokens", lambda: 150)() if mem else 150
        if scratchpad_tok == 0:
            scratchpad_tok = 50

        # 3. Flashlight beam — estimate from last beam size
        beam_tok = getattr(self, "_last_beam_tokens", 0)
        if beam_tok == 0:
            beam_tok = 600 if ctx_max >= 8000 else 250

        # 4. Chat history — committed message tokens in memory
        chat_tok = getattr(mem, "_cached_msg_tokens", 0) if mem else 0

        # 5. Pinned files
        pinned_tok = getattr(mem, "_cached_pinned_tokens", 0) if mem else 0

        def _row(label: str, tok: int, color: str) -> str:
            pct = min(100.0, (tok / ctx_max) * 100)
            filled = min(SPARK_WIDTH, round((pct / 100.0) * SPARK_WIDTH))
            spark = "▪" * filled + "·" * (SPARK_WIDTH - filled)
            return (
                f"[dim]{label:<10}[/dim] "
                f"[{color}]{spark}[/{color}] "
                f"[bold]{tok:>5,}[/bold] "
                f"[dim]{pct:>4.1f}%[/dim]"
            )

        rows = [
            _row("System",     system_tok,     "blue"),
            _row("Scratchpad", scratchpad_tok, "cyan"),
            _row("Beam",       beam_tok,       "bright_cyan"),
            _row("Chat",       chat_tok,       "green"),
        ]
        if pinned_tok > 0:
            rows.append(_row("Pins", pinned_tok, "magenta"))

        static_rows = "\n".join(rows)
        self._ctx_breakdown_cache = static_rows
        self._ctx_breakdown_cache_ts = now

        if stream_tok > 0:
            pct = min(100.0, (stream_tok / ctx_max) * 100)
            filled = min(SPARK_WIDTH, round((pct / 100.0) * SPARK_WIDTH))
            spark = "▪" * filled + "·" * (SPARK_WIDTH - filled)
            stream_row = (
                f"[dim]{'Streaming':<10}[/dim] "
                f"[yellow]{spark}[/yellow] "
                f"[bold]{stream_tok:>5,}[/bold] "
                f"[dim]{pct:>4.1f}%[/dim]"
            )
            return static_rows + "\n" + stream_row

        return static_rows

    def _context_usage(self) -> tuple[int, int, float]:
        tokens_est = self._live_context_tokens()
        ctx_max = CTX_SIZE
        pct = min(100.0, (tokens_est / ctx_max) * 100) if ctx_max > 0 else 0.0
        return int(tokens_est), ctx_max, pct

    def _git_branch(self) -> str:
        try:
            head_file = os.path.join(self.engine.project_root, ".git", "HEAD")
            if os.path.exists(head_file):
                with open(head_file, "r", encoding="utf-8") as f:
                    ref = f.read().strip()
                if ref.startswith("ref: refs/heads/"):
                    return ref[16:]
                if len(ref) >= 7:
                    return ref[:7]
        except Exception:
            pass

        import time as _t
        now = _t.time()
        if now - getattr(self, "_git_branch_ts", 0.0) < 5.0 and hasattr(self, "_git_branch_cache"):
            return self._git_branch_cache
        try:
            proc = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.engine.project_root,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            name = proc.stdout.strip()
            res = name if proc.returncode == 0 and name else ""
        except Exception:
            res = ""
        self._git_branch_ts = now
        self._git_branch_cache = res
        return res

    def _refresh_git_tree(self) -> None:
        """Repoint the file tree at the engine root and refresh git status."""
        try:
            tree = self.query_one("#file-tree", GitFileTree)
            tree.path = self.engine.project_root
            tree.refresh_git()
            tree.reload()
        except Exception:
            pass
