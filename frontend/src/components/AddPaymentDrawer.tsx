import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Drawer } from "./Drawer";
import { api, ApiError } from "../lib/api";
import { Payment } from "../lib/types";
import { useToast } from "./Toast";

const TYPES = ["Manufacturer", "Hexalog", "Logistics", "Refund", "Other"];
const METHODS = ["Bank Transfer", "UPI", "Wallet", "Other"];

export function AddPaymentDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [occurredOn, setOccurredOn] = useState("");
  const [type, setType] = useState(TYPES[0]);
  const [payee, setPayee] = useState("");
  const [reference, setReference] = useState("");
  const [boxAft, setBoxAft] = useState("");
  const [amount, setAmount] = useState("");
  const [paidBy, setPaidBy] = useState("");
  const [method, setMethod] = useState(METHODS[0]);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setOccurredOn(new Date().toISOString().slice(0, 10));
      setType(TYPES[0]);
      setPayee("");
      setReference("");
      setBoxAft("");
      setAmount("");
      setPaidBy("");
      setMethod(METHODS[0]);
      setNotes("");
      setError(null);
    }
  }, [open]);

  const mutation = useMutation({
    mutationFn: () =>
      api.post<Payment>("/payments", {
        occurred_on: occurredOn,
        type,
        payee: payee.trim(),
        reference: reference.trim() || undefined,
        box_aft_number: boxAft.trim() || undefined,
        amount_inr: amount,
        paid_by: paidBy.trim(),
        method,
        notes: notes.trim() || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payments"] });
      toast("Payment recorded.");
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not save the payment."),
  });

  const canSave = occurredOn && payee.trim() && amount && paidBy.trim() && !mutation.isPending;

  return (
    <Drawer
      open={open}
      title="Record payment"
      onClose={onClose}
      footer={
        <>
          <button className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" disabled={!canSave} onClick={() => mutation.mutate()}>
            {mutation.isPending ? "Saving…" : "Save payment"}
          </button>
        </>
      }
    >
      <div className="field">
        <label htmlFor="pDate">Date</label>
        <input id="pDate" type="date" className="mono" value={occurredOn} onChange={(e) => setOccurredOn(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="pType">Type</label>
        <select id="pType" value={type} onChange={(e) => setType(e.target.value)}>
          {TYPES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="pPayee">Paid to</label>
        <input id="pPayee" placeholder="e.g. Kathy / Main CN Manufacturer" value={payee} onChange={(e) => setPayee(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="pAmount">Amount (INR)</label>
        <input id="pAmount" className="mono" placeholder="48650" value={amount} onChange={(e) => setAmount(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="pBy">Paid by</label>
        <input id="pBy" placeholder="Who authorised/made this payment" value={paidBy} onChange={(e) => setPaidBy(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="pMethod">Method</label>
        <select id="pMethod" value={method} onChange={(e) => setMethod(e.target.value)}>
          {METHODS.map((m) => (
            <option key={m}>{m}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="pBox">Related AFT box (optional)</label>
        <input id="pBox" className="mono" placeholder="AFT-0231" value={boxAft} onChange={(e) => setBoxAft(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="pRef">Reference (optional)</label>
        <input id="pRef" placeholder="e.g. MF 43 / AFT 43" value={reference} onChange={(e) => setReference(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="pNotes">Notes</label>
        <textarea id="pNotes" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>
      {error && <p className="err on">{error}</p>}
    </Drawer>
  );
}
