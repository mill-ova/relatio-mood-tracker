#!/usr/bin/env python3
"""
Збирає mood-animation-preview.html з SVG-експортів Figma (_Mood Asset, 5 настроїв x Dark/Light).

Розкрій шарів (index-based, однаковий у всіх 5 настроїв):
    0..2    -> g.glow          (глоу + form glow)
    3..12   -> g.petals > g.petalsInner > g.ring ringN  (2-2-3-3, як у погодженій версії:
               ring3 забирає ядро — саме тому bloom Pleasant читається як розкриття всієї квітки)
    13..24  -> g.core          (play-of-color, віяло, обличчя)
    defs    -> лишається як є

Квірки (перевірені 2026-07-31, лишаються чинними):
  * Angular gradient («Core fan») експортується як foreignObject із самозакритим <div/>.
    HTML-парсер НЕ закриває його і з'їдає решту документа -> примусово закриваємо тег.
  * Idle-трансформи ТІЛЬКИ на внутрішніх групах; корінь SVG статичний, інакше Chrome
    растеризує композитний шар один раз і блюрені риси обличчя «змиваються».
  * Ніякої ET-серіалізації: правки роблю рядковою хірургією, щоб не зачепити ні
    foreignObject, ні порядок атрибутів.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "mood-animation-preview.html")

# key, підпис, десинхрон тривалості (x базовий цикл), фазовий зсув (x базовий цикл)
MOODS = [
    ("sad",        "Sad",        1.00,  0.00),
    ("unpleasant", "Unpleasant", 1.09, -0.33),
    ("neutral",    "Neutral",    0.96, -0.65),
    ("pleasant",   "Pleasant",   1.15, -0.22),
    ("happy",      "Happy",      1.04, -0.50),
]

SCALE = 72 / 56          # асет 56 px рендериться у чіпі 72 px
RINGS = [2, 2, 3, 3]     # розподіл елементів 3..12 по кільцях пелюсток


# --------------------------------------------------------------------------- SVG

def top_level_spans(svg: str):
    """Межі дітей кореневого <svg> у сирому тексті: [(start, end, tag), ...]."""
    body_start = svg.index(">", svg.index("<svg")) + 1
    body_end = svg.rindex("</svg>")
    i, depth, spans, cur = body_start, 0, [], None
    while i < body_end:
        if svg[i] != "<":
            i += 1
            continue
        if svg.startswith("<!--", i):
            i = svg.index("-->", i) + 3
            continue
        j = i
        in_str = None
        while j < len(svg):
            c = svg[j]
            if in_str:
                if c == in_str:
                    in_str = None
            elif c in "\"'":
                in_str = c
            elif c == ">":
                break
            j += 1
        tag_text = svg[i:j + 1]
        closing = tag_text.startswith("</")
        selfclose = tag_text.endswith("/>")
        name = re.match(r"</?\s*([A-Za-z0-9:_-]+)", tag_text).group(1)
        if closing:
            depth -= 1
            if depth == 0 and cur is not None:
                spans.append((cur[0], j + 1, cur[1]))
                cur = None
        elif selfclose:
            if depth == 0:
                spans.append((i, j + 1, name))
        else:
            if depth == 0:
                cur = (i, name)
            depth += 1
        i = j + 1
    return spans


def close_foreign_divs(svg: str) -> str:
    """<div .../>  ->  <div ...></div> (інакше HTML-парсер з'їдає документ)."""
    return re.sub(r"<div\b([^>]*?)\s*/>", r"<div\1></div>", svg)


def prepare_svg(path: str) -> str:
    raw = open(path, encoding="utf-8").read()
    raw = close_foreign_divs(raw)

    head = raw[:raw.index(">", raw.index("<svg")) + 1]
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head)
    w, h = float(vb.group(1)), float(vb.group(2))
    head = re.sub(r'\swidth="[^"]*"', "", head)
    head = re.sub(r'\sheight="[^"]*"', "", head)
    head = head.replace(
        "<svg",
        '<svg xmlns:html="http://www.w3.org/1999/xhtml" '
        f'width="{round(w * SCALE)}" height="{round(h * SCALE)}"',
        1,
    ).replace(">", ' class="mood-svg">', 1) if 'class=' not in head else head

    spans = top_level_spans(raw)
    content = [raw[a:b] for a, b, t in spans if t != "defs"]
    defs = "".join(raw[a:b] for a, b, t in spans if t == "defs")
    if len(content) != 25:
        raise SystemExit(f"{os.path.basename(path)}: очікую 25 елементів + defs, а не {len(content)}")

    glow = "".join(content[0:3])
    petals, k = [], 3
    for n in RINGS:
        petals.append("".join(content[k:k + n]))
        k += n
    core = "".join(content[13:25])

    rings = "".join(f'<g class="ring ring{i}">{p}</g>' for i, p in enumerate(petals))
    return (
        f"{head}"
        f'<g class="glow">{glow}</g>'
        f'<g class="petals"><g class="petalsInner">{rings}</g></g>'
        f'<g class="core">{core}</g>'
        f"{defs}</svg>"
    )


