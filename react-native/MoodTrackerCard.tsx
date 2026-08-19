/**
 * MoodTrackerCard — картка «How are you feeling?» (Relatio redesign)
 *
 * Стек:   react-native-reanimated 3 + expo-haptics (як у StreakScreen.tsx)
 * Дизайн: Figma «Mood Tracker Card» 18594:76721 · компоненти — стор. «↪ Mood Tracker» 18495:97231
 * Рух:    mood-animation-preview.html — усі числа нижче звідти 1:1
 * Асети:  ./assets/mood_<mood>_<theme>_{flower,glow_pulse,core}.png (+@2x/@3x)
 *
 * ПРИНЦИПИ, які не варто «оптимізувати»:
 * 1. Кожна квітка = 3 картинки: glow_pulse (світло, що дихає) ПІД flower (тіло з
 *    запеченим глоу на 80%) ПІД core (ядро + обличчя). Такий розкрій вибраний тому,
 *    що все additive-змішування з Figma лишається ВСЕРЕДИНІ картинок — інакше квітка тускніє.
 * 2. Обличчя (core) масштабується слабше за тіло (×0.55) — воно не має «дихати» разом
 *    з пелюстками, інакше риси пливуть.
 * 3. Рухаються тільки transform і opacity. Ніяких анімацій width/height.
 * 4. Кожна квітка дихає у СВОЇЙ фазі й зі своїм темпом — ряд не має пульсувати в унісон.
 * 5. Тап не залишає вибраного стану: іконка відпрацьовує характер і повертається в idle,
 *    далі екран журналу відкриває навігація (onSelect).
 * 6. Вібрація — частина руху, а не «клац». У кожного настрою своя партитура (HAPTICS),
 *    її біти стоять на тих самих мілісекундах, що й ключові кадри анімації.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  Image,
  ImageSourcePropType,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  Vibration,
  View,
  useColorScheme,
} from 'react-native';
import Animated, {
  Easing,
  SharedValue,
  cancelAnimation,
  interpolate,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import * as Haptics from 'expo-haptics';

/* ──────────────────────────────────────────────────────────────────────────
   ТОКЕНИ
   Значення — резолвнуті з Figma (Color/Semantic). У проді читати з теми DS.
   ────────────────────────────────────────────────────────────────────────── */
const TOKENS = {
  dark: {
    cardTint: 'rgba(255,255,255,0.055)', // bg/secondary @ opacity/60 поверх bg/default
    cardBorder: 'rgba(255,255,255,0.05)',
    textDefault: '#F2F3F5', // text/default
    textSecondary: '#9BA0A8', // text/secondary
    textLabel: '#D6D8DC',
    brand: '#8F7DFF', // text/brand
  },
  light: {
    cardTint: '#FFFFFF', // bg/secondary
    cardBorder: 'rgba(255,255,255,0.6)',
    textDefault: '#17181B',
    textSecondary: '#6E737C',
    textLabel: '#1E2126',
    brand: '#5A4FD6', // brand/600
  },
} as const;

const SPACE = { s4: 4, s8: 8, s12: 12, s16: 16, s20: 20, s24: 24 };
const RADIUS = { r24: 24 };
const CHIP = 72; // шасі чіпа, як у Figma (Icon Button, мода Sizing=Large)

/* ──────────────────────────────────────────────────────────────────────────
   IDLE — «дихання» + пульс світла + похитування
   ────────────────────────────────────────────────────────────────────────── */
const IDLE = {
  cycleMs: 4000, // базовий цикл дихання
  amp: 1.03, // scale тіла на піку (3%)
  coreFactor: 0.55, // ядро дихає слабше за тіло
  swayDeg: 1.6, // похитування пелюсток ±°
  swayFactor: 1.8, // цикл похитування у 1.8 разів повільніший
};

/* ──────────────────────────────────────────────────────────────────────────
   ТАЙМІНГИ ТАПУ (мс) — 1:1 з mood-animation-preview.html
   ────────────────────────────────────────────────────────────────────────── */
const PRESS_MS = 110; // прес до 0.94, поки палець тримають
const TAP_MS = { sad: 640, unpleasant: 680, neutral: 620, pleasant: 620, happy: 760 } as const;
const FX_RING_MS = 620; // ripple / кільце-глоу
const SPARK_MS = 800; // повний розліт іскор Happy (дві хвилі)

