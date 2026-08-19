#!/usr/bin/env python3
"""
mood-rn-preview.html — те саме прев'ю, але складене з ТРЬОХ PNG-шарів,
тобто рівно так, як це робить MoodTrackerCard.tsx у React Native.
Потрібне, щоб (а) звірити, що шари збігаються, (б) показати девам цільовий вигляд.
Картинки вшиті в base64 (@2x), тож файл самодостатній.
"""
import base64
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "rn-assets")
OUT = os.path.join(HERE, "mood-rn-preview.html")

MOODS = [
    ("sad", "Sad", 1.00, 0.00),
    ("unpleasant", "Unpleasant", 1.09, -0.33),
    ("neutral", "Neutral", 0.96, -0.65),
    ("pleasant", "Pleasant", 1.15, -0.22),
    ("happy", "Happy", 1.04, -0.50),
]
MANIFEST = json.load(open(os.path.join(ASSETS, "manifest.json")))


def b64(path):
    return "data:image/png;base64," + base64.b64encode(open(path, "rb").read()).decode()


def chips():
    """Та сама вкладеність, що в MoodTrackerCard.tsx:
       icon > sway > body > (glow, flower)   +   icon > core"""
    out = []
    for key, label, dm, dl in MOODS:
        w, h = MANIFEST[key]["dp"]
        box = f'style="width:{w}px;height:{h}px;left:{(72 - w) / 2}px;top:{(72 - h) / 2}px"'
        icons = []
        for theme in ("dark", "light"):
            src = {n: b64(os.path.join(ASSETS, f"mood_{key}_{theme}_{n}@2x.png"))
                   for n in ("glow_pulse", "flower", "core")}
            icons.append(
                f'<div class="icon icon-{theme}">'
                f'<div class="sway-anim"><div class="body-anim">'
                f'<div class="glow-anim"><img class="lay" {box} src="{src["glow_pulse"]}"></div>'
                f'<img class="lay" {box} src="{src["flower"]}">'
                f'</div></div>'
                f'<div class="core-anim"><img class="lay" {box} src="{src["core"]}"></div>'
                f'</div>'
            )
        out.append(
            f'<div class="chip" data-mood="{key}" data-dm="{dm}" data-dl="{dl}">'
            f'{"".join(icons)}<div class="fx"></div><span class="lbl">{label}</span></div>'
        )
    return "\n".join(out)


