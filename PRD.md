# PRD — Actually Fair Operations Console
### Consignment tracking, order linkage, and data entry

Version 0.1 · August 2026 · Owner: Siddharth

---

## 1. Problem

Fulfilment state lives in a hand-maintained sheet ("Final - Order Tracking", 38 columns, A–AL). When a box leaves the manufacturer with an AFT number, and later gets an air waybill from Hexalog, nothing connects that box to the orders inside it except manual lookup. Three consequences:

- Nobody can answer "which orders are in AFT-0231" without scanning the sheet.
- Nobody can answer "when does this box land in Delhi" except by guessing.
- Customer status messages are sent order-by-order instead of box-by-box, so a box landing in Delhi does not automatically produce the 40 messages it should.

The order promise is delivery inside 2 weeks. Freight now carries a 10 kg chargeable minimum per shipment, so consolidation decisions directly change that promise. Both need to be visible on one screen.

## 2. Users

| Role | Who | Can do |
|---|---|---|
| `owner` | Siddharth | Everything, including user management, exports, and deletion |
| `ops` | Ops staff | Create and edit boxes, enter leg dates, assign orders, send messages |
| `viewer` | Anyone else who needs read access | Read and search only |

Internal only. No customer-facing surface. Expected concurrent users: under 10.

## 3. Assumptions

Flagged for confirmation before build starts. Each one changes the data model if wrong.

1. **AFT number identifies a physical box**, not a shipment. One Hexalog shipment (one tracking ID / AWB) can carry several AFT boxes. The model below assumes this. If one AFT number always equals one shipment, the `boxes` table collapses into `consignments`.
2. An order can be split across boxes at the line-item level (partial dispatch already exists in the message library), so linkage is `box ↔ order_item`, not `box ↔ order`.
3. The Delhi warehouse is a single node. No second domestic hub.
4. Order data comes from Shopify. Fulfilment state comes from manual entry and the daily XLSX upload. Shopify is never written to except order tagging.
5. Deployment is a single private instance. No multi-tenant requirement.

## 4. Scope

**In scope for v1**

- Box and consignment data entry
- Order-to-box assignment
- Predicted Delhi warehouse arrival
- Universal search across orders, customers, boxes, waybills
- Shopify order sync
- XLSX import from the existing tracking sheet
- Login, roles, audit log

**Out of scope for v1**

- Sending WhatsApp messages (the console flags what is ready to send and hands off to the existing generator)
- Inventory and purchase orders
- Customer-facing tracking page
- Multi-store

## 5. Objects

```
Customer —< Order —< OrderItem >— BoxItem —> Box —> Consignment
                                                 │
                                             LegEvent
```

- **Consignment** — one Hexalog shipment. Holds the tracking ID / AWB, chargeable weight, flight date, and the freight invoice.
- **Box** — one physical carton with an AFT number. Belongs to zero or one consignment. Unassigned boxes are the consolidation queue.
- **LegEvent** — a dated transition. Five ordered legs: `MFG_DISPATCH → CN_WAREHOUSE → FLIGHT → DELHI_WAREHOUSE → LAST_MILE_HANDOVER`.
- **OrderItem** — one Shopify line item, with variant, colour, size.

## 6. Features

### F1 — Box entry
Create a box by typing an AFT number. Optional at creation: manufacturer, dispatch date, weight, notes. A box with no orders is valid and expected; orders get attached as the packing list arrives.

*Accepts:* AFT number is unique, case-insensitive, trimmed. Duplicate entry surfaces the existing box instead of erroring.

### F2 — Assign orders to a box
Search an order by number, customer name, or phone, and attach it to the open box. Bulk paste is supported: a newline or comma separated list of order numbers attaches all of them in one action, and reports which ones failed and why.

*Accepts:* attaching an order already in another box is blocked with the conflicting AFT number named in the message. Partial attach at item level is available behind an "attach specific items" control.

### F3 — Consignment entry
Create a consignment by entering the tracking ID. Attach one or more boxes. Enter chargeable weight and flight date. The moment a box joins a consignment, every order in that box inherits the consignment's dates.

*Accepts:* entering a tracking ID that already exists opens it. Chargeable weight below 10 kg shows the shortfall against the Hexalog minimum.

### F4 — What is in this box
Given an AFT number or a tracking ID, return the full manifest: every order, customer name, items, variant, size, value, and current stage. This is the primary read path and must resolve in under 300 ms.