const EIO = Easing.inOut(Easing.ease);
const EOUT = Easing.out(Easing.cubic);

/* ──────────────────────────────────────────────────────────────────────────
   АСЕТИ · розміри в dp з rn-assets/manifest.json (спільний бокс на обидві теми)
   ────────────────────────────────────────────────────────────────────────── */
export type MoodKey = 'sad' | 'unpleasant' | 'neutral' | 'pleasant' | 'happy';
type ThemeKey = 'dark' | 'light';
type LayerSet = { flower: ImageSourcePropType; glow: ImageSourcePropType; core: ImageSourcePropType };

const ART: Record<MoodKey, { w: number; h: number; dark: LayerSet; light: LayerSet }> = {
  sad: {
    w: 106,
    h: 100,
    dark: {
      flower: require('./assets/mood_sad_dark_flower.png'),
      glow: require('./assets/mood_sad_dark_glow_pulse.png'),
      core: require('./assets/mood_sad_dark_core.png'),
    },
    light: {
      flower: require('./assets/mood_sad_light_flower.png'),
      glow: require('./assets/mood_sad_light_glow_pulse.png'),
      core: require('./assets/mood_sad_light_core.png'),
    },
  },
  unpleasant: {
    w: 104,
    h: 104,
    dark: {
      flower: require('./assets/mood_unpleasant_dark_flower.png'),
      glow: require('./assets/mood_unpleasant_dark_glow_pulse.png'),
      core: require('./assets/mood_unpleasant_dark_core.png'),
    },
    light: {
      flower: require('./assets/mood_unpleasant_light_flower.png'),
      glow: require('./assets/mood_unpleasant_light_glow_pulse.png'),
      core: require('./assets/mood_unpleasant_light_core.png'),
    },
  },
  neutral: {
    w: 106,
    h: 106,
    dark: {
      flower: require('./assets/mood_neutral_dark_flower.png'),
      glow: require('./assets/mood_neutral_dark_glow_pulse.png'),
      core: require('./assets/mood_neutral_dark_core.png'),
    },
    light: {
      flower: require('./assets/mood_neutral_light_flower.png'),
      glow: require('./assets/mood_neutral_light_glow_pulse.png'),
      core: require('./assets/mood_neutral_light_core.png'),
    },
  },
  pleasant: {
    w: 110,
    h: 110,
    dark: {
      flower: require('./assets/mood_pleasant_dark_flower.png'),
      glow: require('./assets/mood_pleasant_dark_glow_pulse.png'),
      core: require('./assets/mood_pleasant_dark_core.png'),
    },
    light: {
      flower: require('./assets/mood_pleasant_light_flower.png'),
      glow: require('./assets/mood_pleasant_light_glow_pulse.png'),
      core: require('./assets/mood_pleasant_light_core.png'),
    },
  },
  happy: {
    w: 114,
    h: 114,
    dark: {
      flower: require('./assets/mood_happy_dark_flower.png'),
      glow: require('./assets/mood_happy_dark_glow_pulse.png'),
      core: require('./assets/mood_happy_dark_core.png'),
    },
    light: {
      flower: require('./assets/mood_happy_light_flower.png'),
      glow: require('./assets/mood_happy_light_glow_pulse.png'),
      core: require('./assets/mood_happy_light_core.png'),
    },
  },
};

/** Десинхрон idle: множник тривалості циклу і фазовий зсув (частка циклу). */
type MoodCfg = { key: MoodKey; label: string; durMul: number; phase: number };
const MOODS: MoodCfg[] = [
  { key: 'sad', label: 'Sad', durMul: 1.0, phase: 0.0 },
  { key: 'unpleasant', label: 'Unpleasant', durMul: 1.09, phase: 0.67 },
  { key: 'neutral', label: 'Neutral', durMul: 0.96, phase: 0.35 },
  { key: 'pleasant', label: 'Pleasant', durMul: 1.15, phase: 0.78 },
  { key: 'happy', label: 'Happy', durMul: 1.04, phase: 0.5 },
];

