"""
HTML Games Generation Skill for Torchlight.

Generates complete, playable HTML games with embedded CSS and JS.
Zero external dependencies - everything is self-contained in one file.

Usage:
    HTML_GAME("snake")
    HTML_GAME("snake", output_file="snake.html", theme="dark")
    HTML_GAME("sudoku", output_file="sudoku.html", difficulty="hard")
"""

import os
from typing import Dict, Any
from pathlib import Path
from context_manager.skills.base import BaseSkill, SkillResult


def _render(template: str, **kwargs: str) -> str:
    for k, v in kwargs.items():
        template = template.replace("{" + k + "}", str(v))
    return template


SNAKE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Snake</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:{bg};color:{fg};font-family:'Segoe UI',sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;overflow:hidden}
.wrapper{text-align:center}
h1{font-size:2rem;margin-bottom:8px;color:{accent}}
.score-row{font-size:1.2rem;margin-bottom:12px;display:flex;justify-content:space-between;max-width:{size}px}
canvas{border:2px solid {accent};border-radius:8px;display:block;margin:0 auto;background:{board}}
.controls{margin-top:16px;display:flex;gap:8px;justify-content:center}
button{padding:8px 20px;font-size:1rem;border:2px solid {accent};background:{bg};color:{accent};border-radius:6px;cursor:pointer}
button:hover{background:{accent};color:{bg}}
.game-over{color:#e74c3c;font-size:1.5rem;margin-top:8px;min-height:2rem}
</style>
</head>
<body>
<div class="wrapper">
<h1>&#x1F40D; Snake</h1>
<div class="score-row"><span>Score: <span id="score">0</span></span><span>High: <span id="highScore">0</span></span></div>
<canvas id="game" width="{size}" height="{size}"></canvas>
<div id="gameOver" class="game-over"></div>
<div class="controls">
<button id="restartBtn">Restart</button>
</div>
</div>
<script>
(function(){
var canvas=document.getElementById('game');
var ctx=canvas.getContext('2d');
var scoreEl=document.getElementById('score');
var highScoreEl=document.getElementById('highScore');
var gameOverEl=document.getElementById('gameOver');
var grid={grid};
var cellSize={size}/{grid};
var snake, direction, nextDirection, food, score, highScore, gameLoop, running, speed;

function init(){
snake=[[Math.floor(grid/2),Math.floor(grid/2)]];
direction=[1,0];nextDirection=[1,0];
score=0;scoreEl.textContent='0';
highScore=parseInt(localStorage.getItem('snakeHigh')||'0');
highScoreEl.textContent=highScore;
gameOverEl.textContent='';
running=true;speed=150;
spawnFood();
clearInterval(gameLoop);
gameLoop=setInterval(update,speed);
}

function spawnFood(){
do{food=[Math.floor(Math.random()*grid),Math.floor(Math.random()*grid)]}while(snake.some(function(s){return s[0]===food[0]&&s[1]===food[1]}))
}

function update(){
if(!running)return;
direction=nextDirection;
var head=[snake[0][0]+direction[0],snake[0][1]+direction[1]];
if(head[0]<0||head[0]>=grid||head[1]<0||head[1]>=grid||snake.some(function(s){return s[0]===head[0]&&s[1]===head[1]})){
running=false;gameOverEl.textContent='Game Over! Press Restart';
clearInterval(gameLoop);
return;
}
snake.unshift(head);
if(head[0]===food[0]&&head[1]===food[1]){score++;scoreEl.textContent=score;if(score>highScore){highScore=score;localStorage.setItem('snakeHigh',highScore);highScoreEl.textContent=highScore}
speed=Math.max(60,150-score*3);
clearInterval(gameLoop);gameLoop=setInterval(update,speed);
spawnFood();
}else snake.pop();
draw();
}

function draw(){
ctx.fillStyle='{board}';ctx.fillRect(0,0,{size},{size});
ctx.fillStyle='{snake_color}';
snake.forEach(function(s,i){
ctx.fillRect(s[0]*cellSize+1,s[1]*cellSize+1,cellSize-2,cellSize-2);
if(i===0){ctx.fillStyle='{snake_head}';ctx.fillRect(s[0]*cellSize+1,s[1]*cellSize+1,cellSize-2,cellSize-2);ctx.fillStyle='{snake_color}'}
});
ctx.fillStyle='{food_color}';
ctx.beginPath();ctx.arc(food[0]*cellSize+cellSize/2,food[1]*cellSize+cellSize/2,cellSize/2-2,0,Math.PI*2);ctx.fill();
}

document.addEventListener('keydown',function(e){
var map={ArrowUp:[0,-1],ArrowDown:[0,1],ArrowLeft:[-1,0],ArrowRight:[1,0],w:[0,-1],s:[0,1],a:[-1,0],d:[1,0]};
var d=map[e.key];
if(d&&(d[0]!==-direction[0]||d[1]!==-direction[1]))nextDirection=d;
if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','w','a','s','d'].indexOf(e.key)!==-1)e.preventDefault();
});

var touchStartX=0,touchStartY=0;
canvas.addEventListener('touchstart',function(e){var t=e.touches[0];touchStartX=t.clientX;touchStartY=t.clientY;});
canvas.addEventListener('touchend',function(e){var dx=e.changedTouches[0].clientX-touchStartX;var dy=e.changedTouches[0].clientY-touchStartY;var adx=Math.abs(dx),ady=Math.abs(dy);
if(adx>ady&&adx>20)nextDirection=[dx>0?1:-1,0];
else if(ady>20)nextDirection=[0,dy>0?1:-1];
});

document.getElementById('restartBtn').addEventListener('click',function(){clearInterval(gameLoop);init();});
init();
})();
</script>
</body>
</html>"""


SUDOKU_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sudoku</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:{bg};color:{fg};font-family:'Segoe UI',sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh}
.wrapper{text-align:center}
h1{font-size:2rem;margin-bottom:8px;color:{accent}}
.info{font-size:1rem;margin-bottom:12px;color:{muted}}
.board{display:inline-grid;grid-template-columns:repeat(9,1fr);gap:1px;background:{muted};border:3px solid {accent};border-radius:6px;overflow:hidden}
.cell{width:44px;height:44px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;background:{board};cursor:pointer;user-select:none;position:relative}
.cell:nth-child(3n){border-right:2px solid {accent}}
.cell:nth-child(9n){border-right:none}
.cell:nth-child(n+19):nth-child(-n+27){border-bottom:2px solid {accent}}
.cell:nth-child(n+46):nth-child(-n+54){border-bottom:2px solid {accent}}
.cell.given{font-weight:700;color:{fg}}
.cell.editable{color:{accent}}
.cell.selected{background:{sel}}
.cell.highlighted{background:{hl}}
.cell.error{color:#e74c3c!important}
.cell.pencil{font-size:.65rem;color:{muted};display:grid;grid-template-columns:repeat(3,1fr);padding:2px}
.cell.pencil span{display:flex;align-items:center;justify-content:center;line-height:1}
.controls{margin-top:16px;display:flex;flex-wrap:wrap;gap:6px;justify-content:center;max-width:400px;margin-left:auto;margin-right:auto}
.num-btn{width:40px;height:40px;border:2px solid {accent};background:{bg};color:{accent};border-radius:6px;font-size:1.1rem;cursor:pointer}
.num-btn:hover{background:{accent};color:{bg}}
.num-btn.erase{font-size:.8rem}
.action-btn{padding:8px 16px;border:2px solid {accent};background:{bg};color:{accent};border-radius:6px;cursor:pointer;font-size:.9rem}
.action-btn:hover{background:{accent};color:{bg}}
.timer{font-size:.9rem;color:{muted};margin-bottom:8px}
</style>
</head>
<body>
<div class="wrapper">
<h1>Sudoku</h1>
<div class="info"><span id="difficulty">{difficulty|capitalize}</span> &middot; <span id="timer">00:00</span></div>
<div class="board" id="board"></div>
<div class="controls" id="numPad"></div>
<div style="margin-top:12px;display:flex;gap:8px;justify-content:center">
<button class="action-btn" id="newGameBtn">New Game</button>
<button class="action-btn" id="checkBtn">Check</button>
<button class="action-btn" id="solveBtn">Solve</button>
<button class="action-btn" id="pencilBtn">Pencil &#x270F;&#xFE0F;</button>
</div>
</div>
<script>
(function(){
var boardEl=document.getElementById('board');
var numPadEl=document.getElementById('numPad');
var timerEl=document.getElementById('timer');
var newGameBtn=document.getElementById('newGameBtn');
var checkBtn=document.getElementById('checkBtn');
var solveBtn=document.getElementById('solveBtn');
var pencilBtn=document.getElementById('pencilBtn');

var puzzle, solution, selected, pencilMode=false, timerInterval, seconds=0;

function generate(diff){
var clues={easy:38,medium:30,hard:24};
var d=clues[diff]||30;
var b=Array(9).fill().map(function(){return Array(9).fill(0)});
solveSudoku(b);
solution=b.map(function(r){return r.slice()});
var cells=[];
for(var i=0;i<81;i++)cells.push(i);
for(var i=0;i<81-d;i++){var idx=Math.floor(Math.random()*cells.length);var p=cells.splice(idx,1)[0];var r=Math.floor(p/9),c=p%9;var v=b[r][c];b[r][c]=0;
if(countSolutions(b.map(function(r){return r.slice()}))!==1){b[r][c]=v}
}
return b;
}

function countSolutions(b){
var c=0;
function solve(){
for(var r=0;r<9;r++)for(var cl=0;cl<9;cl++){
if(b[r][cl]===0){
for(var n=1;n<=9;n++){
if(isValid(b,r,cl,n)){b[r][cl]=n;solve();b[r][cl]=0;if(c>1)return}
}return
}
}c++
}
solve();return c;
}

function isValid(b,r,c,n){
for(var i=0;i<9;i++){if(b[r][i]===n||b[i][c]===n)return false}
var br=Math.floor(r/3)*3,bc=Math.floor(c/3)*3;
for(var i=0;i<3;i++)for(var j=0;j<3;j++){if(b[br+i][bc+j]===n)return false}
return true;
}

function solveSudoku(b){
for(var r=0;r<9;r++)for(var c=0;c<9;c++){
if(b[r][c]===0){
for(var n=1;n<=9;n++){
if(isValid(b,r,c,n)){b[r][c]=n;if(solveSudoku(b))return true;b[r][c]=0}
}return false
}
}return true
}

function render(){
boardEl.innerHTML='';
for(var i=0;i<81;i++){var r=Math.floor(i/9),c=i%9;var cell=document.createElement('div');
cell.className='cell';
if(puzzle[r][c]!==0){cell.textContent=puzzle[r][c];cell.classList.add('given')}else{cell.classList.add('editable')}
if(selected!==null&&r===selected[0]&&c===selected[1])cell.classList.add('selected');
else if(selected!==null&&(r===selected[0]||c===selected[1]||(Math.floor(r/3)===Math.floor(selected[0]/3)&&Math.floor(c/3)===Math.floor(selected[1]/3))))cell.classList.add('highlighted');
cell.dataset.r=r;cell.dataset.c=c;
cell.addEventListener('click',(function(rr,cc){return function(){select(rr,cc)}})(r,c));
boardEl.appendChild(cell);
}
updatePencilMarks();
}

function updatePencilMarks(){
if(!puzzle||!selected)return;
var cells=boardEl.children;
for(var i=0;i<81;i++){var r=Math.floor(i/9),c=i%9;
if(puzzle[r][c]!==0)continue;
var el=cells[i];
if(el.classList.contains('pencil'))continue;
var marks=[];
for(var n=1;n<=9;n++){if(isValid(puzzle,r,c,n))marks.push(n)}
el.innerHTML=marks.map(function(m){return '<span>'+m+'</span>'}).join('');
el.classList.add('pencil');
}
}

function select(r,c){
selected=[r,c];render();
}

for(var i=1;i<=9;i++){(function(n){var btn=document.createElement('button');btn.className='num-btn';btn.textContent=n;
btn.addEventListener('click',function(){if(!selected)return;var r=selected[0],c=selected[1];if(puzzle[r][c]!==0)return;if(pencilMode){puzzle[r][c]=n;render();return}
puzzle[r][c]=n;var el=boardEl.children[r*9+c];el.classList.remove('pencil');el.textContent=n;el.classList.add('editable');updatePencilMarks();
});
numPadEl.appendChild(btn);
})(i);}
var erase=document.createElement('button');erase.className='num-btn erase';erase.textContent='X';
erase.addEventListener('click',function(){if(!selected)return;var r=selected[0],c=selected[1];if(puzzle[r][c]!==0)return;puzzle[r][c]=0;render();});
numPadEl.appendChild(erase);

newGameBtn.addEventListener('click',startGame);
checkBtn.addEventListener('click',function(){var ok=true;
for(var r=0;r<9;r++)for(var c=0;c<9;c++){if(puzzle[r][c]!==solution[r][c]){ok=false;var el=boardEl.children[r*9+c];el.classList.add('error')}}
alert(ok?'All correct!':'Some cells are wrong (highlighted in red)');
});
solveBtn.addEventListener('click',function(){for(var r=0;r<9;r++)for(var c=0;c<9;c++){puzzle[r][c]=solution[r][c]}
pencilMode=false;selected=null;render();clearInterval(timerInterval);timerEl.textContent='Solved!';
});
pencilBtn.addEventListener('click',function(){pencilMode=!pencilMode;pencilBtn.style.borderColor=pencilMode?'#e67e22':'{accent}'});

function startGame(){
var diff='{difficulty}';
puzzle=generate(diff);
selected=null;pencilMode=false;seconds=0;
clearInterval(timerInterval);
timerInterval=setInterval(function(){seconds++;var m=String(Math.floor(seconds/60)).padStart(2,'0');var s=String(seconds%60).padStart(2,'0');timerEl.textContent=m+':'+s;},1000);
render();
}
startGame();
})();
</script>
</body>
</html>"""


class HTMLGameSkill(BaseSkill):
    name = "HTML_GAME"
    description = "Generate complete, playable HTML games (snake, sudoku) with embedded CSS and JS"
    icon = "\U0001f3ae"

    THEMES = {
        "dark": {
            "bg": "#1a1a2e",
            "fg": "#e0e0e0",
            "accent": "#e94560",
            "board": "#16213e",
            "muted": "#555",
            "snake_color": "#4ecca3",
            "snake_head": "#2ecc71",
            "food_color": "#e74c3c",
            "sel": "rgba(233,69,96,0.3)",
            "hl": "rgba(78,204,163,0.15)",
        },
        "light": {
            "bg": "#f5f5f5",
            "fg": "#333",
            "accent": "#2c3e50",
            "board": "#fff",
            "muted": "#ccc",
            "snake_color": "#27ae60",
            "snake_head": "#2ecc71",
            "food_color": "#e74c3c",
            "sel": "rgba(44,62,80,0.2)",
            "hl": "rgba(39,174,96,0.1)",
        },
        "retro": {
            "bg": "#0a0a0a",
            "fg": "#33ff33",
            "accent": "#33ff33",
            "board": "#111",
            "muted": "#333",
            "snake_color": "#33ff33",
            "snake_head": "#66ff66",
            "food_color": "#ff3333",
            "sel": "rgba(51,255,51,0.2)",
            "hl": "rgba(51,255,51,0.1)",
        },
        "ocean": {
            "bg": "#0c2461",
            "fg": "#dfe6e9",
            "accent": "#00cec9",
            "board": "#0a3d62",
            "muted": "#555",
            "snake_color": "#00cec9",
            "snake_head": "#55efc4",
            "food_color": "#fd79a8",
            "sel": "rgba(0,206,201,0.3)",
            "hl": "rgba(0,206,201,0.15)",
        },
    }

    def get_prompt(self) -> str:
        return (
            f"{self.icon} **{self.name}**: {self.description}\n"
            "  Input: {game: 'snake'|'sudoku', output_file: 'games/snake.html' (optional),\n"
            "         theme: 'dark'|'light'|'retro'|'ocean' (optional, default 'dark'),\n"
            "         difficulty: 'easy'|'medium'|'hard' (optional, sudoku only)}\n"
            "  Output: Writes a full HTML file, returns path & details.\n"
            "  Supported games: snake, sudoku"
        )

    async def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        game = input_data.get("game", "").strip().lower()
        output_file = input_data.get("output_file", "")
        theme = input_data.get("theme", "dark").strip().lower()
        difficulty = input_data.get("difficulty", "medium").strip().lower()

        if not game:
            return SkillResult(
                success=False, output="", error="No game specified. Use 'snake' or 'sudoku'."
            )
        if game not in ("snake", "sudoku"):
            return SkillResult(
                success=False, output="", error=f"Unknown game '{game}'. Supported: snake, sudoku."
            )
        if theme not in self.THEMES:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown theme '{theme}'. Options: {', '.join(self.THEMES)}.",
            )
        if difficulty not in ("easy", "medium", "hard"):
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown difficulty '{difficulty}'. Options: easy, medium, hard.",
            )

        if not output_file:
            output_dir = Path.cwd() / "games"
            output_dir.mkdir(exist_ok=True)
            output_file = str(output_dir / f"{game}.html")
        else:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        colors = self.THEMES[theme]
        grid_size = 20
        canvas_size = 400

        if game == "snake":
            html = _render(
                SNAKE_TEMPLATE,
                bg=colors["bg"],
                fg=colors["fg"],
                accent=colors["accent"],
                board=colors["board"],
                muted=colors["muted"],
                snake_color=colors["snake_color"],
                snake_head=colors["snake_head"],
                food_color=colors["food_color"],
                size=str(canvas_size),
                grid=str(grid_size),
            )
        else:
            html = _render(
                SUDOKU_TEMPLATE,
                bg=colors["bg"],
                fg=colors["fg"],
                accent=colors["accent"],
                board=colors["board"],
                muted=colors["muted"],
                sel=colors["sel"],
                hl=colors["hl"],
                difficulty=difficulty,
            )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html.strip())

        file_size = os.path.getsize(output_file)
        lines = html.strip().count("\n") + 1

        parts = [
            f"\u2705 Generated '{game}' \u2014 {output_file}",
            f"   Size: {file_size:,} bytes, {lines} lines",
            f"   Theme: {theme}",
        ]
        if game == "sudoku":
            parts.append(f"   Difficulty: {difficulty}")

        return SkillResult(
            success=True,
            output="\n".join(parts),
            metadata={
                "game": game,
                "file": output_file,
                "size_bytes": file_size,
                "lines": lines,
                "theme": theme,
                "difficulty": difficulty if game == "sudoku" else None,
            },
        )
