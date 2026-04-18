"use client";

import { useState, useEffect, useRef } from "react";

const MS_PER_CHAR = 15;
const MAX_DURATION_MS = 3000;

export function useTypewriter(target: string): string {
  const [revealed, setRevealed] = useState("");
  const targetRef = useRef(target);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const indexRef = useRef(0);

  useEffect(() => {
    targetRef.current = target;

    // Clear any previous interval
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
    }

    if (!target) {
      setRevealed("");
      return;
    }

    indexRef.current = 0;
    setRevealed("");

    const totalChars = target.length;
    // Calculate interval so we finish within MAX_DURATION_MS
    const interval = Math.min(MS_PER_CHAR, Math.floor(MAX_DURATION_MS / totalChars));
    // How many chars to reveal per tick to cap total duration
    const charsPerTick = Math.max(1, Math.ceil(totalChars / (MAX_DURATION_MS / MS_PER_CHAR)));

    timerRef.current = setInterval(() => {
      indexRef.current = Math.min(
        indexRef.current + charsPerTick,
        targetRef.current.length
      );
      setRevealed(targetRef.current.slice(0, indexRef.current));

      if (indexRef.current >= targetRef.current.length) {
        if (timerRef.current !== null) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
      }
    }, interval);

    return () => {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [target]);

  return revealed;
}
