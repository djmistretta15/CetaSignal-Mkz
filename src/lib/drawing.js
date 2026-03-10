import { BEHAVIORAL_CLASSES } from './classifier';

export function drawSpectrogram(canvas, features) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  ctx.fillStyle = "#050A10";
  ctx.fillRect(0, 0, W, H);

  const { peakFrequency_hz: pf, freqContour: fc, duration_s: dur, interPulseInterval_ms: ipi, urgencyIndex: urg } = features;
  const T = 200, F = 80;
  const cw = W / T, ch = H / F;
  const maxF = Math.max(pf * 2, 600);

  for (let t = 0; t < T; t++) {
    const tn = t / T;
    let cfn;
    if (fc === "rising") cfn = 0.1 + tn * 0.45;
    else if (fc === "descending") cfn = 0.65 - tn * 0.45;
    else if (fc === "complex") cfn = 0.3 + 0.18 * Math.sin(tn * Math.PI * 4);
    else cfn = (pf / maxF);

    const pulse = ipi ? (t % Math.max(2, Math.floor((ipi / 5000) * 30))) < 3 : true;
    if (!pulse && urg > 0.5) continue;

    for (let f = 0; f < F; f++) {
      const fn = f / F;
      const d = Math.abs(fn - cfn);
      const spread = pf > 1000 ? 80 : 40;
      const intensity = Math.exp(-d * d * spread) * (0.7 + Math.random() * 0.15);
      if (intensity < 0.04) continue;
      let fade = 1;
      if (tn < 0.06) fade = tn / 0.06;
      else if (tn > 0.94) fade = (1 - tn) / 0.06;
      const a = intensity * fade;
      const r = Math.floor(a * 60), g = Math.floor(a * 140 + 30), b = Math.floor(120 + a * 120);
      ctx.fillStyle = `rgba(${r},${g},${b},${Math.min(a * 1.4, 0.95)})`;
      ctx.fillRect(t * cw, (F - 1 - f) * ch, cw + 0.5, ch + 0.5);
    }
  }
  // Axis
  ctx.fillStyle = "rgba(93,184,200,0.2)";
  ctx.font = "8px monospace";
  for (let i = 1; i <= 3; i++) {
    const y = H * (1 - i / 4);
    const freq = Math.round(maxF * i / 4);
    ctx.fillText(`${freq}`, 3, y - 1);
  }
}

export function drawBehaviorCanvas(canvas, specimen, result, t) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, "#001018"); grad.addColorStop(1, "#000508");
  ctx.fillStyle = grad; ctx.fillRect(0, 0, W, H);
  const sy = H * 0.12;
  ctx.strokeStyle = "rgba(93,184,200,0.15)"; ctx.setLineDash([3, 8]); ctx.lineWidth = 0.8;
  ctx.beginPath(); ctx.moveTo(0, sy); ctx.lineTo(W, sy); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = "rgba(93,184,200,0.25)"; ctx.font = "8px monospace"; ctx.fillText("SURFACE", 6, sy - 3);
  for (let d = 1; d <= 3; d++) {
    const y = sy + (H - sy) * d / 4;
    ctx.strokeStyle = "rgba(0,80,140,0.1)"; ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
    ctx.fillStyle = "rgba(0,80,140,0.4)"; ctx.fillText(`-${d * 30}m`, 6, y + 9);
  }
  const prog = Math.min(t / 10, 1);
  const gtMap = { "Pod convergence": "CONTACT", "Long-range contact — call-response exchange": "CONTACT", "Dive initiation": "DIVE", "Foraging spread formation": "FORAGE", "Sustained directional migration": "NAVIGATE", "Stationary broadcasting": "BROADCAST" };
  const gtClass = gtMap[specimen.behavioralRecord.observedBehavior] || "CONTACT";
  const col = BEHAVIORAL_CLASSES[gtClass]?.color || "#5DB8C8";

  if (gtClass === "DIVE") {
    const wx = W / 2, wy = sy + 10 + (H - sy - 20) * 0.85 * Math.min(prog * 1.5, 1);
    drawWhaleMark(ctx, wx, wy, col, 0.18);
    ctx.strokeStyle = col + "30"; ctx.lineWidth = 1.5; ctx.setLineDash([2, 5]);
    ctx.beginPath(); ctx.moveTo(wx, sy + 10); ctx.lineTo(wx, wy); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = col + "AA"; ctx.font = "9px monospace";
    ctx.fillText(`-${Math.floor(Math.min(prog * 1.5, 1) * 80)}m`, wx + 14, wy);
  } else if (gtClass === "CONTACT") {
    const w1x = W * 0.18 + prog * W * 0.28, w2x = W * 0.82 - prog * W * 0.28, wy = sy + 20;
    for (let i = 0; i < 4; i++) {
      const r = 15 + (prog * 160 + i * 40) % 160;
      ctx.strokeStyle = col + Math.floor(Math.max(0, 0.4 - r / 200) * 255).toString(16).padStart(2, "0");
      ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(W * 0.18, wy, r, 0, Math.PI * 2); ctx.stroke();
    }
    drawWhaleMark(ctx, w1x, wy, col, 0.18);
    drawWhaleMark(ctx, w2x, wy, col + "AA", 0.15);
  } else if (gtClass === "FORAGE") {
    const cx = W / 2, cy = sy + 30, spread = prog * 130;
    [[0, 0], [1, -0.5], [-1, -0.4], [0.5, 0.7], [-0.5, 0.6]].forEach(([dx, dy]) => {
      drawWhaleMark(ctx, cx + dx * spread, cy + dy * spread * 0.4, col, 0.14);
    });
    ctx.fillStyle = col + "40"; ctx.font = "9px monospace"; ctx.textAlign = "center";
    ctx.fillText(`~${Math.floor(spread * 1.8)}m spread`, cx, sy - 4); ctx.textAlign = "left";
  } else if (gtClass === "NAVIGATE") {
    const wy = sy + 22, wx = W * 0.08 + prog * W * 0.72;
    ctx.strokeStyle = col + "20"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(W * 0.08, wy); ctx.lineTo(wx, wy); ctx.stroke();
    drawWhaleMark(ctx, wx, wy, col, 0.18);
    if (wx + 30 < W) {
      ctx.strokeStyle = col + "50"; ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(wx + 8, wy); ctx.lineTo(wx + 28, wy);
      ctx.moveTo(wx + 22, wy - 5); ctx.lineTo(wx + 28, wy); ctx.lineTo(wx + 22, wy + 5); ctx.stroke();
    }
  } else if (gtClass === "BROADCAST") {
    const cx = W / 2, cy = sy + 35;
    for (let i = 0; i < 5; i++) {
      const r = 20 + (prog * 200 + i * 40) % 200;
      ctx.strokeStyle = col + Math.floor(Math.max(0, 0.45 - r / 260) * 255).toString(16).padStart(2, "0");
      ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
    }
    drawWhaleMark(ctx, cx, cy, col, 0.2);
  }

  ctx.fillStyle = "rgba(93,184,200,0.3)"; ctx.font = "8px monospace";
  ctx.fillText(`T+${Math.floor(prog * (specimen.behavioralRecord.timeToResponse_s || 60))}s`, W - 38, 14);
}

export function drawWhaleMark(ctx, x, y, color, size) {
  ctx.save(); ctx.translate(x, y);
  ctx.shadowBlur = 12; ctx.shadowColor = color;
  ctx.fillStyle = color;
  ctx.beginPath(); ctx.ellipse(0, 0, 18 * size * 6, 6 * size * 6, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0; ctx.restore();
}
