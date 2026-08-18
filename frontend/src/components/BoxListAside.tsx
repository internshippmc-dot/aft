import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { BoxSummary } from "../lib/types";
import { LegBar } from "./LegBar";

type Filter = "all" | "transit" | "queue";

export function BoxListAside({
  current,
  onSelect,
  filter,
  onFilterChange,
}: {
  current: string | null;
  onSelect: (aft: string) => void;
  filter: Filter;
  onFilterChange: (f: Filter) => void;
}) {
  const { data } = useQuery({
    queryKey: ["boxes", filter],
    queryFn: () => api.get<BoxSummary[]>(`/boxes?filter=${filter}`),
  });

  const boxes = data || [];

  return (
    <aside>
      <div className="aside-head">
        <div className="tabs">
          {(["all", "transit", "queue"] as Filter[]).map((f) => (
            <button key={f} className={`tab ${filter === f ? "on" : ""}`} onClick={() => onFilterChange(f)}>
              {f === "all" ? "All" : f === "transit" ? "In transit" : "Queue"}
            </button>
          ))}
        </div>
        <span className="mono faint">{boxes.length}</span>
      </div>
      <div>
        {boxes.map((b) => (
          <button key={b.aft_number} className={`boxrow ${b.aft_number === current ? "on" : ""}`} onClick={() => onSelect(b.aft_number)}>
            <div className="top">
              <span className="aft">{b.aft_number}</span>
              <span className="meta">
                {b.order_count} order{b.order_count === 1 ? "" : "s"} · {b.gross_weight_kg ? `${parseFloat(b.gross_weight_kg).toFixed(2)} kg` : "— kg"}
              </span>
            </div>
            <LegBar legs={b.legs} eta={b.eta} size="mini" />
            <div className="meta" style={{ marginTop: 6, display: "flex", justifyContent: "space-between" }}>
              <span>
                {b.stage}
                {b.sla_risk && <span className="pill red"> at risk</span>}
              </span>
              <span className="mono faint">{b.tracking_id || "no tracking id"}</span>
            </div>
          </button>
        ))}
        {boxes.length === 0 && (
          <div style={{ padding: 16 }} className="dim">
            No boxes in this view.
          </div>
        )}
      </div>
    </aside>
  );
}
