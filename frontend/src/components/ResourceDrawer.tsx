import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Drawer } from "./Drawer";
import { api, ApiError } from "../lib/api";
import { Resource } from "../lib/types";
import { useToast } from "./Toast";

const TYPES = ["Link", "SOP"];

export function ResourceDrawer({ open, editing, onClose }: { open: boolean; editing: Resource | null; onClose: () => void }) {
  const [type, setType] = useState(TYPES[0]);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [processText, setProcessText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setType(editing?.type || TYPES[0]);
      setTitle(editing?.title || "");
      setCategory(editing?.category || "");
      setUrl(editing?.url || "");
      setDescription(editing?.description || "");
      setProcessText(editing?.process_text || "");
      setError(null);
    }
  }, [open, editing]);

  const mutation = useMutation({
    mutationFn: () => {
      const body = {
        type,
        title: title.trim(),
        category: category.trim() || undefined,
        url: url.trim() || undefined,
        description: description.trim() || undefined,
        process_text: processText.trim() || undefined,
      };
      return editing ? api.patch<Resource>(`/resources/${editing.id}`, body) : api.post<Resource>("/resources", body);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resources"] });
      toast(editing ? "Resource updated." : "Resource added.");
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not save the resource."),
  });

  const canSave = title.trim() && !mutation.isPending;

  return (
    <Drawer
      open={open}
      title={editing ? "Edit resource" : "New resource"}
      onClose={onClose}
      footer={
        <>
          <button className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" disabled={!canSave} onClick={() => mutation.mutate()}>
            {mutation.isPending ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      <div className="field">
        <label htmlFor="rsType">Type</label>
        <select id="rsType" value={type} onChange={(e) => setType(e.target.value)}>
          {TYPES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="rsTitle">Title</label>
        <input id="rsTitle" value={title} onChange={(e) => setTitle(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="rsCategory">Category</label>
        <input id="rsCategory" placeholder="e.g. Orders, Logistics" value={category} onChange={(e) => setCategory(e.target.value)} />
      </div>
      {type === "Link" && (
        <div className="field">
          <label htmlFor="rsUrl">URL</label>
          <input id="rsUrl" className="mono" value={url} onChange={(e) => setUrl(e.target.value)} />
        </div>
      )}
      <div className="field">
        <label htmlFor="rsDesc">Description</label>
        <textarea id="rsDesc" value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
      {type === "SOP" && (
        <div className="field">
          <label htmlFor="rsProcess">Process</label>
          <textarea id="rsProcess" style={{ minHeight: 140 }} value={processText} onChange={(e) => setProcessText(e.target.value)} />
        </div>
      )}
      {error && <p className="err on">{error}</p>}
    </Drawer>
  );
}
