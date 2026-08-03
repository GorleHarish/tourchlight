import asyncio
from rlm_optimized.tui_app import TorchlightApp

async def run():
    app = TorchlightApp(project_root=".")
    async with app.run_test() as pilot:
        app._add_context_chip("src/main.py")
        await pilot.pause()
        bar = app.query_one("#context-chips-bar")
        print(f"Bar visible? {bar.styles.display}")
        chips = bar.query(".context-chip")
        print(f"Chips count: {len(chips)}")
        for c in chips:
            print(f"Chip text: {c.label.plain}, tooltip: {c.tooltip}")

asyncio.run(run())
