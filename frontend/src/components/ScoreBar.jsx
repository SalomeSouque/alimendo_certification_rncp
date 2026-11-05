// src/components/ScoreBar.jsx
// Visual position of a score level (-2 … +2) on the gradient bar.
// The bar is decorative for screen readers: the label carries the information.

/** -2 → 10 %, 0 → 50 %, +2 → 90 % */
function knobPosition(level) {
  return `${50 + level * 20}%`;
}

export default function ScoreBar({ level, label, mini = false }) {
  return (
    <div className={mini ? 'mini-bar' : 'score-bar'} role="img" aria-label={`Potentiel inflammatoire estimé : ${label}`}>
      <span className={mini ? 'mini-knob' : 'score-knob'} style={{ left: knobPosition(level) }} />
    </div>
  );
}
