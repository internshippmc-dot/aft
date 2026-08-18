import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Drawer } from "./Drawer";
import { api, ApiError } from "../lib/api";
import { BoxManifest } from "../lib/types";
import { useToast } from "./Toast";

export function EditBoxDrawer({
  open,
  box,
  onClose,
}: {
  open: boolean;
  box: BoxManifest | null;
  onClose: () => void;
}) {
  const [manufacturer, setManufacturer] = useState("");
  const [weight, setWeight] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    if (open && box) {
      setManufacturer(box.manufacturer || "");
      setWeight(box.gross_weight_kg || "");
      setNotes(box.notes || "");
      setError(null);
    }
  }, [open, box]);

  const mutation = useMutation({
    mutationFn: () =>
      api.patch<BoxManifest>(`/boxes/${encodeURIComponent(box!.aft_number)}`, {
        manufacturer: manufacturer.trim() || null,
        gross_weight_kg: weight ? weight : null,
        notes: notes.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["boxes"] });
      queryClient.invalidateQueries({ queryKey: ["box", box!.aft_number] });
      toast(`Box ${box!.aft_number} updated.`);
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not save changes."),
  });

  return (
    <Drawer
      open={open}
      title={`Edit ${box?.aft_number ?? "box"}`}
      onClose={onClose}
      footer={
        <>
          <button className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn" disabled={mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? "Saving…" : "Save changes"}
          </button>
        </>
      }
    >
      <div className="field">
        <label htmlFor="eMfr">Manufacturer</label>
        <input id="eMfr" placeholder="e.g. Kathy · Yiwu" value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="eWeight">Gross weight (kg)</label>
        <input id="eWeight" className="mono" placeholder="3.20" value={weight} onChange={(e) => setWeight(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="eNotes">Notes</label>
        <textarea id="eNotes" placeholder="Anything worth remembering about this box" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <p className="hint">Shown on the box page, e.g. "Landed in Delhi on 09 Aug, 8 days from manufacturer dispatch."</p>
      </div>
      {error && <p className="err on">{error}</p>}
    </Drawer>
  );
}
