#!/usr/bin/env python3
"""
Чи не втрачаємо ми світло, розрізавши квітку на шари для RN?

Схема, яку перевіряємо (те, що робитиме RN звичайним alpha-блендом):
    фон -> glow_pulse @ opacity t -> flower -> core
Еталон: цілісний SVG на тому самому фоні, де глоу-група має opacity 0.80 + 0.20·t,
тобто саме та фаза пульсу. plus-lighter у ньому працює з реальним бекдропом.

t = 0 (дно пульсу), 0.5 (середина — перевірка лінійності крос-фейду), 1 (пік).
"""
import io
import os
import re
import sys

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_mood_preview import close_foreign_divs, top_level_spans  # noqa: E402
from render_layers import ASSETS, DP_PER_UNIT, GROUPS, OUT, PAD, SCALE  # noqa: E402

MOODS = ["Sad", "Unpleasant", "Neutral", "Pleasant", "Happy"]
BG = {"dark": (24, 24, 25), "light": (255, 255, 255)}   # картка: bg/default + плівка 5.5% / bg/secondary
TS = [0.0, 0.5, 1.0]


def truth(pg, path, bg, glow_opacity):
    raw = close_foreign_divs(open(path, encoding="utf-8").read())
    head = raw[:raw.index(">", raw.index("<svg")) + 1]
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head)
    uw, uh = float(vb.group(1)), float(vb.group(2))
    spans = top_level_spans(raw)
    content = [raw[a:b] for a, b, t in spans if t != "defs"]
    defs = "".join(raw[a:b] for a, b, t in spans if t == "defs")
    body = (f'<g opacity="{glow_opacity}">{"".join(content[0:3])}</g>'
            f'<g>{"".join(content[3:13])}</g><g>{"".join(content[13:25])}</g>')
    px_w = round((uw + PAD * 2) * DP_PER_UNIT * SCALE)
    px_h = round((uh + PAD * 2) * DP_PER_UNIT * SCALE)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:html="http://www.w3.org/1999/xhtml" '
           f'width="{px_w}" height="{px_h}" viewBox="{-PAD} {-PAD} {uw + PAD * 2} {uh + PAD * 2}" '
           f'fill="none">{body}{defs}</svg>')
    html = (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>html,body{{margin:0;'
            f'background:rgb{bg}}}svg{{display:block}}</style></head><body>{svg}</body></html>')
    pg.set_viewport_size({"width": px_w, "height": px_h})
    pg.set_content(html, wait_until="load")
    pg.wait_for_timeout(160)
    im = np.asarray(Image.open(io.BytesIO(pg.screenshot())).convert("RGB"), dtype=float)
    return im, (uw, uh)


def rn_composite(bg, layers_with_alpha):
    h, w = layers_with_alpha[0][0].shape[:2]
    out = np.zeros((h, w, 3), dtype=float)
    out[:] = bg
    for lay, mul in layers_with_alpha:
        a = lay[:, :, 3:4] / 255.0 * mul
        out = lay[:, :, :3] * a + out * (1 - a)
    return out


def main():
    print(f"{'асет':18s} {'t':>4s} {'сер.Δ':>7s} {'99%Δ':>7s} {'макс.Δ':>7s}   (0..255)")
    worst = (0, "")
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--force-color-profile=srgb"])
        pg = b.new_page(device_scale_factor=1)
        for mood in MOODS:
            for theme in ("dark", "light"):
                key = f"{mood.lower()}_{theme}"
                lays = {n: np.asarray(Image.open(f"{OUT}/mood_{key}_{n}@3x.png").convert("RGBA"), dtype=float)
                        for n in ("flower", "glow_pulse", "core")}
                mask = np.maximum(lays["flower"][:, :, 3], lays["core"][:, :, 3]) > 6
                for t in TS:
                    gt_full, (uw, uh) = truth(pg, os.path.join(ASSETS, f"Mood={mood}, Theme={theme.capitalize()}.svg"),
                                              BG[theme], round(0.80 + 0.20 * t, 3))
                    ch, cw = lays["flower"].shape[:2]
                    ppu = DP_PER_UNIT * SCALE
                    cx, cy = (PAD + uw / 2) * ppu, (PAD + uh / 2) * ppu
                    x0, y0 = round(cx - cw / 2), round(cy - ch / 2)
                    gt = gt_full[y0:y0 + ch, x0:x0 + cw]
                    comp = rn_composite(np.array(BG[theme], dtype=float),
                                        [(lays["glow_pulse"], t), (lays["flower"], 1.0), (lays["core"], 1.0)])
                    d = np.abs(comp - gt).max(axis=2)[mask]
                    print(f"{key:18s} {t:4.1f} {d.mean():7.2f} {np.percentile(d, 99):7.1f} {d.max():7.0f}")
                    if d.mean() > worst[0]:
                        worst = (d.mean(), f"{key} @ t={t}")
        b.close()
    print(f"\nнайгірше: {worst[1]} — сер.Δ {worst[0]:.2f}/255 ({worst[0] / 255 * 100:.2f}%)")


if __name__ == "__main__":
    main()
