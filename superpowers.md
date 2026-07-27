# 🦸‍♂️ Torchlight's Superpowers!

Imagine having a super-smart robot assistant living inside your computer that helps you write code. But wait, this robot is running on a normal everyday laptop with only 8GB of memory (RAM)! Usually, these AI robots are so big they need giant, expensive supercomputers to work. 

How does Torchlight do it? It uses **five amazing superpowers**!

---

## 🗺️ Superpower 1: The Magic Code Map (AST Graph & Kùzu DB)

Normally, if you tell a robot to fix a typo in a giant book, it has to read the *entire book* from page 1 to the very end just to find it. That takes way too much time and brainpower.

Instead, Torchlight builds a magic map of your code powered by an embedded graph database (**Kùzu DB**). 
If you ask the robot to fix a specific button on your website, it looks at its magic map, teleports *exactly* to where that button is, and only reads those 30 lines of code instead of 10,000 lines. It can also see how that button connects to other parts of your code instantly with zero latency!

---

## 🔫 Superpower 2: The Shrink Ray (8GB Memory Tricks)

How do you fit a giant AI brain into a small 8GB laptop? You use a bunch of clever tricks to shrink it down!

*   **Squishing Memories (TurboQuant):** The robot squishes its memories into tiny puzzle pieces so they take up way less space in the computer's memory.
*   **Summarizing the Past (Selective Compression):** The robot remembers exactly what you said 2 minutes ago in perfect detail. But for things you talked about an hour ago, it just remembers a short summary. This keeps its head from getting too full!
*   **The Flashlight Beam:** The robot isn't allowed to stare at all your files at once. It can only look through a small "flashlight beam" at 50 lines of code at a time. This keeps the computer running fast and smooth.

---

## 🧠 Superpower 3: Tiny, Ultra-Smart Brains (Small Models)

Instead of using a massive, heavy robot brain that requires 16GB of memory, Torchlight uses special, extra-efficient brains (like Gemma-4-E2B). These brains have been "quantized" — which is a fancy way of saying all the unnecessary fluff has been trimmed off, so the brain is small, fast, and still incredibly smart.

---

## 🎭 Superpower 4: Changing Moods (Phase-Based Inference)

Instead of loading three different brains into memory for different jobs, Torchlight uses one brain but changes its "mood". 
*   When it writes code, it becomes very strict and logical.
*   When it chats with you, it becomes more creative and friendly. 
This saves tons of computer memory because we only need one brain to do everything!

---

## 🔄 Superpower 5: The "Try Again" Loop (RLM)

Most AI chatbots just guess the answer, print out some code, and hope it works. If it's broken, *you* have to fix it. 

Torchlight is an **RLM** (Recursive Language Model). That means it has its own digital playground (a sandbox) where it can test things itself!

*   **It tests its own homework:** It writes the code, runs the code inside its sandbox, and checks the answer. 
*   **It never gives up:** If the code breaks and spits out a red error, the robot doesn't cry or give up. It reads the error, says *"Oops, let me try a different way,"* and fixes its own mistake before it even shows you the final answer! 
*   **Step-by-Step:** If a problem is too big, the robot breaks it down into smaller, easier puzzles and solves them one by one.

---

## 🕵️‍♂️ Superpower 6: The Invisible Devil's Advocate (Out-of-Band Self-Critique)

Before making any big file changes or running commands, Torchlight hires a hidden "Devil's Advocate" auditor inside its head!

*   **Catching Bugs Secretly:** The Devil's Advocate inspects the code for missing imports, edge cases, or zero-division bugs *before* it gets saved.
*   **Zero Memory Bloat:** The auditor works in a temporary secret scratchpad. Once the code is fixed, the scratchpad is wiped clean — meaning it takes up **0 tokens of memory space**!
*   **Clean Status Badges:** You get a clean 1-line badge (`✨ Refined Proposal`) showing what was fixed, keeping your screen and context window totally clutter-free.

---

## 🏃‍♂️ Superpower 7: The 24-Hour Non-Stop Marathon Engine (Autonomous Harness)

What if you want Torchlight to refactor an entire application or write 50 unit tests while you sleep for 24 hours?

*   **Memory Reset Between Sub-Tasks:** Instead of cramming 24 hours of conversation into memory, Torchlight works in short sub-task "sprints" (micro-epochs). After each sub-task, it wipes its conversation memory clean to stay fast and sharp!
*   **Disk Task Board (`tasks.md`):** It keeps its long-term plan written down on disk in `.torchlight/tasks.md` so it never forgets what to do next.
*   **Local Git Save Points:** Every time a sub-task passes its tests, Torchlight makes a local Git commit save point. If a sub-task fails, Torchlight automatically rolls back the bad edits (`git checkout` + `git clean`), keeping your project safe and green 24/7 without needing any remote setup!

---

## 📊 Summary Table of Superpowers

| Superpower | What is the Fancy Name? | What does it do? (In Simple Words) | Why is it awesome for an 8GB Laptop? |
| :--- | :--- | :--- | :--- |
| **Magic Code Map** | AST Graph Indexing | Creates a map to jump straight to the exact lines of code needed. | Saves the robot from reading 10,000 lines, saving huge amounts of memory and time. |
| **Squishing Memories** | TurboQuant KV Compression | Compresses the robot's short-term memory into tiny puzzle pieces. | Prevents the laptop from running out of RAM when working on large projects. |
| **Summarizing the Past**| Selective Compression | Keeps new memories perfect, but turns old memories into short summaries. | Keeps the "Context Window" small so the robot doesn't crash the computer. |
| **Flashlight Beam** | Token Budgeting | Limits the robot to only "seeing" 50 lines of code at a time. | Prevents the robot from flooding the computer's memory with huge files. |
| **Tiny Smart Brains** | Quantized LLM Models | Uses small, trimmed-down AI models instead of giant ones. | Fits the entire AI brain perfectly inside the laptop's limited memory space. |
| **Changing Moods** | Phase-Based Inference | Changes how strict or creative the robot acts based on the current task. | Avoids needing multiple different AI brains for different tasks, saving RAM. |
| **"Try Again" Loop** | RLM Sandbox & Auto-Recovery | The robot tests its own code, catches errors, and fixes them by itself. | Allows the robot to code completely on its own without needing constant human help! |
| **Persistent Memory** | Project State Persistence | The agent saves important project details to a `.torchlight_memory.md` file. | Avoids re-learning project context on every restart, saving token usage and time. |
| **Invisible Devil's Advocate** | Out-of-Band Debate Verifier | Audits and fixes code proposals in an isolated scratchpad before execution. | Catches subtle bugs while using **0 tokens** of main context memory. |
| **Marathon Engine** | Autonomous Goal Harness | Runs sub-tasks in micro-epochs, resetting conversation memory and local Git checkpointing. | Enables 24-hour non-stop goal execution without context window overflow or code degradation! |