/* ──────────────────────────────────────────────────────────────────────────
   ВІБРАЦІЯ · партитура на кожен настрій
   at — мілісекунда від відпускання пальця; збігається з ключовим кадром руху.

   iOS: Core Haptics, кожен біт — окремий чіткий тік, тому граємо всю партитуру.

   ANDROID — інша механіка, перевірено по сорсах expo-haptics
   (HapticsImpactType.kt, HapticsModule.kt):
     * impactAsync = VibrationEffect.createWaveform на 43–60 мс;
     * Soft ІДЕНТИЧНИЙ Light (50 мс @ ампл. 30/255), Rigid ІДЕНТИЧНИЙ Medium (43 мс @ 50/255),
       тобто ладу з п'яти сил там немає;
     * кожен новий vibrate() ГАСИТЬ попередній ефект → серія викликів через 75 мс
       перетворюється на один обрубок, а не на ритм.
   Тому на Android граємо ОДНИМ викликом Vibration.vibrate(pattern) —
   [пауза, вібро, пауза, вібро…]: ритм лишається чесним, а «силу» кодуємо
   тривалістю (на моторах без керування амплітудою це єдиний важіль).
   Потрібен дозвіл VIBRATE — expo-haptics додає його в маніфест сам.
   ────────────────────────────────────────────────────────────────────────── */
type Beat = { at: number; style: Haptics.ImpactFeedbackStyle };
const S = Haptics.ImpactFeedbackStyle;

export const HAPTICS: Record<
  MoodKey,
  { score: Beat[]; androidPattern: number[]; reads: string }
> = {
  sad: {
    // зіщулення (soft) + три затухаючі поштовхи = дрож
    score: [
      { at: 0, style: S.Soft },
      { at: 190, style: S.Rigid },
      { at: 265, style: S.Light },
      { at: 345, style: S.Light },
    ],
    androidPattern: [0, 45, 145, 55, 20, 30, 30, 25],
    reads: 'стиснулось і дрібно затрусилось, гасне',
  },
  unpleasant: {
    // в'янення: поштовх і два дедалі слабші — рух «опадає»
    score: [
      { at: 0, style: S.Soft },
      { at: 150, style: S.Light },
      { at: 306, style: S.Soft },
    ],
    androidPattern: [0, 45, 105, 30, 126, 20],
    reads: 'опадання, два кроки вниз',
  },
  neutral: {
    // желе + два ripple-кільця: два рівні м'які такти, як кола на воді
    score: [
      { at: 0, style: S.Light },
      { at: 140, style: S.Light },
    ],
    androidPattern: [0, 30, 110, 30],
    reads: 'два однакові такти = два кільця',
  },
  pleasant: {
    // bloom: крещендо зсередини назовні
    score: [
      { at: 0, style: S.Soft },
      { at: 110, style: S.Light },
      { at: 236, style: S.Medium },
    ],
    androidPattern: [0, 25, 85, 35, 91, 55],
    reads: 'крещендо: коротке → довше → найдовше',
  },
  happy: {
    // присідання → стрибок → дві іскри
    score: [
      { at: 114, style: S.Rigid },
      { at: 289, style: S.Medium },
      { at: 400, style: S.Light },
      { at: 470, style: S.Light },
    ],
    androidPattern: [114, 40, 135, 60, 51, 20, 50, 20],
    reads: 'антисипейшн, удар, дві іскри',
  },
};

const RING_COLOR: Partial<Record<MoodKey, Record<ThemeKey, string>>> = {
  neutral: { dark: 'rgba(127,217,217,0.65)', light: 'rgba(32,148,150,0.6)' },
  pleasant: { dark: 'rgba(126,222,166,0.55)', light: 'rgba(38,158,100,0.55)' },
  happy: { dark: 'rgba(255,216,134,0.6)', light: 'rgba(214,152,26,0.5)' },
};

const SPARK_COLORS: Record<ThemeKey, string[]> = {
  dark: ['#FFE9A8', '#FFD886', '#FFFFFF', '#FFC96B'],
  light: ['#E3A93B', '#D69417', '#B98A1E', '#E8BC55'],
};

/* ══════════════════════════════════════════════════════════════════════════
   ЧІП ОДНОГО НАСТРОЮ
   ══════════════════════════════════════════════════════════════════════════ */
