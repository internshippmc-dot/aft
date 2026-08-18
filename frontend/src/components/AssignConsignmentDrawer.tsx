import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Drawer } from "./Drawer";
import { api, ApiError } from "../lib/api";
import { ConsignmentOut } from "../lib/types";
import { useToast } from "./Toast";

export function AssignConsignmentDrawer({
  open,
  aftNumber,
  onClose,
}: {
  open: boolean;
  aftNumber: string;
  onClose: () => void;
}) {
  const [trackingId, setTrackingId] = useState("");
  const [weight, setWeight] = useState("");
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setTrackingId("");
      setWeight("");
      setError(null);
    }
  }, [open]);

  const mutation = useMutation({
    mutationFn: () =>
      api.post<ConsignmentOut>("/consignments", {
        tracking_id: trackingId.trim(),
        box_afts: [aftNumber],
        chargeable_weight_kg: weight || undefined,
      }),
    onSuccess: (c) => {
      queryClient.invalidateQueries({ queryKey: ["boxes"] });
      queryClient.invalidateQueries({ queryKey: ["box", aftNumber] });
      queryClient.invalidateQueries({ queryKey: ["consolidation"] });
      const shortfall = parseFloat(c.shortfall_kg);
      toast(
        shortfall > 0
          ? `${c.tracking_id} saved. ${shortfall.toFixed(2)} kg short of the 10 kg minimum.`
          : `${c.tracking_id} saved.`
      );
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not save the consignment."),
  });

  return (
    <Drawer
      open={open}
      title="Assign to consignment"
      onClose={onClose}
      footer={
        <>
          <button className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn" disabled={!trackingId.trim() || mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      <div className="field">
        <label htmlFor="cTrack">Tracking ID</label>
        <input id="cTrack" className="mono" placeholder="HXL-772109" value={trackingId} onChange={(e) => setTrackingId(e.target.value)} />
        <p className="hint">An existing tracking ID opens that consignment and adds this box to it.</p>
      </div>
      <div className="field">
        <label htmlFor="cWeight">Chargeable weight (kg)</label>
        <input id="cWeight" className="mono" placeholder="10.00" value={weight} onChange={(e) => setWeight(e.target.value)} />
        <p className="hint">Below 10 kg, Hexalog still bills for 10 kg — the console will flag the shortfall.</p>
      </div>
      {error && <p className="err on">{error}</p>}
    </Drawer>
  );
}
