/**
 * MoodLogScreen — "Choose how you've felt overall today"
 *
 * Swipe the slider knob and the mood flower morphs smoothly from one emotion
 * into the next, exactly matching the Figma "_Mood Asset" shapes at each stop.
 * Everything (gesture → shape morph → colors → background) runs on the UI
 * thread via Reanimated worklets — no JS-bridge hops while dragging.
 *
 * Figma sources:
 *   assets    — Relatio · App Design System, "_Mood Asset" 18585:111216 (Theme=Light)
 *   screens   — "📱 Mood · Log mood · Light" 19554:120350
 *   slider    — "Mood Slider" component 19579:121514 (5 level dots, knob per stop)
 *
 * Dependencies (standard trio, already in most RN projects):
 *   react-native-reanimated  >= 3.6
 *   react-native-gesture-handler >= 2.14
 *   react-native-svg         >= 15.2  (15.2+ needed for FeGaussianBlur; set
 *                                      ENABLE_BLUR = false to run on older versions)
 *
 * Usage:
 *   <MoodLogScreen onNext={(moodIndex) => ...} />
 */

import React, { useMemo } from 'react';
import { StyleSheet, Text, View, useWindowDimensions, Pressable } from 'react-native';
import { Gesture, GestureDetector, GestureHandlerRootView } from 'react-native-gesture-handler';
import Animated, {
  type SharedValue,
  Extrapolation,
  interpolate,
  interpolateColor,
  runOnJS,
  useAnimatedProps,
  useAnimatedStyle,
  useDerivedValue,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';
import Svg, {
  Circle,
  Defs,
  Ellipse,
  FeGaussianBlur,
  Filter,
  LinearGradient,
  Path,
  RadialGradient,
  Rect,
  Stop,
} from 'react-native-svg';
import {
  BG_BOTTOM,
  GLASS_OPACITY,
  MOOD_BG,
  MOOD_DOTS,
  MOOD_NAMES,
  MOOD_SHAPES,
  MOOD_TRACK,
  type ClosedKey,
  type FlashKey,
  type StrokeKey,
} from './moodShapes';

// ————————————————————————————————————————————————————————— config

/** FeGaussianBlur needs react-native-svg >= 15.2 (new architecture). */
const ENABLE_BLUR = true;

const MOOD_INPUT = [0, 1, 2, 3, 4];
const SPRING = { damping: 18, stiffness: 180, mass: 0.6 };

const AnimatedPath = Animated.createAnimatedComponent(Path);
const AnimatedEllipse = Animated.createAnimatedComponent(Ellipse);
const AnimatedCircle = Animated.createAnimatedComponent(Circle);
const AnimatedStop = Animated.createAnimatedComponent(Stop);

// ————————————————————————————————————————————————— worklet helpers

/** Interpolate two flat [x0,y0,x1,y1,…] arrays and emit an SVG path. */
function morphPath(mood: number, series: number[][], closed: boolean): string {
  'worklet';
  const i = Math.min(Math.floor(mood), 3);
  const f = mood - i;
  const a = series[i];
  const b = series[i + 1];
  const n = a.length;
  let d = '';
  for (let k = 0; k < n; k += 2) {
    const x = a[k] + (b[k] - a[k]) * f;
    const y = a[k + 1] + (b[k + 1] - a[k + 1]) * f;
    d += (k === 0 ? 'M' : 'L') + x.toFixed(1) + ' ' + y.toFixed(1);
  }
  return closed ? d + 'Z' : d;
}

function lerpAt(mood: number, values: number[]): number {
  'worklet';
  return interpolate(mood, MOOD_INPUT, values, Extrapolation.CLAMP);
}

// ————————————————————————————————————————————— morphing hero layers

type SharedMood = SharedValue<number>;

/** Frosted-glass underlay for a petal ring (Figma "Petals N · glass"). */
const GlassMorph = ({ mood, k }: { mood: SharedMood; k: ClosedKey }) => {
  const series = useMemo(() => MOOD_SHAPES.map((m) => m[k].pts), [k]);
  const props = useAnimatedProps(() => ({ d: morphPath(mood.value, series, true) }));
  return <AnimatedPath animatedProps={props} fill="#ffffff" fillOpacity={GLASS_OPACITY} />;
};

/**
 * The glassy core on top of the petal stack (Figma "Core" + "Core fan" +
 * "Core light edge"). The conic sheen fan is approximated with a radial
 * white gradient; the rim keeps its top-lit linear-gradient stroke.
 */
const CoreMorph = ({ mood }: { mood: SharedMood }) => {
  const cores = useMemo(() => MOOD_SHAPES.map((m) => m.core), []);
  const series = useMemo(() => cores.map((c) => c.pts), [cores]);
  const fillProps = useAnimatedProps(() => ({
    d: morphPath(mood.value, series, true),
    opacity: 0.2 * lerpAt(mood.value, cores.map((c) => c.op)), // paintOp 0.2 × layer op
  }));
  const sheenProps = useAnimatedProps(() => ({ d: morphPath(mood.value, series, true) }));
  const edgeProps = useAnimatedProps(() => ({
    d: morphPath(mood.value, series, true),
    strokeWidth: lerpAt(mood.value, cores.map((c) => c.strokeW)),
  }));
  const stop = (idx: number) =>
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useAnimatedProps(() => ({
      stopColor: interpolateColor(mood.value, MOOD_INPUT, cores.map((c) => c.stops[idx])),
    }));
  const c0 = stop(0);
  const c1 = stop(1);
  const c2 = stop(2);
  return (
    <>
      <Defs>
        <RadialGradient id="coreGrad" cx="50%" cy="45%" r="60%">
          <AnimatedStop offset="0" animatedProps={c0} />
          <AnimatedStop offset="0.6" animatedProps={c1} />
          <AnimatedStop offset="1" animatedProps={c2} />
        </RadialGradient>
        <RadialGradient id="sheenGrad" cx="50%" cy="45%" r="55%">
          <Stop offset="0" stopColor="#ffffff" stopOpacity="0.5" />
          <Stop offset="0.7" stopColor="#ffffff" stopOpacity="0.06" />
          <Stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </RadialGradient>
        <LinearGradient id="edgeGrad" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#ffffff" stopOpacity="0.6" />
          <Stop offset="0.5" stopColor="#ffffff" stopOpacity="0.14" />
          <Stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </LinearGradient>
      </Defs>
      <AnimatedPath animatedProps={fillProps} fill="url(#coreGrad)" />
      <AnimatedPath animatedProps={sheenProps} fill="url(#sheenGrad)" opacity={0.35} />
      <AnimatedPath animatedProps={edgeProps} fill="none" stroke="url(#edgeGrad)" strokeLinecap="round" />
    </>
  );
};

const ClosedMorph = ({ mood, k, filter }: { mood: SharedMood; k: ClosedKey; filter?: string }) => {
  const series = useMemo(() => MOOD_SHAPES.map((m) => m[k].pts), [k]);
  const fills = useMemo(() => MOOD_SHAPES.map((m) => m[k].fill), [k]);
  const ops = useMemo(() => MOOD_SHAPES.map((m) => m[k].op), [k]);
  const props = useAnimatedProps(() => ({
    d: morphPath(mood.value, series, true),
    fill: interpolateColor(mood.value, MOOD_INPUT, fills),
    opacity: lerpAt(mood.value, ops),
  }));
  return <AnimatedPath animatedProps={props} filter={filter} />;
};

const StrokeMorph = ({ mood, k, filter }: { mood: SharedMood; k: StrokeKey; filter?: string }) => {
  const series = useMemo(() => MOOD_SHAPES.map((m) => m[k].pts), [k]);
  const strokes = useMemo(() => MOOD_SHAPES.map((m) => m[k].stroke), [k]);
  const ops = useMemo(() => MOOD_SHAPES.map((m) => m[k].op), [k]);
  const widths = useMemo(() => MOOD_SHAPES.map((m) => m[k].w), [k]);
  const props = useAnimatedProps(() => ({
    d: morphPath(mood.value, series, false),
    stroke: interpolateColor(mood.value, MOOD_INPUT, strokes),
    opacity: lerpAt(mood.value, ops),
    strokeWidth: lerpAt(mood.value, widths),
  }));
  return (
    <AnimatedPath
      animatedProps={props}
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      filter={filter}
    />
  );
};

const FlashMorph = ({ mood, k, filter }: { mood: SharedMood; k: FlashKey; filter?: string }) => {
  const L = useMemo(() => MOOD_SHAPES.map((m) => m[k]), [k]);
  const fills = useMemo(() => L.map((l) => l.fill), [L]);
  const props = useAnimatedProps(() => {
    const cx = lerpAt(mood.value, L.map((l) => l.cx));
    const cy = lerpAt(mood.value, L.map((l) => l.cy));
    const rot = lerpAt(mood.value, L.map((l) => l.rot));
    return {
      cx,
      cy,
      rx: lerpAt(mood.value, L.map((l) => l.rx)),
      ry: lerpAt(mood.value, L.map((l) => l.ry)),
      opacity: lerpAt(mood.value, L.map((l) => l.op)),
      fill: fills[0].startsWith('url') ? undefined : interpolateColor(mood.value, MOOD_INPUT, fills),
      transform: `rotate(${rot.toFixed(1)} ${cx.toFixed(1)} ${cy.toFixed(1)})`,
    };
  });
  return <AnimatedEllipse animatedProps={props} filter={filter} fill={fills[0].startsWith('url') ? 'url(#specGrad)' : undefined} />;
};

/**
 * The morphing flower with the face. `size` is the layout box (280 on the
 * screen — the 56pt Figma asset at rescale ×5). The SVG canvas is drawn at
 * 2×size so the soft glow can overflow the box exactly like in Figma, where
 * the component does not clip its blurred layers.
 */
export const MoodMorphHero = ({ mood, size = 280 }: { mood: SharedMood; size?: number }) => {
  const glows = useMemo(() => MOOD_SHAPES.map((m) => m.glow), []);
  const glowProps = useAnimatedProps(() => ({
    cx: lerpAt(mood.value, glows.map((g) => g.cx)),
    cy: lerpAt(mood.value, glows.map((g) => g.cy)),
    r: lerpAt(mood.value, glows.map((g) => g.r)),
    opacity: lerpAt(mood.value, glows.map((g) => g.op)),
  }));
  const glowStop = (idx: number) =>
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useAnimatedProps(() => ({
      stopColor: interpolateColor(mood.value, MOOD_INPUT, glows.map((g) => g.stops[idx].c)),
      stopOpacity: lerpAt(mood.value, glows.map((g) => g.stops[idx].o)),
    }));
  const s0 = glowStop(0);
  const s1 = glowStop(1);
  const s2 = glowStop(2);

  const f = (id: string) => (ENABLE_BLUR ? `url(#${id})` : undefined);

  return (
    <View style={{ width: size, height: size, overflow: 'visible' }}>
      <Svg
        width={size * 2}
        height={size * 2}
        viewBox="-56 -56 112 112"
        style={{ position: 'absolute', left: -size / 2, top: -size / 2 }}
      >
      <Defs>
        {ENABLE_BLUR && (
          <>
            {/* stdDeviation taken from the Figma export (Neutral variant) */}
            <Filter id="bInner" x="-60%" y="-60%" width="220%" height="220%">
              <FeGaussianBlur stdDeviation={12.8} />
            </Filter>
            <Filter id="bGlow" x="-60%" y="-60%" width="220%" height="220%">
              <FeGaussianBlur stdDeviation={3.2} />
            </Filter>
            <Filter id="bForm" x="-60%" y="-60%" width="220%" height="220%">
              <FeGaussianBlur stdDeviation={4.9} />
            </Filter>
            <Filter id="bPetal" x="-30%" y="-30%" width="160%" height="160%">
              <FeGaussianBlur stdDeviation={0.93} />
            </Filter>
            <Filter id="bFlash" x="-120%" y="-120%" width="340%" height="340%">
              <FeGaussianBlur stdDeviation={2.05} />
            </Filter>
            <Filter id="bSpec" x="-60%" y="-60%" width="220%" height="220%">
              <FeGaussianBlur stdDeviation={0.42} />
            </Filter>
          </>
        )}
        <RadialGradient id="glowGrad" cx="50%" cy="50%" r="50%">
          <AnimatedStop offset="0.71" animatedProps={s0} />
          <AnimatedStop offset="0.85" animatedProps={s1} />
          <AnimatedStop offset="1" animatedProps={s2} />
        </RadialGradient>
        <RadialGradient id="specGrad" cx="50%" cy="50%" r="50%">
          <Stop offset="0" stopColor="#ffffff" stopOpacity="0.9" />
          <Stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </RadialGradient>
      </Defs>

      {/* soft ambient light behind everything */}
      <ClosedMorph mood={mood} k="innerLight" filter={f('bInner')} />
      <AnimatedCircle animatedProps={glowProps} fill="url(#glowGrad)" filter={f('bGlow')} />
      <ClosedMorph mood={mood} k="formGlow" filter={f('bForm')} />

      {/* four stacked petal rings, each with its frosted-glass underlay —
          the stacked white glass is what makes the core luminous */}
      <GlassMorph mood={mood} k="petals0" />
      <ClosedMorph mood={mood} k="petals0" filter={f('bPetal')} />
      <GlassMorph mood={mood} k="petals1" />
      <ClosedMorph mood={mood} k="petals1" filter={f('bPetal')} />
      <GlassMorph mood={mood} k="petals2" />
      <ClosedMorph mood={mood} k="petals2" filter={f('bPetal')} />
      <GlassMorph mood={mood} k="petals3" />
      <ClosedMorph mood={mood} k="petals3" filter={f('bPetal')} />

      {/* glassy core with radial gradient, sheen and top-lit rim */}
      <CoreMorph mood={mood} />

      {/* colored light accents + specular highlight */}
      <FlashMorph mood={mood} k="flashBlue" filter={f('bFlash')} />
      <FlashMorph mood={mood} k="flashWarm" filter={f('bFlash')} />
      <FlashMorph mood={mood} k="flashMint" filter={f('bFlash')} />
      <FlashMorph mood={mood} k="specular" filter={f('bSpec')} />

      {/* the face */}
      <StrokeMorph mood={mood} k="eyeL" />
      <StrokeMorph mood={mood} k="eyeR" />
      <StrokeMorph mood={mood} k="mouth" />
      <StrokeMorph mood={mood} k="eyeLightL" />
      <StrokeMorph mood={mood} k="eyeLightR" />
      <StrokeMorph mood={mood} k="mouthLight" />
      </Svg>
    </View>
  );
};

// ———————————————————————————————————————————————————— mood slider

const TRACK_H = 32;
const KNOB = 44;
const DOT = 6;

/**
 * Emotion-tinted slider with 5 level dots (Figma "Mood Slider" 19579:121514).
 * Knob drags freely, morph follows continuously, release snaps to the nearest
 * of the five stops.
 */
export const MoodSlider = ({
  mood,
  width,
  onSettle,
}: {
  mood: SharedMood;
  width: number;
  onSettle?: (index: number) => void;
}) => {
  const travel = width - KNOB; // knob center range, matches Figma's t*332
  const startMood = useSharedValue(0);

  const pan = Gesture.Pan()
    .onStart(() => {
      startMood.value = mood.value;
    })
    .onChange((e) => {
      const next = startMood.value + (e.translationX / travel) * 4;
      mood.value = Math.min(4, Math.max(0, next));
    })
    .onEnd(() => {
      const snapped = Math.round(mood.value);
      mood.value = withSpring(snapped, SPRING);
      if (onSettle) runOnJS(onSettle)(snapped);
    });

  const tap = Gesture.Tap().onEnd((e) => {
    const next = Math.round(((e.x - KNOB / 2) / travel) * 4);
    mood.value = withSpring(Math.min(4, Math.max(0, next)), SPRING);
    if (onSettle) runOnJS(onSettle)(Math.min(4, Math.max(0, next)));
  });

  const trackStyle = useAnimatedStyle(() => ({
    backgroundColor: interpolateColor(mood.value, MOOD_INPUT, MOOD_TRACK),
  }));
  const knobStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: (mood.value / 4) * travel }],
  }));

  return (
    <GestureDetector gesture={Gesture.Simultaneous(tap, pan)}>
      <Animated.View style={[styles.track, { width }, trackStyle]}>
        {MOOD_INPUT.map((i) => (
          <MoodDot key={i} mood={mood} index={i} x={KNOB / 2 + (i / 4) * travel - DOT / 2} />
        ))}
        <Animated.View style={[styles.knob, knobStyle]} />
      </Animated.View>
    </GestureDetector>
  );
};

