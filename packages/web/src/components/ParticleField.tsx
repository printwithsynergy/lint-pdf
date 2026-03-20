"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Animated particle field — floating dots/sparkles
 * that drift like pixie dust, themed to brand blues.
 * Cranked up for visibility on white backgrounds.
 * Only renders on md+ screens to avoid iOS canvas rendering bugs.
 */
export function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    setIsDesktop(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // skipcq: JS-0045 — useEffect legitimately returns undefined (no cleanup) or a cleanup function
  useEffect(() => {
    if (!isDesktop) return undefined;

    const cvs = canvasRef.current;
    if (!cvs) return undefined;

    const cx = cvs.getContext("2d");
    if (!cx) return undefined;

    // Alias to const bindings that TypeScript narrows as non-null
    // (nested functions don't benefit from the narrowing above).
    const canvas: HTMLCanvasElement = cvs;
    const ctx: CanvasRenderingContext2D = cx;

    let animationId: number;
    let particles: Particle[] = [];

    const PARTICLE_COUNT = 110;
    const COLORS = [
      "rgba(22, 45, 96, 0.55)", // brand-900 — deep navy
      "rgba(59, 111, 181, 0.50)", // brand-700
      "rgba(83, 149, 206, 0.55)", // brand-500
      "rgba(120, 188, 225, 0.45)", // brand-400
      "rgba(149, 208, 235, 0.40)", // brand-300
      "rgba(59, 111, 181, 0.35)", // brand-700 softer
    ];
    const GLOW_COLORS = [
      "rgba(83, 149, 206, 0.12)",
      "rgba(120, 188, 225, 0.10)",
      "rgba(22, 45, 96, 0.08)",
    ];

    interface Particle {
      x: number;
      y: number;
      size: number;
      speedX: number;
      speedY: number;
      color: string;
      glowColor: string;
      opacity: number;
      pulse: number;
      kind: "dot" | "sparkle" | "diamond";
    }

    function resize() {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    }

    function createParticle(): Particle {
      const kinds: Particle["kind"][] = [
        "dot",
        "dot",
        "dot",
        "sparkle",
        "sparkle",
        "diamond",
      ];
      return {
        x: Math.random() * canvas.offsetWidth,
        y: Math.random() * canvas.offsetHeight,
        size: Math.random() * 3.5 + 1,
        speedX: (Math.random() - 0.5) * 0.4,
        speedY: -Math.random() * 0.3 - 0.08,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        glowColor: GLOW_COLORS[Math.floor(Math.random() * GLOW_COLORS.length)],
        opacity: Math.random() * 0.5 + 0.4,
        pulse: Math.random() * Math.PI * 2,
        kind: kinds[Math.floor(Math.random() * kinds.length)],
      };
    }

    function init() {
      resize();
      particles = Array.from({ length: PARTICLE_COUNT }, createParticle);
    }

    function drawDiamond(px: number, py: number, r: number) {
      ctx.beginPath();
      ctx.moveTo(px, py - r);
      ctx.lineTo(px + r * 0.6, py);
      ctx.lineTo(px, py + r);
      ctx.lineTo(px - r * 0.6, py);
      ctx.closePath();
      ctx.fill();
    }

    function draw() {
      const width = canvas.offsetWidth;
      const height = canvas.offsetHeight;

      ctx.clearRect(0, 0, width, height);

      for (const p of particles) {
        p.x += p.speedX;
        p.y += p.speedY;
        p.pulse += 0.02;

        const twinkle = Math.sin(p.pulse) * 0.3 + 0.7;

        // Wrap around
        if (p.y < -10) {
          p.y = height + 10;
          p.x = Math.random() * width;
        }
        if (p.x < -10) p.x = width + 10;
        if (p.x > width + 10) p.x = -10;

        const sz = p.size * twinkle;
        const alpha = p.opacity * twinkle;

        // Soft glow halo behind larger particles
        if (p.size > 2) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, sz * 4, 0, Math.PI * 2);
          ctx.fillStyle = p.glowColor;
          ctx.globalAlpha = alpha * 0.5;
          ctx.fill();
        }

        ctx.globalAlpha = alpha;
        ctx.fillStyle = p.color;

        if (p.kind === "dot") {
          ctx.beginPath();
          ctx.arc(p.x, p.y, sz, 0, Math.PI * 2);
          ctx.fill();
        } else if (p.kind === "diamond") {
          drawDiamond(p.x, p.y, sz * 1.4);
        } else {
          // Sparkle — 4-point star cross
          ctx.beginPath();
          ctx.arc(p.x, p.y, sz * 0.6, 0, Math.PI * 2);
          ctx.fill();

          ctx.globalAlpha = alpha * 0.7;
          ctx.strokeStyle = p.color;
          ctx.lineWidth = 0.8;
          ctx.beginPath();
          ctx.moveTo(p.x - sz * 3, p.y);
          ctx.lineTo(p.x + sz * 3, p.y);
          ctx.moveTo(p.x, p.y - sz * 3);
          ctx.lineTo(p.x, p.y + sz * 3);
          ctx.stroke();
        }
      }

      ctx.globalAlpha = 1;
      animationId = requestAnimationFrame(draw);
    }

    init();
    draw();

    window.addEventListener("resize", init);
    return () => {
      window.removeEventListener("resize", init);
      cancelAnimationFrame(animationId);
    };
  }, [isDesktop]);

  if (!isDesktop) {
    return <MobileParticles />;
  }

  return (
    <div className="absolute inset-0 w-full h-full pointer-events-none">
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ background: "transparent" }}
        aria-hidden="true"
      />
    </div>
  );
}