# -------------------------------------------------------------------------- HTML

CSS = """
  :root { --amp: 1.03; --gmin: .80; }
  body { margin:0; font-family:Poppins,sans-serif; background:#f7f7f7; color:#0d0d0d; display:flex; flex-direction:column; align-items:center; padding:32px 16px; }
  h1 { font-size:20px; font-weight:600; margin:0 0 4px; }
  .sub { font-size:13px; color:#6b6b6b; margin:0 0 24px; text-align:center; max-width:640px; line-height:1.5; }
  .wrap { display:flex; gap:24px; align-items:flex-start; flex-wrap:wrap; justify-content:center; }
  .panel { display:flex; flex-direction:column; gap:10px; min-width:230px; max-width:270px; }
  .panel span.h { font-size:13px; color:#6b6b6b; margin-top:6px; }
  .panel .row { display:flex; gap:6px; flex-wrap:wrap; }
  .panel .row button { flex:0 0 auto; }
  button { font-family:Poppins,sans-serif; font-size:13px; font-weight:500; padding:8px 13px; border-radius:999px; border:1px solid #e2e2e2; background:#fff; cursor:pointer; }
  button:hover { background:#f2f2f2; }
  button.on { background:#0d0d0d; color:#fff; border-color:#0d0d0d; }
  label { display:flex; align-items:center; gap:8px; font-size:13px; color:#444; }
  .note { font-size:12px; color:#8a8a8a; line-height:1.5; margin-top:4px; }
  .spec { font-size:12px; color:#8a8a8a; line-height:1.7; margin-top:24px; max-width:640px; }
  .spec b { color:#444; font-weight:600; }

  #phone { position:relative; width:440px; height:640px; border-radius:48px; overflow:hidden; background:#0A0B0D; box-shadow:0 12px 40px rgba(0,0,0,.2); flex:0 0 auto; }
  #island { position:absolute; top:14px; left:50%; transform:translateX(-50%); width:110px; height:30px; border-radius:18px; background:#000; }

  .card { position:absolute; left:16px; right:16px; top:96px; border-radius:28px; padding:20px 16px 24px; background:rgba(255,255,255,.055); border:1px solid rgba(255,255,255,.05); box-sizing:border-box; }
  .card .head { display:flex; justify-content:space-between; align-items:center; padding:0 4px; }
  .card .ttl { font-size:19px; font-weight:600; color:#F2F3F5; letter-spacing:.1px; }
  .card .jrn { font-size:15px; font-weight:500; color:#8F7DFF; display:flex; align-items:center; gap:4px; cursor:pointer; }
  .card .dsc { font-size:14px; color:#9BA0A8; margin:4px 4px 18px; }
  .moods { display:flex; justify-content:space-between; }

  .chip { position:relative; width:76px; display:flex; flex-direction:column; align-items:center; cursor:pointer; -webkit-tap-highlight-color:transparent; user-select:none; }
  .chip .icon { position:relative; width:72px; height:72px; display:flex; align-items:center; justify-content:center; }
  .chip .icon svg { overflow:visible; display:block; flex:0 0 auto; transform-origin:center; }
  .chip .lbl { margin-top:14px; font-size:13px; color:#D6D8DC; }
  .chip .icon-light { display:none; }
  body.light .chip .icon-light { display:flex; }
  body.light .chip .icon-dark { display:none; }

  /* світла тема: bg/default молочно-блакитний, картка bg/secondary біла на м'якій тіні */
  body.light #phone { background:#F6F7FB; }
  body.light .card { background:#FFFFFF; border-color:rgba(255,255,255,.6);
       box-shadow:0 18px 50px rgba(60,70,110,.12), 0 2px 8px rgba(60,70,110,.05); }
  body.light .card .ttl { color:#17181B; }
  body.light .card .dsc { color:#6E737C; }
  body.light .card .jrn { color:#5A4FD6; }
  body.light .card .jrn svg path { stroke:#5A4FD6; }
  body.light .chip .lbl { color:#1E2126; }
  body.light .ghost { background:#FFFFFF; box-shadow:0 12px 34px rgba(60,70,110,.08); }
  body.light #screen2 { background:#F6F7FB; }
  body.light #screen2 .s2title { color:#17181B; }
  body.light #screen2 .s2sub { color:#6E737C; }
  body.light #screen2 .s2pills span { background:#FFFFFF; border-color:rgba(60,70,110,.08); color:#3A3E45;
       box-shadow:0 4px 14px rgba(60,70,110,.06); }
  body.light #screen2 .backBtn { background:#FFFFFF; border-color:rgba(60,70,110,.08); color:#17181B;
       box-shadow:0 4px 14px rgba(60,70,110,.08); }
  .chip .fx { position:absolute; left:50%; top:36px; width:0; height:0; pointer-events:none; }

  /* idle: усі трансформи всередині SVG (вектор, без растеризації) — обличчя лишається чітким */
  .glow, .petals, .petalsInner, .core, .petalsInner > g.ring { transform-box:fill-box; transform-origin:center; }
  .glow { animation: glowIdle var(--bd,4s) ease-in-out infinite; animation-delay: var(--d,0s); }
  .petals { animation: breatheG var(--bd,4s) ease-in-out infinite; animation-delay: var(--d,0s); }
  .petalsInner { animation: sway calc(var(--bd,4s)*1.8) ease-in-out infinite; animation-delay: calc(var(--d,0s)*1.8); }
  .core { animation: breatheCore var(--bd,4s) ease-in-out infinite; animation-delay: var(--d,0s); }

  body.reduced .petals, body.reduced .petalsInner, body.reduced .core { animation:none; }
  body.reduced .glow { animation-name: glowPulse; }

  @keyframes glowIdle { 0%,100% { opacity:var(--gmin,.8); transform:scale(1); } 50% { opacity:1; transform:scale(var(--amp)); } }
  @keyframes breatheG { 0%,100% { transform:scale(1); } 50% { transform:scale(var(--amp)); } }
  @keyframes breatheCore { 0%,100% { transform:scale(1); } 50% { transform:scale(calc(1 + (var(--amp,1.03) - 1)*0.55)); } }
  @keyframes glowPulse { 0%,100% { opacity:var(--gmin,.8); } 50% { opacity:1; } }
  @keyframes sway { 0%,100% { transform:rotate(-1.6deg); } 50% { transform:rotate(1.6deg); } }

  .ghost { position:absolute; left:16px; right:16px; height:110px; border-radius:28px; background:rgba(255,255,255,.04); transition:opacity .3s; }

  /* екран опшенів після тапу — iOS push slide-in */
  #screen2 { position:absolute; inset:0; background:#0A0B0D; transform:translateX(100%);
       transition:transform .42s cubic-bezier(.32,.72,.28,1); pointer-events:none; z-index:30; }
  #screen2.show { transform:translateX(0); pointer-events:auto; }
  #screen2 .backBtn { position:absolute; top:62px; left:20px; width:38px; height:38px; border-radius:50%;
       background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.07); color:#F2F3F5;
       display:flex; align-items:center; justify-content:center; font-size:20px; cursor:pointer; }
  #screen2 .s2title { position:absolute; top:140px; left:32px; right:32px; text-align:center;
       font-size:23px; font-weight:600; color:#F2F3F5; line-height:1.3; }
  #screen2 .s2sub { position:absolute; top:208px; left:32px; right:32px; text-align:center; font-size:14px; color:#9BA0A8; }
  #screen2 .s2pills { position:absolute; top:262px; left:24px; right:24px; display:flex; flex-wrap:wrap; gap:10px; justify-content:center; }
  #screen2 .s2pills span { padding:12px 20px; border-radius:999px; background:rgba(255,255,255,.07);
       border:1px solid rgba(255,255,255,.06); font-size:14px; color:#D6D8DC; }
  #screen2 .s2cta { position:absolute; bottom:44px; left:56px; right:56px; height:56px; border-radius:999px;
       background:#5A4FD6; color:#fff; font-size:16px; font-weight:600; display:flex; align-items:center; justify-content:center; }

  .ripple { position:absolute; left:0; top:0; border:1.5px solid rgba(127,217,217,.65); border-radius:50%; transform:translate(-50%,-50%); }
  .spark { position:absolute; left:0; top:0; width:5px; height:5px; border-radius:50%; transform:translate(-50%,-50%); }
  .spark.star { background:none; width:auto; height:auto; line-height:1; font-family:sans-serif; }
"""

