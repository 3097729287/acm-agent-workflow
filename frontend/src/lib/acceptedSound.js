let context;
const played = new Set();

// Unlock audio during the submit gesture; the result arrives asynchronously.
export function primeAcceptedSound() {
  try {
    const Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) return;
    if (!context || context.state === 'closed') context = new Audio();
    if (context.state === 'suspended') context.resume().catch(() => {});
  } catch { /* Sound availability must never affect submission or progress. */ }
}

export function playAcceptedSound(receiptId) {
  if (!receiptId || played.has(receiptId)) return;
  played.add(receiptId);
  if (played.size > 1000) played.delete(played.values().next().value);
  primeAcceptedSound();
  if (!context || context.state !== 'running') return;
  try {
    const start = context.currentTime + 0.02;
    [[659.25, 0, 0.18], [830.61, 0.12, 0.18], [987.77, 0.24, 0.20], [1318.51, 0.38, 0.32]].forEach(([frequency, offset, duration]) => {
      const tone = context.createOscillator(), gain = context.createGain();
      tone.type = 'sine';
      tone.frequency.value = frequency;
      gain.gain.setValueAtTime(0, start + offset);
      gain.gain.linearRampToValueAtTime(0.09, start + offset + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.001, start + offset + duration);
      tone.connect(gain); gain.connect(context.destination);
      tone.onended = () => { tone.disconnect(); gain.disconnect(); };
      tone.start(start + offset); tone.stop(start + offset + duration + 0.02);
    });
  } catch { /* Keep a confirmed verdict visible even if the audio device fails. */ }
}
