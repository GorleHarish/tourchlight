import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Button
from textual.containers import Horizontal
from textual import on

class TestApp(App):
    CSS = """
    #context-chips-bar {
        display: none;
    }
    #context-chips-bar.has-chips {
        display: block;
    }
    .context-chip {
        background: blue;
    }
    """
    def compose(self) -> ComposeResult:
        yield Horizontal(id="context-chips-bar")
        yield Button("Add Chip", id="add-btn")
        
    @on(Button.Pressed, "#add-btn")
    def add_chip(self):
        self._add_context_chip("src/main.py")
        
    def _add_context_chip(self, filepath: str) -> None:
        chips_bar = self.query_one("#context-chips-bar", Horizontal)
        existing_chips = [btn.tooltip for btn in chips_bar.query(Button) if getattr(btn, "tooltip", None)]
        if filepath in existing_chips:
            return
            
        btn = Button(f"@{filepath} ✕", classes="context-chip")
        btn.tooltip = filepath
        chips_bar.mount(btn)
        chips_bar.add_class("has-chips")

    @on(Button.Pressed, ".context-chip")
    def _on_context_chip_pressed(self, event: Button.Pressed) -> None:
        btn = event.button
        btn.remove()
        chips_bar = self.query_one("#context-chips-bar", Horizontal)
        if not chips_bar.query(Button):
            chips_bar.remove_class("has-chips")

if __name__ == "__main__":
    app = TestApp()
    
    async def run_test():
        async with app.run_test() as pilot:
            await pilot.press("tab") # focus add button
            await pilot.press("enter")
            await pilot.pause()
            
            bar = app.query_one("#context-chips-bar")
            print(f"Bar display: {bar.styles.display}, has-chips: {bar.has_class('has-chips')}")
            print(f"Chips: {len(bar.query(Button))}")
            
            # Click the chip
            chip = bar.query_one(Button)
            await pilot.click(chip.__class__)
            await pilot.pause()
            
            print(f"Bar display after click: {bar.styles.display}, has-chips: {bar.has_class('has-chips')}")
            print(f"Chips after click: {len(bar.query(Button))}")

    asyncio.run(run_test())
