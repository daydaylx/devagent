from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Input, Button, TextLog, Select, Label
from textual.containers import Horizontal, Vertical, Container

from ..logging import get_logger
from ..utils import ensure_git_root
from ..sandbox import Sandbox
from ..config import Config
from ..indexer import build_index
from ..openrouter import ORClient
from ..policies import CostGuard
from ..patcher import apply_patch, PatchValidationError
from ..gitops import add_all, commit as git_commit
from ..tester import run_tests

log = get_logger(__name__)

class DevAgentApp(App):
    CSS = """
    Screen { layout: vertical; }
    #main { height: 1fr; }
    .panel { border: solid $primary 20%; padding: 1; }
    .controls { width: 42; min-width: 40; }
    .grow { height: 1fr; }
    .spacer { height: 1; }
    """

    BINDINGS = [
        Binding("p", "plan", "Plan"),
        Binding("a", "apply", "Apply"),
        Binding("t", "test", "Test"),
        Binding("c", "commit", "Commit"),
        Binding("m", "reload_models", "Reload Models"),
        Binding("q", "quit", "Quit"),
    ]

    spent_usd: reactive[float] = reactive(0.0)
    calls: reactive[int] = reactive(0)

    def __init__(self):
        super().__init__()
        self.root_path: Optional[Path] = None
        self.sb: Optional[Sandbox] = None
        self.cfg: Optional[Config] = None
        self.client: Optional[ORClient] = None
        self.guard: Optional[CostGuard] = None
        self.diff_path: Optional[Path] = None

        self.model_select: Select[str] | None = None
        self.goal_input: Input | None = None
        self.test_input: Input | None = None
        self.commit_input: Input | None = None
        self.diff_log: TextLog | None = None
        self.out_log: TextLog | None = None
        self.session_label: Label | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main"):
            with Horizontal():
                with Vertical(classes="controls panel"):
                    yield Label("Model", id="lbl_model")
                    self.model_select = Select(options=[("loading…", "")])
                    yield self.model_select

                    yield Label("Goal (Plan)")
                    self.goal_input = Input(placeholder="e.g. Fix TS errors in project")
                    yield self.goal_input

                    yield Label("Test Command")
                    self.test_input = Input(placeholder="npm run build | pytest -q", value="")
                    yield self.test_input

                    yield Label("Commit Message")
                    self.commit_input = Input(placeholder="Apply AI patch")
                    yield self.commit_input

                    yield Static(classes="spacer")
                    with Horizontal():
                        yield Button("Plan [P]", id="btn_plan", variant="primary")
                        yield Button("Apply [A]", id="btn_apply")
                    with Horizontal():
                        yield Button("Test [T]", id="btn_test")
                        yield Button("Commit [C]", id="btn_commit")
                    with Horizontal():
                        yield Button("Reload Models [M]", id="btn_models")

                    yield Static(classes="spacer")
                    self.session_label = Label("Session: $0.0000 • 0 calls")
                    yield self.session_label

                with Vertical(classes="panel grow"):
                    yield Label("Diff (.devagent/last_patch.diff)")
                    self.diff_log = TextLog(highlight=False, markup=False, wrap=False)
                    yield self.diff_log
                with Vertical(classes="panel grow"):
                    yield Label("Output Log")
                    self.out_log = TextLog(highlight=True, markup=True, wrap=True)
                    yield self.out_log
        yield Footer()

    async def on_mount(self) -> None:
        try:
            self.root_path = ensure_git_root(Path.cwd())
        except SystemExit as e:
            self.exit(message=str(e))
            return
        self.sb = Sandbox(self.root_path)
        self.sb.ensure()
        self.cfg = Config.load(self.sb.config_file)
        self.client = ORClient(model=self.cfg.model)
        self.guard = CostGuard(self.sb, self.cfg)
        self.diff_path = self.sb.last_patch
        if self.test_input and self.cfg.test_cmd:
            self.test_input.value = self.cfg.test_cmd
        await self.action_reload_models()
        await self._load_existing_diff()
        self._refresh_session_label()

    async def _load_existing_diff(self) -> None:
        if self.diff_log and self.diff_path and self.diff_path.exists():
            self.diff_log.clear()
            self.diff_log.write(self.diff_path.read_text(encoding="utf-8"))

    def _refresh_session_label(self) -> None:
        if not self.sb or not self.session_label:
            return
        sess = self.sb.load_session()
        self.spent_usd = float(sess.get("spent_usd", 0.0))
        self.calls = int(sess.get("calls", 0))
        self.session_label.update(f"Session: ${self.spent_usd:.4f} • {self.calls} calls")

    async def action_reload_models(self) -> None:
        if not self.client or not self.model_select:
            return
        self.model_select.clear_options()
        self.model_select.add_option(("loading…", ""))
        def _fetch():
            return self.client.list_models()
        try:
            data = await asyncio.to_thread(_fetch)
            opts = []
            for m in data:
                mid = m.get("id", "?")
                name = m.get("name", mid)
                opts.append((f"{name}", mid))
            opts.sort(key=lambda x: x[0].lower())
            self.model_select.clear_options()
            for label, mid in opts[:300]:
                self.model_select.add_option((label, mid))
            current = self.cfg.model if self.cfg else None
            if current:
                self.model_select.value = current
        except Exception as e:
            self.log_error(f"Model list failed: {e}")

    def log_info(self, msg: str) -> None:
        if self.out_log:
            self.out_log.write(f"[b]{msg}[/b]")

    def log_error(self, msg: str) -> None:
        if self.out_log:
            self.out_log.write(f"[red]{msg}[/red]")

    async def action_plan(self) -> None:
        if not (self.root_path and self.sb and self.cfg and self.client and self.guard):
            return
        goal = (self.goal_input.value.strip() if self.goal_input else "").strip()
        if not goal:
            self.log_error("Goal ist leer")
            return
        if self.sb.index_file.exists():
            repo_summary = self.sb.index_file.read_text(encoding="utf-8")
        else:
            self.log_info("Indexing repository…")
            summary = await asyncio.to_thread(build_index, self.root_path)
            repo_summary = json.dumps(summary, indent=2)
            self.sb.index_file.write_text(repo_summary, encoding="utf-8")
        if self.model_select and self.model_select.value:
            self.cfg.model = self.model_select.value
            self.sb.config_file.write_text(self.cfg.to_toml(), encoding="utf-8")
        self.log_info(f"Planning with model: {self.cfg.model}")

        def _make():
            from ..tasks import make_diff_for_goal
            return make_diff_for_goal(self.root_path, goal, repo_summary, self.cfg.model, self.client, self.guard)
        try:
            diff_text: str = await asyncio.to_thread(_make)
        except Exception as e:
            self.log_error(f"Plan failed: {e}")
            return
        self.sb.last_plan.write_text(f"GOAL: {goal}\n\n", encoding="utf-8")
        self.sb.last_patch.write_text(diff_text, encoding="utf-8")
        await self._load_existing_diff()
        self._refresh_session_label()
        self.log_info("Plan erstellt. Diff gespeichert.")

    async def action_apply(self) -> None:
        if not (self.root_path and self.sb and self.cfg):
            return
        if not self.sb.last_patch.exists():
            self.log_error("Kein Diff vorhanden (.devagent/last_patch.diff)")
            return
        diff_text = self.sb.last_patch.read_text(encoding="utf-8")
        self.log_info("Validiere & wende Patch an…")
        try:
            changed = await asyncio.to_thread(apply_patch, self.root_path, diff_text, False)
        except PatchValidationError as e:
            self.log_error(f"Patch invalid: {e}")
            return
        await asyncio.to_thread(add_all, self.root_path)
        self.log_info("Applied and staged:\n- " + "\n- ".join(changed))

    async def action_test(self) -> None:
        if not (self.root_path and self.sb and self.cfg):
            return
        cmd = (self.test_input.value.strip() if self.test_input else "") or self.cfg.test_cmd
        if not cmd:
            self.log_error("Kein Test-/Build-Befehl gesetzt.")
            return
        self.log_info(f"Starte Tests: {cmd}")
        rc = await asyncio.to_thread(run_tests, self.root_path, cmd)
        if rc == 0:
            self.log_info("Tests OK")
        else:
            self.log_error(f"Tests fehlgeschlagen (rc={rc})")

    async def action_commit(self) -> None:
        if not self.root_path:
            return
        msg = (self.commit_input.value.strip() if self.commit_input else "") or "Apply AI patch"
        try:
            await asyncio.to_thread(git_commit, self.root_path, msg)
            self.log_info("Commit done.")
        except SystemExit as e:
            self.log_error(str(e))

    def action_quit(self) -> None:
        self.exit()

def run() -> None:
    DevAgentApp().run()
