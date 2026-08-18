export type Role = "owner" | "ops" | "viewer";

export interface Me {
  id: number;
  email: string;
  full_name: string;
  role: Role;
}

export interface Eta {
  p50_date: string;
  p80_date: string;
  sample_n: number;
  confidence: "high" | "low";
}

export interface OrderItem {
  id: number;
  product_title: string;
  colour: string | null;
  size: string | null;
  quantity: number;
}

export interface Legs {
  MFG_DISPATCH: string | null;
  CN_WAREHOUSE: string | null;
  FLIGHT: string | null;
  DELHI_WAREHOUSE: string | null;
}

export interface BoxSummary {
  aft_number: string;
  tracking_id: string | null;
  manufacturer: string | null;
  gross_weight_kg: string | null;
  order_count: number;
  stage: string;
  legs: Legs;
  eta: Eta | null;
  sla_risk: boolean;
  created_at: string;
}

export interface ManifestOrder {
  order_number: string;
  customer_name: string | null;
  city: string | null;
  placed_at: string;
  total_inr: string | null;
  items: OrderItem[];
}

export interface BoxManifest {
  aft_number: string;
  tracking_id: string | null;
  manufacturer: string | null;
  gross_weight_kg: string | null;
  notes: string | null;
  stage: string;
  legs: Legs;
  eta: Eta | null;
  sla_risk: boolean;
  order_count: number;
  units_total: number;
  value_total: string;
  oldest_order_placed_at: string | null;
  orders: ManifestOrder[];
  attach: AttachResult | null;
}

export interface AttachFailure {
  order_number: string;
  reason: string;
}

export interface AttachResult {
  attached: string[];
  already_in_this_box: string[];
  missing: string[];
  failed: AttachFailure[];
}

export interface OrderItemCreate {
  product_title: string;
  colour?: string | null;
  size?: string | null;
  quantity: number;
  unit_price_inr?: string | null;
}

export interface OrderCreateIn {
  order_number: string;
  customer_name: string;
  phone?: string | null;
  city?: string | null;
  items: OrderItemCreate[];
}

export interface LegTimelineEntry {
  leg: string;
  label: string;
  date: string | null;
  actual: boolean;
}

export interface OrderDetail {
  order_number: string;
  customer_name: string | null;
  phone: string | null;
  email: string | null;
  city: string | null;
  total_inr: string | null;
  placed_at: string;
  elapsed_days: number;
  items: OrderItem[];
  box_aft_number: string | null;
  consignment_tracking_id: string | null;
  stage: string;
  timeline: LegTimelineEntry[];
  eta: Eta | null;
  sla_risk: boolean;
}

export interface ConsignmentOut {
  id: number;
  tracking_id: string;
  carrier: string;
  chargeable_weight_kg: string | null;
  freight_cost_inr: string | null;
  notes: string | null;
  shortfall_kg: string;
  created_at: string;
  boxes: BoxSummary[];
}

export interface SearchOrderHit {
  order_number: string;
  customer_name: string | null;
  aft_number: string | null;
}

export interface SearchBoxHit {
  aft_number: string;
  tracking_id: string | null;
  order_count: number;
  stage: string;
}

export interface SearchResults {
  orders: SearchOrderHit[];
  boxes: SearchBoxHit[];
}

export interface Consolidation {
  unassigned_weight_kg: string;
  unassigned_box_count: number;
  minimum_kg: string;
  gauge_pct: number;
  shortfall_kg: string;
}
