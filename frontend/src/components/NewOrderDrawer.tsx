import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Drawer } from "./Drawer";
import { api, ApiError } from "../lib/api";
import { OrderDetail } from "../lib/types";
import { useToast } from "./Toast";

interface ItemDraft {
  title: string;
  colour: string;
  size: string;
  qty: string;
}

const EMPTY_ITEM: ItemDraft = { title: "", colour: "", size: "", qty: "1" };

export function NewOrderDrawer({ open, onClose, onSaved }: { open: boolean; onClose: () => void; onSaved: (orderNumber: string) => void }) {
  const [orderNumber, setOrderNumber] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [phone, setPhone] = useState("");
  const [city, setCity] = useState("");
  const [items, setItems] = useState<ItemDraft[]>([{ ...EMPTY_ITEM }]);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setOrderNumber("");
      setCustomerName("");
      setPhone("");
      setCity("");
      setItems([{ ...EMPTY_ITEM }]);
      setError(null);
    }
  }, [open]);

  function patchItem(idx: number, key: keyof ItemDraft, value: string) {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, [key]: value } : it)));
  }

  const mutation = useMutation({
    mutationFn: () =>
      api.post<OrderDetail>("/orders", {
        order_number: orderNumber.trim(),
        customer_name: customerName.trim(),
        phone: phone.trim() || undefined,
        city: city.trim() || undefined,
        items: items
          .filter((i) => i.title.trim())
          .map((i) => ({
            product_title: i.title.trim(),
            colour: i.colour.trim() || undefined,
            size: i.size.trim() || undefined,
            quantity: parseInt(i.qty, 10) || 1,
          })),
      }),
    onSuccess: (order) => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      toast(`${order.order_number} created.`);
      onSaved(order.order_number);
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not create the order."),
  });

  const canSave = orderNumber.trim() && customerName.trim() && items.some((i) => i.title.trim()) && !mutation.isPending;

  return (
    <Drawer
      open={open}
      title="New order"
      onClose={onClose}
      footer={
        <>
          <button className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" disabled={!canSave} onClick={() => mutation.mutate()}>
            {mutation.isPending ? "Saving…" : "Create order"}
          </button>
        </>
      }
    >
      <div className="field">
        <label htmlFor="oNo">Order number</label>
        <input id="oNo" className="mono" placeholder="e.g. #CUSTOM-001 for a non-Shopify order" value={orderNumber} onChange={(e) => setOrderNumber(e.target.value)} />
        <p className="hint">Use this for orders that don't come through Shopify (phone/Instagram/custom orders).</p>
      </div>
      <div className="field">
        <label htmlFor="oName">Customer name</label>
        <input id="oName" value={customerName} onChange={(e) => setCustomerName(e.target.value)} />
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="oPhone">Phone</label>
          <input id="oPhone" value={phone} onChange={(e) => setPhone(e.target.value)} />
        </div>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="oCity">City</label>
          <input id="oCity" value={city} onChange={(e) => setCity(e.target.value)} />
        </div>
      </div>
      <div className="field">
        <label>Items</label>
        {items.map((it, idx) => (
          <div key={idx} style={{ display: "flex", gap: 6, marginTop: 6 }}>
            <input placeholder="Product" value={it.title} onChange={(e) => patchItem(idx, "title", e.target.value)} style={{ flex: 2 }} />
            <input placeholder="Colour" value={it.colour} onChange={(e) => patchItem(idx, "colour", e.target.value)} style={{ flex: 1 }} />
            <input placeholder="Size" value={it.size} onChange={(e) => patchItem(idx, "size", e.target.value)} style={{ flex: 1 }} />
            <input type="number" min={1} value={it.qty} onChange={(e) => patchItem(idx, "qty", e.target.value)} style={{ width: 52 }} />
          </div>
        ))}
        <button className="btn ghost small" style={{ marginTop: 8 }} onClick={() => setItems((prev) => [...prev, { ...EMPTY_ITEM }])}>
          + Add item
        </button>
      </div>
      {error && <p className="err on">{error}</p>}
    </Drawer>
  );
}