CSS = """
  :root { --amp: 1.03; }
  body { margin:0; font-family:Poppins,sans-serif; background:#f7f7f7; color:#0d0d0d;
         display:flex; flex-direction:column; align-items:center; padding:32px 16px; }
  h1 { font-size:20px; font-weight:600; margin:0 0 4px; }
  .sub { font-size:13px; color:#6b6b6b; margin:0 0 24px; text-align:center; max-width:660px; line-height:1.5; }
  .wrap { display:flex; gap:24px; align-items:flex-start; flex-wrap:wrap; justify-content:center; }
  .panel { display:flex; flex-direction:column; gap:10px; min-width:230px; max-width:270px; }
  .panel span.h { font-size:13px; color:#6b6b6b; margin-top:6px; }
  .panel .row { display:flex; gap:6px; flex-wrap:wrap; }
  button { font-family:Poppins,sans-serif; font-size:13px; font-weight:500; padding:8px 13px;
           border-radius:999px; border:1px solid #e2e2e2; background:#fff; cursor:pointer; }
  button.on { background:#0d0d0d; color:#fff; border-color:#0d0d0d; }
  label { display:flex; align-items:center; gap:8px; font-size:13px; color:#444; }
  .note { font-size:12px; color:#8a8a8a; line-height:1.5; margin-top:4px; }
  .spec { font-size:12px; color:#8a8a8a; line-height:1.7; margin-top:24px; max-width:660px; }
  .spec b { color:#444; font-weight:600; }

  #phone { position:relative; width:440px; height:420px; border-radius:48px; overflow:hidden;
           background:#0A0B0D; box-shadow:0 12px 40px rgba(0,0,0,.2); flex:0 0 auto; }
  .card { position:absolute; left:16px; right:16px; top:40px; border-radius:28px; padding:20px 16px 24px;
          background:rgba(255,255,255,.055); border:1px solid rgba(255,255,255,.05); box-sizing:border-box; }
  .card .head { display:flex; justify-content:space-between; align-items:center; padding:0 4px; }
  .card .ttl { font-size:19px; font-weight:600; color:#F2F3F5; letter-spacing:.1px; }
  .card .jrn { font-size:15px; font-weight:500; color:#8F7DFF; }
  .card .dsc { font-size:14px; color:#9BA0A8; margin:4px 4px 18px; }
  .moods { display:flex; justify-content:space-between; }

  .chip { position:relative; width:76px; display:flex; flex-direction:column; align-items:center;
          cursor:pointer; user-select:none; -webkit-tap-highlight-color:transparent; }
  .icon { position:relative; width:72px; height:72px; }
  .icon .lay { position:absolute; display:block; }
  .chip .lbl { margin-top:14px; font-size:13px; color:#D6D8DC; }
  .icon-light { display:none; }
  body.light .icon-light { display:block; }
  body.light .icon-dark { display:none; }
  body.light #phone { background:#F6F7FB; }
  body.light .card { background:#fff; border-color:rgba(255,255,255,.6);
       box-shadow:0 18px 50px rgba(60,70,110,.12), 0 2px 8px rgba(60,70,110,.05); }
  body.light .card .ttl { color:#17181B; }
  body.light .card .dsc { color:#6E737C; }
  body.light .card .jrn { color:#5A4FD6; }
  body.light .chip .lbl { color:#1E2126; }

  /* idle: ті самі числа, що в MoodTrackerCard.tsx */
  .icon .glow, .icon .flower { transform-origin:center; }
  .body-anim { position:absolute; inset:0; animation: breathe var(--bd,4s) ease-in-out infinite;
               animation-delay: var(--d,0s); transform-origin:center; }
  .sway-anim { position:absolute; inset:0; animation: sway calc(var(--bd,4s)*1.8) ease-in-out infinite;
               animation-delay: calc(var(--d,0s)*1.8); transform-origin:center; }
  .core-anim { position:absolute; inset:0; animation: breatheCore var(--bd,4s) ease-in-out infinite;
               animation-delay: var(--d,0s); transform-origin:center; }
  .glow-anim { position:absolute; inset:0; animation: glowPulse var(--bd,4s) ease-in-out infinite;
               animation-delay: var(--d,0s); }
  body.reduced .body-anim, body.reduced .sway-anim, body.reduced .core-anim { animation:none; }

  @keyframes breathe { 0%,100% { transform:scale(1); } 50% { transform:scale(var(--amp)); } }
  @keyframes breatheCore { 0%,100% { transform:scale(1); } 50% { transform:scale(calc(1 + (var(--amp,1.03) - 1)*0.55)); } }
  @keyframes sway { 0%,100% { transform:rotate(-1.6deg); } 50% { transform:rotate(1.6deg); } }
  @keyframes glowPulse { 0%,100% { opacity:0; } 50% { opacity:1; } }

  .fx { position:absolute; left:50%; top:36px; width:0; height:0; pointer-events:none; }
  .ripple { position:absolute; left:0; top:0; border:1.5px solid rgba(127,217,217,.65);
            border-radius:50%; transform:translate(-50%,-50%); }
  .spark { position:absolute; left:0; top:0; border-radius:50%; transform:translate(-50%,-50%); }
"""

