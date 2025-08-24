"""Main GUI application for DevAgent using Textual."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional, Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header, Footer, Button, Input, TextArea, Label, Tree, 
    DataTable, ProgressBar, Tabs, TabPane, Static, Log
)
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding

from .config import Config
from .scanner import ProjectScanner
from .checks import ProjectChecker
from .context import ContextBuilder
from .llm import LLMClient
from .patch import PatchManager
from .logging import get_logger

logger = get_logger(__name__)


class ScanTab(Static):
    """Project scanning tab."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Project Scanner", classes="tab-title"),
            Horizontal(
                Input(
                    placeholder="Project path (leave empty for current directory)",
                    id="scan-path"
                ),
                Button("Browse", id="scan-browse", variant="default"),
                classes="input-group"
            ),
            Button("Start Scan", id="scan-start", variant="primary"),
            Static(id="scan-progress"),
            DataTable(id="scan-results"),
            classes="tab-content"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "scan-start":
            self.scan_project()

    def scan_project(self) -> None:
        """Start project scanning."""
        path_input = self.query_one("#scan-path", Input)
        scan_path = Path(path_input.value) if path_input.value else Path.cwd()
        
        # Clear previous results
        results_table = self.query_one("#scan-results", DataTable)
        results_table.clear()
        
        try:
            progress_container = self.query_one("#scan-progress", Static)
            progress_container.update("🔍 Scanning project...")
            
            scanner = ProjectScanner(scan_path)
            result = scanner.scan()
            
            # Update results table
            results_table.add_columns("Metric", "Value")
            results_table.add_row("Files scanned", str(result['files_scanned']))
            results_table.add_row("Summaries created", str(len(result['file_summaries'])))
            results_table.add_row("Cache location", ".agentcache/")
            
            progress_container.update("✅ Scan completed successfully!")
            
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            progress_container.update(f"❌ Scan failed: {e}")


class CheckTab(Static):
    """Health checks tab."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Project Health Checks", classes="tab-title"),
            Horizontal(
                Input(
                    placeholder="Project path (leave empty for current directory)",
                    id="check-path"
                ),
                Button("Browse", id="check-browse", variant="default"),
                classes="input-group"
            ),
            Button("Run Checks", id="check-start", variant="primary"),
            Static(id="check-progress"),
            DataTable(id="check-results"),
            classes="tab-content"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "check-start":
            self.run_checks()

    def run_checks(self) -> None:
        """Run project health checks."""
        path_input = self.query_one("#check-path", Input)
        check_path = Path(path_input.value) if path_input.value else Path.cwd()
        
        # Clear previous results
        results_table = self.query_one("#check-results", DataTable)
        results_table.clear()
        
        try:
            progress_container = self.query_one("#check-progress", Static)
            progress_container.update("🔍 Running checks...")
            
            checker = ProjectChecker(check_path)
            results = checker.run_checks()
            
            # Update results table
            results_table.add_columns("Check", "Status", "Summary")
            
            for check_name in results["checks_run"]:
                check_result = results["results"].get(check_name, {})
                status = "✅ Pass" if check_result.get("success") else "❌ Fail"
                summary = check_result.get("summary", "No details")
                results_table.add_row(check_name.title(), status, summary)
            
            if results["overall_status"] == "success":
                progress_container.update("🎉 All checks passed!")
            else:
                progress_container.update(f"⚠️ Some checks failed: {results.get('summary', '')}")
                
        except Exception as e:
            logger.error(f"Checks failed: {e}")
            progress_container.update(f"❌ Checks failed: {e}")


class ProposeTab(Static):
    """AI proposal generation tab."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("AI Code Proposals", classes="tab-title"),
            Horizontal(
                Input(
                    placeholder="Project path (leave empty for current directory)",
                    id="propose-path"
                ),
                Button("Browse", id="propose-browse", variant="default"),
                classes="input-group"
            ),
            Input(
                placeholder="Development goal/task description",
                id="propose-goal"
            ),
            TextArea(
                text="# Files to include (one per line)",
                id="propose-files"
            ),
            Horizontal(
                Input(
                    placeholder="Model (optional, defaults to config)",
                    id="propose-model"
                ),
                Button("Generate Proposal", id="propose-start", variant="primary"),
                classes="input-group"
            ),
            Static(id="propose-progress"),
            TextArea(id="propose-results", read_only=True),
            classes="tab-content"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "propose-start":
            self.generate_proposal()

    def generate_proposal(self) -> None:
        """Generate AI code proposal."""
        path_input = self.query_one("#propose-path", Input)
        goal_input = self.query_one("#propose-goal", Input)
        files_input = self.query_one("#propose-files", TextArea)
        model_input = self.query_one("#propose-model", Input)
        
        project_path = Path(path_input.value) if path_input.value else Path.cwd()
        goal = goal_input.value
        files_text = files_input.text
        model = model_input.value if model_input.value else None
        
        if not goal:
            self.query_one("#propose-progress", Static).update("❌ Please provide a development goal")
            return
            
        if not files_text:
            self.query_one("#propose-progress", Static).update("❌ Please specify files to include")
            return
        
        touch_files = [f.strip() for f in files_text.split('\n') if f.strip()]
        
        try:
            progress_container = self.query_one("#propose-progress", Static)
            results_area = self.query_one("#propose-results", TextArea)
            
            progress_container.update("🤖 Generating AI proposal...")
            results_area.text = ""
            
            config = Config()
            context_builder = ContextBuilder(project_path)
            llm_client = LLMClient(config)
            patch_manager = PatchManager(project_path)
            
            # Build context
            progress_container.update("📋 Building context...")
            context = context_builder.build_context(touch_files=touch_files, goal=goal)
            
            # Generate proposal
            progress_container.update("🧠 Generating proposal...")
            response = llm_client.generate_proposal(context, model_override=model)
            
            # Save patch
            progress_container.update("💾 Saving patch...")
            patch_path = patch_manager.save_patch(response["patch"], response["commit_message"])
            
            # Display results
            results_text = f"""✨ Proposal Generated Successfully!

📁 Patch File: {patch_path}
🔗 Latest Link: patches/latest.patch
📝 Commit Message: {response['commit_message']}
🧪 Test Plan: {response.get('test_plan', 'Not provided')}
🔄 Rollback Plan: {response.get('rollback', 'Not provided')}

💡 Ready to apply with: devagent apply patches/latest.patch
"""
            results_area.text = results_text
            progress_container.update("✅ Proposal generated successfully!")
            
        except Exception as e:
            logger.error(f"Proposal generation failed: {e}")
            progress_container.update(f"❌ Proposal failed: {e}")


