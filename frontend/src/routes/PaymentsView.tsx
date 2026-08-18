import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Me, Payment } from "../lib/types";
import { fmtDate, inr } from "../lib/format";
import { AddPaymentDrawer } from "../components/AddPaymentDrawer";

export function PaymentsView({ me }: { me: Me }) {
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["payments"],
    queryFn: () => api.get<Payment[]>("/payments"),
  });

  const payments = data || [];
  const total = payments.reduce((sum, p) => sum + parseFloat(p.amount_inr), 0);

  return (
    <>
      <div className="h-row">
        <div>
          <h2 className="title">Payments</h2>
          <div className="sub">
            {payments.length} record{payments.length === 1 ? "" : "s"} · {inr(total.toFixed(2))} total
          </div>
        </div>
        {(me.role === "owner" || me.role === "ops") && (
          <button className="btn primary" onClick={() => setOpen(true)}>
            + Record payment
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="dim" style={{ padding: 24 }}>
          Loading…
        </div>
      ) : payments.length === 0 ? (
        <div className="empty">
          <h3>No payments recorded yet</h3>
          <p>Manufacturer, logistics, and refund payments will show up here as they're recorded.</p>
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th style={{ width: 96 }}>Date</th>
              <th style={{ width: 110 }}>Type</th>
              <th>Paid to</th>
              <th style={{ width: 100 }}>Box</th>
              <th className="num" style={{ width: 110 }}>
                Amount
              </th>
              <th style={{ width: 110 }}>Method</th>
              <th>Paid by</th>
            </tr>
          </thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id}>
                <td className="mono dim">{fmtDate(p.occurred_on)}</td>
                <td>
                  <span className="pill grey">{p.type}</span>
                </td>
                <td>
                  {p.payee}
                  {p.reference && (
                    <div className="faint" style={{ fontSize: 11 }}>
                      {p.reference}
                    </div>
                  )}
                </td>
                <td className="mono dim">{p.box_aft_number || "—"}</td>
                <td className="num">{inr(p.amount_inr)}</td>
                <td className="dim">{p.method || "—"}</td>
                <td className="dim">{p.paid_by}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <AddPaymentDrawer open={open} onClose={() => setOpen(false)} />
    </>
  );
}
