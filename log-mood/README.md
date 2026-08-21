# Log mood — morphing emotion slider

The "Choose how you've felt overall today" screen. Dragging the slider knob
morphs the mood flower **continuously** from one emotion into the next; at the
five stops the shapes are pixel-identical to the Figma `_Mood Asset`
(Theme=Light) components. Releasing the knob springs to the nearest stop.

Figma sources: screens `📱 Mood · Log mood · Light` (19554:120350),
slider component `Mood Slider` (19579:121514), assets `_Mood Asset` (18585:111216).

## What's inside

| File | What it is |
| --- | --- |
| `prototype/mood-morph-preview.html` | Self-contained browser prototype — open and drag. Source of truth for the motion feel. |
| `react-native/MoodLogScreen.tsx` | The screen: `MoodMorphHero` (morphing flower), `MoodSlider` (track + 5 level dots + knob), background, label cross-fade, CTA. Each part is exported separately. |
| `react-native/moodShapes.ts` | Generated geometry: every layer of all 5 moods resampled to a fixed point count for point-wise interpolation. Do not edit by hand. |

## Dependencies

`react-native-reanimated >= 3.6`, `react-native-gesture-handler >= 2.14`,
`react-native-svg >= 15.2` (needed for `FeGaussianBlur`; set `ENABLE_BLUR = false`
in `MoodLogScreen.tsx` on older versions — the flower stays correct, just crisper).
Gesture, morph and every color interpolation run on the UI thread (worklets);
there are no JS-bridge hops while dragging. Type-checked with `tsc --strict`.

## How the morph works (rules, do not "optimize" away)

- All five Figma assets share the **same 17-layer structure**, so the morph is
  a per-layer point-wise interpolation between adjacent moods — never a
  cross-fade. `mood` is a single shared value 0..4 (Sad → Happy).
- Layer order matters: each petal ring has a **white 36% glass underlay** below
  its color fill; the four stacked glass layers are what make the core glow.
  The core keeps its radial gradient (animated stops), a sheen and a top-lit rim.
- The Figma conic "Core fan" sheen is approximated with a radial white gradient
  (SVG/RN have no conic gradients). Everything else matches the asset's paints.
- The hero draws on a **2× canvas** around its 280pt layout box so the blurred
  glow can overflow exactly like in Figma (the component does not clip it).
- Eyes and mouth are stroked curves, not fills — their color, width and shape
  all interpolate.
- Slider: knob center travels `t * 332` inside a 376×32 track (radius full),
  5 level dots at the stops (ramp /500 @ 50%), snap via `withSpring`.

## Open questions for devs

- Haptics on snap (e.g. `expo-haptics` selection tick) — wanted but not wired.
- Dark theme: assets exist in Figma (`Theme=Dark`); geometry pipeline is ready,
  ping design when needed.