const MoodDot = ({ mood, index, x }: { mood: SharedMood; index: number; x: number }) => {
  const style = useAnimatedStyle(() => ({
    backgroundColor: interpolateColor(mood.value, MOOD_INPUT, MOOD_DOTS),
  }));
  return <Animated.View style={[styles.dot, { left: x }, style]} />;
};

// ————————————————————————————————————————————————————— full screen

export const MoodLogScreen = ({ onNext }: { onNext?: (moodIndex: number) => void }) => {
  const { width } = useWindowDimensions();
  const mood = useSharedValue(2); // start at Neutral

  const bgStyle = useAnimatedStyle(() => ({
    backgroundColor: interpolateColor(mood.value, MOOD_INPUT, MOOD_BG),
  }));

  const handleNext = () => onNext?.(Math.round(mood.value));

  return (
    <GestureHandlerRootView style={styles.root}>
      {/* emotion-colored gradient: ramp tone on top → bg/default at the bottom,
          mirroring the Figma screens (gradient stop 0 → 0.9). The colored layer
          fades via a static white-to-transparent overlay, so only one animated
          color is needed. */}
      <Animated.View style={[StyleSheet.absoluteFill, bgStyle]} />
      <Svg style={StyleSheet.absoluteFill} width="100%" height="100%">
        <Defs>
          <LinearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor={BG_BOTTOM} stopOpacity="0" />
            <Stop offset="0.9" stopColor={BG_BOTTOM} stopOpacity="1" />
          </LinearGradient>
        </Defs>
        <Rect width="100%" height="100%" fill="url(#fade)" />
      </Svg>

      <View style={styles.content}>
        <Text style={styles.heading}>Choose how you’ve felt{'\n'}overall today</Text>

        <View style={styles.heroBox}>
          <MoodMorphHero mood={mood} size={280} />
        </View>

        <MoodLabel mood={mood} />

        <View style={styles.sliderBlock}>
          <MoodSlider mood={mood} width={Math.min(width, 440) - 64} />
          <View style={[styles.edgeLabels, { width: Math.min(width, 440) - 64 }]}>
            <Text style={styles.edgeLabel}>VERY UNPLEASANT</Text>
            <Text style={styles.edgeLabel}>VERY PLEASANT</Text>
          </View>
        </View>

        <Pressable style={styles.cta} onPress={handleNext}>
          <Text style={styles.ctaLabel}>Next</Text>
        </Pressable>
      </View>
    </GestureHandlerRootView>
  );
};

