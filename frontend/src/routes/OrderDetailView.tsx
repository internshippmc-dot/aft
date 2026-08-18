import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { Me, OrderDetail, ReturnCase, Shipment } from "../lib/types";
import { LegBar } from "../components/LegBar";
import { inr } from "../lib/format";
import { etaNote } from "../lib/etaNote";
import { useToast } from "../components/Toast";
import { QueueMessageDrawer } from "../components/QueueMessageDrawer";
import { NewTaskDrawer } from "../components/NewTaskDrawer";

export function OrderDetailView({
  orderNumber,
  onSelectBox,
  me,
}: {
  orderNumber: string;
  onSelectBox: (aft: string) => void;
  me: Me;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [messageOpen, setMessageOpen] = useState(false);
  const [reminderOpen, setReminderOpen] = useState(false);
  const { data: order, isLoading } = useQuery({
    queryKey: ["order", orderNumber],
    queryFn: () => api.get<OrderDetail>(`/orders/${encodeURIComponent(orderNumber)}`),
  });

  const bookShipment = useMutation({
    mutationFn: () =>
      api.post<Shipment>(`/integrations/orders/${encodeURIComponent(orderNumber)}/ithink/book`),
    onSuccess: (shipment) => {
      queryClient.invalidateQueries({ queryKey: ["order", orderNumber] });
      toast(shipment.awb ? `Booked with iThink — AWB ${shipment.awb}.` : "Booked with iThink.");
    },
    onError: (err) => toast(err instanceof ApiError ? err.message : "Could not book the shipment."),
  });

  const { data: returnCases } = useQuery({
    queryKey: ["returns", "order", orderNumber],
    queryFn: () => api.get<ReturnCase[]>(`/returns?order_number=${encodeURIComponent(orderNumber)}`),
  });
  const openCase = returnCases?.[0];

  if (isLoading || !order) return <div className="dim" style={{ padding: 24 }}>Loading…</div>;

  // Narrowed copy — TS control-flow narrowing doesn't carry into the closure below.
  const timeline = order.timeline;

  // LegBar draws "done" purely from a leg being present here, so only actual
  // dates go in — the predicted segment is drawn separately from order.eta.
  function actualDate(leg: string): string | null {
    const entry = timeline.find((t) => t.leg === leg);
    return entry?.actual ? entry.date : null;
  }
  const legs = {
    MFG_DISPATCH: actualDate("MFG_DISPATCH"),
    CN_WAREHOUSE: actualDate("CN_WAREHOUSE"),
    FLIGHT: actualDate("FLIGHT"),
    DELHI_WAREHOUSE: actualDate("DELHI_WAREHOUSE"),
  };

  return (
    <>
      <div className="crumb">
        {order.box_aft_number ? (
          <button className="dim" onClick={() => onSelectBox(order.box_aft_number!)}>
            Boxes / {order.box_aft_number}
          </button>
        ) : (
          <span className="dim">Orders</span>
        )}{" "}
        / <span className="mono">{order.order_number}</span>
      </div>

      <div className="h-row">
        <div>
          <h2 className="title">{order.order_number}</h2>
          <div className="sub">
            {order.customer_name || "—"} · {order.city || "—"} · <span className="mono">{order.phone || "—"}</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {!order.shipment && (me.role === "owner" || me.role === "ops") && (
            <button className="btn ghost" disabled={bookShipment.isPending} onClick={() => bookShipment.mutate()}>
              {bookShipment.isPending ? "Booking…" : "Book with iThink"}
            </button>
          )}
          <button className="btn ghost" onClick={() => setMessageOpen(true)}>
            Queue status message
          </button>
          <button className="btn ghost" onClick={() => setReminderOpen(true)}>
            + Reminder
          </button>
        </div>
      </div>

      <div className="facts">
        <div className="fact">
          <div className="k">Placed</div>
          <div className="v">{new Date(order.placed_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}</div>
        </div>
        <div className="fact">
          <div className="k">Elapsed</div>
          <div className={`v ${order.elapsed_days > 11 ? "warn" : ""}`}>{order.elapsed_days} days</div>
        </div>
        <div className="fact">
          <div className="k">Box</div>
          <div className="v">{order.box_aft_number || "Unassigned"}</div>
        </div>
        <div className="fact">
          <div className="k">Consignment</div>
          <div className="v">{order.consignment_tracking_id || "—"}</div>
        </div>
        <div className="fact">
          <div className="k">Value</div>
          <div className="v">{inr(order.total_inr)}</div>
        </div>
        {order.shipment && (
          <>
            <div className="fact">
              <div className="k">Courier</div>
              <div className="v">{order.shipment.courier || "—"}</div>
            </div>
            <div className="fact">
              <div className="k">AWB</div>
              <div className="v mono">{order.shipment.awb || "—"}</div>
            </div>
            <div className="fact">
              <div className="k">Shipment status</div>
              <div className="v">{order.shipment.delivered_on ? "Delivered" : order.shipment.status || "Booked"}</div>
            </div>
          </>
        )}
        {openCase && (
          <div className="fact">
            <div className="k">{openCase.type}</div>
            <div className="v">{openCase.status}</div>
          </div>
        )}
      </div>

      {order.box_aft_number ? (
        <div className="panel-legs">
          <LegBar legs={legs} eta={order.eta} size="lg" />
          <p className={`eta-note ${order.sla_risk ? "warn" : ""}`}>{etaNote(legs, order.eta, order.sla_risk)}</p>
        </div>
      ) : (
        <p className="eta-note" style={{ margin: "22px 0" }}>
          This order has not been attached to a box yet, so there is no shipment timeline to show.
        </p>
      )}

      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th style={{ width: 110 }}>Colour</th>
            <th style={{ width: 70 }}>Size</th>
            <th className="num" style={{ width: 50 }}>
              Qty
            </th>
          </tr>
        </thead>
        <tbody>
          {order.items.map((i) => (
            <tr key={i.id}>
              <td>{i.product_title}</td>
              <td className="dim">{i.colour || "—"}</td>
              <td className="mono">{i.size || "—"}</td>
              <td className="num">{i.quantity}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <QueueMessageDrawer open={messageOpen} order={order} onClose={() => setMessageOpen(false)} />
      <NewTaskDrawer open={reminderOpen} prefillEntityId={order.order_number} onClose={() => setReminderOpen(false)} />
    </>
  );
}