type ChipProps = {
  mood: MoodCfg;
  theme: ThemeKey;
  reduceMotion: boolean;
  haptics: boolean;
  onSelect?: (mood: MoodKey) => void;
};

function MoodChip({ mood, theme, reduceMotion, haptics, onSelect }: ChipProps) {
  const art = ART[mood.key];
  const layers = art[theme];
  const c = TOKENS[theme];
  const d = TAP_MS[mood.key];

  // асет більший за шасі 72 — центруємо його вручну (без flex, щоб шари точно збіглися)
  const artBox = useMemo(
    () => ({ position: 'absolute' as const, left: (CHIP - art.w) / 2, top: (CHIP - art.h) / 2, width: art.w, height: art.h }),
    [art.w, art.h],
  );

  // idle
  const breath = useSharedValue(0); // 0 — дно вдиху, 1 — пік
  const sway = useSharedValue(0.5); // 0..1 -> -1.6°..+1.6°

  // tap
  const sx = useSharedValue(1);
  const sy = useSharedValue(1);
  const rot = useSharedValue(0); // поворот усієї квітки
  const petalRot = useSharedValue(0); // поворот тільки пелюсток (+ глоу)
  const tx = useSharedValue(0);
  const ty = useSharedValue(0);
  const bloom = useSharedValue(1); // розкриття пелюсток (Pleasant)
  const flash = useSharedValue(0); // додаткове світло замість filter: brightness

  // fx
  const ring1 = useSharedValue(0);
  const ring2 = useSharedValue(0);
  const sparks = useSharedValue(0);

  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const pressed = useRef(false);
  const clearTimers = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  /* ── idle-луп ─────────────────────────────────────────────────────────── */
  useEffect(() => {
    const cycle = IDLE.cycleMs * mood.durMul;
    const delay = cycle * mood.phase;
    breath.value = withDelay(delay, withRepeat(withTiming(1, { duration: cycle / 2, easing: EIO }), -1, true));
    if (!reduceMotion) {
      sway.value = withDelay(
        delay * IDLE.swayFactor,
        withRepeat(withTiming(1, { duration: (cycle * IDLE.swayFactor) / 2, easing: EIO }), -1, true),
      );
    } else {
      sway.value = 0.5;
    }
    return () => {
      cancelAnimation(breath);
      cancelAnimation(sway);
    };
  }, [mood.durMul, mood.phase, reduceMotion, breath, sway]);

  useEffect(() => clearTimers, [clearTimers]);

  /* ── вібрація ─────────────────────────────────────────────────────────── */
  const playHaptics = useCallback(() => {
    if (!haptics) return;
    const { score, androidPattern } = HAPTICS[mood.key];
    if (Platform.OS === 'android') {
      // один виклик на всю партитуру: послідовні vibrate() гасять один одного
      Vibration.vibrate(androidPattern);
      return;
    }
    score.forEach(({ at, style }) => {
      timers.current.push(
        setTimeout(() => {
          Haptics.impactAsync(style).catch(() => {});
        }, at),
      );
    });
  }, [haptics, mood.key]);

  /* ── характер тапу ────────────────────────────────────────────────────── */
  const playTap = useCallback(() => {
    playHaptics();

    if (reduceMotion) {
      // без руху — тільки коротке підтвердження світлом
      sx.value = withSequence(withTiming(0.97, { duration: 90 }), withTiming(1, { duration: 160 }));
      sy.value = withSequence(withTiming(0.97, { duration: 90 }), withTiming(1, { duration: 160 }));
      flash.value = withSequence(withTiming(1, { duration: 140 }), withTiming(0, { duration: 260 }));
      timers.current.push(setTimeout(() => onSelect?.(mood.key), 300));
      return;
    }

    switch (mood.key) {
      /* Sad — зіщулення + дрож, пелюстки підгинаються */
      case 'sad': {
        const squeeze = () =>
          withSequence(
            withTiming(0.88, { duration: 0.18 * d, easing: EOUT }),
            withTiming(0.88, { duration: 0.46 * d }),
            withTiming(1.03, { duration: 0.22 * d, easing: EOUT }),
            withTiming(1, { duration: 0.14 * d }),
          );
        sx.value = squeeze();
        sy.value = squeeze();
        ty.value = withSequence(
          withTiming(2, { duration: 0.18 * d, easing: EOUT }),
          withTiming(2, { duration: 0.46 * d }),
          withTiming(0, { duration: 0.36 * d, easing: EOUT }),
        );
        tx.value = withDelay(
          0.18 * d,
          withSequence(
            withTiming(-1.6, { duration: 0.12 * d, easing: EIO }),
            withTiming(1.6, { duration: 0.12 * d, easing: EIO }),
            withTiming(-1.2, { duration: 0.12 * d, easing: EIO }),
            withTiming(1, { duration: 0.1 * d, easing: EIO }),
            withTiming(0, { duration: 0.18 * d, easing: EIO }),
          ),
        );
        petalRot.value = withSequence(
          withTiming(-8, { duration: 0.3 * d, easing: EIO }),
          withTiming(-8, { duration: 0.3 * d }),
          withTiming(0, { duration: 0.4 * d, easing: EIO }),
        );
        break;
      }

      /* Unpleasant — в'янення: пелюстки хилить в один бік, потім відпускає */
      case 'unpleasant': {
        const settle = () =>
          withSequence(
            withTiming(0.97, { duration: 0.25 * d, easing: EOUT }),
            withTiming(1, { duration: 0.25 * d, easing: EOUT }),
          );
        sx.value = settle();
        sy.value = settle();
        rot.value = withSequence(
          withTiming(-4, { duration: 0.25 * d, easing: EOUT }),
          withTiming(2.5, { duration: 0.25 * d, easing: EOUT }),
          withTiming(-1, { duration: 0.25 * d, easing: EOUT }),
          withTiming(0, { duration: 0.25 * d, easing: EOUT }),
        );
        petalRot.value = withSequence(
          withTiming(-13, { duration: 0.22 * d, easing: EOUT }),
          withTiming(9, { duration: 0.23 * d, easing: EOUT }),
          withTiming(-5, { duration: 0.2 * d, easing: EOUT }),
          withTiming(2, { duration: 0.17 * d, easing: EOUT }),
          withTiming(0, { duration: 0.18 * d, easing: EOUT }),
        );
        break;
      }

      /* Neutral — желе + два кільця на воді */
      case 'neutral': {
        sx.value = withSequence(
          withTiming(1.07, { duration: 0.3 * d, easing: EIO }),
          withTiming(0.96, { duration: 0.25 * d, easing: EIO }),
          withTiming(1.02, { duration: 0.23 * d, easing: EIO }),
          withTiming(1, { duration: 0.22 * d, easing: EIO }),
        );
        sy.value = withSequence(
          withTiming(0.95, { duration: 0.3 * d, easing: EIO }),
          withTiming(1.05, { duration: 0.25 * d, easing: EIO }),
          withTiming(0.99, { duration: 0.23 * d, easing: EIO }),
          withTiming(1, { duration: 0.22 * d, easing: EIO }),
        );
        ring1.value = 0;
        ring1.value = withTiming(1, { duration: FX_RING_MS, easing: EOUT });
        ring2.value = 0;
        ring2.value = withDelay(140, withTiming(1, { duration: FX_RING_MS, easing: EOUT }));
        break;
      }

      /* Pleasant — bloom: пелюстки розкриваються, світло наростає, кільце */
      case 'pleasant': {
        bloom.value = withSequence(
          withTiming(1.24, { duration: 0.38 * d, easing: EIO }),
          withTiming(0.97, { duration: 0.34 * d, easing: EIO }),
          withTiming(1, { duration: 0.28 * d, easing: EIO }),
        );
        const swell = () =>
          withSequence(
            withTiming(1.05, { duration: 0.4 * d, easing: EIO }),
            withTiming(1, { duration: 0.6 * d, easing: EIO }),
          );
        sx.value = swell();
        sy.value = swell();
        flash.value = withSequence(
          withTiming(1, { duration: 0.4 * d, easing: EIO }),
          withTiming(0, { duration: 0.6 * d, easing: EIO }),
        );
        ring1.value = 0;
        ring1.value = withTiming(1, { duration: FX_RING_MS, easing: EOUT });
        break;
      }

      /* Happy — присідання, стрибок squash&stretch, іскри */
      case 'happy': {
        sx.value = withSequence(
          withTiming(0.92, { duration: 0.15 * d, easing: EIO }),
          withTiming(1.18, { duration: 0.23 * d, easing: EIO }),
          withTiming(0.92, { duration: 0.2 * d, easing: EIO }),
          withTiming(1.06, { duration: 0.2 * d, easing: EIO }),
          withTiming(1, { duration: 0.22 * d, easing: EIO }),
        );
        sy.value = withSequence(
          withTiming(0.86, { duration: 0.15 * d, easing: EIO }),
          withTiming(0.88, { duration: 0.23 * d, easing: EIO }),
          withTiming(1.14, { duration: 0.2 * d, easing: EIO }),
          withTiming(0.97, { duration: 0.2 * d, easing: EIO }),
          withTiming(1, { duration: 0.22 * d, easing: EIO }),
        );
        ty.value = withSequence(
          withTiming(3, { duration: 0.15 * d, easing: EIO }),
          withTiming(-2, { duration: 0.23 * d, easing: EIO }),
          withTiming(-6, { duration: 0.2 * d, easing: EIO }),
          withTiming(0, { duration: 0.42 * d, easing: EIO }),
        );
        flash.value = withSequence(
          withDelay(0.15 * d, withTiming(1, { duration: 0.23 * d, easing: EIO })),
          withTiming(0, { duration: 0.4 * d, easing: EIO }),
        );
        ring1.value = 0;
        ring1.value = withTiming(1, { duration: FX_RING_MS, easing: EOUT });
        sparks.value = 0;
        sparks.value = withTiming(1, { duration: SPARK_MS, easing: Easing.out(Easing.quad) });
        break;
      }
    }

    // після руху — навігація на екран журналу (push робить навігатор)
    timers.current.push(setTimeout(() => onSelect?.(mood.key), d));
  }, [mood.key, d, reduceMotion, onSelect, playHaptics, sx, sy, rot, petalRot, tx, ty, bloom, flash, ring1, ring2, sparks]);

  /* ── прес / відпускання ───────────────────────────────────────────────── */
  const onPressIn = useCallback(() => {
    pressed.current = true;
    // на Android selectionAsync — те саме 50 мс гудіння, що й перший біт партитури,
    // і воно б його загасило -> тік на прес-ін лишаємо тільки на iOS
    if (haptics && Platform.OS !== 'android') Haptics.selectionAsync().catch(() => {});
    sx.value = withTiming(0.94, { duration: PRESS_MS, easing: EOUT });
    sy.value = withTiming(0.94, { duration: PRESS_MS, easing: EOUT });
  }, [haptics, sx, sy]);

  // onPress = палець відпустили ВСЕРЕДИНІ чіпа -> граємо характер
  const onPress = useCallback(() => {
    pressed.current = false;
    clearTimers();
    playTap();
  }, [clearTimers, playTap]);

  // onPressOut після зсуву пальця за межі: тихо вертаємо прес назад, без характеру
  const onPressOut = useCallback(() => {
    if (!pressed.current) return;
    pressed.current = false;
    if (Platform.OS === 'android') Vibration.cancel();
    sx.value = withTiming(1, { duration: 160, easing: EOUT });
    sy.value = withTiming(1, { duration: 160, easing: EOUT });
  }, [sx, sy]);

  /* ── стилі ────────────────────────────────────────────────────────────── */
  // весь чіп: прес, squash&stretch, зсуви, поворот
  const iconStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: tx.value },
      { translateY: ty.value },
      { rotate: `${rot.value}deg` },
      { scaleX: sx.value },
      { scaleY: sy.value },
    ],
  }));

  // тіло + світло: дихання, похитування, bloom
  const bodyStyle = useAnimatedStyle(() => {
    const breathe = 1 + (IDLE.amp - 1) * breath.value;
    const swayDeg = reduceMotion ? 0 : interpolate(sway.value, [0, 1], [-IDLE.swayDeg, IDLE.swayDeg]);
    return { transform: [{ scale: breathe * bloom.value }, { rotate: `${swayDeg + petalRot.value}deg` }] };
  });

  // додаткові 20% глоу: пульс у фазі з диханням + спалах на тапі
  const glowStyle = useAnimatedStyle(() => ({
    opacity: Math.min(1, breath.value + flash.value),
  }));

  // ядро + обличчя: дихає слабше, не похитується
  const coreStyle = useAnimatedStyle(() => ({
    transform: [{ scale: 1 + (IDLE.amp - 1) * IDLE.coreFactor * breath.value }],
  }));

  const ring1Style = useAnimatedStyle(() => ({
    opacity: ring1.value === 0 || ring1.value === 1 ? 0 : interpolate(ring1.value, [0, 1], [0.75, 0]),
    transform: [{ scale: interpolate(ring1.value, [0, 1], [0.32, 1]) }],
  }));
  const ring2Style = useAnimatedStyle(() => ({
    opacity: ring2.value === 0 || ring2.value === 1 ? 0 : interpolate(ring2.value, [0, 1], [0.7, 0]),
    transform: [{ scale: interpolate(ring2.value, [0, 1], [0.32, 1]) }],
  }));

  // іскри Happy: кути фіксуємо один раз, щоб вони не «стрибали» між тапами
  const sparkSeeds = useMemo(
    () =>
      Array.from({ length: 12 }, (_, i) => {
        const wave = i < 7 ? 0 : 1;
        const a = ((wave ? i - 7 : i) / (wave ? 5 : 7)) * Math.PI * 2 + (i % 3) * 0.21;
        const r = (wave ? 58 : 40) + (i % 4) * 4;
        return { dx: Math.cos(a) * r, dy: Math.sin(a) * r, wave, size: 3 + (i % 3) };
      }),
    [],
  );

  const ringColor = RING_COLOR[mood.key]?.[theme];

  return (
    <Pressable
      onPressIn={onPressIn}
      onPress={onPress}
      onPressOut={onPressOut}
      accessibilityRole="button"
      accessibilityLabel={mood.label}
      style={styles.chip}
      hitSlop={6}
    >
      <Animated.View style={[styles.icon, iconStyle]}>
        <Animated.View style={[StyleSheet.absoluteFill, styles.overflow, bodyStyle]} pointerEvents="none">
          <Animated.View style={[artBox, glowStyle]}>
            <Image source={layers.glow} style={styles.fill} resizeMode="contain" />
          </Animated.View>
          <View style={artBox}>
            <Image source={layers.flower} style={styles.fill} resizeMode="contain" />
          </View>
        </Animated.View>

        <Animated.View style={[StyleSheet.absoluteFill, styles.overflow, coreStyle]} pointerEvents="none">
          <View style={artBox}>
            <Image source={layers.core} style={styles.fill} resizeMode="contain" />
          </View>
        </Animated.View>

        {/* ripple (Neutral) / кільце-глоу (Pleasant, Happy) */}
        {ringColor ? (
          <>
            <Animated.View style={[styles.ring, { borderColor: ringColor }, ring1Style]} pointerEvents="none" />
            {mood.key === 'neutral' ? (
              <Animated.View style={[styles.ring, { borderColor: ringColor }, ring2Style]} pointerEvents="none" />
            ) : null}
          </>
        ) : null}

        {/* іскри Happy */}
        {mood.key === 'happy'
          ? sparkSeeds.map((s, i) => <Spark key={i} seed={s} progress={sparks} theme={theme} index={i} />)
          : null}
      </Animated.View>

      <Text style={[styles.label, { color: c.textLabel }]} numberOfLines={1}>
        {mood.label}
      </Text>
    </Pressable>
  );
}

