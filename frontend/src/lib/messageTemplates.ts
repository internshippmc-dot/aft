// Ported from Shopify-Excel-Exporter/message_templates.json — the real,
// currently-used template library (27 templates across the full customer
// lifecycle), not the older prototype's 9 hardcoded strings. That file is
// explicitly marked "Source of truth for all customer message copy... do
// not reword, shorten, or improve any body string" — bodies here are
// copied verbatim.
//
// Variables sourced from Shopify/order data are auto-filled by
// `renderTemplate`. Variables marked manual-only in the source file
// (flight_date, pickup_date, attempt_count, courier_partner, tracking_id)
// are left as literal {{placeholders}} for ops to fill in before sending —
// this app doesn't track those fields yet.

export interface MessageTemplate {
  id: string;
  label: string;
  stage: string;
  agent: "Juhi" | "Keya";
  body: string;
}

const AGENT_NAME: Record<string, "Juhi" | "Keya"> = { juhi: "Juhi", keya: "Keya" };

export const MESSAGE_TEMPLATES: MessageTemplate[] = [
  { id: "order_confirmed", label: "Order Confirmed", stage: "confirmation", agent: "Juhi", body: "Hi {{customer_first_name}}, this is {{agent_name}} from Actually Fair 🤍\n\nOrder No: #{{order_number}}\n\nThank you so much for ordering the {{product_name}} in {{color}}, size {{size}}. Your total payable amount is ₹{{total_amount}}.\n\nPlease reply with a 👍 to confirm your order, or let me know if there are any changes required in the color or sizing.\n\nWe'll ship it out after the confirmation and your order will be delivered to you within {{delivery_weeks}} weeks!\n\nPlease expect a confirmation call for the same.\n\nI'm here in case you need any help :)" },
  { id: "order_confirmation_ack", label: "Acknowledge Confirmation", stage: "confirmation", agent: "Juhi", body: "Thank you for confirming 🤍\n\nWe have confirmed your order from our end and will now start processing it. We'll keep you updated as your order moves ahead.\n\nThank you for shopping with Actually Fair :)" },
  { id: "factory_dispatched", label: "Left Factory (payment to Kathy done, box image received)", stage: "logistics", agent: "Juhi", body: "Hi {{customer_first_name}}, this is {{agent_name}} from Actually Fair 🤍\n\nOrder No: #{{order_number}}\n\nQuick update, your order has been prepared by our overseas manufacturer and has now left the factory.\n\nIt is on its way to the next processing step, and we'll keep you updated as it moves ahead.\n\nThank you for your patience :)" },
  { id: "warehouse_china", label: "Reached China Warehouse (Hexalog)", stage: "logistics", agent: "Juhi", body: "Hi {{customer_first_name}}, hope you are doing well.\n\nOrder No: #{{order_number}}\n\nQuick update, your order has reached our China warehouse from the manufacturer's factory and is currently being planned for the flight on {{flight_date}}.\n\nOnce it flies out, we'll share the next update with you.\n\nThank you for your patience :)" },
  { id: "flight_departed", label: "Flown from China", stage: "logistics", agent: "Juhi", body: "Hi {{customer_first_name}},\n\nOrder No: #{{order_number}}\n\nGood news, your order has now flown from China and is on its way to India.\n\nJust a few more days until it reaches you. We're so excited for you to receive it :)\n\nWe'll share the next update once it reaches our India warehouse." },
  { id: "warehouse_delhi", label: "Reached Delhi Warehouse", stage: "logistics", agent: "Juhi", body: "Hi {{customer_first_name}},\n\nOrder No: #{{order_number}}\n\nA little order update, it has reached our Delhi warehouse and will be dispatched shortly.\n\nIt should reach you very soon now. Can't wait for it to reach you :)\n\nWe'll share the tracking link as soon as it is dispatched." },
  { id: "in_transit", label: "In Transit + Tracking Link", stage: "logistics", agent: "Keya", body: "Hi {{customer_first_name}},\n\nOrder No: #{{order_number}}\n\nExciting news, your order is now in transit and on its way to you.\n\nIt should reach you soon. Let me know if you need any help :)\n\nTracking: {{tracking_id}} ({{courier_partner}})" },
  { id: "delivered", label: "Delivered", stage: "logistics", agent: "Keya", body: "Hi {{customer_first_name}},\n\nOrder No: #{{order_number}}\n\nYour order has been delivered.\n\nWe hope you love your product and enjoy something made fair :)\n\nThank you for shopping with Actually Fair 🤍" },
  { id: "feedback_request", label: "Feedback Request", stage: "post_delivery", agent: "Keya", body: "Hi {{customer_first_name}},\n\n{{agent_name}} here, from actuallyfair\n\nI hope you're enjoying the product we shipped out to you last week!\n\nAs a young company, we take feedback very seriously and genuinely use it to improve your experience. Whenever you get a minute, please do share your feedback on the product with us.\n\nIt would really help us make the shopping experience better for you and our future customers.\n\nThank you so much :)" },
  { id: "address_confirm", label: "Confirm Correct Address", stage: "address", agent: "Keya", body: "Hi {{customer_first_name}}, this is {{agent_name}} from Actually Fair 🤍\n\nJust confirming if this is your correct full delivery address:\n\n{{full_address}}\n\nPlease reply with a 👍 if it's correct, or send the updated address if anything needs to be changed.\n\nThank you :)" },
  { id: "address_incomplete", label: "Request Complete Address", stage: "address", agent: "Keya", body: "Hi {{customer_first_name}}, this is {{agent_name}} from Actually Fair 🤍\n\nThank you for sharing your address. It seems a little incomplete from our end.\n\nCould you please share your full delivery address with the house/flat number, building name, street/locality, city, state, and pincode?\n\nThis will help us make sure your order reaches you without any issue :)\n\nThank you!" },
  { id: "return_request_received", label: "Return Requested - Ask Reason", stage: "returns", agent: "Keya", body: "Hey {{customer_first_name}}, {{agent_name}} here,\n\nI'm really sorry to hear that you're looking to return your order, but happy to help you with this.\n\nCould you please share the reason for the return request?\n\nOnce we have the details, we'll check it from our end and guide you with the next steps :)" },
  { id: "return_initiated", label: "Return Will Be Initiated", stage: "returns", agent: "Keya", body: "Thank you for sharing the details. I understood your return requirements and communicated with the team. We will initiate the return process from our end.\n\nThe return should be completed within 2 to 3 days from today. Please keep the product packed and ready for pickup.\n\nOnce the return pickup is completed and the product reaches our facility, we'll be able to make the refund from our end. Will keep you posted!!\n\nThank you for your patience :)" },
  { id: "return_details", label: "Return Pickup Details", stage: "returns", agent: "Keya", body: "Hey {{customer_first_name}}, {{agent_name}} here from Actually Fair 🤍\n\nWe have initiated your return request. Please find the return details below:\n\nOrder No: #{{order_number}}\nReturn Pickup Date: {{pickup_date}}\nPickup Partner: {{courier_partner}}\nReturn Tracking ID: {{tracking_id}}\n\nPlease keep the product packed and ready for pickup." },
  { id: "sizing_issue", label: "Sizing Issue - Ask Detail", stage: "returns", agent: "Keya", body: "hey {{customer_first_name}}, {{agent_name_lower}} here\n\nI'm really sorry to hear that the fit wasn't quite right. Happy to help you with this.\n\nCould you please elaborate a little on the sizing issue you're facing? This will help us understand it better and guide you with the right next steps.\n\nThank you :)" },
  { id: "partial_dispatch", label: "Partial Dispatch", stage: "logistics", agent: "Keya", body: "Hi {{customer_first_name}}, this is {{agent_name}}\n\nOrder No: #{{order_number}}\n\nYour order is being shipped in parts as a few items have reached us earlier.\n\nIn this delivery, we are sending you:\n{{items_list}}\n\nThe remaining items from your order are still on the way to us. As soon as we receive them, we'll dispatch them to you at the earliest.\n\nThank you for your patience :)" },
  { id: "refund_pending", label: "Refund - Pending Pickup", stage: "refunds", agent: "Keya", body: "Hey {{customer_first_name}}, {{agent_name}} here from Actually Fair 🤍\n\nOnce the return pickup is completed and the product reaches our facility, we'll be able to initiate the refund from our end.\n\nI hope you understand, and we'll keep you updated once we receive the return, should be about 3-4 days.\n\nThank you for your patience :)" },
  { id: "refund_upi_request", label: "Refund - Ask for UPI", stage: "refunds", agent: "Keya", body: "Hey {{customer_first_name}},\n\nCould you please kindly share your UPI details so we can process the refund from our end?\n\nThank you :)" },
  { id: "delivery_attempts", label: "Failed Delivery Attempts", stage: "delivery_exceptions", agent: "Keya", body: "Hey {{customer_first_name}},\n\n{{agent_name}} here from Actually Fair 🤍\n\nThe delivery partner has been trying to reach you for a while to deliver your order. They have already made {{attempt_count}} delivery attempts.\n\nCould you please let us know if there's any issue, or if you'd like the delivery to be done at a different time or location as per your convenience?\n\nLooking forward to your response :)\n\nTracking: {{tracking_id}}" },
  { id: "rto_received", label: "RTO Received", stage: "delivery_exceptions", agent: "Keya", body: "Hey {{customer_first_name}},\n\n{{agent_name}} here from Actually Fair 🤍\n\nHope you're doing well.\n\nWe noticed that your order has been marked as RTO, which means it is being returned to us after unsuccessful delivery attempts. The delivery partner had been trying to reach you for a while to deliver the order.\n\nCould you please let us know if there was any issue, or if you would like the delivery to be arranged again at a different time or location as per your convenience?\n\nLooking forward to your response :)" },
  { id: "reorder_offer", label: "Unfulfilled Earlier - Offer to Resend", stage: "recovery", agent: "Keya", body: "Hey {{customer_first_name}},\n\n{{agent_name}} here from Actually Fair, hope you're doing well.\n\nYou had placed an order for {{product_name}} from our website earlier, but since we were just starting out, we faced some logistics issues and unfortunately weren't able to fulfil the order at that time.\n\nWe're really sorry for the inconvenience caused. We're now able to fulfil this requirement and would be happy to send it to you if you're still interested in the product. Please let us know if you'd like us to process it again.\n\nLooking forward to your response, and thank you for understanding :)" },
  { id: "reorder_confirm", label: "Reorder - Confirm Details", stage: "recovery", agent: "Keya", body: "Great, thank you for confirming 🤍\n\nJust confirming your order details before we process it again:\n\nProduct: {{product_name}}\nColour: {{color}}\nSize: {{size}}\nQuantity: {{quantity}}\nTotal Amount: ₹{{total_amount}}\nDelivery Address: {{full_address}}\n\nPlease reply with a 👍 if everything looks correct, or let us know if anything needs to be changed.\n\nOnce confirmed, we'll start processing your order :)" },
  { id: "size_chart_hold", label: "Size Chart Asked - Holding Reply", stage: "enquiry", agent: "Keya", body: "Hey {{customer_first_name}}, {{agent_name}} here from Actually Fair 🤍\n\nSure, please give me a few minutes. I'll check and get back to you with the accurate size chart for this product.\n\nThank you :)" },
  { id: "general_query_hold", label: "Other Details Asked - Holding Reply", stage: "enquiry", agent: "Keya", body: "Hey {{customer_first_name}}, {{agent_name}} here\n\nSure, please give me a few minutes. I'll check the details with the team and get back to you asap.\n\nThank you :)" },
  { id: "website_link", label: "Share Website Link", stage: "enquiry", agent: "Keya", body: "Hey {{customer_first_name}}, {{agent_name}} here from Actually Fair 🤍\n\nSure, you can check out our website here: {{website_url}}\n\nLet me know if you need any help finding a product or placing an order :)" },
  { id: "out_of_stock_swap", label: "Out of Stock - Offer Alternative", stage: "enquiry", agent: "Keya", body: "Hey {{customer_first_name}}, {{agent_name}} here from Actually Fair 🤍\n\nWe're really sorry, but the product you ordered has gone out of stock and we won't be able to deliver it at the moment.\n\nIt would take a few more weeks for the product to be restocked. Since we don't want to keep you waiting, would you like to choose something from our available stock instead?\n\nWe can share the available options with you, and if you like anything, we'll process that for you right away.\n\nThank you for understanding :)" },
  { id: "return_policy", label: "Return Policy Explained", stage: "enquiry", agent: "Keya", body: "Hey {{customer_first_name}}, {{agent_name}} here from Actually Fair 🤍\n\nWe have a 30-day free return/exchange policy because we genuinely want you to feel confident about what you buy from us.\n\nIf you're not happy with the product or need a sizing exchange, you can raise a request out to me and we'll help you with the process. Once the product is picked up and reaches our facility, we'll inspect it and initiate the refund from our end.\n\nLet me know if you'd like me to help you start a return request :)" },
  { id: "missing_item", label: "Item Missing from Package", stage: "issues", agent: "Keya", body: "Hey {{customer_first_name}}, {{agent_name}} here from Actually Fair 🤍\n\nI'm really sorry to hear that.\n\nWe checked your order and you had ordered the following items:\n\n{{items_list}}\n\nCould you please confirm which item is missing from your package?\n\nOnce you confirm, we'll check this from our end and help resolve it as soon as possible.\n\nThank you for your patience :)" },
];

