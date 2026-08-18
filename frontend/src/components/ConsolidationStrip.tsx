import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Consolidation } from "../lib/types";

export function ConsolidationStrip() {
  const { data } = useQuery({
    queryKey: ["consolidation"],
    queryFn: () => api.get<Consolidation>("/consolidation"),
  });

  if (!data || data.unassigned_box_count === 0) return null;

  const weight = parseFloat(data.unassigned_weight_kg);
  const shortfall = parseFloat(data.shortfall_kg);
  const short = shortfall > 0;

  return (
    <div className="strip">
      <span className="eyebrow">Consolidation queue</span>
      <span>
        <b>{weight.toFixed(2)}</b> kg unassigned across <b>{data.unassigned_box_count}</b> box
        {data.unassigned_box_count === 1 ? "" : "es"}
      </span>
      <div className={`gauge ${short ? "short" : ""}`} title="Against the 10 kg Hexalog minimum">
        <i style={{ width: `${data.gauge_pct}%` }} />
      </div>
      <span className="dim">
        {short
          ? `${shortfall.toFixed(2)} kg short of the 10 kg chargeable minimum. Shipping now bills for 10 kg regardless.`
          : "At or above the 10 kg chargeable minimum."}
      </span>
    </div>
  );
}
