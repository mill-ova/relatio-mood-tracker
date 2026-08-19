#!/usr/bin/env python3
"""
Ріже кожен _Mood Asset на 3 PNG-шари для React Native:
    glow   — елементи 0..2
    petals — 3..12 (усі 4 кільця разом)
    core   — 13..24 (play-of-color, віяло, обличчя)

Рендер у справжньому Chromium (блюри й градієнти як у Figma), потім:
  * спільний кроп по об'єднаному alpha-bbox трьох шарів -> шари ідеально накладаються;
  * @3x -> @2x -> @1x через LANCZOS;
  * поруч кладемо full-<mood>-<theme>.png (цілісний рендер) для звірки склейки.
"""
import io
import json
import os
import re

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "rn-assets")
FULL = os.path.join(HERE, "rn-full")
os.makedirs(OUT, exist_ok=True)
os.makedirs(FULL, exist_ok=True)

MOODS = ["Sad", "Unpleasant", "Neutral", "Pleasant", "Happy"]
THEMES = ["Dark", "Light"]
DP_PER_UNIT = 72 / 56          # так само як у веб-прев'ю
PAD = 18                       # запас у юнітах під bleed блюрів
SCALE = 3                      # рендеримо @3x

import sys
sys.path.insert(0, HERE)
from build_mood_preview import top_level_spans, close_foreign_divs  # noqa: E402

GROUPS = [("glow", 0, 3), ("petals", 3, 13), ("core", 13, 25)]

# Що насправді ріжемо (див. верифікацію verify_layers.py):
#   flower     = glow(×0.80) + petals  — усе additive-змішування лишається ВСЕРЕДИНІ картинки
#   glow_pulse = glow(×0.20)           — «дихаюча» добавка світла, кладеться ПІД flower
#   core       = ядро + обличчя        — у Figma блендиться нормально, тож кладеться зверху 1:1
# Пульс глоу в RN = opacity 0..1 на glow_pulse (перевірено verify_layers.py: у Light майже
# точно, у Dark на піку халу трохи темніше за Figma — plus-lighter нормальним блендом не
# відтворити; варіанти зі screen і з крос-фейдом двох повних кадрів виміряно ГІРШИМИ).
# імена файлів — тільки нижній регістр і підкреслення: Android drawable не любить
# ні дефісів, ні великих літер (Metro зводить шлях у назву ресурсу)
LAYERS = {
    "flower":     {"glow": 0.80, "petals": True, "core": False},   # тіло + глоу на дні пульсу
    "glow_pulse": {"glow": 0.20, "petals": False, "core": False},  # ті самі 20% глоу, що «дихають»
    "core":       {"glow": None, "petals": False, "core": True},   # ядро + обличчя, зверху
}


def page_html(svg_path: str, visible: str | None, spec: dict | None = None):
    raw = close_foreign_divs(open(svg_path, encoding="utf-8").read())
    head = raw[:raw.index(">", raw.index("<svg")) + 1]
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head)
    w, h = float(vb.group(1)), float(vb.group(2))
    spans = top_level_spans(raw)
    content = [raw[a:b] for a, b, t in spans if t != "defs"]
    defs = "".join(raw[a:b] for a, b, t in spans if t == "defs")

    parts = []
    for name, lo, hi in GROUPS:
        if spec is not None:                       # режим «шар для RN»
            val = spec[name]
            if val in (None, False):
                continue
            op = f' opacity="{val}"' if isinstance(val, float) else ""
            parts.append(f'<g{op}>{"".join(content[lo:hi])}</g>')
        else:                                      # режим «одна група для звірки»
            style = "" if visible in (None, name) else ' style="display:none"'
            parts.append(f'<g{style}>{"".join(content[lo:hi])}</g>')

    px_w, px_h = round((w + PAD * 2) * DP_PER_UNIT * SCALE), round((h + PAD * 2) * DP_PER_UNIT * SCALE)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:html="http://www.w3.org/1999/xhtml" '
        f'width="{px_w}" height="{px_h}" viewBox="{-PAD} {-PAD} {w + PAD * 2} {h + PAD * 2}" fill="none">'
        f'{"".join(parts)}{defs}</svg>'
    )
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
            f'html,body{{margin:0;padding:0;background:transparent}}'
            f'svg{{display:block}}</style></head><body>{svg}</body></html>'), px_w, px_h, w, h


