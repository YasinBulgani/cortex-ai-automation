function MiniBarChart({ velocity }: { velocity: number }) {
  const multipliers = [0.5, 0.7, 0.6, 0.8, 0.9, 1.0, 1.1, 1.0];
  const barValues = multipliers.map((m) => velocity * m);

  const max = Math.max(...barValues, 0.01);
  const WIDTH = 200;
  const HEIGHT = 80;
  const BAR_COUNT = 8;
  const BAR_WIDTH = 18;
  const GAP = (WIDTH - BAR_COUNT * BAR_WIDTH) / (BAR_COUNT + 1);
  const MAX_BAR_H = 52;
  const X_AXIS_Y = HEIGHT - 14;

  // last 8 hours labels (T-7 … T-0)
  const now = new Date();
  const labels = Array.from({ length: BAR_COUNT }, (_, i) => {
    const d = new Date(now.getTime() - (BAR_COUNT - 1 - i) * 3600 * 1000);
    return d.getHours().toString().padStart(2, "0");
  });

  return (
    <div className="rounded-xl border border-border bg-surface-raised p-3 flex flex-col gap-1">
      <span className="text-[10px] font-bold uppercase tracking-widest text-fg-muted">
        Saatlik Hız
      </span>

      <svg
        width={WIDTH}
        height={HEIGHT}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      >
        {barValues.map((v, i) => {
          const isActive = i === BAR_COUNT - 1;
          const barH = Math.max(2, (v / max) * MAX_BAR_H);
          const x = GAP + i * (BAR_WIDTH + GAP);
          const y = X_AXIS_Y - barH;

          return (
            <g key={i}>
              <rect
                x={x}
                y={y}
                width={BAR_WIDTH}
                height={barH}
                rx="3"
                fill={isActive ? "#14b8a6" : "#1e3a5f"}
                opacity={isActive ? 1 : 0.7}
              />
              {isActive && (
                <rect
                  x={x}
                  y={y}
                  width={BAR_WIDTH}
                  height={Math.min(barH, 3)}
                  rx="3"
                  fill="#5eead4"
                  opacity="0.9"
                />
              )}
              <text
                x={x + BAR_WIDTH / 2}
                y={HEIGHT - 2}
                textAnchor="middle"
                fill={isActive ? "#5eead4" : "#475569"}
                fontSize="8"
                fontWeight={isActive ? "700" : "400"}
              >
                {labels[i]}
              </text>
            </g>
          );
        })}

        {/* baseline */}
        <line
          x1={GAP / 2}
          y1={X_AXIS_Y}
          x2={WIDTH - GAP / 2}
          y2={X_AXIS_Y}
          stroke="#1e293b"
          strokeWidth="1"
        />
      </svg>
    </div>
  );
}