class PatchTab(Static):
    """Patch management tab."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Patch Management", classes="tab-title"),
            Horizontal(
                Input(
                    placeholder="Patch file path",
                    id="patch-file"
                ),
                Button("Browse", id="patch-browse", variant="default"),
                classes="input-group"
            ),
            Horizontal(
                Input(
                    placeholder="Repository path (leave empty for current directory)",
                    id="patch-repo"
                ),
                Button("Browse Repo", id="patch-repo-browse", variant="default"),
                classes="input-group"
            ),
            Horizontal(
                Button("Apply Patch", id="patch-apply", variant="primary"),
                Button("Apply & Commit", id="patch-apply-commit", variant="success"),
                Button("Apply (Keep on Fail)", id="patch-apply-keep", variant="warning"),
                classes="button-group"
            ),
            Static(id="patch-progress"),
            DataTable(id="patch-results"),
            classes="tab-content"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "patch-apply":
            self.apply_patch(autocommit=False, keep_on_fail=False)
        elif event.button.id == "patch-apply-commit":
            self.apply_patch(autocommit=True, keep_on_fail=False)
        elif event.button.id == "patch-apply-keep":
            self.apply_patch(autocommit=False, keep_on_fail=True)

    def apply_patch(self, autocommit: bool = False, keep_on_fail: bool = False) -> None:
        """Apply a patch file."""
        patch_input = self.query_one("#patch-file", Input)
        repo_input = self.query_one("#patch-repo", Input)
        
        if not patch_input.value:
            self.query_one("#patch-progress", Static).update("❌ Please specify a patch file")
            return
            
        patch_file = Path(patch_input.value)
        repo_path = Path(repo_input.value) if repo_input.value else Path.cwd()
        
        # Clear previous results
        results_table = self.query_one("#patch-results", DataTable)
        results_table.clear()
        
        try:
            progress_container = self.query_one("#patch-progress", Static)
            
            patch_manager = PatchManager(repo_path)
            checker = ProjectChecker(repo_path)
            
            # Validate
            progress_container.update("🔍 Validating patch...")
            patch_manager.validate_patch(patch_file)
            
            # Apply
            progress_container.update("📝 Applying patch...")
            affected_files = patch_manager.apply_patch(patch_file)
            
            # Check
            progress_container.update("✅ Running checks...")
            check_results = checker.run_checks()
            
            # Show affected files
            if affected_files:
                results_table.add_columns("Modified Files")
                for file_path in affected_files:
                    results_table.add_row(file_path)
            
            if check_results["overall_status"] != "success":
                progress_container.update("⚠️ Post-apply checks failed")
                if not keep_on_fail:
                    progress_container.update("❌ Use 'Keep on Fail' to proceed despite failures")
                    return
            
            if autocommit:
                commit_msg = f"Apply patch: {patch_file.name}"
                progress_container.update("📤 Committing changes...")
                patch_manager.commit_changes(commit_msg)
                progress_container.update(f"🚀 Changes committed: {commit_msg}")
            else:
                progress_container.update("✅ Patch applied successfully!")
                
        except Exception as e:
            logger.error(f"Patch application failed: {e}")
            progress_container.update(f"❌ Patch failed: {e}")


class DevAgentGUI(App):
    """Main DevAgent GUI application."""
    
    TITLE = "DevAgent - AI Development Assistant"
    CSS_PATH = "gui.css"
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+s", "scan", "Scan", show=False),
        Binding("ctrl+h", "check", "Check", show=False),
        Binding("ctrl+p", "propose", "Propose", show=False),
        Binding("ctrl+a", "apply", "Apply", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Tabs(
                TabPane("Scanner", ScanTab(), id="scan-tab"),
                TabPane("Health Checks", CheckTab(), id="check-tab"),
                TabPane("AI Proposals", ProposeTab(), id="propose-tab"),
                TabPane("Patch Management", PatchTab(), id="patch-tab"),
                id="main-tabs"
            ),
            id="main-container"
        )
        yield Footer()

    def action_scan(self) -> None:
        """Focus on scan tab."""
        self.query_one("#main-tabs", Tabs).active = "scan-tab"

    def action_check(self) -> None:
        """Focus on check tab."""
        self.query_one("#main-tabs", Tabs).active = "check-tab"

    def action_propose(self) -> None:
        """Focus on propose tab."""
        self.query_one("#main-tabs", Tabs).active = "propose-tab"

    def action_apply(self) -> None:
        """Focus on apply tab."""
        self.query_one("#main-tabs", Tabs).active = "patch-tab"


def main() -> None:
    """Run the DevAgent GUI."""
    app = DevAgentGUI()
    app.run()


if __name__ == "__main__":
    main()