JS = r"""
const SPEED = { v: 1 };
const BASE = { v: 4 };

function applyIdle() {
  const unison = document.getElementById('unison').checked;
  document.querySelectorAll('.chip').forEach(chip => {
    const dm = parseFloat(chip.dataset.dm), dl = parseFloat(chip.dataset.dl);
    const bd = unison ? BASE.v : BASE.v * dm;
    const d  = unison ? 0 : BASE.v * dl;
    chip.style.setProperty('--bd', bd + 's');
    chip.style.setProperty('--d', d + 's');
  });
}

function seq(el, frames, opts) {
  return el.animate(frames, Object.assign({}, opts, { duration: opts.duration * SPEED.v }));
}

const running = new Map(); // chip -> active animations

function stopRunning(chip) {
  (running.get(chip) || []).forEach(a => { try { a.cancel(); } catch(e){} });
  running.set(chip, []);
}
function track(chip, anim) {
  if (!running.has(chip)) running.set(chip, []);
  running.get(chip).push(anim);
  return anim;
}

function sparkles(chip) {
  const fx = chip.querySelector('.fx');
  const colors = FX.sparks();
  const N = 12; // дві хвилі: 7 ближніх + 5 дальніх
  for (let i = 0; i < N; i++) {
    const wave = i < 7 ? 0 : 1;
    const star = i % 3 !== 0; // більшість — зірочки
    const s = document.createElement('div');
    s.className = 'spark' + (star ? ' star' : '');
    if (star) {
      s.textContent = '✦';
      s.style.color = colors[i % 4];
      s.style.fontSize = (9 + Math.random() * 6) + 'px';
    } else {
      s.style.background = colors[i % 4];
    }
    fx.appendChild(s);
    const a = ((wave ? i - 7 : i) / (wave ? 5 : 7)) * Math.PI * 2 + Math.random() * 0.6;
    const r = (wave ? 58 : 40) + Math.random() * 16;
    s.animate([
      { transform: 'translate(-50%,-50%) translate(0,0) scale(.4) rotate(0deg)', opacity: 0 },
      { transform: `translate(-50%,-50%) translate(${Math.cos(a)*r*.55}px,${Math.sin(a)*r*.55}px) scale(1.15) rotate(70deg)`, opacity: 1, offset: .35 },
      { transform: `translate(-50%,-50%) translate(${Math.cos(a)*r}px,${Math.sin(a)*r}px) scale(0) rotate(150deg)`, opacity: 0 }
    ], { duration: (520 + Math.random()*180) * SPEED.v, easing: 'cubic-bezier(.17,.67,.4,1)', delay: (wave*120 + i*10) * SPEED.v, fill:'forwards' })
    .onfinish = () => s.remove();
  }
}

function glowRing(chip, color) {
  const fx = chip.querySelector('.fx');
  const r = document.createElement('div');
  r.className = 'ripple';
  r.style.borderColor = color;
  r.style.filter = 'blur(1.5px)';
  fx.appendChild(r);
  r.animate([
    { width:'34px', height:'34px', opacity:.8 },
    { width:'110px', height:'110px', opacity:0 }
  ], { duration: 620 * SPEED.v, easing:'cubic-bezier(.2,.6,.35,1)', fill:'forwards' })
  .onfinish = () => r.remove();
}

function ripples(chip) {
  const fx = chip.querySelector('.fx');
  [0, 140].forEach(delay => {
    const r = document.createElement('div');
    r.className = 'ripple';
    r.style.borderColor = FX.ripple();
    fx.appendChild(r);
    r.animate([
      { width:'30px', height:'30px', opacity:.7 },
      { width:'96px', height:'96px', opacity:0 }
    ], { duration: 560 * SPEED.v, easing:'cubic-bezier(.2,.6,.35,1)', delay: delay*SPEED.v, fill:'forwards' })
    .onfinish = () => r.remove();
  });
}

const TAPS = {
  sad(chip, svg, petals) {
    track(chip, seq(svg, [
      { transform:'scale(0.94)' },
      { transform:'scale(0.88) translate(0px,2px)', offset:.18 },
      { transform:'scale(0.88) translate(-1.6px,2px)', offset:.30 },
      { transform:'scale(0.88) translate(1.6px,2px)', offset:.42 },
      { transform:'scale(0.88) translate(-1.2px,2px)', offset:.54 },
      { transform:'scale(0.88) translate(1px,2px)', offset:.64 },
      { transform:'scale(1.03)', offset:.86 },
      { transform:'scale(1)' }
    ], { duration:640, easing:'ease-in-out' }));
    track(chip, seq(petals, [
      { transform:'rotate(0deg) scale(1)' },
      { transform:'rotate(-8deg) scale(0.93)', offset:.3 },
      { transform:'rotate(-8deg) scale(0.93)', offset:.6 },
      { transform:'rotate(0deg) scale(1)' }
    ], { duration:640, easing:'ease-in-out' }));
  },
  unpleasant(chip, svg, petals) {
    track(chip, seq(svg, [
      { transform:'scale(0.94) rotate(0deg)' },
      { transform:'scale(0.97) rotate(-4deg)', offset:.25 },
      { transform:'scale(1) rotate(2.5deg)', offset:.5 },
      { transform:'scale(1) rotate(-1deg)', offset:.75 },
      { transform:'scale(1) rotate(0deg)' }
    ], { duration:680, easing:'ease-out' }));
    track(chip, seq(petals, [
      { transform:'rotate(0deg)' },
      { transform:'rotate(-13deg)', offset:.22 },
      { transform:'rotate(9deg)', offset:.45 },
      { transform:'rotate(-5deg)', offset:.65 },
      { transform:'rotate(2deg)', offset:.82 },
      { transform:'rotate(0deg)' }
    ], { duration:680, easing:'ease-out' }));
  },
  neutral(chip, svg) {
    ripples(chip);
    track(chip, seq(svg, [
      { transform:'scale(0.94,0.94)' },
      { transform:'scale(1.07,0.95)', offset:.3 },
      { transform:'scale(0.96,1.05)', offset:.55 },
      { transform:'scale(1.02,0.99)', offset:.78 },
      { transform:'scale(1,1)' }
    ], { duration:620, easing:'ease-in-out' }));
  },
  pleasant(chip, svg) {
    // bloom-каскад: кільця розкриваються зсередини назовні, чергуючи напрям повороту
    const rings = [...themeIcon(chip).querySelectorAll('.petalsInner > g.ring')].reverse(); // ring3 (внутрішнє) перше
    rings.forEach((rg, i) => track(chip, seq(rg, [
      { transform:'scale(1) rotate(0deg)' },
      { transform:`scale(1.24) rotate(${i % 2 ? -7 : 7}deg)`, offset:.38 },
      { transform:'scale(0.97) rotate(-2deg)', offset:.72 },
      { transform:'scale(1) rotate(0deg)' }
    ], { duration:620, easing:'ease-in-out', delay: i * 55 * SPEED.v })));
    glowRing(chip, FX.pleasantRing());
    track(chip, seq(svg, [
      { transform:'scale(0.94)', filter:'brightness(1)' },
      { transform:'scale(1.05)', filter:`brightness(${bright(1.3)})`, offset:.4 },
      { transform:'scale(1)', filter:'brightness(1)' }
    ], { duration:840, easing:'ease-in-out' }));
  },
  happy(chip, svg) {
    sparkles(chip);
    glowRing(chip, FX.happyRing());
    track(chip, seq(svg, [
      { transform:'scale(0.94,0.94) translate(0,0)', filter:'brightness(1)' },
      { transform:'scale(0.92,0.86) translate(0,3px)', filter:'brightness(1)', offset:.15 },   // присідання перед стрибком
      { transform:'scale(1.18,0.88) translate(0,-2px)', filter:`brightness(${bright(1.4)})`, offset:.38 },
      { transform:'scale(0.92,1.14) translate(0,-6px)', filter:`brightness(${bright(1.2)})`, offset:.58 },
      { transform:'scale(1.06,0.97) translate(0,0)', filter:`brightness(${bright(1.05)})`, offset:.78 },
      { transform:'scale(1,1) translate(0,0)', filter:'brightness(1)' }
    ], { duration:760, easing:'ease-in-out' }));
  }
};

const TITLES = {
  sad: "What's weighing on you?",
  unpleasant: "What made today unpleasant?",
  neutral: "What's on your mind?",
  pleasant: "What made it pleasant?",
  happy: "What sparked the joy?"
};

let inTransition = false;

const themeIcon = chip => chip.querySelector(
  document.body.classList.contains('light') ? '.icon-light' : '.icon-dark');

const isLight = () => document.body.classList.contains('light');
// глоу в новому арті вже яскравіший, тому спалахи яскравості тримаємо коротшими:
// на світлому пересвічує -> ~30% ефекту, на темному -> 70%
const bright = v => isLight() ? 1 + (v - 1) * 0.3 : 1 + (v - 1) * 0.7;
const FX = {
  ripple:       () => isLight() ? 'rgba(32,148,150,.6)'  : 'rgba(127,217,217,.65)',
  pleasantRing: () => isLight() ? 'rgba(38,158,100,.55)' : 'rgba(126,222,166,.55)',
  happyRing:    () => isLight() ? 'rgba(214,152,26,.5)'  : 'rgba(255,216,134,.6)',
  sparks:       () => isLight() ? ['#E3A93B','#D69417','#B98A1E','#E8BC55'] : ['#FFE9A8','#FFD886','#FFFFFF','#FFC96B']
};

function slideScreen1(out) {
  // паралакс контенту першого екрана, як в iOS push
  const els = [document.querySelector('.card'), ...document.querySelectorAll('.ghost')];
  els.forEach(el => el.animate(
    out ? [{ transform:'translateX(0)', opacity:1 }, { transform:'translateX(-120px)', opacity:.55 }]
        : [{ transform:'translateX(-120px)', opacity:.55 }, { transform:'translateX(0)', opacity:1 }],
    { duration: 420 * SPEED.v, easing:'cubic-bezier(.32,.72,.28,1)', fill:'forwards' }));
}

function goNext(chip) {
  if (inTransition) return;
  inTransition = true;
  const s2 = document.getElementById('screen2');
  s2.querySelector('.s2title').textContent = TITLES[chip.dataset.mood];
  s2.style.transitionDuration = (420 * SPEED.v) + 'ms';
  s2.classList.add('show');
  slideScreen1(true);
}

function goBack() {
  if (!inTransition) return;
  const s2 = document.getElementById('screen2');
  s2.style.transitionDuration = (380 * SPEED.v) + 'ms';
  s2.classList.remove('show');
  slideScreen1(false);
  setTimeout(() => { inTransition = false; }, 400 * SPEED.v);
}
document.querySelector('#screen2 .backBtn').addEventListener('click', goBack);

function playTap(chip) {
  if (inTransition) return;
  const icon = themeIcon(chip);
  const svg = icon.querySelector('svg.mood-svg');
  const petals = icon.querySelector('.petals');
  stopRunning(chip);
  TAPS[chip.dataset.mood](chip, svg, petals);
  const anims = running.get(chip) || [];
  Promise.all(anims.map(a => a.finished)).then(() => {
    if (document.getElementById('doTrans').checked) goNext(chip);
  }).catch(() => {});
}

document.querySelectorAll('.chip').forEach(chip => {
  let press = null;
  chip.addEventListener('pointerdown', e => {
    if (inTransition) return;
    const svg = themeIcon(chip).querySelector('svg.mood-svg');
    stopRunning(chip);
    press = track(chip, svg.animate(
      [{ transform:'scale(1)' }, { transform:'scale(0.94)' }],
      { duration: 110 * SPEED.v, fill:'forwards', easing:'ease-out' }));
  });
  const release = () => { if (!press) return; press = null; playTap(chip); };
  chip.addEventListener('pointerup', release);
  chip.addEventListener('pointerleave', () => { if (press) { stopRunning(chip); press = null; } });
});

document.getElementById('tapRow').addEventListener('click', e => {
  const m = e.target.dataset && e.target.dataset.m;
  if (!m) return;
  playTap(document.querySelector(`.chip[data-mood="${m}"]`));
});

function radioRow(id, fn) {
  const row = document.getElementById(id);
  row.addEventListener('click', e => {
    if (!e.target.matches('button')) return;
    row.querySelectorAll('button').forEach(b => b.classList.remove('on'));
    e.target.classList.add('on');
    fn(e.target);
  });
}
radioRow('ampRow', b => document.documentElement.style.setProperty('--amp', b.dataset.amp));
radioRow('glowRow', b => document.documentElement.style.setProperty('--gmin', b.dataset.g));
radioRow('tempoRow', b => { BASE.v = parseFloat(b.dataset.t); applyIdle(); });
radioRow('speedRow', b => { SPEED.v = parseFloat(b.dataset.s); });
document.getElementById('unison').addEventListener('change', applyIdle);
document.getElementById('reduced').addEventListener('change', e => document.body.classList.toggle('reduced', e.target.checked));
radioRow('themeRow', b => document.body.classList.toggle('light', b.dataset.th === 'light'));

applyIdle();
"""

