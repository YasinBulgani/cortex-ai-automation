"use client";

import { useEffect, useRef } from "react";

// ── Tech armies ───────────────────────────────────────────────────────────────
const LLM_UNITS   = ["GPT-4o","Claude 3","Gemini","Llama 3","Mistral","Grok","Phi-3","Qwen","Falcon","DeepSeek","Cohere","Command R+","Gemini Ultra","Claude Opus"];
const LLM_NATIONS = ["OpenAI Empire","Anthropic State","Google DeepMind","Meta AI Land","Mistral Republic","xAI Territory","DeepSeek Empire","MS Copilot","Cohere Nation","Qwen Dynasty"];
const AI_UNITS    = ["Playwright","Selenium","Cypress","TestNG","Cucumber","Jest","Pytest","Appium","Robot FW","JUnit","K6","Postman","Vitest","WebdriverIO"];
const AI_NATIONS  = ["Playwright State","Selenium Empire","Cypress Nation","Cucumber Republic","Jest Kingdom","Pytest Domain","Appium Territory","Robot Framework","JUnit Legion","K6 Corps"];

// ── Map colors ────────────────────────────────────────────────────────────────
const OCEAN_DEEP   = "#020810";
const OCEAN_MID    = "#050e1d";
const LAND_FILL    = "#0f2240";
const LAND_BRIGHT  = "#1a3a6a";
const LAND_STROKE  = "#2a5fa8";
const LAND_COAST   = "#3a7acc";

