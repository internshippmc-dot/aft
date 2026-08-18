import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Me, OrderListItem } from "../lib/types";
import { fmtDate, inr } from "../lib/format";
import { NewOrderDrawer } from "../components/NewOrderDrawer";

export function OrdersView({ me, onSelectOrder }: { me: Me; onSelectOrder: (orderNumber: string) => void }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["orders", q],
    queryFn: () => api.get<OrderListItem[]>(`/orders${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  });

  const orders = data || [];
  const canWrite = me.role === "owner" || me.role === "ops";

  return (
    <>
      <div className="h-row">
        <div>
          <h2 className="title">All Orders</h2>
          <div className="sub">Newest first — synced from Shopify plus any orders added directly.</div>
        </div>
        {canWrite && (
          <button className="btn primary" onClick={() => setOpen(true)}>
            + New order
          </button>
        )}
      </div>

      <div className="toolbar" style={{ margin: "0 0 16px" }}>
        <input placeholder="Search order number or customer…" value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 320 }} />
      </div>

      {isLoading ? (
        <div className="dim" style={{ padding: 24 }}>
          Loading…
        </div>
      ) : orders.length === 0 ? (
        <div className="empty">
          <h3>No orders yet</h3>
          <p>Orders will appear here once Shopify sync runs, or add one directly.</p>
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th style={{ width: 96 }}>Order</th>
              <th>Customer</th>
              <th style={{ width: 100 }}>City</th>
              <th style={{ width: 96 }}>Placed</th>
              <th className="num" style={{ width: 90 }}>
                Value
              </th>
              <th style={{ width: 90 }}>Box</th>
              <th style={{ width: 80 }}>Source</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.order_number} className="clickable" onClick={() => onSelectOrder(o.order_number)}>
                <td className="mono">{o.order_number}</td>
                <td>{o.customer_name || "—"}</td>
                <td className="dim">{o.city || "—"}</td>
                <td className="mono dim">{fmtDate(o.placed_at)}</td>
                <td className="num">{inr(o.total_inr)}</td>
                <td className="mono dim">{o.box_aft_number || "—"}</td>
                <td>
                  <span className={`pill ${o.source === "shopify" ? "green" : "purple"}`}>{o.source === "shopify" ? "Shopify" : "Custom"}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <NewOrderDrawer open={open} onClose={() => setOpen(false)} onSaved={onSelectOrder} />
    </>
  );
}
