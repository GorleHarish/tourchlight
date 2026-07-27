"""
CLI entry point to launch the Torchlight 24-Hour Autonomous Harness.
"""

import argparse
from pathlib import Path

from core.memory.manager import TieredMemory, MemoryConfig
from core.execution.autonomous_harness import AutonomousHarness, HarnessConfig


def main():
    parser = argparse.ArgumentParser(description="Torchlight Autonomous Harness Runner")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--goal-id", default="goal_01", help="Goal ID")
    parser.add_argument("--title", default="Autonomous Improvement Goal", help="Goal Title")
    parser.add_argument("--description", default="Run continuous task optimization", help="Goal Description")
    parser.add_argument("--duration", type=int, default=86400, help="Max duration in seconds (default 86400 / 24h)")
    parser.add_argument("--max-steps", type=int, default=10, help="Max steps per epoch")

    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    memory = TieredMemory(config=MemoryConfig.auto_tune(max_tokens=4000))
    config = HarnessConfig(max_duration_seconds=args.duration, max_epoch_steps=args.max_steps)

    harness = AutonomousHarness(project_root=project_root, memory=memory, config=config)

    # Load existing goal or initialize demo goal
    goal = harness.load_goal_spec()
    if not goal:
        print(f"Initializing new goal: {args.title}")
        demo_tasks = [
            {"id": "task_01", "description": "Audit codebase structure", "target_files": ["core/execution/feedback_loop.py"]},
            {"id": "task_02", "description": "Verify test suite health", "target_files": ["core/tests/test_autonomous_harness.py"]},
        ]
        goal = harness.initialize_goal(goal_id=args.goal_id, title=args.title, description=args.description, tasks=demo_tasks)

    print(f"Goal loaded: {goal.title} ({len(goal.tasks)} tasks)")
    print(f"Tasks Markdown written to: {harness.tasks_md_path}")
    print("Starting Autonomous Harness Daemon...")

    results = harness.run_daemon()
    print("\n--- Harness Daemon Summary ---")
    print(f"Total Tasks: {results['total_tasks']}")
    print(f"Verified: {results['verified']}")
    print(f"Failed: {results['failed']}")
    print(f"Pending: {results['pending']}")
    print(f"Elapsed Time: {results['elapsed_seconds']:.2f}s")


if __name__ == "__main__":
    main()