// ── Continent polygon data (Mercator normalized 0–1) ─────────────────────────
const CONTINENTS: { pts: number[][]; label?: string; lx?: number; ly?: number }[] = [
  // ── North America ───────────────────────────────────────────────────────────
  { label:"North America", lx:0.155, ly:0.22,
    pts:[[0.03,0.07],[0.07,0.04],[0.12,0.03],[0.17,0.03],[0.21,0.04],[0.25,0.06],
         [0.27,0.09],[0.29,0.13],[0.30,0.16],[0.30,0.20],[0.28,0.24],[0.26,0.28],
         [0.24,0.33],[0.22,0.37],[0.19,0.40],[0.17,0.43],[0.15,0.42],[0.13,0.43],
         [0.11,0.40],[0.09,0.38],[0.07,0.33],[0.06,0.27],[0.04,0.20],[0.03,0.13]] },
  // ── Central America ─────────────────────────────────────────────────────────
  { pts:[[0.17,0.43],[0.19,0.41],[0.21,0.42],[0.22,0.44],[0.21,0.47],[0.19,0.49],[0.17,0.47]] },
  // ── Caribbean islands (dot-like) ────────────────────────────────────────────
  { pts:[[0.23,0.38],[0.25,0.37],[0.26,0.39],[0.24,0.40]] },
  // ── South America ───────────────────────────────────────────────────────────
  { label:"South America", lx:0.215, ly:0.60,
    pts:[[0.17,0.49],[0.20,0.47],[0.23,0.47],[0.27,0.48],[0.31,0.50],[0.33,0.53],
         [0.34,0.57],[0.33,0.62],[0.31,0.67],[0.28,0.72],[0.25,0.76],[0.22,0.78],
         [0.19,0.77],[0.16,0.74],[0.14,0.69],[0.12,0.62],[0.12,0.55],[0.14,0.52]] },
  // ── Falklands ───────────────────────────────────────────────────────────────
  { pts:[[0.22,0.84],[0.24,0.83],[0.25,0.85],[0.22,0.86]] },
  // ── Greenland ───────────────────────────────────────────────────────────────
  { pts:[[0.22,0.01],[0.28,0.00],[0.32,0.01],[0.33,0.04],[0.31,0.07],[0.27,0.08],[0.22,0.07]] },
  // ── Iceland ─────────────────────────────────────────────────────────────────
  { pts:[[0.34,0.08],[0.37,0.07],[0.39,0.09],[0.37,0.11],[0.34,0.10]] },
  // ── UK + Ireland ────────────────────────────────────────────────────────────
  { pts:[[0.40,0.10],[0.42,0.09],[0.44,0.10],[0.44,0.13],[0.42,0.15],[0.40,0.14]] },
  // ── Europe mainland ─────────────────────────────────────────────────────────
  { label:"Europe", lx:0.47, ly:0.17,
    pts:[[0.39,0.11],[0.43,0.08],[0.48,0.07],[0.52,0.08],[0.55,0.09],[0.57,0.11],
         [0.58,0.14],[0.57,0.18],[0.56,0.21],[0.54,0.23],[0.51,0.25],[0.48,0.27],
         [0.45,0.27],[0.42,0.25],[0.40,0.22],[0.38,0.18],[0.39,0.14]] },
  // ── Iberian Peninsula ───────────────────────────────────────────────────────
  { pts:[[0.39,0.18],[0.41,0.17],[0.44,0.20],[0.43,0.24],[0.40,0.25],[0.38,0.22]] },
  // ── Italy ───────────────────────────────────────────────────────────────────
  { pts:[[0.47,0.18],[0.49,0.17],[0.50,0.20],[0.49,0.24],[0.47,0.25],[0.46,0.22]] },
  // ── Scandinavia ─────────────────────────────────────────────────────────────
  { pts:[[0.45,0.03],[0.48,0.01],[0.52,0.02],[0.54,0.05],[0.53,0.08],[0.50,0.09],
         [0.47,0.09],[0.44,0.08]] },
  // ── Finland + Baltics ───────────────────────────────────────────────────────
  { pts:[[0.52,0.04],[0.57,0.03],[0.59,0.06],[0.57,0.09],[0.53,0.09]] },
  // ── Africa ──────────────────────────────────────────────────────────────────
  { label:"Africa", lx:0.475, ly:0.47,
    pts:[[0.40,0.28],[0.43,0.26],[0.47,0.25],[0.51,0.25],[0.55,0.26],[0.58,0.28],
         [0.60,0.31],[0.61,0.35],[0.62,0.40],[0.61,0.46],[0.59,0.52],[0.57,0.58],
         [0.54,0.63],[0.51,0.67],[0.48,0.68],[0.45,0.67],[0.42,0.63],[0.40,0.57],
         [0.38,0.50],[0.37,0.42],[0.38,0.35],[0.39,0.31]] },
  // ── Madagascar ──────────────────────────────────────────────────────────────
  { pts:[[0.57,0.52],[0.59,0.51],[0.61,0.53],[0.61,0.58],[0.59,0.62],[0.57,0.61],[0.55,0.57]] },
  // ── Middle East + Arabia ────────────────────────────────────────────────────
  { pts:[[0.55,0.19],[0.59,0.18],[0.63,0.18],[0.67,0.20],[0.69,0.24],[0.70,0.29],
         [0.68,0.33],[0.65,0.36],[0.62,0.37],[0.59,0.35],[0.57,0.32],[0.55,0.27]] },
  // ── Asia (main body) ────────────────────────────────────────────────────────
  { label:"Asia", lx:0.73, ly:0.17,
    pts:[[0.55,0.06],[0.60,0.04],[0.66,0.03],[0.72,0.03],[0.78,0.04],[0.83,0.05],
         [0.87,0.08],[0.90,0.11],[0.93,0.15],[0.95,0.19],[0.94,0.24],[0.92,0.28],
         [0.89,0.31],[0.85,0.33],[0.80,0.35],[0.75,0.36],[0.70,0.36],[0.65,0.36],
         [0.61,0.35],[0.58,0.32],[0.55,0.27],[0.53,0.22],[0.53,0.16],[0.54,0.10]] },
  // ── Kamchatka ───────────────────────────────────────────────────────────────
  { pts:[[0.92,0.16],[0.95,0.14],[0.97,0.18],[0.96,0.23],[0.93,0.24]] },
  // ── India subcontinent ──────────────────────────────────────────────────────
  { pts:[[0.62,0.29],[0.66,0.28],[0.70,0.29],[0.72,0.33],[0.73,0.38],[0.71,0.43],
         [0.68,0.47],[0.65,0.49],[0.62,0.46],[0.60,0.41],[0.60,0.35]] },
  // ── Sri Lanka ───────────────────────────────────────────────────────────────
  { pts:[[0.66,0.49],[0.68,0.48],[0.69,0.51],[0.67,0.53]] },
  // ── Southeast Asia peninsula ────────────────────────────────────────────────
  { pts:[[0.73,0.35],[0.78,0.34],[0.82,0.36],[0.83,0.40],[0.82,0.44],[0.78,0.47],
         [0.74,0.47],[0.72,0.43],[0.72,0.38]] },
  // ── Sumatra ─────────────────────────────────────────────────────────────────
  { pts:[[0.73,0.48],[0.78,0.47],[0.82,0.49],[0.81,0.54],[0.77,0.55],[0.73,0.53]] },
  // ── Borneo ──────────────────────────────────────────────────────────────────
  { pts:[[0.80,0.47],[0.85,0.46],[0.88,0.49],[0.88,0.54],[0.84,0.57],[0.80,0.55],[0.78,0.51]] },
  // ── Java ────────────────────────────────────────────────────────────────────
  { pts:[[0.79,0.57],[0.83,0.57],[0.87,0.58],[0.87,0.60],[0.82,0.61],[0.78,0.60]] },
  // ── Japan (Honshu) ──────────────────────────────────────────────────────────
  { pts:[[0.88,0.13],[0.91,0.12],[0.94,0.14],[0.94,0.18],[0.91,0.20],[0.88,0.18]] },
  // ── Hokkaido ────────────────────────────────────────────────────────────────
  { pts:[[0.90,0.11],[0.93,0.10],[0.95,0.12],[0.93,0.14],[0.90,0.13]] },
  // ── Korea peninsula ─────────────────────────────────────────────────────────
  { pts:[[0.85,0.16],[0.87,0.16],[0.88,0.19],[0.86,0.22],[0.84,0.21]] },
  // ── Taiwan ──────────────────────────────────────────────────────────────────
  { pts:[[0.87,0.27],[0.89,0.26],[0.90,0.28],[0.88,0.30]] },
  // ── Philippines ─────────────────────────────────────────────────────────────
  { pts:[[0.85,0.38],[0.87,0.37],[0.88,0.40],[0.87,0.43],[0.84,0.42]] },
  // ── Australia ───────────────────────────────────────────────────────────────
  { label:"Australia", lx:0.81, ly:0.61,
    pts:[[0.72,0.52],[0.77,0.50],[0.82,0.50],[0.87,0.51],[0.91,0.53],[0.93,0.57],
         [0.93,0.62],[0.91,0.67],[0.88,0.70],[0.84,0.72],[0.79,0.72],[0.74,0.70],
         [0.71,0.66],[0.70,0.60],[0.71,0.55]] },
  // ── Tasmania ────────────────────────────────────────────────────────────────
  { pts:[[0.83,0.73],[0.85,0.72],[0.86,0.75],[0.84,0.76]] },
  // ── New Zealand ─────────────────────────────────────────────────────────────
  { pts:[[0.94,0.65],[0.96,0.63],[0.97,0.66],[0.96,0.69],[0.94,0.68]] },
  { pts:[[0.93,0.70],[0.95,0.69],[0.96,0.72],[0.94,0.74],[0.92,0.72]] },
  // ── Antarctica ──────────────────────────────────────────────────────────────
  { pts:[[0.00,0.89],[0.10,0.87],[0.25,0.86],[0.40,0.87],[0.55,0.86],[0.70,0.87],
         [0.85,0.86],[1.00,0.87],[1.00,1.00],[0.00,1.00]] },
  // ── Russia (extends into Asia block but drawn separately for visual weight)
  { pts:[[0.54,0.06],[0.62,0.04],[0.70,0.03],[0.78,0.03],[0.86,0.04],[0.92,0.06],
         [0.96,0.09],[0.96,0.13],[0.92,0.15],[0.86,0.10],[0.78,0.08],[0.68,0.07],
         [0.60,0.07],[0.54,0.08]] },
];

