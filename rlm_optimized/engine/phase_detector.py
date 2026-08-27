"""Phase detection, dynamic signal matching, and inference parameter adaptation."""

from __future__ import annotations

from typing import Optional
from core.prompts.system import get_phase_system_prompt
from core.api.base import InferenceParams

try:
    from core.memory.models import FIXED_EXECUTION_MODES
except ImportError:
    FIXED_EXECUTION_MODES = frozenset({"plan", "code", "chat"})


class PhaseDetectorMixin:
    def _get_active_execution_mode(self) -> str:
        """Resolve and normalize active execution mode from self or attached memory."""
        mode_val = getattr(self, "execution_mode", None)
        if hasattr(mode_val, "value"):
            mode_val = mode_val.value
        mode_str = str(mode_val or "").lower().strip()

        mem = getattr(self, "_memory", None) or getattr(self, "memory", None)
        if mem and hasattr(mem, "state") and hasattr(mem.state, "execution_mode"):
            mem_mode = mem.state.execution_mode
            if hasattr(mem_mode, "value"):
                mem_mode = mem_mode.value
            mem_mode_str = str(mem_mode or "").lower().strip()
            if mem_mode_str and (not mode_str or mode_str == "unified"):
                return mem_mode_str

        return mode_str or "unified"


    # Phase detection signals (ported from CLI)
    _PLAN_SIGNALS = (
        "<plan>",
        "plan",
        "planning",
        "brainstorm",
        "brainstorming",
        "implementation plan",
        "steps to implement",
        "generate plan",
        "make a plan",
        "create a plan",
        "plan mode",
        "let me plan",
        "step by step",
        "here is my plan",
        "i will:",
        "steps:",
        "roadmap",
        "break down tasks",
        "break down the tasks",
        "decompose tasks",
    )


    _CODE_SIGNALS = (
        "implement",
        "write",
        "create",
        "build",
        "add",
        "modify",
        "change",
        "update",
        "edit",
        "refactor",
        "fix",
        "code",
        "function",
        "class",
        "method",
        "api",
        "endpoint",
        "handler",
        "component",
        "module",
        "script",
        "test",
        "mock",
        "stub",
        "prototype",
        "integrate",
        "connect",
        "wire",
        "hook",
        "register",
        "define",
        "declare",
        "instantiate",
        "initialize",
        "configure",
        "setup",
        "install",
        "deploy",
        "release",
        "publish",
        "ship",
        "run",
        "execute",
        "call",
        "invoke",
        "trigger",
        "emit",
        "dispatch",
        "send",
        "receive",
        "fetch",
        "query",
        "read",
        "write",
        "save",
        "load",
        "parse",
        "serialize",
        "deserialize",
        "transform",
        "map",
        "filter",
        "reduce",
        "aggregate",
        "validate",
        "sanitize",
        "normalize",
        "encode",
        "decode",
        "encrypt",
        "decrypt",
        "hash",
        "sign",
        "verify",
        "authenticate",
        "authorize",
        "login",
        "logout",
        "session",
        "token",
        "cookie",
        "header",
        "body",
        "payload",
        "request",
        "response",
        "status",
        "error",
        "exception",
        "throw",
        "catch",
        "try",
        "finally",
        "raise",
        "assert",
        "expect",
        "should",
        "must",
        "will",
        "shall",
        "return",
        "yield",
        "await",
        "async",
        "promise",
        "future",
        "callback",
        "handler",
        "listener",
        "observer",
        "subscriber",
        "publisher",
        "event",
        "signal",
        "emit",
        "broadcast",
        "notify",
        "dispatch",
        "fire",
        "trigger",
    )

    _TROUBLESHOOT_SIGNALS = (
        "error",
        "fail",
        "bug",
        "issue",
        "problem",
        "crash",
        "exception",
        "traceback",
        "stack",
        "segfault",
        "outofmemory",
        "timeout",
        "hang",
        "deadlock",
        "race",
        "leak",
        "corrupt",
        "invalid",
        "unexpected",
        "wrong",
        "broken",
        "stuck",
        "freeze",
        "slow",
        "performance",
        "latency",
        "bottleneck",
        "optimize",
        "memory",
        "cpu",
        "disk",
        "network",
        "connection",
        "refused",
        "reset",
        "abort",
        "kill",
        "oom",
        "nullpointer",
        "undefined",
        "index error",
        "indexerror",
        "out of bounds",
        "overflow",
        "underflow",
        "division by zero",
        "nan",
        "inf",
        "assertion",
        "panic",
        "abort",
        "segmentation",
        "fault",
        "access",
        "violation",
        "protection",
        "permission",
        "denied",
        "forbidden",
        "unauthorized",
        "authentication",
        "certificate",
        "ssl",
        "tls",
        "handshake",
        "verify",
        "trust",
        "chain",
        "expired",
        "revoked",
        "self-signed",
        "hostname",
        "mismatch",
        "cipher",
        "protocol",
        "version",
        "alpn",
        "sni",
        "ocsp",
        "crl",
        "dp",
        "pipe",
        "channel",
        "socket",
        "port",
        "host",
        "address",
        "interface",
        "bind",
        "listen",
        "accept",
        "connect",
        "dial",
        "resolve",
        "lookup",
        "dns",
        "nameserver",
        "record",
        "zone",
        "ttl",
        "cache",
        "expire",
        "stale",
        "fresh",
        "hit",
        "miss",
        "evict",
        "purge",
        "invalidate",
        "refresh",
        "warm",
        "cold",
        "preload",
        "prefetch",
        "bundle",
        "chunk",
        "split",
        "lazy",
        "dynamic",
        "import",
        "module",
        "export",
        "default",
        "named",
        "namespace",
        "scope",
        "closure",
        "hoisting",
        "temporal",
        "dead",
        "zone",
        "tdz",
        "const",
        "let",
        "var",
        "function",
        "arrow",
        "class",
        "extends",
        "super",
        "constructor",
        "prototype",
        "instanceof",
        "typeof",
        "delete",
        "new",
        "this",
        "arguments",
        "rest",
        "spread",
        "destructuring",
        "template",
        "literal",
        "tagged",
        "raw",
        "escape",
        "unicode",
        "regexp",
        "regex",
        "pattern",
        "match",
        "replace",
        "split",
        "search",
        "exec",
        "test",
        "flags",
        "global",
        "ignore",
        "case",
        "multiline",
        "sticky",
        "unicode",
        "dotall",
        "lookahead",
        "lookbehind",
        "capture",
        "group",
        "backreference",
        "quantifier",
        "greedy",
        "lazy",
        "possessive",
        "alternation",
        "anchor",
        "boundary",
        "word",
        "digit",
        "whitespace",
        "character",
        "class",
        "range",
        "negation",
        "escape",
        "literal",
        "meta",
        "special",
        "why is",
        "why does",
        "what went wrong",
        "debug",
        "diagnose",
        "trace",
        "log",
        "monitor",
        "alert",
        "metric",
        "dashboard",
        "grafana",
        "prometheus",
        "datadog",
        "newrelic",
        "splunk",
        "elk",
        "loki",
        "tempo",
        "jaeger",
        "zipkin",
        "opentelemetry",
        "otel",
        "trace",
        "span",
        "context",
        "baggage",
        "propagation",
        "w3c",
        "b3",
        "jaeger",
        "zipkin",
        "otlp",
        "grpc",
        "http",
        "protobuf",
        "json",
        "thrift",
        "avro",
        "parquet",
        "orc",
        "csv",
        "tsv",
        "psv",
        "jsonl",
        "ndjson",
        "logfmt",
        "key",
        "value",
        "structured",
        "unstructured",
        "semi",
        "schema",
        "field",
        "type",
        "format",
        "encoding",
        "compression",
        "encryption",
        "signing",
        "verification",
        "authentication",
        "authorization",
        "error",
        "fail",
        "failing",
        "failure",
        "bug",
        "issue",
        "problem",
        "crash",
        "exception",
        "traceback",
        "stacktrace",
        "fix",
        "broken",
        "panic",
    )

    def _detect_phase(self, user_input: str, last_response: str = "") -> str:
        """
        Infer the current agent phase from user input and the last model response.
        Returns one of: "goal" | "plan" | "code" | "troubleshoot" | "chat".
        """
        current_mode = self._get_active_execution_mode()
        if current_mode in FIXED_EXECUTION_MODES:
            return current_mode
        if current_mode == "goal":
            return "goal"

        inp_lower = user_input.lower()
        # Check plan signals against user input only to prevent generic model responses from flipping phase
        if any(s in inp_lower for s in self._PLAN_SIGNALS):
            return "plan"
        if any(s in inp_lower for s in self._TROUBLESHOOT_SIGNALS):
            return "troubleshoot"

        if any(
            s in inp_lower
            for s in (
                "resume",
                "continue",
                "proceed",
                "carry on",
                "pick up",
                "finish task",
            )
        ):
            return "code"
        if any(
            w in inp_lower
            for w in (
                "write",
                "create file",
                "add file",
                "save file",
                "make file",
                "edit file",
                "build file",
                ".txt",
                ".py",
                ".js",
                ".ts",
                ".go",
                ".rs",
                ".java",
                ".json",
                ".html",
                ".css",
                ".md",
            )
        ):
            return "code"
        if any(s in inp_lower for s in self._CODE_SIGNALS):
            return "code"
        return "chat"


    def lock_phase(self, phase: str) -> bool:
        """Manually lock or unlock the agent phase ('code', 'plan', 'goal', 'troubleshoot', 'debug', 'chat', or 'auto')."""
        phase_key = (phase or "").lower().strip()
        if phase_key in ("auto", "unlock", "reset"):
            self._params_locked = False
            return True
        if phase_key == "debug":
            phase_key = "troubleshoot"
        if phase_key in ("code", "plan", "goal", "troubleshoot", "chat"):
            self._current_phase = phase_key
            self._params_locked = True
            model_name = getattr(self.client, "model", None) or getattr(
                self.client, "model_name", None
            )
            calibrated = InferenceParams.for_model_and_phase(model_name, phase_key)
            if hasattr(self.client, "temperature"):
                self.client.temperature = calibrated.temperature
            if hasattr(self.client, "top_k"):
                self.client.top_k = calibrated.top_k
            if hasattr(self.client, "top_p"):
                self.client.top_p = calibrated.top_p
            if hasattr(self.client, "min_p"):
                self.client.min_p = calibrated.min_p
            if hasattr(self.client, "repeat_penalty"):
                self.client.repeat_penalty = calibrated.repeat_penalty
            if hasattr(self.client, "repetition_penalty"):
                self.client.repetition_penalty = getattr(
                    calibrated, "repetition_penalty", calibrated.repeat_penalty
                )
            if hasattr(self.client, "presence_penalty"):
                self.client.presence_penalty = calibrated.presence_penalty
            if hasattr(self.client, "frequency_penalty"):
                self.client.frequency_penalty = calibrated.frequency_penalty
            mem = getattr(self, "_memory", None) or getattr(self, "memory", None)
            if mem and hasattr(mem, "update_system_prompt"):
                mem.update_system_prompt(get_phase_system_prompt(phase_key))
            return True
        return False

    def get_locked_phase(self) -> str:
        """Return the current locked phase or 'auto' if dynamic phase detection is active."""
        if getattr(self, "_params_locked", False):
            return getattr(self, "_current_phase", "code")
        return "auto"

    def _update_params(self, user_input: str, last_response: str = "") -> None:
        """Auto-switch inference parameters based on detected phase. No-op in fixed modes."""
        if getattr(self, "_params_locked", False):
            return
        current_mode = self._get_active_execution_mode()
        if current_mode in FIXED_EXECUTION_MODES:
            return

        phase = self._detect_phase(user_input, last_response)
        if phase == getattr(self, "_current_phase", "code"):
            return

        self._current_phase = phase
        model_name = getattr(self.client, "model", None) or getattr(
            self.client, "model_name", None
        )
        calibrated = InferenceParams.for_model_and_phase(model_name, phase)
        if hasattr(self.client, "temperature"):
            self.client.temperature = calibrated.temperature
        if hasattr(self.client, "top_k"):
            self.client.top_k = calibrated.top_k
        if hasattr(self.client, "top_p"):
            self.client.top_p = calibrated.top_p
        if hasattr(self.client, "min_p"):
            self.client.min_p = calibrated.min_p
        if hasattr(self.client, "repeat_penalty"):
            self.client.repeat_penalty = calibrated.repeat_penalty
        if hasattr(self.client, "repetition_penalty"):
            self.client.repetition_penalty = getattr(
                calibrated, "repetition_penalty", calibrated.repeat_penalty
            )
        if hasattr(self.client, "presence_penalty"):
            self.client.presence_penalty = calibrated.presence_penalty
        if hasattr(self.client, "frequency_penalty"):
            self.client.frequency_penalty = calibrated.frequency_penalty
        mem = getattr(self, "_memory", None) or getattr(self, "memory", None)
        if mem and hasattr(mem, "update_system_prompt"):
            mem.update_system_prompt(get_phase_system_prompt(phase))