CHEVRON = ('<svg width="7" height="12" viewBox="0 0 7 12" fill="none">'
           '<path d="M1 1L6 6L1 11" stroke="#8F7DFF" stroke-width="1.6" '
           'stroke-linecap="round" stroke-linejoin="round"/></svg>')

SPEC = """<b>Параметри для доки:</b> Idle — scale 1→1.03 (sine, цикл 4 с ±15% на квітку),
глоу opacity 0.80→1 у тій самій фазі (у новому арті запечений глоу яскравіший на ~70%,
тому пульс став неглибоким; 0.72 лишився в перемикачі для порівняння), пелюстки rotate ±1.6°
(цикл ×1.8 повільніший); фазовий зсув між квітками ~0.3–0.65 циклу.
Tap — прес: scale 0.94, 110 мс; відпускання: своя анімація 620–700 мс (ease-in-out із overshoot),
повернення в idle. Sad — зіщулення scale 0.88 + shiver ±1.6px + пелюстки −8°;
Unpleasant — в'янення, пелюстки −13°→+9°→0 із загасанням;
Neutral — желе scaleX/Y + 2 ripple-кільця навколо іконки;
Pleasant — bloom-каскад: 4 кільця пелюсток розкриваються зсередини назовні (scale 1.24, ±7°, стагер 55 мс)
+ зелене кільце-глоу + спалах; Happy — присідання (антисипейшн) → стрибок squash&amp;stretch 1.18/0.86
+ 12 іскор двома хвилями (зірочки ✦ + крапки, розліт 40–74px) + жовте кільце-глоу.
Спалахи яскравості: 70% від номіналу на Dark і 30% на Light — сильніший глоу нового арту інакше вигорає.
Перехід: після tap-анімації — iOS push: екран опшенів slide-in справа 420 мс cubic-bezier(.32,.72,.28,1),
перший екран — паралакс −120px + пригасання до 55%; назад — дзеркально 380 мс.
Reduce motion: лишається тільки пульс глоу.
Технічне: idle-трансформи тільки на внутрішніх групах SVG (корінь статичний), інакше композитинг
розмиває дрібні риси обличчя; розкрій шарів — glow 0–2, пелюстки 3–12 (кільця 2·2·3·3, ядро йде
з внутрішнім кільцем — саме тому bloom читається як розкриття всієї квітки), core 13–24."""


