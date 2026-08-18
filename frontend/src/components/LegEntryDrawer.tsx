import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Drawer } from "./Drawer";
import { api, ApiError } from "../lib/api";
import { useToast } from "./Toast";

const LEG_OPTIONS = [
  ["MFG_DISPATCH", "Dispatch (manufacturer)"],
  ["CN_WAREHOUSE", "CN warehouse"],
  ["FLIGHT", "Flight"],
  ["DELHI_WAREHOUSE", "Delhi warehouse"],
];

export function LegEntryDrawer({
  open,
  aftNumber,
  trackingId,
  onClose,
}: {
  open: boolean;
  aftNumber: string;
  trackingId: string | null;
  onClose: () => void;
}) {
  const [leg, setLeg] = useState("MFG_DISPATCH");
  const [date, setDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setLeg("MFG_DISPATCH");
      setDate(new Date().toISOString().slice(0, 10));
      setError(null);
    }
  }, [open]);

  const scopeLabel = trackingId ? `consignment ${trackingId}` : `box ${aftNumber}`;
  const path = trackingId ? `/consignments/${encodeURIComponent(trackingId)}/legs` : `/boxes/${encodeURIComponent(aftNumber)}/legs`;

  const mutation = useMutation({
    mutationFn: () => api.post(path, { leg, occurred_on: date }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["boxes"] });
      queryClient.invalidateQueries({ queryKey: ["box", aftNumber] });
      if (trackingId) queryClient.invalidateQueries({ queryKey: ["consignment", trackingId] });
      toast(`Leg date recorded for ${scopeLabel}.`);
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not save the leg date."),
  });

  return (
    <Drawer
      open={open}
      title="Enter leg date"
      onClose={onClose}
      footer={
        <>
          <button className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn" disabled={!date || mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      <p className="hint" style={{ marginBottom: 14 }}>
        Applies to {scopeLabel}
        {trackingId ? " — every box and order inside it inherits this date." : "."}
      </p>
      <div className="field">
        <label htmlFor="legSelect">Leg</label>
        <select id="legSelect" value={leg} onChange={(e) => setLeg(e.target.value)} style={{ width: "100%", padding: "9px 10px", border: "1px solid var(--rule)", borderRadius: 2 }}>
          {LEG_OPTIONS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="legDate">Date</label>
        <input id="legDate" type="date" className="mono" value={date} onChange={(e) => setDate(e.target.value)} />
        <p className="hint">Entering out of order is allowed but flagged — real shipments arrive out of sequence too.</p>
      </div>
      {error && <p className="err on">{error}</p>}
    </Drawer>
  );
}