/**
 * CSS-only floating dots for mobile — no canvas, no iOS bugs.
 * Uses CSS keyframe animations for drift and pulse effects.
 */
const MOBILE_DOTS = [
  {
    top: "12%",
    left: "8%",
    size: 4,
    color: "bg-brand-500/50",
    delay: "0s",
    duration: "7s",
    anim: "particle-drift",
  },
  {
    top: "25%",
    left: "75%",
    size: 3,
    color: "bg-brand-700/40",
    delay: "1.2s",
    duration: "8s",
    anim: "particle-drift-alt",
  },
  {
    top: "45%",
    left: "15%",
    size: 5,
    color: "bg-brand-400/45",
    delay: "0.5s",
    duration: "9s",
    anim: "particle-drift",
  },
  {
    top: "60%",
    left: "85%",
    size: 3,
    color: "bg-brand-900/35",
    delay: "2s",
    duration: "7.5s",
    anim: "particle-drift-alt",
  },
  {
    top: "35%",
    left: "50%",
    size: 4,
    color: "bg-brand-500/40",
    delay: "1.8s",
    duration: "8.5s",
    anim: "particle-drift",
  },
  {
    top: "70%",
    left: "30%",
    size: 3,
    color: "bg-brand-300/50",
    delay: "0.8s",
    duration: "7s",
    anim: "particle-drift-alt",
  },
  {
    top: "18%",
    left: "60%",
    size: 5,
    color: "bg-brand-700/35",
    delay: "3s",
    duration: "9.5s",
    anim: "particle-drift",
  },
  {
    top: "80%",
    left: "45%",
    size: 3,
    color: "bg-brand-400/40",
    delay: "1.5s",
    duration: "8s",
    anim: "particle-drift-alt",
  },
  {
    top: "50%",
    left: "90%",
    size: 4,
    color: "bg-brand-500/45",
    delay: "2.5s",
    duration: "7.5s",
    anim: "particle-drift",
  },
  {
    top: "8%",
    left: "40%",
    size: 3,
    color: "bg-brand-300/40",
    delay: "0.3s",
    duration: "8.5s",
    anim: "particle-drift-alt",
  },
  {
    top: "55%",
    left: "5%",
    size: 4,
    color: "bg-brand-700/30",
    delay: "3.5s",
    duration: "9s",
    anim: "particle-drift",
  },
  {
    top: "40%",
    left: "70%",
    size: 3,
    color: "bg-brand-900/25",
    delay: "1s",
    duration: "7s",
    anim: "particle-drift-alt",
  },
  {
    top: "15%",
    left: "25%",
    size: 2,
    color: "bg-brand-500/50",
    delay: "2.2s",
    duration: "6s",
    anim: "particle-pulse",
  },
  {
    top: "65%",
    left: "55%",
    size: 2,
    color: "bg-brand-400/50",
    delay: "4s",
    duration: "5s",
    anim: "particle-pulse",
  },
  {
    top: "30%",
    left: "92%",
    size: 2,
    color: "bg-brand-700/40",
    delay: "1.5s",
    duration: "6.5s",
    anim: "particle-pulse",
  },
] as const;

function MobileParticles() {
  return (
    <div
      className="absolute inset-0 w-full h-full pointer-events-none overflow-hidden"
      aria-hidden="true"
    >
      {MOBILE_DOTS.map((dot, i) => (
        <div
          key={`dot-${dot.top}-${dot.left}`}
          className={`absolute rounded-full ${dot.color}`}
          style={{
            top: dot.top,
            left: dot.left,
            width: dot.size,
            height: dot.size,
            animation: `${dot.anim} ${dot.duration} ${dot.delay} infinite ease-in-out`,
          }}
        />
      ))}
    </div>
  );
}
