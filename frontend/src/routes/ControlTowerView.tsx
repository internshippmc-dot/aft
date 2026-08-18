import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { ControlTowerCard, Me, PIPELINE_STAGES } from "../lib/types";
import { fmtDate } from "../lib/format";
import { ControlTowerCardDrawer } from "../components/ControlTowerCardDrawer";

function cardInfo(c: ControlTowerCard): string {
  switch (c.pipeline_stage) {
    case "Manufacturer → Hexalog":
      return `CN tracking: ${c.cn_tracking || "Pending"} · PL: ${c.pl_status || "—"}`;
    case "Sitting in Hexalog":
      return `Hexalog arrival: ${c.hexalog_arrival ? fmtDate(c.hexalog_arrival) : "—"} · Flight: ${c.flight_date ? fmtDate(c.flight_date) : "—"}`;
    case "On Flight":
      return `Flight: ${c.flight_date ? fmtDate(c.flight_date) : "—"} · Lands same day → customs`;
    case "Delhi Warehouse":
      return `Delhi arrival: ${c.delhi_arrival ? fmtDate(c.delhi_arrival) : "—"} · Labels: ${c.labels_generated}/${c.labels_total}`;
    case "In Transit":
      return `Labels: ${c.labels_generated}/${c.labels_total} · Delivered: ${c.delivery_pct}%`;
    case "Delivered":
      return `Delivered: 100% · Next: feedback after 5 days`;
    case "Feedback":
      return `Delivered: 100% · Feedback messaging active`;
    case "Closed":
      return `Closed / archived · All operational steps complete`;
    default:
      return "";
  }
}

export function ControlTowerView({ me, onOpenBox }: { me: Me; onOpenBox: (aft: string) => void }) {
  const [selected, setSelected] = useState<ControlTowerCard | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["control-tower"],
    queryFn: () => api.get<ControlTowerCard[]>("/control-tower"),
  });

  const cards = data || [];

  return (
    <>
      <div className="h-row">
        <div>
          <h2 className="title">China Control Tower</h2>
          <div className="sub">
            Live physical pipeline: Manufacturer → Hexalog → Flight → Delhi → In Transit → Delivered → Feedback.
          </div>
        </div>
        <span className="pill grey">Drag/drop comes in a later build</span>
      </div>

      {isLoading ? (
        <div className="dim" style={{ padding: 24 }}>
          Loading…
        </div>
      ) : (
        <div className="kanban">
          {PIPELINE_STAGES.map((stage) => {
            const inStage = cards.filter((c) => c.pipeline_stage === stage);
            return (
              <div className="kcol" key={stage}>
                <div className="khead">
                  <span>{stage}</span>
                  <span className="pill grey">{inStage.length}</span>
                </div>
                {inStage.length === 0 && <div className="empty" style={{ padding: 16, fontSize: 11 }}>No packages</div>}
                {inStage.map((c) => (
                  <div className="kcard" key={c.aft_number} onClick={() => setSelected(c)}>
                    <span className={`flag-btn ${c.flagged ? "flagged" : ""}`}>⚑</span>
                    <div className="aft">
                      {c.aft_number} {c.mf_number && <span className="pill grey">{c.mf_number}</span>}
                    </div>
                    <div className="m">
                      {c.order_count} orders · ₹{Number(c.amount_paid_inr).toLocaleString("en-IN")}
                    </div>
                    <div className="control-detail">{cardInfo(c)}</div>
                    <div className="next">
                      <b>Next:</b> {c.next_action || "—"}
                    </div>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      )}

      <ControlTowerCardDrawer
        card={selected}
        me={me}
        onClose={() => setSelected(null)}
        onOpenBox={(aft) => {
          setSelected(null);
          onOpenBox(aft);
        }}
      />
    </>
  );
}
