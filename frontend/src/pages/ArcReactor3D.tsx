import { useEffect, useRef, useState } from "react";

// 3D Arc Reactor - canvas-based holographic Iron Man arc reactor
// No Three.js needed for MSI size, pure canvas with 3D illusion

export default function ArcReactor3D({ size = 220, power = 97.3 }: { size?: number; power?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const [hover, setHover] = useState(false);
  const [currentPower, setCurrentPower] = useState(power);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let pulse = 0;
    let rot = 0;

    const draw = () => {
      pulse += 0.04;
      rot += hover ? 0.03 : 0.01;
      setCurrentPower(97.3 + Math.sin(pulse * 0.5) * 0.5);

      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;
      const base = size / 2;

      ctx.clearRect(0, 0, w, h);

      // Background glow
      const bgGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, base + 20);
      bgGrad.addColorStop(0, `rgba(6, 182, 212, ${0.15 + Math.sin(pulse) * 0.05})`);
      bgGrad.addColorStop(0.5, `rgba(6, 182, 212, 0.05)`);
      bgGrad.addColorStop(1, `rgba(0,0,0,0)`);
      ctx.fillStyle = bgGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, base + 20, 0, Math.PI * 2);
      ctx.fill();

      // Outer housing — metallic
      ctx.strokeStyle = `rgba(100, 116, 139, ${0.6 + Math.sin(pulse) * 0.1})`;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(cx, cy, base, 0, Math.PI * 2);
      ctx.stroke();

      // Inner outer ring
      ctx.strokeStyle = `rgba(6, 182, 212, 0.4)`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, base - 5, 0, Math.PI * 2);
      ctx.stroke();

      // 12 segments like real arc reactor
      for (let i = 0; i < 12; i++) {
        const angle = (i / 12) * Math.PI * 2 + rot * 0.2;
        const r1 = base - 15;
        const r2 = base - 35;
        const x1 = cx + Math.cos(angle) * r1;
        const y1 = cy + Math.sin(angle) * r1;
        const x2 = cx + Math.cos(angle) * r2;
        const y2 = cy + Math.sin(angle) * r2;

        ctx.strokeStyle = `rgba(6, 182, 212, ${0.3 + Math.sin(pulse + i) * 0.2})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // Middle ring — energy
      const midR = base - 45;
      ctx.strokeStyle = `rgba(6, 182, 212, ${0.8 + Math.sin(pulse) * 0.2})`;
      ctx.lineWidth = 2;
      ctx.shadowColor = "#06b6d4";
      ctx.shadowBlur = 15;
      ctx.beginPath();
      ctx.arc(cx, cy, midR, 0, Math.PI * 2);
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Rotating energy segments — 3 prongs
      for (let i = 0; i < 3; i++) {
        const angle = (i / 3) * Math.PI * 2 + rot;
        const innerR = 20;
        const outerR = midR - 10;

        const grad = ctx.createLinearGradient(
          cx + Math.cos(angle) * innerR,
          cy + Math.sin(angle) * innerR,
          cx + Math.cos(angle) * outerR,
          cy + Math.sin(angle) * outerR
        );
        grad.addColorStop(0, `rgba(255, 255, 255, 0.9)`);
        grad.addColorStop(0.3, `rgba(6, 182, 212, 0.8)`);
        grad.addColorStop(1, `rgba(6, 182, 212, 0.3)`);

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(angle - 0.15) * innerR, cy + Math.sin(angle - 0.15) * innerR);
        ctx.lineTo(cx + Math.cos(angle - 0.1) * outerR, cy + Math.sin(angle - 0.1) * outerR);
        ctx.lineTo(cx + Math.cos(angle + 0.1) * outerR, cy + Math.sin(angle + 0.1) * outerR);
        ctx.lineTo(cx + Math.cos(angle + 0.15) * innerR, cy + Math.sin(angle + 0.15) * innerR);
        ctx.closePath();
        ctx.fill();
      }

      // Inner core — pulsing
      const corePulse = 18 + Math.sin(pulse) * 3;
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, corePulse + 10);
      coreGrad.addColorStop(0, `rgba(255, 255, 255, 0.95)`);
      coreGrad.addColorStop(0.2, `rgba(6, 182, 212, 0.9)`);
      coreGrad.addColorStop(0.5, `rgba(6, 182, 212, 0.6)`);
      coreGrad.addColorStop(1, `rgba(6, 182, 212, 0)`);

      ctx.fillStyle = coreGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, corePulse + 10, 0, Math.PI * 2);
      ctx.fill();

      // Core solid
      ctx.fillStyle = `rgba(255, 255, 255, ${0.9 + Math.sin(pulse) * 0.1})`;
      ctx.shadowColor = "#06b6d4";
      ctx.shadowBlur = 20;
      ctx.beginPath();
      ctx.arc(cx, cy, corePulse, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;

      // Inner ring
      ctx.strokeStyle = `rgba(255, 255, 255, 0.6)`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, 28, 0, Math.PI * 2);
      ctx.stroke();

      // Energy lines radiating
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + rot * 0.5;
        const len = 5 + Math.sin(pulse + i) * 3;
        const x1 = cx + Math.cos(angle) * (midR + 5);
        const y1 = cy + Math.sin(angle) * (midR + 5);
        const x2 = cx + Math.cos(angle) * (midR + 5 + len);
        const y2 = cy + Math.sin(angle) * (midR + 5 + len);

        ctx.strokeStyle = `rgba(6, 182, 212, ${0.2 + Math.sin(pulse + i) * 0.1})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // Tick marks around
      for (let i = 0; i < 48; i++) {
        const angle = (i / 48) * Math.PI * 2;
        const isMajor = i % 4 === 0;
        const r1 = base + (isMajor ? 3 : 1);
        const r2 = base + (isMajor ? 8 : 4);
        const x1 = cx + Math.cos(angle) * r1;
        const y1 = cy + Math.sin(angle) * r1;
        const x2 = cx + Math.cos(angle) * r2;
        const y2 = cy + Math.sin(angle) * r2;

        ctx.strokeStyle = isMajor ? `rgba(6, 182, 212, 0.6)` : `rgba(100, 116, 139, 0.3)`;
        ctx.lineWidth = isMajor ? 1.5 : 0.5;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      animRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => cancelAnimationFrame(animRef.current);
  }, [size, hover]);

  return (
    <div
      className="relative flex flex-col items-center"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <canvas
        ref={canvasRef}
        width={size + 60}
        height={size + 60}
        className="cursor-pointer"
        style={{ filter: hover ? "brightness(1.3)" : "brightness(1)" }}
        onClick={() => setCurrentPower(100)}
      />
      <div className="mt-2 flex flex-col items-center gap-1">
        <div className="font-mono text-[10px] tracking-[0.3em] text-cyan-400">
          ARC REACTOR MK XLII
        </div>
        <div className="flex items-center gap-2">
          <div className="h-1 w-16 rounded bg-black/50">
            <div
              className="h-1 rounded bg-gradient-to-r from-cyan-400 to-emerald-400 transition-all"
              style={{ width: `${currentPower}%` }}
            />
          </div>
          <span className="font-mono text-[9px] text-emerald-400">
            {currentPower.toFixed(1)}%
          </span>
        </div>
        <div className="font-mono text-[7px] tracking-widest text-slate-500">
          {hover ? "HOVER BOOST — 1.3X POWER" : "STANDBY — CLICK TO RECHARGE"}
        </div>
      </div>
    </div>
  );
}
