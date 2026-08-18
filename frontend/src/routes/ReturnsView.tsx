import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { Me, RETURN_STATUSES, ReturnCase } from "../lib/types";
import { fmtDate } from "../lib/format";
import { NewReturnDrawer } from "../components/NewReturnDrawer";
import { useToast } from "../components/Toast";

function statusPill(status: string): string {
  if (status === "Closed" || status === "Refunded" || status === "Replacement Sent") return "green";
  if (status === "Requested") return "amber";
  return "blue";
}

export function ReturnsView({ me }: { me: Me }) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const toast = useToast();
  const canWrite = me.role === "owner" || me.role === "ops";

  const { data, isLoading } = useQuery({
    queryKey: ["returns"],
    queryFn: () => api.get<ReturnCase[]>("/returns"),
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => api.patch<ReturnCase>(`/returns/${id}`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["returns"] });
      toast("Status updated.");
    },
    onError: (err) => toast(err instanceof ApiError ? err.message : "Could not update the status."),
  });

  const cases = data || [];

  return (
    <>
      <div className="h-row">
        <div>
          <h2 className="title">Returns & Exchanges</h2>
          <div className="sub">{cases.length} case{cases.length === 1 ? "" : "s"}</div>
        </div>
        {canWrite && (
          <button className="btn primary" onClick={() => setOpen(true)}>
            + New case
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="dim" style={{ padding: 24 }}>
          Loading…
        </div>
      ) : cases.length === 0 ? (
        <div className="empty">
          <h3>No return or exchange cases</h3>
          <p>Cases raised against an order will show up here.</p>
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th style={{ width: 96 }}>Order</th>
              <th>Customer</th>
              <th style={{ width: 90 }}>Type</th>
              <th>Reason</th>
              <th style={{ width: 96 }}>Requested</th>
              <th style={{ width: 160 }}>Status</th>
              <th>Next action</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id}>
                <td className="mono">{c.order_number}</td>
                <td>{c.customer_name || "—"}</td>
                <td className="dim">{c.type}</td>
                <td className="dim">{c.reason || "—"}</td>
                <td className="mono dim">{fmtDate(c.requested_on)}</td>
                <td>
                  {canWrite ? (
                    <select
                      value={c.status}
                      disabled={updateStatus.isPending}
                      onChange={(e) => updateStatus.mutate({ id: c.id, status: e.target.value })}
                    >
                      {RETURN_STATUSES.map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                  ) : (
                    <span className={`pill ${statusPill(c.status)}`}>{c.status}</span>
                  )}
                </td>
                <td className="dim">{c.next_action || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <NewReturnDrawer open={open} onClose={() => setOpen(false)} />
    </>
  );
}