// ── Major tech city dots [x, y, name] ────────────────────────────────────────
const CITIES: [number, number, string][] = [
  [0.10, 0.22, "San Francisco"],
  [0.14, 0.20, "Seattle"],
  [0.18, 0.23, "Austin"],
  [0.22, 0.19, "New York"],
  [0.41, 0.13, "London"],
  [0.47, 0.14, "Amsterdam"],
  [0.50, 0.15, "Berlin"],
  [0.53, 0.18, "Warsaw"],
  [0.58, 0.14, "Helsinki"],
  [0.63, 0.18, "Dubai"],
  [0.68, 0.32, "Bangalore"],
  [0.80, 0.23, "Beijing"],
  [0.83, 0.25, "Shanghai"],
  [0.88, 0.19, "Tokyo"],
  [0.85, 0.22, "Seoul"],
  [0.76, 0.45, "Singapore"],
  [0.81, 0.61, "Sydney"],
  [0.45, 0.37, "Lagos"],
  [0.50, 0.32, "Cairo"],
];

// ── Types ─────────────────────────────────────────────────────────────────────
interface Unit {
  id: number; x: number; y: number; vx: number; vy: number;
  faction: "llm" | "ai"; hp: number; maxHp: number; label: string;
  trail: Array<{x:number;y:number}>;
}
interface Missile {
  id: number; x: number; y: number; tx: number; ty: number;
  faction: "llm"|"ai"; progress: number; speed: number; label: string;
}
interface Explosion {
  id: number; x: number; y: number; radius: number; maxRadius: number; alpha: number;
  particles: Array<{x:number;y:number;vx:number;vy:number;life:number;color:string}>;
  nuke: boolean;
}
interface Territory { x:number;y:number;radius:number;faction:"llm"|"ai";alpha:number; }
interface Nation { x:number;y:number;name:string;faction:"llm"|"ai";age:number;maxAge:number; }
interface FrontLine { x1:number;y1:number;x2:number;y2:number;age:number; }
interface Bomber {
  id:number; x:number; y:number; vx:number; vy:number;
  faction:"llm"|"ai"; label:string; bombs:number; nextBomb:number;
}
interface Ship {
  id:number; x:number; y:number; vx:number; vy:number;
  faction:"llm"|"ai"; label:string; hp:number;
}
interface MushroomCloud {
  id:number; x:number; y:number; age:number; maxAge:number;
}

let uid = 0;
const nid = () => ++uid;