def shoot(pg, svg_path, visible, px_w, px_h, html):
    pg.set_viewport_size({"width": px_w, "height": px_h})
    pg.set_content(html, wait_until="load")
    pg.wait_for_timeout(180)
    return Image.open(io.BytesIO(pg.screenshot(omit_background=True))).convert("RGBA")


def alpha_bbox(ims):
    acc = None
    for im in ims:
        a = np.asarray(im)[:, :, 3]
        acc = a if acc is None else np.maximum(acc, a)
    ys, xs = np.where(acc > 2)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def main():
    manifest = {}
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--force-color-profile=srgb"])
        pg = b.new_page(device_scale_factor=1)
        for mood in MOODS:
            # 1) рендеримо обидві теми, 2) один спільний бокс на настрій —
            # інакше при перемиканні теми асет змінював би розмір і «стрибав»
            shots, fulls, meta = {}, {}, {}
            for theme in THEMES:
                path = os.path.join(ASSETS, f"Mood={mood}, Theme={theme}.svg")
                html_all, px_w, px_h, uw, uh = page_html(path, None)
                meta[theme] = (uw, uh)
                for name, spec in LAYERS.items():
                    html, *_ = page_html(path, None, spec)
                    shots[(theme, name)] = shoot(pg, path, name, px_w, px_h, html)
                fulls[theme] = shoot(pg, path, None, px_w, px_h, html_all)

            bx0, by0, bx1, by1 = alpha_bbox(list(shots.values()))
            # кроп СИМЕТРИЧНИЙ щодо центру viewBox: тоді в RN достатньо центрувати
            # картинку в чіпі, і оптичний центр квітки сяде рівно так, як у Figma
            uw, uh = meta["Dark"]
            ppu = DP_PER_UNIT * SCALE
            cx, cy = (PAD + uw / 2) * ppu, (PAD + uh / 2) * ppu
            half_w = max(cx - bx0, bx1 - cx)
            half_h = max(cy - by0, by1 - cy)
            half_w += (-(2 * half_w)) % (SCALE * 2) / 2   # щоб ширина була кратна 3 (і парна)
            half_h += (-(2 * half_h)) % (SCALE * 2) / 2
            x0, y0 = round(cx - half_w), round(cy - half_h)
            x1, y1 = x0 + round(half_w * 2), y0 + round(half_h * 2)
            w3, h3 = x1 - x0, y1 - y0
            w3 -= w3 % SCALE
            h3 -= h3 % SCALE
            x1, y1 = x0 + w3, y0 + h3

            for theme in THEMES:
                key = f"{mood.lower()}_{theme.lower()}"
                for name in LAYERS:
                    c = shots[(theme, name)].crop((x0, y0, x1, y1))
                    c.save(f"{OUT}/mood_{key}_{name}@3x.png")
                    c.resize((w3 * 2 // 3, h3 * 2 // 3), Image.LANCZOS).save(f"{OUT}/mood_{key}_{name}@2x.png")
                    c.resize((w3 // 3, h3 // 3), Image.LANCZOS).save(f"{OUT}/mood_{key}_{name}.png")
                fulls[theme].crop((x0, y0, x1, y1)).save(f"{FULL}/full_{key}@3x.png")

            manifest[mood.lower()] = {
                "dp": [w3 // SCALE, h3 // SCALE],
                "px3x": [w3, h3],
                "viewBox": list(meta["Dark"]),
            }
            print(f"{mood.lower():12s} @3x {w3}x{h3} -> {w3 // SCALE}x{h3 // SCALE} dp (спільний бокс на обидві теми)")
        b.close()
    json.dump(manifest, open(f"{OUT}/manifest.json", "w"), indent=2, ensure_ascii=False)
    print("manifest ok")


if __name__ == "__main__":
    main()