def build() -> str:
    chips = []
    for key, label, dm, dl in MOODS:
        dark = prepare_svg(os.path.join(ASSETS, f"Mood={label}, Theme=Dark.svg"))
        light = prepare_svg(os.path.join(ASSETS, f"Mood={label}, Theme=Light.svg"))
        chips.append(
            f'<div class="chip" data-mood="{key}" data-dm="{dm}" data-dl="{dl}">'
            f'<div class="icon icon-dark">{dark}</div>'
            f'<div class="icon icon-light">{light}</div>'
            f'<div class="fx"></div><span class="lbl">{label}</span></div>'
        )
    taps = "".join(
        f'<button data-m="{k}">{lbl if len(lbl) < 8 else lbl[:5] + "."}</button>'
        for k, lbl, _, _ in MOODS
    )

    return f"""<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Relatio · Mood Tracker — превью анімації</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<h1>Mood Tracker — превью анімації</h1>
<p class="sub">Асети від 19.08 · Idle: «дихання» + пульс глоу + похитування пелюсток, кожна квітка у своїй фазі · Тап: свій характер у кожної → slide-in екрана опшенів · «‹» повертає назад</p>
<div class="wrap">
  <div id="phone">
    <div id="island"></div>
    <div class="card">
      <div class="head"><span class="ttl">How are you feeling?</span><span class="jrn">Journal {CHEVRON}</span></div>
      <div class="dsc">Mood and daily reflections</div>
      <div class="moods">
{chr(10).join(chips)}
      </div>
    </div>
    <div class="ghost" style="top:356px"></div>
    <div class="ghost" style="top:482px"></div>
    <div id="screen2">
      <div class="backBtn">‹</div>
      <div class="s2title">What's making you feel this way?</div>
      <div class="s2sub">Add a reflection to your journal</div>
      <div class="s2pills"><span>Work</span><span>Family</span><span>Health</span><span>Friends</span><span>Sleep</span><span>+</span></div>
      <div class="s2cta">Save to Journal</div>
    </div>
  </div>
  <div class="panel">
    <span class="h">Дихання — амплітуда</span>
    <div class="row" id="ampRow">
      <button data-amp="1.02">2%</button>
      <button data-amp="1.03" class="on">3%</button>
      <button data-amp="1.05">5%</button>
    </div>
    <span class="h">Пульс глоу — глибина</span>
    <div class="row" id="glowRow">
      <button data-g="0.72">0.72→1</button>
      <button data-g="0.80" class="on">0.80→1</button>
      <button data-g="0.88">0.88→1</button>
    </div>
    <span class="h">Дихання — темп (базовий цикл)</span>
    <div class="row" id="tempoRow">
      <button data-t="3.2">3.2 с</button>
      <button data-t="4" class="on">4 с</button>
      <button data-t="5">5 с</button>
    </div>
    <span class="h">Тема</span>
    <div class="row" id="themeRow">
      <button data-th="dark" class="on">Dark</button>
      <button data-th="light">Light</button>
    </div>
    <label><input type="checkbox" id="unison"> Унісон (без десинхрону — для порівняння)</label>
    <label><input type="checkbox" id="reduced"> Reduce motion (лишається тільки глоу)</label>
    <label><input type="checkbox" id="doTrans" checked> Перехід на екран журналу після тапу</label>
    <span class="h">Швидкість tap-анімації</span>
    <div class="row" id="speedRow">
      <button data-s="1" class="on">1×</button>
      <button data-s="2">0.5×</button>
      <button data-s="4">0.25×</button>
    </div>
    <span class="h">Програти тап</span>
    <div class="row" id="tapRow">
      {taps}
    </div>
    <p class="note">Після тапу іконка повертається в idle — обраного стану немає. Прес (палець утримано) — легкий squash 0.94.</p>
  </div>
</div>
<p class="spec">{SPEC}</p>
<script>{JS}</script>
</body>
</html>
"""


if __name__ == "__main__":
    html = build()
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"OK {OUT} — {len(html):,} bytes", file=sys.stderr)
