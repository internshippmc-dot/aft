// Exact content from actually_fair_logistics_prototype_v28.html lines
// 1152-1169 ("Workflow & SLA" / "Order → Delivery Operating Cadence").
// The prototype's "Save changes" button didn't persist anything (just
// toast('Settings saved in prototype')) — this is kept as a reference
// page rather than faking a save that wouldn't do anything real.

const CADENCE: [string, string, string][] = [
  ["Day 0", "Order received on Shopify", "Send customer acknowledgement / confirmation the same day."],
  ["Day 1", "Acknowledged → MF sheet + manufacturer payment", "Create MF batch such as MF28 (#2218–#2250), send sheet and pay manufacturer same day."],
  ["Day 2", "Manufacturer dispatch + CN tracking", "Tracking receipt immediately triggers: factory-dispatch customer message + create AFT packing list and send to Hexalog."],
  ["Day 6", "Confirm AFT reached Hexalog CN warehouse", "Once confirmed, send CN warehouse update to every customer in the AFT batch."],
  ["Day 8", "Ask Hexalog for flight update", "Operational follow-up reminder."],
  ["Day 9", "Flight date expected", "Inform all customers in the batch of the planned flight date."],
  ["Day 12", "Flight flies", "Tell customers flight has flown, lands today and then undergoes customs."],
  ["Day 13", "Undergoing customs", "Internal tracking stage."],
  ["Day 14", "Reached Delhi", "Message customer, create iThink label and tracking link; dispatch tomorrow."],
  ["Day 15", "Dispatched from Delhi", "Send in-transit message + tracking link."],
  ["Day 18", "Check delivery", "Delivered → send delivered message. Not delivered → move check to next day."],
  ["Delivered + 5 days", "Feedback", "Send feedback request five days after the actual delivered date."],
];

export function WorkflowView() {
  return (
    <>
      <div className="h-row">
        <div>
          <h2 className="title">Workflow & SLA</h2>
          <div className="sub">Your exact Day 0 → Day 18 operating cadence and customer-message triggers.</div>
        </div>
      </div>

      <div className="panel-legs" style={{ maxWidth: 760 }}>
        <div className="eyebrow" style={{ marginBottom: 12 }}>
          Order → Delivery Operating Cadence
        </div>
        {CADENCE.map(([day, title, detail]) => (
          <div key={day} style={{ display: "flex", gap: 14, padding: "11px 0", borderBottom: "1px solid var(--rule-soft)" }}>
            <span className="pill blue" style={{ flex: "0 0 auto", height: "fit-content" }}>
              {day}
            </span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 12 }}>{title}</div>
              <div className="dim" style={{ fontSize: 12, marginTop: 2 }}>
                {detail}
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
