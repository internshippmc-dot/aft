import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Drawer } from "./Drawer";
import { api, ApiError } from "../lib/api";
import { CustomerMessage, OrderDetail } from "../lib/types";
import { MESSAGE_TEMPLATES, OrderContext, renderTemplate } from "../lib/messageTemplates";
import { useToast } from "./Toast";

export function QueueMessageDrawer({
  open,
  order,
  onClose,
}: {
  open: boolean;
  order: OrderDetail;
  onClose: () => void;
}) {
  const [templateId, setTemplateId] = useState(MESSAGE_TEMPLATES[0].id);
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  const ctx: OrderContext = useMemo(
    () => ({
      customerName: order.customer_name,
      orderNumber: order.order_number,
      productName: order.items[0]?.product_title,
      colour: order.items[0]?.colour || undefined,
      size: order.items[0]?.size || undefined,
      quantity: order.items.reduce((n, i) => n + i.quantity, 0) || undefined,
      totalInr: order.total_inr,
      address: order.city || undefined,
      itemsList: order.items.map((i) => `${i.product_title} - ${i.colour || "-"} - ${i.size || "-"} x${i.quantity}`).join("\n"),
    }),
    [order]
  );

  const template = MESSAGE_TEMPLATES.find((t) => t.id === templateId) || MESSAGE_TEMPLATES[0];

  useEffect(() => {
    if (open) {
      setTemplateId(MESSAGE_TEMPLATES[0].id);
      setError(null);
    }
  }, [open]);

  useEffect(() => {
    if (open) setBody(renderTemplate(template, ctx));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, templateId]);

  const mutation = useMutation({
    mutationFn: () => api.post<CustomerMessage>("/messages", { order_number: order.order_number, type: template.label, body }),
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
        <select id="mType" value={templateId} onChange={(e) => setTemplateId(e.target.value)}>
          {MESSAGE_TEMPLATES.map((t) => (
            <option key={t.id} value={t.id}>
              {t.label}
            </option>
          ))}
        </select>
        <p className="hint">Sent as {template.agent}. Any {"{{placeholder}}"} left in the body below needs a manual fill-in before sending.</p>
      </div>
      <div className="field">
        <label htmlFor="mBody">Message (edit before sending)</label>
        <textarea id="mBody" style={{ minHeight: 180 }} value={body} onChange={(e) => setBody(e.target.value)} />
        <p className="hint">This queues the message for {order.order_number}; it doesn't send anything automatically — mark it Sent from Customer Messages once it's gone out on WhatsApp.</p>
      </div>
      {error && <p className="err on">{error}</p>}
    </Drawer>
  );
}