/* ── одна іскра Happy ───────────────────────────────────────────────────── */
function Spark({
  seed,
  progress,
  theme,
  index,
}: {
  seed: { dx: number; dy: number; wave: number; size: number };
  progress: SharedValue<number>;
  theme: ThemeKey;
  index: number;
}) {
  const style = useAnimatedStyle(() => {
    // друга хвиля стартує на 0.2 прогресу — «дві хвилі», як у прев'ю
    const raw = (progress.value - seed.wave * 0.2) / 0.8;
    const p = Math.max(0, Math.min(1, raw));
    return {
      opacity: p <= 0 || p >= 1 ? 0 : interpolate(p, [0, 0.35, 1], [0, 1, 0]),
      transform: [
        { translateX: seed.dx * p },
        { translateY: seed.dy * p },
        { scale: interpolate(p, [0, 0.35, 1], [0.4, 1.15, 0]) },
      ],
    };
  });
  return (
    <Animated.View
      pointerEvents="none"
      style={[
        styles.spark,
        {
          width: seed.size,
          height: seed.size,
          borderRadius: seed.size / 2,
          backgroundColor: SPARK_COLORS[theme][index % 4],
        },
        style,
      ]}
    />
  );
}

/* ══════════════════════════════════════════════════════════════════════════
   КАРТКА
   ══════════════════════════════════════════════════════════════════════════ */
