function EtaDisplay({
  etaHours,
  predictedCompletion,
}: {
  etaHours: number | null;
  predictedCompletion: string | null;
}) {
  const urgent = etaHours !== null && etaHours < 2;
  const warning = etaHours !== null && etaHours >= 2 && etaHours < 8;

  const colorClass = urgent
    ? "text-red-400"
    : warning
    ? "text-amber-400"
    : "text-emerald-400";

  const borderClass = urgent
    ? "border-red-500 bg-red-950/30"
    : warning
    ? "border-amber-500 bg-amber-950/30"
    : "border-emerald-500 bg-emerald-950/30";

  const pulseClass = urgent ? "animate-pulse" : "";

  let etaLabel = "Belirsiz";
  if (etaHours !== null) {
    const h = Math.floor(etaHours);
    const m = Math.round((etaHours - h) * 60);
    if (h === 0) {
      etaLabel = `${m}dk`;
    } else if (m === 0) {
      etaLabel = `${h}s`;
    } else {
      etaLabel = `${h}s ${m}dk`;
    }
  }

  let completionLabel: string | null = null;
  if (predictedCompletion) {
    try {
      const d = new Date(predictedCompletion);
      if (!isNaN(d.getTime())) {
        const hh = d.getHours().toString().padStart(2, "0");
        const mm = d.getMinutes().toString().padStart(2, "0");
        completionLabel = `${hh}:${mm}`;
      }
    } catch {
      completionLabel = null;
    }
  }

  return (
    <div
      className={`rounded-xl border p-4 flex flex-col gap-1 ${borderClass} ${pulseClass}`}
    >
      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
        ETA
      </span>
      <span className={`text-4xl font-bold tabular-nums ${colorClass}`}>
        {etaLabel}
      </span>
      {completionLabel && (
        <span className="text-xs text-slate-400">
          Tahmini bitiş:{" "}
          <span className={`font-semibold ${colorClass}`}>
            {completionLabel}
          </span>
        </span>
      )}
      {etaHours === null && (
        <span className="text-xs text-slate-500">Yeterli veri yok</span>
      )}
    </div>
  );
}
