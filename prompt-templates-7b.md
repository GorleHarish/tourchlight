# Prompt Templates for 7B Coder Models

Quick reference for crafting effective prompts for small (7B) coding LLMs.
Covers initial creation, feature enhancement, and bug fixing.

---

## Why Prompt Style Matters for 7B Models

| Prompt Style | 7B Effectiveness | When to Use |
|---|---|---|
| Simple ("fix this bug") | Poor — misses context, over/under-engineers | Avoid for anything non-trivial |
| Middle ground (goal + key context) | Good — sweet spot for most tasks | Quick edits, known codebase |
| Fully structured (task + constraints + output format) | Best — small models need hand-holding | Initial creation, complex features |

### Key Characteristics of 7B Models

- **Unreliable output length:** ~1-2k tokens reliable, 4k+ risky
- **Forgetful mid-response:** constraints stated early may be dropped later
- **Needs explicit values:** grid sizes, colors, timing — never assume inference
- **Context loss:** don't assume it "remembers" prior conversation turns

---

## Template 1: Initial Creation

Use when: building something from scratch (new file, new component, new feature).

```
Create `snake.html` — a single-file HTML Snake game.

Tech: HTML5 Canvas + vanilla JS, no frameworks.

Grid: 20x20 cells, cell size 20px (400x400 canvas).
Snake: starts center, length 3, moves right every 150ms.
Controls: arrow keys.
Food: random empty cell, red circle.
Snake: head #2d6a4f, body #52b788.
Walls: wrap around (no death).
Self-collision: game over.

UI:
- Score above canvas, updates on eat
- "Game Over" + final score overlay
- Space to restart

Output complete file. No TODOs.
```

### Structure

1. **File name and type** — be explicit about single vs multi-file
2. **Tech constraints** — stack, no-framework rule
3. **Data model** — sizes, positions, speeds
4. **Input** — controls, interactions
5. **Visuals** — colors, shapes, layout
6. **Behavior** — win/lose conditions
7. **UI elements** — score, overlays, restart
8. **Output instruction** — complete file, no placeholders

---

## Template 2: Feature Enhancement

Use when: adding features to existing code. Always paste the current code or reference the file.

```
Current file: [paste snake.html or reference it]

Add these features (keep all existing functionality):

1. Speed increase: every 5 foods eaten, reduce interval by 10ms (min 50ms)
2. High score: store in localStorage, display below canvas
3. Pause: press P to pause/resume, show "PAUSED" overlay
4. Walls kill: toggle with W key, show current mode label "Walls: ON/OFF"

Do NOT rewrite the whole file. Only show changed/added code with line references.
```

### Structure

1. **Context** — paste existing code or file path
2. **Feature list** — numbered, each with clear acceptance criteria
3. **Constraint** — preserve existing functionality
4. **Output instruction** — diffs only, not full rewrites

### Why Diffs Only?

7B models degrade when rewriting full files mid-conversation. Keeping output
focused on changes reduces hallucinated code and token waste.

---

## Template 3: Bug Fix

Use when: something is broken. Provide maximum context.

```
File: [paste snake.html]

Bug: snake passes through itself without dying
Expected: snake should die on self-collision
Steps to reproduce:
1. Grow snake to length 5+
2. Turn into its own body
3. Snake continues instead of game over

Console errors (if any):
Uncaught TypeError: Cannot read property 'x' of undefined at game.js:42

Fix the bug. Show only the changed lines with context (±3 lines).
Explain root cause in one sentence.
```

### Structure

1. **File** — paste full code or reference
2. **Bug description** — what happens (observable behavior)
3. **Expected behavior** — what should happen
4. **Reproduction steps** — numbered, specific
5. **Error output** — console messages, stack traces
6. **Output instruction** — surgical fix with context lines, one-line explanation

---

## Token Budget Guide

| Phase | Prompt Size | Expected Output |
|---|---|---|
| Initial creation | ~1.5k tokens | Full file (1-2k tokens) |
| Feature enhancement | ~800 tokens | Changed code only (500-1k tokens) |
| Bug fix | ~500 tokens | Patch + explanation (200-500 tokens) |

---

## Breaking Complex Tasks into Chained Prompts

If step 1 produces broken output, split into two prompts:

**Prompt 1:**
```
Create `snake.html` with HTML boilerplate and canvas setup.
- 400x400 canvas, 20x20 grid
- Style: centered, dark background
- Score element above canvas
Output complete file so far.
```

**Prompt 2:**
```
Here is the current snake.html: [paste]

Add game logic:
- Snake array, movement, collision detection
- Food spawning, score increment
- Game over + restart

Do NOT change the HTML/CSS. Only add JS.
```

---

## General Rules for 7B Models

1. **Always paste existing code** — small models lose context fast
2. **Be explicit about sizes, colors, timing** — don't let it guess
3. **Ask for diffs on edits** — full rewrites degrade quality
4. **Keep prompts under 1.5k tokens** — longer prompts dilute attention
5. **One task per prompt** — chain prompts for multi-feature work
6. **Include verification steps** — "press X to see Y", "score should show Z"
7. **Specify output format** — "complete file", "diff only", "single function"
8. **No vague words** — "nice UI" → "centered, 12px font, #333 color"

---

## Prompt Pattern: Chained Development

```
Step 1: Create base HTML + canvas setup
Step 2: Add snake movement + controls
Step 3: Add food + scoring
Step 4: Add game over + restart
Step 5: Polish UI (colors, overlays, labels)
```

Each step builds on the last. Paste previous output into each new prompt.
This keeps each prompt focused and within 7B's reliable output range.
