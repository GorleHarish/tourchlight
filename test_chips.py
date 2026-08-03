import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Button
from textual.containers import Horizontal

class TestApp(App):
    def compose(self) -> ComposeResult:
        yield Horizontal(id="context-chips-bar")
        
    def on_mount(self) -> None:
        try:
            chips_bar = self.query_one("#context-chips-bar", Horizontal)
            btn = Button("@src/main.py X", classes="context-chip")
            btn.tooltip = "src/main.py"
            chips_bar.mount(btn)
            chips_bar.add_class("has-chips")
            print("MOUNTED")
            
            existing = [b.tooltip for b in chips_bar.query(".context-chip") if getattr(b, "tooltip", None)]
            print(f"EXISTING: {existing}")
            self.exit()
        except Exception as e:
            print(f"ERROR: {e}")
            self.exit()

if __name__ == "__main__":
    app = TestApp()
    app.run()
