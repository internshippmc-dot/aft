import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { CustomerMessage, Me } from "../lib/types";
import { useToast } from "../components/Toast";

export function MessagesView({ me }: { me: Me }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const canWrite = me.role === "owner" || me.role === "ops";

  const { data, isLoading } = useQuery({
    queryKey: ["messages"],
    queryFn: () => api.get<CustomerMessage[]>("/messages"),
  });

  const markSent = useMutation({
    mutationFn: (id: number) => api.patch<CustomerMessage>(`/messages/${id}/sent`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["messages"] });
      toast("Marked sent.");
    },
    onError: (err) => toast(err instanceof ApiError ? err.message : "Could not update the message."),
  });

  const messages = data || [];
  const pending = messages.filter((m) => m.status === "Pending").length;

  return (
    <>
      <div className="h-row">
        <div>
          <h2 className="title">Customer Messages</h2>
          <div className="sub">
            {messages.length} queued · {pending} pending
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="dim" style={{ padding: 24 }}>
          Loading…
        </div>
      ) : messages.length === 0 ? (
        <div className="empty">
          <h3>Nothing queued</h3>
          <p>Use "Queue status message" on an order to add one here.</p>
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th style={{ width: 150 }}>Type</th>
              <th style={{ width: 96 }}>Order</th>
              <th style={{ width: 100 }}>Box</th>
              <th>Body</th>
              <th style={{ width: 90 }}>Status</th>
              {canWrite && <th style={{ width: 90 }}></th>}
            </tr>
          </thead>
          <tbody>
            {messages.map((m) => (
              <tr key={m.id}>
                <td>{m.type}</td>
                <td className="mono">{m.order_number}</td>
                <td className="mono dim">{m.box_aft_number || "—"}</td>
                <td className="dim">{m.body || "—"}</td>
                <td>
                  <span className={`pill ${m.status === "Sent" ? "green" : "amber"}`}>{m.status}</span>
                </td>
                {canWrite && (
                  <td>
                    {m.status === "Pending" && (
                      <button className="btn small ghost" disabled={markSent.isPending} onClick={() => markSent.mutate(m.id)}>
                        Mark sent
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