### F5 — Predicted Delhi arrival
Every box and every order shows a predicted Delhi warehouse date, computed from historical leg durations. See section 7.

### F6 — Universal search
One input resolves order number, customer name, phone, email, AWB, tracking ID, and AFT number. Results are grouped by type. Selecting an order opens its full timeline: order placed, box assigned, each leg with actual or predicted date, courier handover, delivery.

### F7 — Leg date entry
Enter a date against a leg for a consignment, and it applies to every box and order inside it. Entering out of order is allowed but flagged, since real shipments do arrive out of sequence in the sheet.

### F8 — Shopify sync
Pull orders on a schedule and on demand. Read-only except for optional order tagging. Fields required: order number, created at, customer name, phone, email, line items with variant and size, total, payment method, financial status, shipping address.

### F9 — XLSX import
Upload the "Final - Order Tracking" sheet. Column mapping is stored, so subsequent uploads need no remapping. The importer previews changes before committing, and never deletes rows the sheet omits.

### F10 — Audit log
Every write records actor, timestamp, object, before, and after. Visible to `owner`, immutable, exportable.

## 7. ETA model

Predict the Delhi warehouse arrival date for any box that has not reached it.

Method: for each leg, take the trailing 20 completed shipments and compute the median and 80th percentile duration in days. Sum the medians for the remaining legs, add to the last known actual date, and skip Sundays for the flight and customs legs. Return three values: `p50` date, `p80` date, and `sample_n`.

Rules:

- Fewer than 5 completed samples for a leg, fall back to a configured default and label the estimate low confidence.
- Display as a range, never a single hard date, in any customer-facing text.
- Recompute nightly and on every leg entry.
- An order whose `p80` date pushes total elapsed time past 14 days from order creation raises an SLA flag.

## 8. Proposed additions

Beyond the brief. Ranked by value against effort.

1. **Consolidation planner.** Show total weight of unassigned boxes against the 10 kg minimum, with the cost per kg at current weight versus at 10 kg. This makes the hold-or-ship decision explicit instead of a gut call, and it is the single feature most tied to margin right now.
2. **Message trigger queue.** When a consignment hits Delhi, generate the "reached Delhi warehouse" message for every order inside it, queued for one-click send through the existing template engine. Box-level events become batch customer communication.
3. **Landed cost per order.** Allocate freight cost across the box by weight or by unit, and write the per-order landed cost back. Feeds the existing unit economics work without a separate sheet.
4. **Aging board.** Orders grouped by days since placement, with the 14-day promise line drawn. Anything approaching it is visible before the customer notices.
5. **Orphan detection.** Orders with no box after N days, and boxes with no consignment after N days. Both are silent failures today.
6. **Lane performance.** Actual versus predicted by leg over time. Tells you whether Hexalog is slipping, with evidence, before a rate conversation.
7. **RTO linkage.** Carry the RTO status column through, and surface RTO rate by consignment and by manufacturer dispatch batch.

## 9. Non-functional

- **Security** — see `SECURITY.md`. Summary: mandatory MFA, short sessions, role checks on every endpoint, full audit trail, encrypted at rest and in transit, no secrets in the repo.
- **Performance** — search under 300 ms at 50,000 orders. Manifest render under 500 ms.
- **Availability** — single instance is acceptable. Nightly automated backup with a monthly restore test.
- **Data retention** — orders retained indefinitely. Audit log retained 24 months minimum.
- **Browser support** — current Chrome and Safari. Desktop first, usable on a phone for read and leg entry.

## 10. Phases

| Phase | Contents | Gate |
|---|---|---|
| 0 | Auth, roles, audit log, empty shell | Login works, roles enforced, every write logged |
| 1 | Data model, Shopify sync, XLSX import | 50 orders hand-verified against the sheet |
| 2 | Box and consignment entry, order assignment, manifest view | Full manifest correct for 10 real boxes |
| 3 | ETA engine, search, timeline | Predictions within 2 days of actual on 10 completed shipments |
| 4 | Consolidation planner, message queue, landed cost | In daily use, sheet retired |

## 11. Success

The tracking sheet stops being updated by hand within 60 days of Phase 4. Time to answer "where is this order" drops from minutes to seconds. Predicted Delhi date is within two days of actual on 80 percent of shipments.