export type MoodTrackerCardProps = {
  title?: string;
  subtitle?: string;
  linkLabel?: string;
  onPressLink?: () => void;
  /** Викликається після того, як іконка відпрацювала свій характер. */
  onSelect?: (mood: MoodKey) => void;
  /** Вібрація. Дефолт — увімкнена; вимикати, якщо в застосунку є свій тумблер. */
  haptics?: boolean;
  /** Форсувати тему (інакше — системна). */
  theme?: ThemeKey;
};

export function MoodTrackerCard({
  title = 'How are you feeling?',
  subtitle = 'Mood and daily reflections',
  linkLabel = 'Journal',
  onPressLink,
  onSelect,
  haptics = true,
  theme,
}: MoodTrackerCardProps) {
  const scheme = useColorScheme();
  const th: ThemeKey = theme ?? (scheme === 'light' ? 'light' : 'dark');
  const c = TOKENS[th];

  const [reduceMotion, setReduceMotion] = useState(false);
  useEffect(() => {
    let alive = true;
    AccessibilityInfo.isReduceMotionEnabled().then(v => {
      if (alive) setReduceMotion(v);
    });
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => {
      alive = false;
      sub.remove();
    };
  }, []);

  return (
    <View style={[styles.card, { backgroundColor: c.cardTint, borderColor: c.cardBorder }]}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: c.textDefault }]}>{title}</Text>
        <Pressable onPress={onPressLink} accessibilityRole="link" hitSlop={8}>
          {/* у проді замінити «›» на іконку DS (ChevronRight) */}
          <Text style={[styles.link, { color: c.brand }]}>{linkLabel} ›</Text>
        </Pressable>
      </View>
      <Text style={[styles.subtitle, { color: c.textSecondary }]}>{subtitle}</Text>

      <View style={styles.row}>
        {MOODS.map(m => (
          <MoodChip key={m.key} mood={m} theme={th} reduceMotion={reduceMotion} haptics={haptics} onSelect={onSelect} />
        ))}
      </View>
    </View>
  );
}

