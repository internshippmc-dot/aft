import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Drawer } from "./Drawer";
import { api, ApiError } from "../lib/api";
import { ControlTowerCard, Me, PIPELINE_STAGES } from "../lib/types";
import { useToast } from "./Toast";

export function ControlTowerCardDrawer({
  card,
  me,
  onClose,
  onOpenBox,
}: {
  card: ControlTowerCard | null;
  me: Me;
  onClose: () => void;
  onOpenBox: (aft: string) => void;
}) {
  const [stage, setStage] = useState("");
  const [nextAction, setNextAction] = useState("");
  const [mfNumber, setMfNumber] = useState("");
  const [cnTracking, setCnTracking] = useState("");
  const [plStatus, setPlStatus] = useState("");
  const queryClient = useQueryClient();
  const toast = useToast();
  const canWrite = me.role === "owner" || me.role === "ops";

  useEffect(() => {
    if (card) {
      setStage(card.pipeline_stage);
      setNextAction(card.next_action || "");
      setMfNumber(card.mf_number || "");
      setCnTracking(card.cn_tracking || "");
      setPlStatus(card.pl_status || "");
    }
  }, [card]);

  const mutation = useMutation({
    mutationFn: () =>
      api.patch<ControlTowerCard>(`/control-tower/${encodeURIComponent(card!.aft_number)}`, {
        pipeline_stage: stage,
        next_action: nextAction.trim() || undefined,
        mf_number: mfNumber.trim() || undefined,
        cn_tracking: cnTracking.trim() || undefined,
        pl_status: plStatus.trim() || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["control-tower"] });
      toast(`${card!.aft_number} updated.`);
      onClose();
    },
    onError: (err) => toast(err instanceof ApiError ? err.message : "Could not save."),
  });

  const flag = useMutation({
    mutationFn: () =>
      api.patch<ControlTowerCard>(`/control-tower/${encodeURIComponent(card!.aft_number)}`, { flagged: !card!.flagged }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["control-tower"] });
    },
    onError: (err) => toast(err instanceof ApiError ? err.message : "Could not update the flag."),
  });

  if (!card) return null;

  return (
    <Drawer
      open={!!card}
      title={card.aft_number}
      onClose={onClose}
      footer={
        canWrite ? (
          <>
            <button className="btn ghost" onClick={onClose}>
              Cancel
            </button>
            <button className="btn primary" disabled={mutation.isPending} onClick={() => mutation.mutate()}>
              {mutation.isPending ? "Saving…" : "Save"}
            </button>
          </>
        ) : (
          <button className="btn ghost" onClick={onClose}>
            Close
          </button>
        )
      }
    >
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button className="btn small ghost" onClick={() => onOpenBox(card.aft_number)}>
          Open box detail
        </button>
        {canWrite && (
          <button className={`btn small ${card.flagged ? "danger" : "ghost"}`} disabled={flag.isPending} onClick={() => flag.mutate()}>
            ⚑ {card.flagged ? "Flagged" : "Flag priority"}
          </button>
        )}
      </div>

      <div className="facts" style={{ margin: "0 0 18px" }}>
        <div className="fact">
          <div className="k">Orders</div>
          <div className="v">{card.order_count}</div>
        </div>
        <div className="fact">
          <div className="k">Amount paid</div>
          <div className="v">₹{Number(card.amount_paid_inr).toLocaleString("en-IN")}</div>
        </div>
        <div className="fact">
          <div className="k">Labels</div>
          <div className="v">
            {card.labels_generated}/{card.labels_total}
          </div>
        </div>
        <div className="fact">
          <div className="k">Delivered</div>
          <div className="v">{card.delivery_pct}%</div>
        </div>
      </div>

      {canWrite ? (
        <>
          <div className="field">
            <label htmlFor="ctStage">Pipeline stage</label>
            <select id="ctStage" value={stage} onChange={(e) => setStage(e.target.value)}>
              {PIPELINE_STAGES.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="ctNext">Next action</label>
            <input id="ctNext" value={nextAction} onChange={(e) => setNextAction(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="ctMf">MF number</label>
            <input id="ctMf" className="mono" placeholder="MF 43" value={mfNumber} onChange={(e) => setMfNumber(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="ctCn">CN domestic tracking</label>
            <input id="ctCn" className="mono" value={cnTracking} onChange={(e) => setCnTracking(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="ctPl">Packing list status</label>
            <input id="ctPl" placeholder="Pending / Sent" value={plStatus} onChange={(e) => setPlStatus(e.target.value)} />
          </div>
        </>
      ) : (
        <>
          <div className="field">
            <label>Pipeline stage</label>
            <p>{card.pipeline_stage}</p>
          </div>
          <div className="field">
            <label>Next action</label>
            <p>{card.next_action || "—"}</p>
          </div>
        </>
      )}
    </Drawer>
  );
}
