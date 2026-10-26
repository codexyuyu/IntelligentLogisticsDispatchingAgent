// R25: one high-resolution simulation clock, throttled React snapshots.
// Three.js reads getTime() every rendered frame, React only commits at ~12 Hz.
import { useCallback, useEffect, useRef, useState } from 'react';

export type SimClock = {
  t: number;
  playing: boolean;
  speed: number;
  getTime: () => number;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  setSpeed: (speed: number) => void;
  seek: (t: number) => void;
};

export function useSimClock(horizonS: number, autoStart = false): SimClock {
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(autoStart);
  const [speed, setSpeedState] = useState(4);
  const timeRef = useRef(0);
  const speedRef = useRef(4);
  const horizonRef = useRef(horizonS);
  horizonRef.current = Math.max(0, horizonS);

  const getTime = useCallback(() => timeRef.current, []);
  const seek = useCallback((value: number) => {
    const next = Math.max(0, Math.min(horizonRef.current, Number.isFinite(value) ? value : 0));
    timeRef.current = next;
    setT(next); // Scrubbing always updates the UI immediately.
  }, []);
  const setSpeed = useCallback((value: number) => {
    if (!Number.isFinite(value) || value <= 0 || value > 1024) return;
    speedRef.current = value;
    setSpeedState(value);
  }, []);
  const play = useCallback(() => {
    if (timeRef.current >= horizonRef.current) seek(0);
    setPlaying(true);
  }, [seek]);
  const pause = useCallback(() => {
    setPlaying(false);
    setT(timeRef.current);
  }, []);
  const toggle = useCallback(() => setPlaying((wasPlaying) => {
    if (!wasPlaying && timeRef.current >= horizonRef.current) {
      timeRef.current = 0;
      setT(0);
    }
    return !wasPlaying;
  }), []);

  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    let last = performance.now();
    let lastUi = last;
    const step = (now: number) => {
      const dt = Math.max(0, Math.min(0.1, (now - last) / 1000));
      last = now;
      timeRef.current = Math.min(horizonRef.current, timeRef.current + dt * speedRef.current);
      if (now - lastUi >= 80 || timeRef.current >= horizonRef.current) {
        setT(timeRef.current);
        lastUi = now;
      }
      if (timeRef.current >= horizonRef.current) {
        setPlaying(false);
        return;
      }
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [playing]);

  useEffect(() => {
    if (timeRef.current > horizonS) seek(horizonS);
  }, [horizonS, seek]);

  return { t, playing, speed, getTime, play, pause, toggle, setSpeed, seek };
}