export default MoodTrackerCard;

/* ══════════════════════════════════════════════════════════════════════════ */
const styles = StyleSheet.create({
  card: {
    borderRadius: RADIUS.r24,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: SPACE.s16,
    paddingTop: SPACE.s20,
    paddingBottom: SPACE.s24,
  },
  head: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: SPACE.s4 },
  title: { fontFamily: 'Poppins-SemiBold', fontSize: 19, letterSpacing: 0.1 },
  link: { fontFamily: 'Poppins-Medium', fontSize: 15 },
  subtitle: {
    fontFamily: 'Poppins-Regular',
    fontSize: 14,
    marginTop: SPACE.s4,
    marginHorizontal: SPACE.s4,
    marginBottom: SPACE.s16,
  },
  row: { flexDirection: 'row', justifyContent: 'space-between' },

  chip: { width: 76, alignItems: 'center' },
  icon: { width: CHIP, height: CHIP, alignItems: 'center', justifyContent: 'center', overflow: 'visible' },
  overflow: { overflow: 'visible' },
  fill: { width: '100%', height: '100%' },
  label: { fontFamily: 'Poppins-Regular', fontSize: 13, marginTop: SPACE.s12 },

  ring: { position: 'absolute', width: 104, height: 104, borderRadius: 52, borderWidth: 1.5 },
  spark: { position: 'absolute' },
});
