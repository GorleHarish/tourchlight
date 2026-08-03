import asyncio
from textual.app import App
from textual.widgets import Button

class TestApp(App):
    def compose(self):
        try:
            yield Button("Test", id="chip-main.py")
            print("SUCCESS")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    app = TestApp()
    asyncio.run(app.run_test())