/** Cross-fading mood name under the hero. */
const MoodLabel = ({ mood }: { mood: SharedMood }) => (
  <View style={styles.labelBox}>
    {MOOD_NAMES.map((name, i) => {
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const style = useAnimatedStyle(() => ({
        opacity: interpolate(mood.value, [i - 0.5, i, i + 0.5], [0, 1, 0], Extrapolation.CLAMP),
      }));
      return (
        <Animated.Text key={name} style={[styles.moodLabel, style]}>
          {name}
        </Animated.Text>
      );
    })}
  </View>
);

// —————————————————————————————————————————————————————————— styles

const styles = StyleSheet.create({
  root: { flex: 1 },
  content: { flex: 1, alignItems: 'center', paddingTop: 90, paddingHorizontal: 16 },
  heading: {
    fontFamily: 'Poppins-Medium', // Heading/Large
    fontSize: 24,
    lineHeight: 32,
    textAlign: 'center',
    color: '#0c0d11', // text/default (Light)
  },
  heroBox: { marginTop: 60, height: 280, justifyContent: 'center' },
  labelBox: { marginTop: 44, height: 40, alignSelf: 'stretch' },
  moodLabel: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    fontFamily: 'Poppins-Medium', // Display/Small/Medium
    fontSize: 30,
    lineHeight: 40,
    textAlign: 'center',
    color: '#0c0d11',
  },
  sliderBlock: { marginTop: 40, alignItems: 'center' },
  track: {
    height: TRACK_H,
    borderRadius: TRACK_H / 2, // radius/full
    justifyContent: 'center',
  },
  dot: {
    position: 'absolute',
    width: DOT,
    height: DOT,
    borderRadius: DOT / 2,
    opacity: 0.5, // opacity/50, matches the Figma level dots
  },
  knob: {
    position: 'absolute',
    width: KNOB,
    height: KNOB,
    borderRadius: KNOB / 2,
    backgroundColor: '#f9fafd', // bg/default (Light)
    shadowColor: '#000',
    shadowOpacity: 0.18,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 4,
  },
  edgeLabels: { marginTop: 16, flexDirection: 'row', justifyContent: 'space-between' },
  edgeLabel: {
    fontFamily: 'Poppins-Medium', // Body/Small/Medium
    fontSize: 12,
    letterSpacing: 0.4,
    color: '#6a6b74', // text/secondary (Light)
  },
  cta: {
    marginTop: 'auto',
    marginBottom: 48,
    alignSelf: 'stretch',
    height: 56,
    borderRadius: 28,
    backgroundColor: '#0c0d11', // Button Primary
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaLabel: {
    fontFamily: 'Poppins-Medium',
    fontSize: 16,
    color: '#f9fafd',
  },
});

export default MoodLogScreen;
