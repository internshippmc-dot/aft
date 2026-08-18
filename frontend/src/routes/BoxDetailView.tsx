import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { BoxManifest } from "../lib/types";
import { LegBar } from "../components/LegBar";
import { NewBoxDrawer } from "../components/NewBoxDrawer";
import { EditBoxDrawer } from "../components/EditBoxDrawer";
import { LegEntryDrawer } from "../components/LegEntryDrawer";
import { AssignConsignmentDrawer } from "../components/AssignConsignmentDrawer";
import { NewTaskDrawer } from "../components/NewTaskDrawer";
import { fmtDate, inr, daysBetween } from "../lib/format";
import { etaNote } from "../lib/etaNote";

export function BoxDetailView({ aft, onBack, onSelectOrder }: { aft: string; onBack: () => void; onSelectOrder: (orderNumber: string) => void }) {
  const [attachOpen, setAttachOpen] = useState(false);
  const [legOpen, setLegOpen] = useState(false);
  const [consignOpen, setConsignOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [reminderOpen, setReminderOpen] = useState(false);

  const { data: box, isLoading } = useQuery({
    queryKey: ["box", aft],
    queryFn: () => api.get<BoxManifest>(`/boxes/${encodeURIComponent(aft)}`),
  });

  if (isLoading || !box) return <div className="dim" style={{ padding: 24 }}>Loading…</div>;

  const elapsed = box.oldest_order_placed_at ? daysBetween(box.oldest_order_placed_at, new Date().toISOString()) : null;

  return (
    <>
      <div className="crumb">
        <button className="dim" onClick={onBack}>
          Boxes
        </button>{" "}
        / <span className="mono">{box.aft_number}</span>
      </div>

      <div className="h-row">
        <div>
          <h2 className="title">{box.aft_number}</h2>
          <div className="sub">
            {box.manufacturer || "—"} · {box.tracking_id ? `Consignment ${box.tracking_id}` : "Not yet consigned"}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn ghost" onClick={() => setLegOpen(true)}>
            Enter leg date
          </button>
          {!box.tracking_id && (
            <button className="btn ghost" onClick={() => setConsignOpen(true)}>
              Assign to consignment
            </button>
          )}
          <button className="btn ghost" onClick={() => setAttachOpen(true)}>
            Attach orders
          </button>
          <button className="btn ghost" onClick={() => setReminderOpen(true)}>
            + Reminder
          </button>
          <button className="btn ghost" onClick={() => setEditOpen(true)}>
            Edit
          </button>
        </div>
      </div>

      <div className="facts">
        <div className="fact">
          <div className="k">Stage</div>
          <div className="v">{box.stage}</div>
        </div>
        <div className="fact">
          <div className="k">Orders</div>
          <div className="v">{box.order_count}</div>
        </div>
        <div className="fact">
          <div className="k">Units</div>
          <div className="v">{box.units_total}</div>
        </div>
        <div className="fact">
          <div className="k">Gross weight</div>
          <div className="v">{box.gross_weight_kg ? `${parseFloat(box.gross_weight_kg).toFixed(2)} kg` : "—"}</div>
        </div>
        <div className="fact">
          <div className="k">Order value</div>
          <div className="v">{inr(box.value_total)}</div>
        </div>
        {elapsed !== null && (
          <div className="fact">
            <div className="k">Oldest order</div>
            <div className={`v ${elapsed > 11 ? "warn" : ""}`}>{elapsed} days</div>
          </div>
        )}
      </div>

      <div className="panel-legs">
        <LegBar legs={box.legs} eta={box.eta} size="lg" />
        <p className={`eta-note ${box.sla_risk ? "warn" : ""}`}>{etaNote(box.legs, box.eta, box.sla_risk)}</p>
      </div>

      {box.notes && (
        <div className="notes-block">
          <div className="eyebrow">Notes</div>
          <p>{box.notes}</p>
        </div>
      )}

      {box.orders.length === 0 ? (
        <div className="empty">
          <h3>No orders attached yet</h3>
          <p>Attach orders as the packing list comes in. Paste order numbers one per line and the console reports anything already sitting in another box.</p>
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th style={{ width: 88 }}>Order</th>
              <th>Customer</th>
              <th>Items</th>
              <th style={{ width: 96 }}>Placed</th>
              <th className="num" style={{ width: 90 }}>
                Value
              </th>
            </tr>
          </thead>
          <tbody>
            {box.orders.map((o) => (
              <tr key={o.order_number} className="clickable" onClick={() => onSelectOrder(o.order_number)}>
                <td className="mono">{o.order_number}</td>
                <td>
                  {o.customer_name || "—"}
                  <div className="faint" style={{ fontSize: 11 }}>
                    {o.city || ""}
                  </div>
                </td>
                <td>
                  {o.items.map((i, idx) => (
                    <div key={idx}>
                      {i.product_title} <span className="dim">{[i.colour, i.size].filter(Boolean).join(" · ")}</span>
                    </div>
                  ))}
                </td>
                <td className="mono dim">{fmtDate(o.placed_at)}</td>
                <td className="num">{inr(o.total_inr)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <NewBoxDrawer open={attachOpen} prefillAft={box.aft_number} onClose={() => setAttachOpen(false)} onSaved={() => {}} />
      <EditBoxDrawer open={editOpen} box={box} onClose={() => setEditOpen(false)} />
      <LegEntryDrawer open={legOpen} aftNumber={box.aft_number} trackingId={box.tracking_id} onClose={() => setLegOpen(false)} />
      <AssignConsignmentDrawer open={consignOpen} aftNumber={box.aft_number} onClose={() => setConsignOpen(false)} />
      <NewTaskDrawer open={reminderOpen} prefillEntityId={box.aft_number} onClose={() => setReminderOpen(false)} />
    </>
  );
}
