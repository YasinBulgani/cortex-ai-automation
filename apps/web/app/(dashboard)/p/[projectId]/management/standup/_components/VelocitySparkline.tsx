function VelocitySparkline({ currentVelocity }: { currentVelocity: number }) {
  const velocityHistory = [
    currentVelocity * 0.6,
    currentVelocity * 0.8,
    currentVelocity * 0.7,
    currentVelocity * 0.9,
    currentVelocity * 1.1,
    currentVelocity * 1.0,
    currentVelocity,
  ];

  const max = Math.max(...velocityHistory, 0.01);
  const WIDTH = 220;
  const HEIGHT = 90;
  const PAD_X = 4;
  const PAD_Y = 5;

  const points = velocityHistory.map((v, i) => {
    const x = PAD_X + i * 33;
    const y = HEIGHT - PAD_Y - (v / max) * 80;
    return { x, y };
  });

  const polylinePoints = points.map((p) => `${p.x},${p.y}`).join(" ");

  // area fill path: go along line then close at bottom
  const areaPath =
    `M ${points[0].x},${HEIGHT - PAD_Y} ` +
    points.map((p) => `L ${p.x},${p.y}`).join(" ") +
    ` L ${points[points.length - 1].x},${HEIGHT - PAD_Y} Z`;

  const last = points[points.length - 1];

  return (
    <div className="rounded-xl border border-border bg-surface-raised p-3 flex flex-col gap-1">
      <div className="flex items-baseline justify-between">
        <span className="text-[10px] font-bold uppercase tracking-widest text-fg-muted">HIZ</span>
        <div className="flex items-baseline gap-1">
          <span className="text-2xl font-bold text-teal-400">{currentVelocity.toFixed(1)}</span>
          <span className="text-[10px] text-fg-subtle">case/saat</span>
        </div>
      </div>

      <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} overflow="visible">
        <defs>
          <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#14b8a6" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#14b8a6" stopOpacity="0.02" />
          </linearGradient>
          <filter id="sparkGlow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* area fill */}
        <path d={areaPath} fill="url(#sparkGrad)" />

        {/* line */}
        <polyline
          points={polylinePoints}
          fill="none"
          stroke="#14b8a6"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
          filter="url(#sparkGlow)"
        />

        {/* intermediate dots */}
        {points.slice(0, -1).map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="2" fill="#14b8a6" opacity="0.5" />
        ))}

        {/* last point pulse */}
        <circle cx={last.x} cy={last.y} r="5" fill="#14b8a6" opacity="0.9">
          <animate
            attributeName="r"
            values="5;9;5"
            dur="1.8s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            values="0.9;0.2;0.9"
            dur="1.8s"
            repeatCount="indefinite"
          />
        </circle>
        <circle cx={last.x} cy={last.y} r="4" fill="#14b8a6" />
      </svg>
    </div>
  );
}