JS = r"""
const SPEED = { v: 1 };
const BASE = { v: 4 };
const TAP_MS = { sad:640, unpleasant:680, neutral:620, pleasant:620, happy:760 };

function applyIdle() {
  const unison = document.getElementById('unison').checked;
  document.querySelectorAll('.chip').forEach(chip => {
    const dm = parseFloat(chip.dataset.dm), dl = parseFloat(chip.dataset.dl);
    chip.style.setProperty('--bd', (unison ? BASE.v : BASE.v * dm) + 's');
    chip.style.setProperty('--d', (unison ? 0 : BASE.v * dl) + 's');
  });
}

const isLight = () => document.body.classList.contains('light');
const themeIcon = chip => chip.querySelector(isLight() ? '.icon-light' : '.icon-dark');
const FX = {
  ring: m => ({
    neutral: isLight() ? 'rgba(32,148,150,.6)'  : 'rgba(127,217,217,.65)',
    pleasant: isLight() ? 'rgba(38,158,100,.55)' : 'rgba(126,222,166,.55)',
    happy:    isLight() ? 'rgba(214,152,26,.5)'  : 'rgba(255,216,134,.6)',
  }[m]),
  sparks: () => isLight() ? ['#E3A93B','#D69417','#B98A1E','#E8BC55'] : ['#FFE9A8','#FFD886','#FFFFFF','#FFC96B'],
};

const running = new Map();
const stop = chip => { (running.get(chip)||[]).forEach(a => { try { a.cancel(); } catch(e){} }); running.set(chip, []); };
const track = (chip, a) => { if (!running.has(chip)) running.set(chip, []); running.get(chip).push(a); return a; };
const seq = (el, frames, opts) => el.animate(frames, Object.assign({}, opts, { duration: opts.duration * SPEED.v }));

function ring(chip, color, from, to, dur, delay = 0) {
  const r = document.createElement('div');
  r.className = 'ripple'; r.style.borderColor = color;
  chip.querySelector('.fx').appendChild(r);
  r.animate([{ width:from+'px', height:from+'px', opacity:.75 }, { width:to+'px', height:to+'px', opacity:0 }],
    { duration: dur*SPEED.v, delay: delay*SPEED.v, easing:'cubic-bezier(.2,.6,.35,1)', fill:'forwards' })
   .onfinish = () => r.remove();
}

function sparkles(chip) {
  const colors = FX.sparks();
  for (let i = 0; i < 12; i++) {
    const wave = i < 7 ? 0 : 1;
    const a = ((wave ? i-7 : i)/(wave ? 5 : 7))*Math.PI*2 + (i%3)*0.21;
    const r = (wave ? 58 : 40) + (i%4)*4;
    const size = 3 + (i%3);
    const s = document.createElement('div');
    s.className = 'spark';
    s.style.width = s.style.height = size+'px';
    s.style.background = colors[i%4];
    chip.querySelector('.fx').appendChild(s);
    s.animate([
      { transform:'translate(-50%,-50%) translate(0,0) scale(.4)', opacity:0 },
      { transform:`translate(-50%,-50%) translate(${Math.cos(a)*r*.55}px,${Math.sin(a)*r*.55}px) scale(1.15)`, opacity:1, offset:.35 },
      { transform:`translate(-50%,-50%) translate(${Math.cos(a)*r}px,${Math.sin(a)*r}px) scale(0)`, opacity:0 }
    ], { duration: 800*SPEED.v, delay: wave*160*SPEED.v, easing:'cubic-bezier(.17,.67,.4,1)', fill:'forwards' })
     .onfinish = () => s.remove();
  }
}

const TAPS = {
  sad(chip, icon, body, sway, d) {
    track(chip, seq(icon, [
      { transform:'scale(0.94)' },
      { transform:'scale(0.88) translate(0px,2px)', offset:.18 },
      { transform:'scale(0.88) translate(-1.6px,2px)', offset:.30 },
      { transform:'scale(0.88) translate(1.6px,2px)', offset:.42 },
      { transform:'scale(0.88) translate(-1.2px,2px)', offset:.54 },
      { transform:'scale(0.88) translate(1px,2px)', offset:.64 },
      { transform:'scale(1.03)', offset:.86 },
      { transform:'scale(1)' }], { duration:d, easing:'ease-in-out' }));
    track(chip, seq(sway, [
      { transform:'rotate(0deg)' }, { transform:'rotate(-8deg)', offset:.3 },
      { transform:'rotate(-8deg)', offset:.6 }, { transform:'rotate(0deg)' }], { duration:d, easing:'ease-in-out' }));
  },
  unpleasant(chip, icon, body, sway, d) {
    track(chip, seq(icon, [
      { transform:'scale(0.94) rotate(0deg)' },
      { transform:'scale(0.97) rotate(-4deg)', offset:.25 },
      { transform:'scale(1) rotate(2.5deg)', offset:.5 },
      { transform:'scale(1) rotate(-1deg)', offset:.75 },
      { transform:'scale(1) rotate(0deg)' }], { duration:d, easing:'ease-out' }));
    track(chip, seq(sway, [
      { transform:'rotate(0deg)' }, { transform:'rotate(-13deg)', offset:.22 },
      { transform:'rotate(9deg)', offset:.45 }, { transform:'rotate(-5deg)', offset:.65 },
      { transform:'rotate(2deg)', offset:.82 }, { transform:'rotate(0deg)' }], { duration:d, easing:'ease-out' }));
  },
  neutral(chip, icon, body, sway, d) {
    ring(chip, FX.ring('neutral'), 30, 96, 620);
    ring(chip, FX.ring('neutral'), 30, 96, 620, 140);
    track(chip, seq(icon, [
      { transform:'scale(0.94,0.94)' }, { transform:'scale(1.07,0.95)', offset:.3 },
      { transform:'scale(0.96,1.05)', offset:.55 }, { transform:'scale(1.02,0.99)', offset:.78 },
      { transform:'scale(1,1)' }], { duration:d, easing:'ease-in-out' }));
  },
  pleasant(chip, icon, body, sway, d) {
    ring(chip, FX.ring('pleasant'), 34, 110, 620);
    track(chip, seq(body, [
      { transform:'scale(1)' }, { transform:'scale(1.24)', offset:.38 },
      { transform:'scale(0.97)', offset:.72 }, { transform:'scale(1)' }], { duration:d, easing:'ease-in-out' }));
    track(chip, seq(icon, [
      { transform:'scale(0.94)' }, { transform:'scale(1.05)', offset:.4 }, { transform:'scale(1)' }],
      { duration:d*1.35, easing:'ease-in-out' }));
    track(chip, seq(icon.querySelector('.glow-anim'), [
      { opacity:0 }, { opacity:1, offset:.4 }, { opacity:0 }], { duration:d*1.35, easing:'ease-in-out' }));
  },
  happy(chip, icon, body, sway, d) {
    sparkles(chip);
    ring(chip, FX.ring('happy'), 34, 110, 620);
    track(chip, seq(icon, [
      { transform:'scale(0.94,0.94) translate(0,0)' },
      { transform:'scale(0.92,0.86) translate(0,3px)', offset:.15 },
      { transform:'scale(1.18,0.88) translate(0,-2px)', offset:.38 },
      { transform:'scale(0.92,1.14) translate(0,-6px)', offset:.58 },
      { transform:'scale(1.06,0.97) translate(0,0)', offset:.78 },
      { transform:'scale(1,1) translate(0,0)' }], { duration:d, easing:'ease-in-out' }));
    track(chip, seq(icon.querySelector('.glow-anim'), [
      { opacity:0 }, { opacity:1, offset:.38 }, { opacity:0 }], { duration:d, easing:'ease-in-out' }));
  }
};

function playTap(chip) {
  const icon = themeIcon(chip);
  const body = icon.querySelector('.body-anim');
  const sway = icon.querySelector('.sway-anim');
  stop(chip);
  TAPS[chip.dataset.mood](chip, icon, body, sway, TAP_MS[chip.dataset.mood]);
}

document.querySelectorAll('.chip').forEach(chip => {
  let press = null;
  chip.addEventListener('pointerdown', () => {
    const icon = themeIcon(chip); stop(chip);
    press = track(chip, icon.animate([{ transform:'scale(1)' }, { transform:'scale(0.94)' }],
      { duration:110*SPEED.v, fill:'forwards', easing:'ease-out' }));
  });
  chip.addEventListener('pointerup', () => { if (!press) return; press = null; playTap(chip); });
  chip.addEventListener('pointerleave', () => { if (press) { stop(chip); press = null; } });
});

document.getElementById('tapRow').addEventListener('click', e => {
  const m = e.target.dataset && e.target.dataset.m;
  if (m) playTap(document.querySelector(`.chip[data-mood="${m}"]`));
});
function radioRow(id, fn) {
  const row = document.getElementById(id);
  row.addEventListener('click', e => {
    if (!e.target.matches('button')) return;
    row.querySelectorAll('button').forEach(b => b.classList.remove('on'));
    e.target.classList.add('on'); fn(e.target);
  });
}
radioRow('ampRow', b => document.documentElement.style.setProperty('--amp', b.dataset.amp));
radioRow('tempoRow', b => { BASE.v = parseFloat(b.dataset.t); applyIdle(); });
radioRow('speedRow', b => { SPEED.v = parseFloat(b.dataset.s); });
radioRow('themeRow', b => document.body.classList.toggle('light', b.dataset.th === 'light'));
document.getElementById('unison').addEventListener('change', applyIdle);
document.getElementById('reduced').addEventListener('change', e => document.body.classList.toggle('reduced', e.target.checked));
applyIdle();
"""


