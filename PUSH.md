# Що залито

Дата: 2026-08-19. Репо: `mill-ova/relatio-mood-tracker` (private).

| шлях | що це |
|---|---|
| `README.md` | вхідна точка: логіка картки, правила «не оптимізувати», що перевірено |
| `prototype/index.html` | цілісний SVG-прототип — **джерело істини по числах** (idle, 5 характерів тапу, перемикачі амплітуди/темпу/теми, reduce motion) |
| `prototype/rn-layers.html` | той самий рух на PNG-шарах — так це виглядає в RN; порівнювати з `index.html` |
| `react-native/MoodTrackerCard.tsx` | компонент: idle, тапи, вібро-партитури (iOS + Android), reduce motion, токени |
| `react-native/assets/` | 90 PNG: `mood_<mood>_<theme>_{flower,glow_pulse,core}` × `@1x/@2x/@3x` + `manifest.json` (розміри в dp) |
| `docs/motion-and-haptics.md` | спека: таблиці idle й тапів, партитури вібрації, розкрій арту з виміряними похибками, Android-специфіка, чеклист приймання |
| `tools/*.py` | пайплайн нарізки асетів із Figma-експортів |

## Якщо квітки виглядають «плоскими» або не тими

Асети мусять лежати рівно в `react-native/assets/` поруч із компонентом — `require('./assets/mood_sad_dark_flower.png')`. Якщо в проєкті вже був старий набір Apple State of Mind із тими самими іменами — прибрати його, інакше Metro підхопить старий. Після заміни асетів: `npx react-native start --reset-cache`.

## Як перегенерувати асети

Потрібні `playwright` (Chromium), `pillow`, `numpy`. Нові експорти з Figma («Mood=X, Theme=Y.svg», 5 × 2) покласти в `assets/` поруч зі скриптами і прогнати:

```bash
python3 tools/render_layers.py     # SVG -> 3 шари × @1x/@2x/@3x + manifest.json
python3 tools/verify_layers.py     # попіксельна звірка склейки з еталоном
python3 tools/build_rn_preview.py  # prototype/rn-layers.html на цих PNG
```

## Відкриті питання до девів

1. **Амплітуди вібрації на Android.** `expo-haptics` віддає лише три пресети (і `Soft` там ідентичний `Light`, `Rigid` — `Medium`), тому крещендо Pleasant закодоване тривалістю, а не силою. Справжня динаміка = свій ~30-рядковий модуль на `VibrationEffect.createWaveform(timings, amplitudes, -1)`. Робимо?
2. **Каскад bloom у Pleasant.** У SVG-прототипі чотири кільця пелюсток розкривалися зі стагером 55 мс; у RN шари не поділені на кільця, тому це одне розкриття. Якщо каскад потрібен — розріжу пелюстки на два шари (ціна: ще один шар і трохи світла в Dark).
3. **`filter: brightness()`** на спалахах Pleasant/Happy замінено виходом глоу в максимум — per-view brightness у RN немає. 1:1 можливий через `@shopify/react-native-skia` (`blendMode="plus"` там заодно закриє й похибку глоу в темній темі). Чи є Skia в проєкті?
