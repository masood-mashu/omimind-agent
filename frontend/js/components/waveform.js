/**
 * waveform.js - 60fps Ambient Audio Canvas Waveform Visualizer
 * High-DPI / Retina display calibrated with window.devicePixelRatio and reduced-motion awareness.
 */

let animationFrameId = null;

export function initWaveform(canvasId, getFrequencyData, isAudioActiveFn) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return () => {};

  const ctx = canvas.getContext('2d');
  let step = 0;

  // Cache display size and device pixel ratio
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const logicalWidth = rect.width || canvas.width || 800;
  const logicalHeight = rect.height || canvas.height || 36;

  // Scale internal bitmap by DPR
  canvas.width = Math.round(logicalWidth * dpr);
  canvas.height = Math.round(logicalHeight * dpr);

  // Check reduced motion preference
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function render() {
    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, logicalWidth, logicalHeight);
    const mid = logicalHeight / 2;

    const isActive = isAudioActiveFn ? isAudioActiveFn() : false;
    let baseAmp = isActive ? 12 : 2.5;

    if (getFrequencyData) {
      const freq = getFrequencyData();
      if (freq && freq.length > 0) {
        let sum = 0;
        for (let i = 0; i < freq.length; i++) sum += freq[i];
        const avg = sum / freq.length;
        if (avg > 2) {
          baseAmp = Math.max(baseAmp, avg * 0.35);
        }
      }
    }

    if (prefersReducedMotion) {
      // Gentle calm static line when reduced motion is preferred
      ctx.strokeStyle = isActive ? '#06b6d4' : 'rgba(56, 189, 248, 0.4)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(0, mid);
      ctx.lineTo(logicalWidth, mid);
      ctx.stroke();
      ctx.restore();
      return;
    }

    const speed = isActive ? 0.08 : 0.02;
    step += speed;

    // Subtle center baseline
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, mid);
    ctx.lineTo(logicalWidth, mid);
    ctx.stroke();

    // Primary cyan wave
    ctx.beginPath();
    ctx.strokeStyle = isActive ? '#06b6d4' : 'rgba(56, 189, 248, 0.4)';
    ctx.lineWidth = isActive ? 2 : 1.2;

    for (let x = 0; x < logicalWidth; x++) {
      const y = mid + Math.sin(x * 0.04 + step) * baseAmp * Math.sin(x * 0.01 + step * 0.5);
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Secondary purple wave when audio is active
    if (isActive) {
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(168, 85, 247, 0.5)';
      ctx.lineWidth = 1.5;
      for (let x = 0; x < logicalWidth; x++) {
        const y = mid + Math.cos(x * 0.05 - step) * (baseAmp * 0.7);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    ctx.restore();

    animationFrameId = requestAnimationFrame(render);
  }

  render();

  return () => {
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
  };
}

