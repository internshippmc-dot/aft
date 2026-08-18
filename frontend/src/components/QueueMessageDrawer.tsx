import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Drawer } from "./Drawer";
import { api, ApiError } from "../lib/api";
import { CustomerMessage, MESSAGE_TYPES } from "../lib/types";
import { useToast } from "./Toast";

export function QueueMessageDrawer({
  open,
  orderNumber,
  onClose,
}: {
  open: boolean;
  orderNumber: string;
  onClose: () => void;
}) {
  const [type, setType] = useState<string>(MESSAGE_TYPES[0]);
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setType(MESSAGE_TYPES[0]);
      setBody("");
      setError(null);
    }
  }, [open]);

  const mutation = useMutation({
    mutationFn: () => api.post<CustomerMessage>("/messages", { order_number: orderNumber, type, body: body.trim() || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["messages"] });
      toast("Message queued.");
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not queue the message."),
  });

  return (
    <Drawer
      open={open}
      title="Queue status message"
      onClose={onClose}
      footer={
        <>
          <button className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" disabled={mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? "Queuing…" : "Queue message"}
          </button>
        </>
      }
    >
      <div className="field">
        <label htmlFor="mType">Template</label>
        <select id="mType" value={type} onChange={(e) => setType(e.target.value)}>
          {MESSAGE_TYPES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="mBody">Message (optional — edit before sending)</label>
        <textarea id="mBody" style={{ minHeight: 100 }} value={body} onChange={(e) => setBody(e.target.value)} />
        <p className="hint">This queues the message for {orderNumber}; it doesn't send anything automatically — mark it Sent from Customer Messages once it's gone out.</p>
      </div>
      {error && <p className="err on">{error}</p>}
    </Drawer>
  );
}