const WEBSITE_URL = "https://actuallyfair.in/";
const DELIVERY_WEEKS = "2";

export interface OrderContext {
  customerName?: string | null;
  orderNumber: string;
  productName?: string;
  colour?: string;
  size?: string;
  quantity?: number;
  totalInr?: string | null;
  address?: string;
  itemsList?: string;
}

export function renderTemplate(template: MessageTemplate, ctx: OrderContext): string {
  const firstName = (ctx.customerName || "").trim().split(/\s+/)[0] || "there";
  const vars: Record<string, string> = {
    customer_first_name: firstName,
    agent_name: template.agent,
    agent_name_lower: template.agent.toLowerCase(),
    order_number: ctx.orderNumber.replace(/^#/, ""),
    product_name: ctx.productName || "{{product_name}}",
    color: ctx.colour || "{{color}}",
    size: ctx.size || "{{size}}",
    quantity: ctx.quantity ? String(ctx.quantity) : "{{quantity}}",
    total_amount: ctx.totalInr ? Number(ctx.totalInr).toLocaleString("en-IN") : "{{total_amount}}",
    delivery_weeks: DELIVERY_WEEKS,
    full_address: ctx.address || "{{full_address}}",
    items_list: ctx.itemsList || "{{items_list}}",
    website_url: WEBSITE_URL,
    // Not tracked by this app yet — left as literal placeholders for ops to fill in.
    flight_date: "{{flight_date}}",
    pickup_date: "{{pickup_date}}",
    attempt_count: "3",
    tracking_id: "{{tracking_id}}",
    courier_partner: "{{courier_partner}}",
  };
  return template.body.replace(/\{\{(\w+)\}\}/g, (match, key) => vars[key] ?? match);
}
