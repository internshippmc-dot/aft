import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Drawer } from "./Drawer";
import { api, ApiError } from "../lib/api";
import { ReturnCase } from "../lib/types";
import { useToast } from "./Toast";

const TYPES = ["Return", "Exchange"];

export function NewReturnDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [orderNumber, setOrderNumber] = useState("");
  const [type, setType] = useState(TYPES[0]);
  const [reason, setReason] = useState("");
  const [requestedOn, setRequestedOn] = useState("");
  const [nextAction, setNextAction] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setOrderNumber("");
      setType(TYPES[0]);
      setReason("");
      setRequestedOn(new Date().toISOString().slice(0, 10));
      setNextAction("");
      setNotes("");
      setError(null);
    }
  }, [open]);

  const mutation = useMutation({
    mutationFn: () =>
      api.post<ReturnCase>("/returns", {
        order_number: orderNumber.trim(),
        type,
        reason: reason.trim() || undefined,
        requested_on: requestedOn,
        next_action: nextAction.trim() || undefined,
        notes: notes.trim() || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["returns"] });
      toast("Case created.");
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not create the case."),
  });

  const canSave = orderNumber.trim() && requestedOn && !mutation.isPending;

  return (
    <Drawer
      open={open}
      title="New return / exchange"
      onClose={onClose}
      footer={
        <>
          <button className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" disabled={!canSave} onClick={() => mutation.mutate()}>
            {mutation.isPending ? "Saving…" : "Create case"}
          </button>
        </>
      }
    >
      <div className="field">
        <label htmlFor="rOrder">Order number</label>
        <input id="rOrder" className="mono" placeholder="#AF1442" value={orderNumber} onChange={(e) => setOrderNumber(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="rType">Type</label>
        <select id="rType" value={type} onChange={(e) => setType(e.target.value)}>
          {TYPES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="rReason">Reason</label>
        <input id="rReason" placeholder="e.g. Sizing issue" value={reason} onChange={(e) => setReason(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="rDate">Requested on</label>
        <input id="rDate" type="date" className="mono" value={requestedOn} onChange={(e) => setRequestedOn(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="rNext">Next action</label>
        <input id="rNext" placeholder="e.g. Schedule pickup" value={nextAction} onChange={(e) => setNextAction(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="rNotes">Notes</label>
        <textarea id="rNotes" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>
      {error && <p className="err on">{error}</p>}
    </Drawer>
  );
}