// ── Component ─────────────────────────────────────────────────────────────────
export function WorldWarBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;

    let raf: number;
    let W = 0, H = 0;
    let mapCanvas: HTMLCanvasElement | null = null;

    const units:         Unit[]          = [];
    const missiles:      Missile[]       = [];
    const explosions:    Explosion[]     = [];
    const territories:   Territory[]     = [];
    const nations:       Nation[]        = [];
    const frontLines:    FrontLine[]     = [];
    const bombers:       Bomber[]        = [];
    const ships:         Ship[]          = [];
    const mushrooms:     MushroomCloud[] = [];
    let frame = 0;
    let llmScore = 50, aiScore = 50;

    // ── Helpers ───────────────────────────────────────────────────────────────
    function glow(c: CanvasRenderingContext2D, x:number, y:number, r:number, color:string, alpha=1) {
      const g = c.createRadialGradient(x,y,0,x,y,r);
      const a = Math.round(alpha*255).toString(16).padStart(2,"0");
      g.addColorStop(0, `${color}${a}`);
      g.addColorStop(1, `${color}00`);
      c.fillStyle = g;
      c.beginPath(); c.arc(x,y,r,0,Math.PI*2); c.fill();
    }

    // ── Pre-render static map ─────────────────────────────────────────────────
    function buildMap() {
      mapCanvas = document.createElement("canvas");
      mapCanvas.width  = W;
      mapCanvas.height = H;
      const mc = mapCanvas.getContext("2d")!;

      // Ocean gradient
      const og = mc.createLinearGradient(0,0,0,H);
      og.addColorStop(0,   OCEAN_DEEP);
      og.addColorStop(0.5, OCEAN_MID);
      og.addColorStop(1,   OCEAN_DEEP);
      mc.fillStyle = og;
      mc.fillRect(0, 0, W, H);

      // Subtle ocean shimmer lines
      mc.strokeStyle = "rgba(15,40,80,0.3)";
      mc.lineWidth = 0.4;
      for (let y=0; y<H; y+=H/30) {
        mc.beginPath(); mc.moveTo(0,y); mc.bezierCurveTo(W*0.3,y+3,W*0.7,y-3,W,y); mc.stroke();
      }

      // Lat/lon grid
      mc.strokeStyle = "rgba(18,48,100,0.28)";
      mc.lineWidth = 0.5;
      for (let lat=0.05; lat<1; lat+=0.11) {
        mc.beginPath(); mc.moveTo(0,lat*H); mc.lineTo(W,lat*H); mc.stroke();
      }
      for (let lon=0; lon<=1.001; lon+=0.0556) {
        mc.beginPath(); mc.moveTo(lon*W,0); mc.lineTo(lon*W,H); mc.stroke();
      }
      // Equator — dashed, brighter
      mc.strokeStyle = "rgba(30,80,160,0.4)";
      mc.lineWidth = 1;
      mc.setLineDash([5,5]);
      mc.beginPath(); mc.moveTo(0,0.50*H); mc.lineTo(W,0.50*H); mc.stroke();
      mc.setLineDash([]);
      // Tropic of Cancer (0.38) & Capricorn (0.62)
      mc.strokeStyle = "rgba(20,60,120,0.25)";
      mc.setLineDash([3,8]);
      mc.beginPath(); mc.moveTo(0,0.38*H); mc.lineTo(W,0.38*H); mc.stroke();
      mc.beginPath(); mc.moveTo(0,0.62*H); mc.lineTo(W,0.62*H); mc.stroke();
      mc.setLineDash([]);

      // Continent shadows (slightly offset)
      mc.save();
      mc.translate(3, 4);
      for (const c of CONTINENTS) {
        mc.beginPath();
        mc.moveTo(c.pts[0][0]*W, c.pts[0][1]*H);
        for (let i=1;i<c.pts.length;i++) mc.lineTo(c.pts[i][0]*W, c.pts[i][1]*H);
        mc.closePath();
        mc.fillStyle = "rgba(0,5,20,0.6)";
        mc.fill();
      }
      mc.restore();

      // Continent fill with vertical gradient
      for (const c of CONTINENTS) {
        mc.beginPath();
        mc.moveTo(c.pts[0][0]*W, c.pts[0][1]*H);
        for (let i=1;i<c.pts.length;i++) mc.lineTo(c.pts[i][0]*W, c.pts[i][1]*H);
        mc.closePath();
        // gradient per continent
        const minY = Math.min(...c.pts.map(p=>p[1]));
        const maxY = Math.max(...c.pts.map(p=>p[1]));
        const fg = mc.createLinearGradient(0, minY*H, 0, maxY*H);
        fg.addColorStop(0,   LAND_BRIGHT);
        fg.addColorStop(0.5, LAND_FILL);
        fg.addColorStop(1,   LAND_FILL);
        mc.fillStyle = fg;
        mc.fill();
      }

      // Continent coast glow (double pass)
      mc.shadowColor = LAND_COAST;
      mc.shadowBlur  = 10;
      for (const c of CONTINENTS) {
        mc.beginPath();
        mc.moveTo(c.pts[0][0]*W, c.pts[0][1]*H);
        for (let i=1;i<c.pts.length;i++) mc.lineTo(c.pts[i][0]*W, c.pts[i][1]*H);
        mc.closePath();
        mc.strokeStyle = LAND_STROKE;
        mc.lineWidth = 1.2;
        mc.stroke();
      }
      mc.shadowBlur = 0;

      // Continent labels
      mc.font = "bold 9px monospace";
      mc.textAlign = "center";
      for (const c of CONTINENTS) {
        if (!c.label) continue;
        const lx = (c.lx ?? 0.5) * W;
        const ly = (c.ly ?? 0.5) * H;
        mc.fillStyle = "rgba(100,160,255,0.55)";
        mc.fillText(c.label, lx, ly);
      }
      mc.textAlign = "left";

      // City dots
      for (const [cx, cy, name] of CITIES) {
        const px = cx*W, py = cy*H;
        glow(mc, px, py, 9, "#4488ff", 0.18);
        mc.fillStyle = "#5599dd";
        mc.beginPath(); mc.arc(px, py, 2, 0, Math.PI*2); mc.fill();
        mc.fillStyle = "rgba(80,140,210,0.45)";
        mc.font = "5.5px monospace";
        mc.fillText(name, px+3, py-2);
      }
    }

    function resize() {
      W = canvas!.width  = canvas!.offsetWidth;
      H = canvas!.height = canvas!.offsetHeight;
      buildMap();
    }
    resize();
    window.addEventListener("resize", resize);

    // ── Spawn helpers ─────────────────────────────────────────────────────────
    function spawnUnit(faction:"llm"|"ai") {
      const isL = faction === "llm";
      const x   = isL ? (0.01+Math.random()*0.18)*W : (0.80+Math.random()*0.18)*W;
      const y   = (0.04+Math.random()*0.90)*H;
      const spd = 0.4+Math.random()*0.6;
      const ang = isL ? (-0.6+Math.random()*1.2) : (Math.PI+(-0.6+Math.random()*1.2));
      const pool = isL ? LLM_UNITS : AI_UNITS;
      units.push({ id:nid(), x, y, faction,
        vx:Math.cos(ang)*spd, vy:Math.sin(ang)*spd,
        hp:100, maxHp:100, trail:[],
        label: pool[Math.floor(Math.random()*pool.length)] });
    }

    function fireMissile(from:Unit, to:Unit) {
      missiles.push({ id:nid(), x:from.x, y:from.y, tx:to.x, ty:to.y,
        faction:from.faction, progress:0,
        speed:0.009+Math.random()*0.008, label:from.label });
    }

    function spawnBomber(faction:"llm"|"ai") {
      const isL = faction === "llm";
      // LLM bombers enter from left/top, AI bombers from right/top
      const x = isL ? -20 : W+20;
      const y = (0.05 + Math.random()*0.6)*H;
      const spd = 1.2 + Math.random()*0.8;
      const vx = isL ? spd : -spd;
      const vy = (Math.random()-0.5)*0.4;
      const pool = isL ? LLM_UNITS : AI_UNITS;
      bombers.push({ id:nid(), x, y, vx, vy,
        faction, bombs: 2+Math.floor(Math.random()*3),
        nextBomb: 60+Math.floor(Math.random()*80),
        label: pool[Math.floor(Math.random()*pool.length)] });
    }

    function spawnShip(faction:"llm"|"ai") {
      const isL = faction === "llm";
      // Ships sail in ocean areas (x between 0.28–0.38 = Atlantic, or 0.60–0.73 = Indian Ocean)
      const oceanX = Math.random() < 0.5
        ? (0.28 + Math.random()*0.10)*W   // Atlantic
        : (0.60 + Math.random()*0.12)*W;  // Indian Ocean
      const x = isL ? oceanX * 0.6 : oceanX;
      const y = (0.35 + Math.random()*0.35)*H;
      const spd = 0.18 + Math.random()*0.15;
      const vx = isL ? spd : -spd;
      const pool = isL ? LLM_UNITS : AI_UNITS;
      ships.push({ id:nid(), x, y, vx, vy:0,
        faction, label: pool[Math.floor(Math.random()*pool.length)], hp: 100 });
    }

    function drawBomber(bx:number, by:number, faction:"llm"|"ai", vx:number) {
      const col = faction==="llm" ? "#818CF8" : "#34D399";
      const dir = vx > 0 ? 1 : -1;
      ctx.save();
      ctx.translate(bx, by);
      ctx.scale(dir, 1);
      // Fuselage
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.ellipse(0, 0, 10, 3, 0, 0, Math.PI*2);
      ctx.fill();
      // Wings
      ctx.beginPath();
      ctx.moveTo(-4, 0); ctx.lineTo(-12, 5); ctx.lineTo(-2, 1);
      ctx.moveTo(-4, 0); ctx.lineTo(-12, -5); ctx.lineTo(-2, -1);
      ctx.fillStyle = col;
      ctx.fill();
      // Tail
      ctx.beginPath();
      ctx.moveTo(-8, 0); ctx.lineTo(-13, 3); ctx.lineTo(-10, 0);
      ctx.fill();
      ctx.restore();
      // Engine glow
      glow(ctx, bx, by, 12, col, 0.3);
    }

    function drawShip(sx:number, sy:number, faction:"llm"|"ai") {
      const col = faction==="llm" ? "#818CF8" : "#34D399";
      ctx.save();
      ctx.translate(sx, sy);
      // Hull
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.moveTo(-10, 2); ctx.lineTo(10, 2); ctx.lineTo(8, 5); ctx.lineTo(-8, 5);
      ctx.closePath(); ctx.fill();
      // Superstructure
      ctx.fillRect(-4, -2, 7, 4);
      // Mast
      ctx.strokeStyle = col; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(0, -2); ctx.lineTo(0, -7); ctx.stroke();
      ctx.restore();
      glow(ctx, sx, sy, 8, col, 0.25);
    }

    function boom(x:number, y:number, faction:"llm"|"ai", big=false) {
      const mc2 = faction==="llm" ? "#818CF8" : "#34D399";
      territories.push({ x, y, radius:0, faction, alpha:big?0.45:0.32 });
      const nuke = big || Math.random() < 0.10;
      if (nuke) mushrooms.push({ id:nid(), x, y, age:0, maxAge:180 });
      explosions.push({ id:nid(), x, y, radius:4, maxRadius:(nuke?60:30)+Math.random()*20, alpha:1, nuke,
        particles: Array.from({length: nuke?40:20}, () => {
          const a=Math.random()*Math.PI*2, s=(nuke?2:1.5)+Math.random()*3;
          return { x, y, vx:Math.cos(a)*s, vy:Math.sin(a)*s, life:1,
            color:Math.random()>0.5?mc2:Math.random()>0.5?"#FCD34D":"#fb923c" };
        })
      });
      // Spawn front line
      if (Math.random() < 0.3) {
        const a = Math.random()*Math.PI*2;
        frontLines.push({ x1:x, y1:y, x2:x+Math.cos(a)*80, y2:y+Math.sin(a)*80, age:0 });
      }
    }

    // Init
    for (let i=0;i<11;i++) spawnUnit("llm");
    for (let i=0;i<11;i++) spawnUnit("ai");
    for (let i=0;i<2;i++)  spawnBomber("llm");
    for (let i=0;i<2;i++)  spawnBomber("ai");
    for (let i=0;i<3;i++)  spawnShip("llm");
    for (let i=0;i<3;i++)  spawnShip("ai");

    // ── Main loop ─────────────────────────────────────────────────────────────
    function loop() {
      frame++;

      // Blit pre-rendered map
      if (mapCanvas) ctx.drawImage(mapCanvas, 0, 0);

      // ── Territories ───────────────────────────────────────────────────────
      for (let i=territories.length-1;i>=0;i--) {
        const t=territories[i];
        t.radius = Math.min(t.radius+0.3, 70);
        if (t.radius>=70) t.alpha = Math.max(t.alpha-0.0006, 0.02);
        glow(ctx, t.x, t.y, t.radius, t.faction==="llm"?"#6366f1":"#10b981", t.alpha);
        if (t.alpha<=0.02) territories.splice(i,1);
      }

      // ── Ambient side gradient overlays ────────────────────────────────────
      const lG=ctx.createLinearGradient(0,0,W*0.28,0);
      lG.addColorStop(0,"rgba(99,102,241,0.12)"); lG.addColorStop(1,"transparent");
      ctx.fillStyle=lG; ctx.fillRect(0,0,W*0.28,H);
      const rG=ctx.createLinearGradient(W,0,W*0.72,0);
      rG.addColorStop(0,"rgba(16,185,129,0.12)"); rG.addColorStop(1,"transparent");
      ctx.fillStyle=rG; ctx.fillRect(W*0.72,0,W*0.28,H);

      // ── Front lines ───────────────────────────────────────────────────────
      for (let i=frontLines.length-1;i>=0;i--) {
        const f=frontLines[i]; f.age++;
        const al = f.age<20 ? f.age/20 : Math.max(1-(f.age-20)/80, 0);
        ctx.strokeStyle=`rgba(252,211,77,${al*0.4})`;
        ctx.lineWidth=1.5; ctx.setLineDash([4,4]);
        ctx.beginPath(); ctx.moveTo(f.x1,f.y1); ctx.lineTo(f.x2,f.y2); ctx.stroke();
        ctx.setLineDash([]);
        if (al<=0) frontLines.splice(i,1);
      }

      // ── Mushroom clouds ───────────────────────────────────────────────────
      for (let i=mushrooms.length-1;i>=0;i--) {
        const mc=mushrooms[i]; mc.age++;
        const p=mc.age/mc.maxAge;
        const al=p<0.15?p/0.15:p>0.7?1-(p-0.7)/0.3:1;
        const stemH=Math.min(mc.age*0.9,55);
        const capR=Math.min(mc.age*0.6,35);
        ctx.globalAlpha=al*0.6;
        // Stem
        ctx.strokeStyle="#fb923c"; ctx.lineWidth=6;
        ctx.beginPath(); ctx.moveTo(mc.x,mc.y); ctx.lineTo(mc.x,mc.y-stemH); ctx.stroke();
        // Cap
        ctx.fillStyle="rgba(251,146,60,0.5)";
        ctx.beginPath(); ctx.arc(mc.x,mc.y-stemH,capR,Math.PI,0); ctx.fill();
        // Inner cap
        ctx.fillStyle="rgba(252,211,77,0.6)";
        ctx.beginPath(); ctx.arc(mc.x,mc.y-stemH,capR*0.55,Math.PI,0); ctx.fill();
        // Glow
        ctx.globalAlpha=1;
        glow(ctx, mc.x, mc.y-stemH, capR*1.5, "#ff6600", al*0.4);
        if (mc.age>=mc.maxAge) mushrooms.splice(i,1);
      }

      // ── Bombers ───────────────────────────────────────────────────────────
      for (let i=bombers.length-1;i>=0;i--) {
        const b=bombers[i];
        b.x+=b.vx; b.y+=b.vy;
        b.nextBomb--;

        // Drop bomb on an enemy unit below
        if (b.nextBomb<=0 && b.bombs>0) {
          b.nextBomb=50+Math.floor(Math.random()*80);
          b.bombs--;
          // Find nearest enemy unit below bomber
          const enemies=units.filter(u=>u.faction!==b.faction&&Math.abs(u.x-b.x)<W*0.25);
          const target=enemies.length>0
            ? enemies.reduce((a,c)=>Math.abs(c.x-b.x)<Math.abs(a.x-b.x)?c:a)
            : null;
          const tx=target?target.x : b.x+(Math.random()-0.5)*80;
          const ty=target?target.y : b.y+80+Math.random()*60;
          missiles.push({ id:nid(), x:b.x, y:b.y, tx, ty,
            faction:b.faction, progress:0, speed:0.018, label:"💣" });
        }

        // Draw bomber
        drawBomber(b.x, b.y, b.faction, b.vx);
        // Label
        ctx.textAlign="center"; ctx.font="6px monospace";
        ctx.fillStyle=b.faction==="llm"?"rgba(196,181,253,0.8)":"rgba(110,231,183,0.8)";
        ctx.fillText(b.label, b.x, b.y-16);
        ctx.fillText(`💣×${b.bombs}`, b.x, b.y-10);
        ctx.textAlign="left";

        // Off-screen → remove or respawn
        if (b.x<-60 || b.x>W+60) {
          bombers.splice(i,1);
        }
      }
      // Spawn new bomber periodically
      if (frame%220===0  && bombers.filter(b=>b.faction==="llm").length<4) spawnBomber("llm");
      if (frame%220===110 && bombers.filter(b=>b.faction==="ai").length<4)  spawnBomber("ai");

      // ── Ships ─────────────────────────────────────────────────────────────
      for (let i=ships.length-1;i>=0;i--) {
        const s=ships[i];
        s.x+=s.vx;
        // Slight wave bobbing
        s.y+=Math.sin(frame*0.03+s.id)*0.12;

        // Ship fires at enemies
        if (frame%60===(s.id%60)) {
          const enemies=units.filter(u=>u.faction!==s.faction&&Math.hypot(u.x-s.x,u.y-s.y)<W*0.35);
          if (enemies.length) {
            const nearest=enemies.reduce((a,c)=>Math.hypot(c.x-s.x,c.y-s.y)<Math.hypot(a.x-s.x,a.y-s.y)?c:a);
            missiles.push({ id:nid(), x:s.x, y:s.y-5, tx:nearest.x, ty:nearest.y,
              faction:s.faction, progress:0, speed:0.012, label:s.label });
          }
        }

        drawShip(s.x, s.y, s.faction);
        // Ship name
        ctx.textAlign="center"; ctx.font="6px monospace";
        ctx.fillStyle=s.faction==="llm"?"rgba(196,181,253,0.7)":"rgba(110,231,183,0.7)";
        ctx.fillText(s.label, s.x, s.y-10);
        ctx.textAlign="left";

        if (s.x<-40 || s.x>W+40) ships.splice(i,1);
      }
      if (frame%300===0   && ships.filter(s=>s.faction==="llm").length<5) spawnShip("llm");
      if (frame%300===150 && ships.filter(s=>s.faction==="ai").length<5)  spawnShip("ai");

      // ── Spawn ground units ────────────────────────────────────────────────
      if (frame%70===0  && units.filter(u=>u.faction==="llm").length<16) spawnUnit("llm");
      if (frame%70===35 && units.filter(u=>u.faction==="ai").length<16)  spawnUnit("ai");

      // ── Units ─────────────────────────────────────────────────────────────
      for (let i=units.length-1;i>=0;i--) {
        const u=units[i];
        // Steer toward center
        const cx=W*0.5, cy=H*0.5;
        const dx=cx-u.x, dy=cy-u.y;
        const d=Math.hypot(dx,dy);
        if (d>W*0.45) { u.vx+=dx/d*0.06; u.vy+=dy/d*0.06; }

        u.x+=u.vx; u.y+=u.vy;
        if (u.x<4)  u.vx= Math.abs(u.vx);
        if (u.x>W-4)u.vx=-Math.abs(u.vx);
        if (u.y<4)  u.vy= Math.abs(u.vy);
        if (u.y>H-4)u.vy=-Math.abs(u.vy);
        // Speed cap
        const spd=Math.hypot(u.vx,u.vy);
        if (spd>1.2) { u.vx*=1.2/spd; u.vy*=1.2/spd; }

        u.trail.push({x:u.x,y:u.y});
        if (u.trail.length>18) u.trail.shift();

        // Trail
        for (let t=0;t<u.trail.length-1;t++) {
          const a = t/u.trail.length*0.4;
          ctx.strokeStyle = u.faction==="llm"
            ? `rgba(129,140,248,${a})`
            : `rgba(52,211,153,${a})`;
          ctx.lineWidth=1.5;
          ctx.beginPath(); ctx.moveTo(u.trail[t].x,u.trail[t].y);
          ctx.lineTo(u.trail[t+1].x,u.trail[t+1].y); ctx.stroke();
        }

        // Glow ring
        glow(ctx, u.x, u.y, 18, u.faction==="llm"?"#818cf8":"#34d399", 0.50);
        glow(ctx, u.x, u.y, 7,  u.faction==="llm"?"#a78bfa":"#6ee7b7", 0.85);
        ctx.fillStyle = u.faction==="llm" ? "#c4b5fd" : "#6ee7b7";
        ctx.beginPath(); ctx.arc(u.x,u.y,3,0,Math.PI*2); ctx.fill();

        // Label
        ctx.textAlign="center";
        ctx.font="bold 7px monospace";
        ctx.fillStyle = u.faction==="llm" ? "rgba(196,181,253,0.95)" : "rgba(110,231,183,0.95)";
        ctx.fillText(u.label, u.x, u.y-16);

        // HP bar
        const bW=26;
        ctx.fillStyle="rgba(0,0,0,0.6)"; ctx.fillRect(u.x-bW/2, u.y-11, bW, 3);
        const hpColor = u.hp>60 ? (u.faction==="llm"?"#818CF8":"#34D399") : u.hp>30?"#FCD34D":"#ef4444";
        ctx.fillStyle=hpColor;
        ctx.fillRect(u.x-bW/2, u.y-11, bW*(u.hp/u.maxHp), 3);
        ctx.textAlign="left";

        // Fire missile
        if (frame%35===(u.id%35)) {
          const enemies=units.filter(e=>e.faction!==u.faction);
          if (enemies.length) {
            const nearest=enemies.reduce((b,e)=>
              Math.hypot(e.x-u.x,e.y-u.y)<Math.hypot(b.x-u.x,b.y-u.y)?e:b);
            if (Math.hypot(nearest.x-u.x,nearest.y-u.y)<W*0.5) fireMissile(u,nearest);
          }
        }

        if (u.hp<=0) {
          boom(u.x, u.y, u.faction==="llm"?"ai":"llm");
          if (u.faction==="llm") aiScore=Math.min(aiScore+2,99);
          else                   llmScore=Math.min(llmScore+2,99);
          units.splice(i,1);
        }
      }

      // ── Missiles ──────────────────────────────────────────────────────────
      for (let i=missiles.length-1;i>=0;i--) {
        const m=missiles[i];
        m.progress = Math.min(m.progress+m.speed, 1);
        const arc = Math.sin(m.progress*Math.PI)*35;
        const midX=(m.x+m.tx)/2, midY=(m.y+m.ty)/2-arc;
        const t=m.progress;
        const cx=(1-t)*(1-t)*m.x+2*(1-t)*t*midX+t*t*m.tx;
        const cy=(1-t)*(1-t)*m.y+2*(1-t)*t*midY+t*t*m.ty;

        // Missile trail (draw from origin to current)
        ctx.beginPath();
        ctx.strokeStyle = m.faction==="llm"
          ? `rgba(167,139,250,${0.8-m.progress*0.6})`
          : `rgba(52,211,153,${0.8-m.progress*0.6})`;
        ctx.lineWidth=1.5;
        ctx.shadowColor = m.faction==="llm" ? "#818CF8" : "#34D399";
        ctx.shadowBlur=6;
        ctx.moveTo(m.x,m.y);
        ctx.quadraticCurveTo(midX,midY,cx,cy);
        ctx.stroke();
        ctx.shadowBlur=0;

        // Missile head glow
        glow(ctx, cx, cy, 10, m.faction==="llm"?"#a78bfa":"#34d399", 0.95);
        ctx.fillStyle = m.faction==="llm" ? "#c4b5fd" : "#6ee7b7";
        ctx.beginPath(); ctx.arc(cx,cy,2.5,0,Math.PI*2); ctx.fill();

        // Mid-flight label
        if (m.progress>0.30 && m.progress<0.70) {
          ctx.textAlign="center";
          ctx.font="6px monospace";
          ctx.fillStyle=m.faction==="llm"?"rgba(167,139,250,0.8)":"rgba(52,211,153,0.8)";
          ctx.fillText(m.label, cx, cy-11);
          ctx.textAlign="left";
        }

        if (m.progress>=1) {
          const tgt=units.find(u=>u.faction!==m.faction&&Math.hypot(u.x-m.tx,u.y-m.ty)<30);
          if (tgt) { tgt.hp-=20+Math.random()*25; }
          boom(m.tx, m.ty, m.faction);
          missiles.splice(i,1);
        }
      }

      // ── Explosions ────────────────────────────────────────────────────────
      for (let i=explosions.length-1;i>=0;i--) {
        const e=explosions[i];
        e.radius=Math.min(e.radius+2.5,e.maxRadius);
        e.alpha=Math.max(e.alpha-0.018,0);

        // Nuke flash
        if (e.nuke && e.alpha>0.8) {
          ctx.fillStyle = `rgba(255,255,200,${(e.alpha-0.8)*2*0.4})`;
          ctx.fillRect(0,0,W,H);
        }

        // Rings
        for (let r=0;r<3;r++) {
          ctx.beginPath();
          ctx.arc(e.x, e.y, e.radius*(0.4+r*0.3), 0, Math.PI*2);
          const ringColor = e.alpha>0.5
            ? `rgba(252,211,77,${e.alpha*(1-r*0.3)})`
            : `rgba(251,146,60,${e.alpha*(1-r*0.3)})`;
          ctx.strokeStyle=ringColor;
          ctx.lineWidth=2.5-r*0.5;
          ctx.shadowColor="#FCD34D"; ctx.shadowBlur=10;
          ctx.stroke(); ctx.shadowBlur=0;
        }
        if (e.alpha>0.45) glow(ctx, e.x, e.y, e.radius*0.8, "#ffdd44", e.alpha*0.55);

        // Smoke column for nukes
        if (e.nuke && e.radius>20) {
          const sh = e.radius * 1.5;
          ctx.beginPath();
          ctx.moveTo(e.x-8,e.y);
          ctx.quadraticCurveTo(e.x-4,e.y-sh*0.5, e.x,e.y-sh);
          ctx.quadraticCurveTo(e.x+6,e.y-sh*0.5, e.x+8,e.y);
          ctx.strokeStyle=`rgba(180,100,20,${e.alpha*0.35})`;
          ctx.lineWidth=8;
          ctx.stroke();
        }

        // Particles
        for (const p of e.particles) {
          p.x+=p.vx; p.y+=p.vy;
          p.vx*=0.93; p.vy*=0.93; p.vy+=0.04; // gravity
          p.life=Math.max(p.life-0.020,0);
          ctx.globalAlpha=p.life;
          ctx.fillStyle=p.color;
          ctx.beginPath(); ctx.arc(p.x,p.y,2.2,0,Math.PI*2); ctx.fill();
          ctx.globalAlpha=1;
        }

        if (e.alpha<=0) {
          if (e.maxRadius>40 && Math.random()<0.45) {
            const f=Math.random()<0.5?"llm":"ai";
            const pool=f==="llm"?LLM_NATIONS:AI_NATIONS;
            nations.push({ x:e.x, y:e.y, faction:f, age:0, maxAge:340,
              name:pool[Math.floor(Math.random()*pool.length)] });
          }
          explosions.splice(i,1);
        }
      }

      // ── Nations (rising flags) ────────────────────────────────────────────
      for (let i=nations.length-1;i>=0;i--) {
        const n=nations[i]; n.age++;
        const p=n.age/n.maxAge;
        const al=p<0.12 ? p/0.12 : p>0.80 ? 1-(p-0.80)/0.20 : 1;
        const col=n.faction==="llm"?"#818CF8":"#34D399";
        ctx.globalAlpha=al;
        // Flag pole
        ctx.strokeStyle=col; ctx.lineWidth=1.5;
        ctx.beginPath(); ctx.moveTo(n.x,n.y); ctx.lineTo(n.x,n.y-24); ctx.stroke();
        // Flag rectangle
        ctx.fillStyle=col;
        ctx.fillRect(n.x, n.y-24, 12, 8);
        // Flag text (abbreviated)
        ctx.font="bold 5px monospace"; ctx.textAlign="left";
        ctx.fillStyle="#ffffff";
        ctx.fillText(n.name.slice(0,3), n.x+1, n.y-18);
        // Full name above
        ctx.font="bold 8px monospace"; ctx.textAlign="center";
        ctx.fillStyle="#ffffff";
        ctx.shadowColor=col; ctx.shadowBlur=7;
        ctx.fillText(n.name, n.x+6, n.y-30);
        ctx.shadowBlur=0; ctx.textAlign="left";
        ctx.globalAlpha=1;
        if (n.age>=n.maxAge) nations.splice(i,1);
      }

      // ── Score bar ─────────────────────────────────────────────────────────
      const bY=H-22, bX=W*0.24, bW=W*0.52, bH=7;
      ctx.fillStyle="rgba(0,0,0,0.65)";
      ctx.beginPath();
      (ctx as CanvasRenderingContext2D & {roundRect:Function}).roundRect(bX-3,bY-3,bW+6,bH+6,5);
      ctx.fill();
      // LLM side
      const llmW=(llmScore/100)*bW;
      const llmG=ctx.createLinearGradient(bX,0,bX+llmW,0);
      llmG.addColorStop(0,"#4f46e5"); llmG.addColorStop(1,"#818CF8");
      ctx.fillStyle=llmG; ctx.fillRect(bX,bY,llmW,bH);
      // AI side
      const aiW=(aiScore/100)*bW;
      const aiG=ctx.createLinearGradient(bX+llmW,0,bX+llmW+aiW,0);
      aiG.addColorStop(0,"#10b981"); aiG.addColorStop(1,"#34D399");
      ctx.fillStyle=aiG; ctx.fillRect(bX+llmW,bY,aiW,bH);
      // Score border
      ctx.strokeStyle="rgba(255,255,255,0.15)"; ctx.lineWidth=0.5;
      ctx.strokeRect(bX,bY,bW,bH);
      // Labels
      ctx.font="bold 10px monospace";
      ctx.fillStyle="#818CF8";
      ctx.fillText(`LLM ${llmScore}%`, bX-62, bY+6);
      ctx.fillStyle="#34D399";
      const aiLabel=`AI ${aiScore}%`;
      ctx.fillText(aiLabel, bX+bW+8, bY+6);

      // ── Side army labels ──────────────────────────────────────────────────
      ctx.font="bold 10px monospace";
      ctx.shadowColor="#6366f1"; ctx.shadowBlur=8;
      ctx.fillStyle="rgba(129,140,248,0.55)"; ctx.fillText("◄ LLM ORDUSU",8,H/2-10);
      ctx.shadowBlur=0;
      ctx.font="7px monospace";
      ctx.fillStyle="rgba(129,140,248,0.30)"; ctx.fillText("GPT·Claude·Gemini·Llama",8,H/2+5);
      ctx.font="bold 10px monospace";
      ctx.shadowColor="#10b981"; ctx.shadowBlur=8;
      ctx.fillStyle="rgba(52,211,153,0.55)";
      const tr="TEST ORDUSU ►";
      ctx.fillText(tr,W-ctx.measureText(tr).width-8,H/2-10);
      ctx.shadowBlur=0;
      ctx.font="7px monospace";
      ctx.fillStyle="rgba(52,211,153,0.30)";
      const sr="Playwright·Selenium·Cypress";
      ctx.fillText(sr,W-ctx.measureText(sr).width-8,H/2+5);

      raf=requestAnimationFrame(loop);
    }

    loop();
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize",resize); };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full"
    />
  );
}
