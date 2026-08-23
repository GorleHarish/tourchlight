---
name: snake-game
description: Scaffolds polished, modern HTML5 Canvas Snake games with retro-neon aesthetics, Web Audio sound effects, particle bursts, and touch/keyboard controls.
icon: 🐍
risk_level: confirm
category: game-dev
tags: [snake, game, html, css, javascript, canvas, arcade]
---

# HTML5 / CSS / JS Snake Game Builder Skill

An expert skill for scaffolding, enhancing, and debugging complete arcade-grade Snake games using pure HTML5, Vanilla CSS, and JavaScript (Canvas API).

---

## 🕹️ Architecture & Core Standards

When generating or refactoring a Snake game, always produce a clean 3-file modular layout (or single self-contained `index.html` if requested):

1. **`index.html`**: Semantic layout, viewport scaling meta, score HUD, restart modal, and touch controls container.
2. **`style.css`**: Deep dark/neon theme, glassmorphism containers (`backdrop-filter: blur()`), glowing borders, responsive centering.
3. **`game.js`**: Game loop with fixed-timestep accumulator, grid coordinate system, Web Audio synthesizer, and particle engine.

---

## 🎮 Essential Game Mechanics Checklist

### 1. Fixed Timestep Loop
Use `requestAnimationFrame` with a time accumulator rather than `setInterval` to ensure jitter-free, lag-free gameplay:
```javascript
let lastTime = 0;
const step = 1 / 15; // 15 updates per second

function gameLoop(timestamp) {
  if (!lastTime) lastTime = timestamp;
  let dt = Math.min(1, (timestamp - lastTime) / 1000);
  lastTime = timestamp;

  while (dt > step) {
    update();
    dt -= step;
  }
  draw();
  if (!isGameOver) requestAnimationFrame(gameLoop);
}
```

### 2. Input Handling & 180° Lock
Prevent self-collision glitches when rapidly pressing two keys within a single frame:
```javascript
let inputQueue = [];

window.addEventListener('keydown', (e) => {
  const key = e.key.toLowerCase();
  const dirMap = {
    arrowup: {x: 0, y: -1}, w: {x: 0, y: -1},
    arrowdown: {x: 0, y: 1}, s: {x: 0, y: 1},
    arrowleft: {x: -1, y: 0}, a: {x: -1, y: 0},
    arrowright: {x: 1, y: 0}, d: {x: 1, y: 0}
  };
  if (dirMap[key]) {
    const nextDir = dirMap[key];
    const current = inputQueue.length ? inputQueue[inputQueue.length - 1] : velocity;
    if (nextDir.x !== -current.x || nextDir.y !== -current.y) {
      inputQueue.push(nextDir);
    }
  }
});
```

### 3. Zero-Dependency Web Audio Synth
Synthesize crisp 8-bit sound effects directly with the Web Audio API (no external MP3/WAV files required):
```javascript
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function playSound(type) {
  if (audioCtx.state === 'suspended') audioCtx.resume();
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.connect(gain);
  gain.connect(audioCtx.destination);

  const now = audioCtx.currentTime;
  if (type === 'eat') {
    osc.frequency.setValueAtTime(440, now);
    osc.frequency.exponentialRampToValueAtTime(880, now + 0.1);
    gain.gain.setValueAtTime(0.3, now);
    gain.gain.linearRampToValueAtTime(0.01, now + 0.1);
    osc.start(now);
    osc.stop(now + 0.1);
  } else if (type === 'die') {
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(220, now);
    osc.frequency.linearRampToValueAtTime(55, now + 0.3);
    gain.gain.setValueAtTime(0.4, now);
    gain.gain.linearRampToValueAtTime(0.01, now + 0.3);
    osc.start(now);
    osc.stop(now + 0.3);
  }
}
```

### 4. Particle Effects Engine
Spawn dynamic neon sparks upon eating food or hitting walls:
```javascript
class Particle {
  constructor(x, y, color) {
    this.x = x;
    this.y = y;
    this.color = color;
    this.radius = Math.random() * 3 + 1;
    this.vx = (Math.random() - 0.5) * 8;
    this.vy = (Math.random() - 0.5) * 8;
    this.alpha = 1.0;
    this.decay = Math.random() * 0.03 + 0.02;
  }
  update() {
    this.x += this.vx;
    this.y += this.vy;
    this.alpha -= this.decay;
  }
  draw(ctx) {
    ctx.save();
    ctx.globalAlpha = Math.max(0, this.alpha);
    ctx.fillStyle = this.color;
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}
```

---

## 🎨 Visual Polish & UI Specifications

- **Theme Palette**:
  - Background: `#0a0e17` (Deep Cyber Navy)
  - Grid Backdrop: `#111827` with faint `#1f2937` grid lines
  - Snake Head: `#00f0ff` (Cyan Glow)
  - Snake Body: `#00d2ff` with gradient fade toward tail
  - Regular Food: `#ff0055` (Neon Pink Glow)
  - Bonus Food: `#ffd700` (Gold Sparkle)
- **Scoreboard**:
  - Glass card with `background: rgba(17, 24, 39, 0.7)`, `border: 1px solid rgba(255, 255, 255, 0.1)`, `backdrop-filter: blur(10px)`.
  - Current Score, High Score (persisted via `localStorage.getItem('snake_highscore')`), and Speed Level.
- **Controls**:
  - Desktop: Keyboard Arrow Keys & WASD.
  - Mobile: On-screen D-pad buttons (`#dpad-up`, `#dpad-down`, `#dpad-left`, `#dpad-right`) or swipe touch gestures.

---

## 🚀 Generation Workflow

1. **Verify Workspace**: Check if the project already has an existing `index.html` or needs a new game directory.
2. **Scaffold Files**: Write clean `index.html`, `style.css`, and `game.js` (or embedded single file).
3. **Validate**: Test game loop start, food spawning without overlapping snake segments, wall collisions vs wrap-around mode, score persistence, and audio synthesizer.
