import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Drawer } from "./Drawer";
import { api, ApiError } from "../lib/api";
import { Task } from "../lib/types";
import { useToast } from "./Toast";

const PRIORITIES = ["High", "Medium", "Low"];

export function NewTaskDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("Medium");
  const [dueOn, setDueOn] = useState("");
  const [entityId, setEntityId] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setTitle("");
      setPriority("Medium");
      setDueOn("");
      setEntityId("");
      setNotes("");
      setError(null);
    }
  }, [open]);

  const mutation = useMutation({
    mutationFn: () =>
      api.post<Task>("/tasks", {
        title: title.trim(),
        priority,
        due_on: dueOn || undefined,
        entity_id: entityId.trim() || undefined,
        entity_type: entityId.trim() ? (entityId.trim().startsWith("#") ? "order" : "box") : undefined,
        notes: notes.trim() || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      toast("Task added.");
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not add the task."),
  });

  const canSave = title.trim() && !mutation.isPending;

  return (
    <Drawer
      open={open}
      title="New task"
      onClose={onClose}
      footer={
        <>
          <button className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" disabled={!canSave} onClick={() => mutation.mutate()}>
            {mutation.isPending ? "Saving…" : "Add task"}
          </button>
        </>
      }
    >
      <div className="field">
        <label htmlFor="tTitle">Title</label>
        <input id="tTitle" placeholder="e.g. Send packing list for AFT-0234" value={title} onChange={(e) => setTitle(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="tPriority">Priority</label>
        <select id="tPriority" value={priority} onChange={(e) => setPriority(e.target.value)}>
          {PRIORITIES.map((p) => (
            <option key={p}>{p}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="tDue">Due date</label>
        <input id="tDue" type="date" className="mono" value={dueOn} onChange={(e) => setDueOn(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="tEntity">Related order or box (optional)</label>
        <input id="tEntity" className="mono" placeholder="#AF1442 or AFT-0231" value={entityId} onChange={(e) => setEntityId(e.target.value)} />
        <p className="hint">Starts with # → treated as an order. Anything else → treated as a box.</p>
      </div>
      <div className="field">
        <label htmlFor="tNotes">Notes</label>
        <textarea id="tNotes" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>
      {error && <p className="err on">{error}</p>}
    </Drawer>
  );
}