def build():
    html_chips = chips()

    return f"""<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<title>Relatio · Mood Tracker — RN-збірка (3 PNG-шари)</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<h1>Mood Tracker — так це виглядає в React Native</h1>
<p class="sub">Кожна квітка складена з трьох PNG (glow_pulse · flower · core) тими самими трансформами,
що в <code>MoodTrackerCard.tsx</code>. Порівнюй із mood-animation-preview.html — там цілісний SVG.</p>
<div class="wrap">
  <div id="phone">
    <div class="card">
      <div class="head"><span class="ttl">How are you feeling?</span><span class="jrn">Journal ›</span></div>
      <div class="dsc">Mood and daily reflections</div>
      <div class="moods">
{html_chips}
      </div>
    </div>
  </div>
  <div class="panel">
    <span class="h">Дихання — амплітуда</span>
    <div class="row" id="ampRow">
      <button data-amp="1.02">2%</button><button data-amp="1.03" class="on">3%</button><button data-amp="1.05">5%</button>
    </div>
    <span class="h">Темп (базовий цикл)</span>
    <div class="row" id="tempoRow">
      <button data-t="3.2">3.2 с</button><button data-t="4" class="on">4 с</button><button data-t="5">5 с</button>
    </div>
    <span class="h">Тема</span>
    <div class="row" id="themeRow">
      <button data-th="dark" class="on">Dark</button><button data-th="light">Light</button>
    </div>
    <label><input type="checkbox" id="unison"> Унісон</label>
    <label><input type="checkbox" id="reduced"> Reduce motion</label>
    <span class="h">Швидкість тапу</span>
    <div class="row" id="speedRow">
      <button data-s="1" class="on">1×</button><button data-s="2">0.5×</button><button data-s="4">0.25×</button>
    </div>
    <span class="h">Програти тап</span>
    <div class="row" id="tapRow">
      <button data-m="sad">Sad</button><button data-m="unpleasant">Unpl.</button><button data-m="neutral">Neut.</button>
      <button data-m="pleasant">Pleas.</button><button data-m="happy">Happy</button>
    </div>
    <p class="note">Вібрації тут немає — вона тільки на пристрої (expo-haptics). Партитури — у докс-файлі.</p>
  </div>
</div>
<p class="spec"><b>Що навмисно інакше, ніж у SVG-прев'ю:</b> bloom Pleasant — це одне розкриття всіх пелюсток
(у SVG кільця розкривалися каскадом по 55 мс: у RN шари не поділені на кільця);
спалах яскравості замінено на вихід глоу в максимум (у RN немає filter: brightness);
кільця-ripple без блюру. Решта — ті самі числа.</p>
<script>{JS}</script>
</body>
</html>
"""


if __name__ == "__main__":
    html = build()
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"OK {OUT} — {len(html):,} bytes")
