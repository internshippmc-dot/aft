import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Drawer } from "./Drawer";
import { api, ApiError } from "../lib/api";
import { AttachResult, BoxManifest, OrderCreateIn } from "../lib/types";
import { useToast } from "./Toast";

interface ItemDraft {
  title: string;
  qty: string;
}

interface OrderDraft {
  customer_name: string;
  phone: string;
  city: string;
  items: ItemDraft[];
}

const EMPTY_ITEM: ItemDraft = { title: "", qty: "1" };
const EMPTY_DRAFT: OrderDraft = { customer_name: "", phone: "", city: "", items: [EMPTY_ITEM] };

function splitNumbers(raw: string): string[] {
  return raw
    .split(/[,\n\r]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export function NewBoxDrawer({
  open,
  prefillAft,
  onClose,
  onSaved,
}: {
  open: boolean;
  prefillAft?: string;
  onClose: () => void;
  onSaved: (box: BoxManifest) => void;
}) {
  const [aft, setAft] = useState(prefillAft || "");
  const [manufacturer, setManufacturer] = useState("");
  const [weight, setWeight] = useState("");
  const [date, setDate] = useState("");
  const [notes, setNotes] = useState("");
  const [orders, setOrders] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [failures, setFailures] = useState<AttachResult["failed"]>([]);
  // order numbers pasted but not in the system — quick-create forms below
  const [missing, setMissing] = useState<string[]>([]);
  const [drafts, setDrafts] = useState<Record<string, OrderDraft>>({});
  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setAft(prefillAft || "");
      setManufacturer("");
      setWeight("");
      setDate("");
      setNotes("");
      setOrders("");
      setError(null);
      setFailures([]);
      setMissing([]);
      setDrafts({});
    }
  }, [open, prefillAft]);

  function patch(no: string, key: keyof OrderDraft, value: string) {
    setDrafts((d) => ({ ...d, [no]: { ...(d[no] || EMPTY_DRAFT), [key]: value } }));
  }

  function patchItem(no: string, idx: number, key: keyof ItemDraft, value: string) {
    setDrafts((d) => {
      const base = d[no] || EMPTY_DRAFT;
      const items = base.items.map((it, i) => (i === idx ? { ...it, [key]: value } : it));
      return { ...d, [no]: { ...base, items } };
    });
  }

  function addItem(no: string) {
    setDrafts((d) => {
      const base = d[no] || EMPTY_DRAFT;
      return { ...d, [no]: { ...base, items: [...base.items, EMPTY_ITEM] } };
    });
  }

  function removeItem(no: string, idx: number) {
    setDrafts((d) => {
      const base = d[no] || EMPTY_DRAFT;
      return { ...d, [no]: { ...base, items: base.items.filter((_, i) => i !== idx) } };
    });
  }

  function dropMissing(no: string) {
    setMissing((m) => m.filter((n) => n !== no));
    setDrafts((d) => {
      const next = { ...d };
      delete next[no];
      return next;
    });
  }

  // The first save pastes order numbers and reports which don't exist; the
  // second save (after the quick-create forms are filled) sends the filled
  // forms as new_orders and re-attaches anything still pending.
  const missingSet = new Set(missing);
  const remainingRaw = splitNumbers(orders)
    .filter((n) => !missingSet.has(n))
    .join("\n");

  const newOrders: OrderCreateIn[] | undefined = missing.length
    ? missing.map((no) => {
        const d = drafts[no] || EMPTY_DRAFT;
        return {
          order_number: no,
          customer_name: d.customer_name.trim(),
          phone: d.phone.trim() || undefined,
          city: d.city.trim() || undefined,
          items: d.items
            .filter((i) => i.title.trim())
            .map((i) => ({ product_title: i.title.trim(), quantity: parseInt(i.qty, 10) || 1 })),
        };
      })
    : undefined;

  const draftsValid = missing.every((no) => {
    const d = drafts[no];
    return !!d && d.customer_name.trim().length > 0 && d.items.some((i) => i.title.trim().length > 0);
  });

  // Attaching to an existing box goes through /items so the per-order
  // failure reasons (PRD F2) come back; creating a new box uses the
  // combined create+attach path since there's nothing to conflict with yet.
  const mutation = useMutation({
    mutationFn: async () => {
      if (prefillAft) {
        const result = await api.post<AttachResult>(`/boxes/${encodeURIComponent(prefillAft)}/items`, {
          orders_raw: remainingRaw || undefined,
          new_orders: newOrders,
        });
        const box = await api.get<BoxManifest>(`/boxes/${encodeURIComponent(prefillAft)}`);
        return { box, result };
      }
      const box = await api.post<BoxManifest>("/boxes", {
        aft_number: aft.trim(),
        manufacturer: manufacturer.trim() || undefined,
        gross_weight_kg: weight ? weight : undefined,
        dispatched_on: date || undefined,
        notes: notes.trim() || undefined,
        orders_raw: remainingRaw || undefined,
        new_orders: newOrders,
      });
      return { box, result: null as AttachResult | null };
    },
    onSuccess: ({ box, result }) => {
      queryClient.invalidateQueries({ queryKey: ["boxes"] });
      queryClient.invalidateQueries({ queryKey: ["box", box.aft_number] });
      // attach-mode failures come back in `result`; create-mode failures ride
      // on the box manifest's `attach` field so pasted orders aren't dropped silently.
      const attach = result || box.attach;
      if (attach && attach.missing.length > 0) {
        setMissing(attach.missing);
        setDrafts((d) => {
          const next = { ...d };
          for (const no of attach.missing) if (!next[no]) next[no] = { ...EMPTY_DRAFT, items: [{ ...EMPTY_ITEM }] };
          return next;
        });
        setFailures(attach.failed);
        toast(
          `${attach.missing.length} order${attach.missing.length === 1 ? "" : "s"} not found — add customer and item details below to create ${attach.missing.length === 1 ? "it" : "them"}.`
        );
        return; // keep the drawer open for the create forms
      }
      if (attach && attach.failed.length > 0) {
        setFailures(attach.failed);
        toast(`${attach.attached.length} attached, ${attach.failed.length} failed — see below.`);
        return;
      }
      if (attach) {
        toast(`${box.aft_number} saved. ${attach.attached.length} order${attach.attached.length === 1 ? "" : "s"} attached and logged.`);
      } else {
        toast(`${box.aft_number} saved.`);
      }
      onSaved(box);
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not save the box."),
  });

  const canSave =
    (prefillAft ? orders.trim().length > 0 || missing.length > 0 : aft.trim().length > 0) &&
    (!missing.length || draftsValid) &&
    !mutation.isPending;

  return (
    <Drawer
      open={open}
      title={prefillAft ? "Attach orders" : "New box"}
      onClose={onClose}
      footer={
        <>
          <button className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn" disabled={!canSave} onClick={() => mutation.mutate()}>
            {mutation.isPending ? "Saving…" : missing.length ? "Create & attach" : "Save box"}
          </button>
        </>
      }
    >
      <div className="field">
        <label htmlFor="dAft">AFT number</label>
        <input
          id="dAft"
          className="mono"
          placeholder="AFT-0236"
          value={aft}
          disabled={!!prefillAft}
          onChange={(e) => setAft(e.target.value)}
        />
        <p className="hint">Uppercased on save. An existing number opens that box instead of creating a duplicate.</p>
      </div>
      {!prefillAft && (
        <>
          <div className="field">
            <label htmlFor="dMfr">Manufacturer</label>
            <input id="dMfr" placeholder="e.g. Kathy · Yiwu" value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="dWeight">Gross weight (kg)</label>
            <input id="dWeight" className="mono" placeholder="3.20" value={weight} onChange={(e) => setWeight(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="dDate">Dispatched from manufacturer</label>
            <input id="dDate" type="date" className="mono" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="dNotes">Notes</label>
            <textarea id="dNotes" placeholder="Anything worth remembering about this box" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </>
      )}
      <div className="field">
        <label htmlFor="dOrders">Orders in this box</label>
        <textarea
          id="dOrders"
          placeholder={"#2000\n#2001\n#2002"}
          value={orders}
          onChange={(e) => setOrders(e.target.value)}
        />
        <p className="hint">One per line, or paste comma separated. Orders already assigned elsewhere are reported back with the box they sit in. Unknown numbers get a create form below.</p>
      </div>
      {missing.length > 0 && (
        <div className="field">
          <label>Create these orders</label>
          {missing.map((no) => {
            const d = drafts[no] || EMPTY_DRAFT;
            return (
              <div key={no} style={{ border: "1px solid var(--rule)", borderRadius: 2, padding: 10, marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <span className="mono">{no}</span>
                  <button className="btn ghost" style={{ padding: "2px 6px" }} onClick={() => dropMissing(no)} title="Skip this order for now">
                    Skip
                  </button>
                </div>
                <input
                  placeholder="Customer name"
                  value={d.customer_name}
                  onChange={(e) => patch(no, "customer_name", e.target.value)}
                />
                <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                  <input placeholder="Phone" value={d.phone} onChange={(e) => patch(no, "phone", e.target.value)} />
                  <input placeholder="City" value={d.city} onChange={(e) => patch(no, "city", e.target.value)} />
                </div>
                {d.items.map((it, idx) => (
                  <div key={idx} style={{ display: "flex", gap: 6, marginTop: 6, alignItems: "center" }}>
                    <input
                      placeholder="Item (e.g. Daily Track Set)"
                      value={it.title}
                      onChange={(e) => patchItem(no, idx, "title", e.target.value)}
                      style={{ flex: 1 }}
                    />
                    <input
                      type="number"
                      min={1}
                      value={it.qty}
                      onChange={(e) => patchItem(no, idx, "qty", e.target.value)}
                      style={{ width: 52 }}
                    />
                    {d.items.length > 1 && (
                      <button className="btn ghost" style={{ padding: "4px 8px" }} onClick={() => removeItem(no, idx)}>
                        ×
                      </button>
                    )}
                  </div>
                ))}
                <button className="btn ghost" style={{ marginTop: 6 }} onClick={() => addItem(no)}>
                  + Add item
                </button>
              </div>
            );
          })}
        </div>
      )}
      {failures.length > 0 && (
        <div className="field">
          <label>Could not attach</label>
          {failures.map((f) => (
            <p key={f.order_number} className="err on" style={{ marginTop: 4 }}>
              {f.order_number} — {f.reason}
            </p>
          ))}
        </div>
      )}
      {error && <p className="err on">{error}</p>}
    </Drawer>
  );
}
