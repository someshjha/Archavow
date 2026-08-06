"use client";

import { motion, useReducedMotion } from "motion/react";

export function AmbientBackground() {
  const reduce = useReducedMotion();

  return (
    <div className="ambient" aria-hidden="true">
      <div className="ambient-grid" />
      {!reduce ? (
        <>
          <motion.div
            className="ambient-orb ambient-orb-a"
            animate={{ x: [0, 40, -20, 0], y: [0, -30, 20, 0], scale: [1, 1.08, 0.96, 1] }}
            transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="ambient-orb ambient-orb-b"
            animate={{ x: [0, -50, 30, 0], y: [0, 40, -25, 0], scale: [1, 0.92, 1.1, 1] }}
            transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
          />
        </>
      ) : (
        <>
          <div className="ambient-orb ambient-orb-a" />
          <div className="ambient-orb ambient-orb-b" />
        </>
      )}
    </div>
  );
}
