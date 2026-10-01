# Smart Merchant Assistant

## POS Transaction Flow & Business Rules v1

Status: **DECIDED — Foundation v1**
Scope: POS Transaction Lifecycle
Primary Goal: Fast, reliable, auditable sales flow
Initial Vertical: Restaurants & Cafés

Source: owner-supplied requirements, received 2026-10-01. This is a structured transcription with normalized layout and compact prose; it is not a byte-for-byte archive of the chat. Original rule numbers are retained as POS-001 through POS-150 for traceability. Recommendations, examples, configurable values and future features retain their original status; examples do not become production defaults. DECIDED describes the requirement baseline, not implementation or acceptance.

Related: [delivery and decision plan](POS_DELIVERY_PLAN_V1.md), [acceptance matrix](POS_ACCEPTANCE_V1.md).

### 1. Core POS Principle

Rule ID: POS-001

The POS must optimize for FAST, RELIABLE, SIMPLE. The cashier should never be exposed to backend complexity. The transaction system behind the cashier must be AUDITABLE, IDEMPOTENT, OFFLINE-CAPABLE, FINANCIALLY SAFE.

### 2. Primary POS Lifecycle

Rule ID: POS-002

Employee Login → Terminal Validation → Shift Open → Create Order → Add Products → Apply Modifiers → Apply Discounts → Calculate Tax → Confirm Order → Accept Payment → Complete Sale → Print Receipt → Create Inventory Consumption → Calculate Profit Snapshot → Emit SaleCompleted → Sync / Analytics / Alerts.

### 3. Employee Login

Rule ID: POS-003

Cashier authenticates using PIN, Password, or Employee Code. Future: NFC / biometric device. MVP recommendation: Employee PIN for fast cashier switching.

### 4. Login Rules

Rule ID: POS-004

A POS employee must satisfy: User active AND Membership active AND Branch access granted AND Role allows POS login AND Terminal active. Otherwise login is rejected.

### 5. Terminal Validation

Rule ID: POS-005

Every transaction must be tied to organization_id, branch_id, terminal_id, user_id. The POS cannot change these identities arbitrarily. They are validated by the backend.

### 6. Shift Requirement

Rule ID: POS-006

Normally a cashier cannot create paid orders without an open shift. Flow: Cashier Login → Check Open Shift → No Shift → Open Shift.

### 7. Open Shift

Rule ID: POS-007

The cashier enters opening_cash if cash handling is enabled. Example: Opening Cash: 500 SAR. System creates Shift + CashMovement = OPENING_BALANCE.

### 8. Shift State

Rule ID: POS-008

Possible states: OPEN, CLOSING, CLOSED, CANCELLED. Only one active shift per terminal is recommended initially.

### 9. Order Creation

Rule ID: POS-009

When cashier starts a transaction: OrderCreated. Order state: DRAFT. It receives order_id, client_transaction_id, order_number, terminal_id, business_date.

### 10. Local Order Creation

Rule ID: POS-010

The POS should create the order locally first. This makes the UI instant. Local flow: Tap Product → Update Local Order → Render Immediately. Backend communication must not block every tap.

### 11. Product Selection

Rule ID: POS-011

Cashier can add Product, Variant, Quantity, Modifiers, Notes. Example: Spanish Latte, Large, Cold, Oat Milk, Extra Shot.

### 12. Price Resolution

Rule ID: POS-012

The POS resolves price using this order: Branch-specific price → Active organization/brand price → Default product price. Only active prices valid for the transaction time may be used.

### 13. Price Snapshot

Rule ID: POS-013

Once the item is confirmed into the order, the system stores unit_price_snapshot. This protects the transaction if prices change later.

### 14. Product Availability

Rule ID: POS-014

Before adding a product: Product active? Branch enabled? Variant active? Current price available? If any required condition fails: Product cannot be sold.

### 15. Inventory Availability

Rule ID: POS-015

Two possible product modes: STRICT and WARNING_ONLY. STRICT: Do not allow the sale if the required inventory is unavailable. WARNING_ONLY: Allow the sale but warn: Low or insufficient stock. For restaurants, initial recommendation: WARNING_ONLY because physical reality and system stock may temporarily differ.

### 16. Modifier Rules

Rule ID: POS-016

Modifier groups support Required / Optional, Single Select, Multi Select, Minimum Selection, Maximum Selection. Example: Milk Type, Required, Min: 1, Max: 1.

### 17. Modifier Price

Rule ID: POS-017

Modifier pricing is added to the base product price. Example: Latte 18 + Oat Milk 2 + Extra Shot 3 = Total 23 SAR. Modifier price is snapshotted.

### 18. Order Item Notes

Rule ID: POS-018

Cashier may add No ice, No sugar, Extra hot, No onions. These notes do not automatically affect recipe quantity unless they correspond to structured modifiers.

### 19. Quantity Update

Rule ID: POS-019

Changing item quantity recalculates subtotal, discount, tax, total, expected recipe consumption before payment.

### 20. Order Type

Rule ID: POS-020

Every order must have an explicit type: DINE_IN, TAKEAWAY, PICKUP, DELIVERY. Default may be configured per branch.

### 21. Dine-In Future Structure

Rule ID: POS-021

For restaurants with tables: Area, Table, Guest Count should be separate entities. Not mandatory for MVP unless needed by target pilot merchants.

### 22. Order Calculation Engine

Rule ID: POS-022

All money calculations must come from one shared calculation engine. Never duplicate pricing logic between POS App, Backend, Owner App, Web Dashboard. The backend is authoritative.

### 23. Calculation Order

Rule ID: POS-023

Recommended order: Base Item Price + Paid Modifiers = Gross Item Amount → Discounts → Discounted Amount → Tax Calculation → Final Item Amount. Exact tax handling must follow the configured tax model.

### 24. Money Precision

Rule ID: POS-024

All calculations use decimal arithmetic. Never float for money.

### 25. Rounding

Rule ID: POS-025

A single centralized rounding policy must be used. Example concept: Currency precision = 2 decimal places. Rounding behavior must be consistent across POS, API, Receipts, Reports, Accounting.

### 26. Discount Types

Rule ID: POS-026

Supported initially: ITEM_PERCENTAGE, ITEM_FIXED, ORDER_PERCENTAGE, ORDER_FIXED.

### 27. Discount Permissions

Rule ID: POS-027

Possible permission levels: Cashier up to X%; Manager up to Y%; Owner unrestricted. Example: Cashier max discount = 10%. Anything higher requires approval.

### 28. Discount Approval

Rule ID: POS-028

Cashier applies 20% → Permission exceeds limit → Manager approval required → Manager PIN → approved_by stored. This must be audited.

### 29. Manual Price Override

Rule ID: POS-029

Default: DISABLED. If enabled: Permission required, Reason required, Audit log required.

### 30. Free Item

Rule ID: POS-030

A 100% discount must be treated explicitly. Reason examples: COMP, MANAGER_GIFT, CUSTOMER_RECOVERY, PROMOTION. Never silently set product price to zero.

### 31. Order Confirmation

Rule ID: POS-031

Before payment: DRAFT → CONFIRMED. The confirmation step freezes the commercial structure of the order unless intentionally reopened.

### 32. Confirmed Order Validation

Rule ID: POS-032

Check Product validity, Price validity, Modifier requirements, Discount permissions, Tax calculation, Order total, Shift status.

### 33. Payment Start

Rule ID: POS-033

Payment begins only after a valid payable order exists. Flow: Order Confirmed → Create Payment Attempt → Choose Method.

### 34. Payment Methods

Rule ID: POS-034

Initial methods: CASH, CARD, MADA, VISA, MASTERCARD, APPLE_PAY, OTHER. POS UI may group card methods as CARD while backend stores provider metadata when available.

### 35. Cash Payment

Rule ID: POS-035

Amount Due → Cash Received → Calculate Change → Capture Payment. Example: Due 47 SAR; Received 50 SAR; Change 3 SAR.

### 36. Cash Validation

Rule ID: POS-036

Cash received cannot be lower than amount due unless split payment is active.

### 37. Card Payment

Rule ID: POS-037

Create Payment Intent → Send to Payment Adapter → Await Result → CAPTURED or FAILED. The POS must never mark card payment as successful based only on UI state.

### 38. Payment Failure

Rule ID: POS-038

If card payment fails: Order remains CONFIRMED; Payment = FAILED. Cashier can retry or select another method.

### 39. Payment Timeout

Rule ID: POS-039

If payment provider status is unknown: UNKNOWN / PENDING. Do not immediately retry blindly. First reconcile with the payment provider where supported. This reduces double charging.

### 40. Split Payment

Rule ID: POS-040

System architecture should support split payment. Example: Total 100 SAR; Cash 40; Card 60. MVP may hide this if not required initially, but the payment model must support multiple payments per order.

### 41. Payment Invariant

Rule ID: POS-041

For successful completion: Captured Payments = Amount Due unless an explicitly supported payment flow allows another state.

### 42. Overpayment

Rule ID: POS-042

Cash may exceed the amount due because change is returned. Card payment must generally not exceed payable amount.

### 43. Successful Payment

Rule ID: POS-043

When payment succeeds: Payment = CAPTURED. Then transaction completion begins.

### 44. Complete Sale

Rule ID: POS-044

Atomic business action: CompleteSale. Backend validates Order confirmed, Payment complete, No duplicate completion, Valid shift, Valid tenant.

### 45. Sale Completion State

Rule ID: POS-045

Order becomes COMPLETED and receives completed_at.

### 46. Financial Snapshot

Rule ID: POS-046

At completion store selling_price_snapshot, discount_snapshot, tax_snapshot, cost_snapshot, gross_profit_snapshot, recipe_version_snapshot. This data is immutable.

### 47. Cost Resolution

Rule ID: POS-047

Cost Engine determines the cost using Recipe + Current authoritative ingredient costing method + Packaging + Configured direct variable costs. The calculated result is snapshotted into the completed order item.

### 48. Inventory Consumption

Rule ID: POS-048

After successful sale completion: SaleCompleted → Recipe Engine → Inventory Movement. Example: SALE_CONSUMPTION; Chicken -150g; Bread -1; Sauce -30g.

### 49. Inventory Timing

Rule ID: POS-049

Inventory consumption should happen from the authoritative completed sale event. Not merely when an item is added to the cart.

### 50. Reserved Inventory

Rule ID: POS-050

MVP: No reservation for ordinary counter orders. Future: Reservations may be useful for Delivery, Pre-orders, Long-running table orders.

### 51. Event Emission

Rule ID: POS-051

Completed transaction emits SaleCompleted. Payload references IDs rather than duplicating unnecessary full records.

### 52. SaleCompleted Consumers

Rule ID: POS-052

Consumers include Inventory, Profit Engine, Analytics, Accounting, Alerts, Owner Live Feed, Notifications.

### 53. Transactional Outbox

Rule ID: POS-053

Order completion and event creation must occur in the same database transaction. Example: BEGIN → Complete Order → Capture authoritative state → Insert Outbox Event → COMMIT. Worker processes downstream actions.

### 54. Receipt Generation

Rule ID: POS-054

Receipt is generated from completed transaction data. Receipt should never query current product price. It uses transaction snapshots.

### 55. Receipt Information

Rule ID: POS-055

Typical fields: Merchant Name, Branch, Tax Information, Order Number, Date / Time, Cashier, Items, Modifiers, Discounts, Tax, Total, Payment Method, Receipt QR / Fiscal Data. Exact fiscal fields depend on applicable compliance requirements.

### 56. Receipt Printing Failure

Rule ID: POS-056

If the sale completes but printer fails: DO NOT rollback sale. Instead: Payment complete; Sale complete; Receipt print failed. Allow Reprint Receipt.

### 57. Receipt Reprint

Rule ID: POS-057

Every reprint should optionally record who, when, terminal, reason, especially where merchants need auditability.

### 58. Kitchen Printing

Rule ID: POS-058

For restaurants: Order Confirmed → Kitchen Routing. Possible destinations: Hot Kitchen, Cold Bar, Coffee Bar, Dessert Station. Kitchen routing should remain separate from fiscal receipt printing.

### 59. Kitchen Display Future

Rule ID: POS-059

Architecture should later support KDS (Kitchen Display System) using the same order events.

### 60. Offline Transaction Mode

Rule ID: POS-060

When internet is unavailable: POS switches to OFFLINE. Core sales should continue where safe.

### 61. Offline Order Flow

Rule ID: POS-061

Create Local Order → Confirm Locally → Accept Allowed Payment → Complete Local Transaction → Print Local Receipt → Add Event to Sync Queue.

### 62. Offline Allowed Payments

Rule ID: POS-062

Safe default: CASH. Other offline payment methods depend on payment-terminal capability. Do not assume card payments can operate offline.

### 63. Offline Transaction Identity

Rule ID: POS-063

Every transaction has client_transaction_id, terminal_id, sequence_number. Example: terminal_id T-ABHA-01; sequence 18421.

### 64. Sequence Rule

Rule ID: POS-064

Each terminal maintains a monotonically increasing local sequence. This improves deduplication, ordering, audit, sync diagnostics.

### 65. Offline Sync Queue

Rule ID: POS-065

Local event states: PENDING, SYNCING, SYNCED, FAILED. Failed events remain available for retry. Never delete failed transaction data automatically.

### 66. Sync Processing

Rule ID: POS-066

When internet returns: POS connects → Send oldest pending event → Server validates → Server checks idempotency → Accept / Reject → Return canonical server ID → Mark local event SYNCED.

### 67. Sync Ordering

Rule ID: POS-067

Transactions from one terminal should normally sync by sequence_number ASC.

### 68. Duplicate Sync

Rule ID: POS-068

If the POS sends the same transaction twice: Server detects same transaction identity → Returns original result. It must not create another sale.

### 69. Sync Conflict — Price Changed

Rule ID: POS-069

Example: POS went offline at Latte = 18 SAR. Server later changes Latte = 20 SAR. Offline transaction completed at 18. Rule: Preserve valid transaction snapshot. Do not silently rewrite customer's historical sale. Conflict should be logged.

### 70. Sync Conflict — Product Disabled

Rule ID: POS-070

If product was disabled while POS was offline: A locally completed legitimate transaction remains a transaction. Rule: Import transaction + Flag configuration mismatch. Do not erase the sale.

### 71. Sync Conflict — Inventory

Rule ID: POS-071

If offline sale causes calculated stock to go negative: Import valid sale → Inventory may become negative → Generate stock discrepancy alert. Never destroy financial reality to make inventory look clean.

### 72. Negative Stock

Rule ID: POS-072

Negative stock should be allowed at ledger level when required to represent reality. But it should generate Alert and require reconciliation.

### 73. Cancel Before Payment

Rule ID: POS-073

A draft or confirmed unpaid order may be cancelled. Flow: Order → CANCELLED. Store cancelled_at, cancelled_by, reason.

### 74. Cancellation Permission

Rule ID: POS-074

Possible rule: Draft: Cashier allowed. Confirmed: Manager permission. Paid: Cannot cancel; Use refund.

### 75. Paid Order Cancellation

Rule ID: POS-075

Never delete or simply cancel a captured transaction. Use REFUND or VOID depending on payment state and provider capabilities.

### 76. Payment Void

Rule ID: POS-076

A payment may be voided only where provider supports void AND payment has not been fully settled. Provider-specific details stay behind Payment Adapter.

### 77. Refund Flow

Rule ID: POS-077

Find Original Sale → Select Items / Amount → Enter Reason → Permission Check → Create Refund → Process Payment Reversal → Update Order Refund State → Inventory Return Decision → Accounting / Analytics Update.

### 78. Refund Types

Rule ID: POS-078

Support architecture for FULL REFUND, PARTIAL REFUND, ITEM REFUND.

### 79. Refund Invariant

Rule ID: POS-079

Total Refunded <= Total Captured. Always.

### 80. Refund Inventory Rule

Rule ID: POS-080

Refund does not automatically mean stock should return. Example: Returned sealed product: RETURN_IN. Consumed restaurant meal: NO INVENTORY RETURN. Cashier/manager chooses according to allowed workflow.

### 81. Refund Reason Codes

Rule ID: POS-081

Examples: CUSTOMER_REQUEST, WRONG_ORDER, QUALITY_ISSUE, DUPLICATE_PAYMENT, CASHIER_ERROR, MANAGER_OVERRIDE, OTHER.

### 82. Refund Approval

Rule ID: POS-082

Branch may configure: Cashier: No refunds; Manager: Up to X SAR; Owner: Unlimited.

### 83. Refund Audit

Rule ID: POS-083

Always record original_order, original_payment, refund_amount, reason, requested_by, approved_by, terminal, timestamp.

### 84. Partial Refund State

Rule ID: POS-084

After partial refund: Order = PARTIALLY_REFUNDED. After full refund: Order = REFUNDED.

### 85. Inventory Return from Refund

Rule ID: POS-085

If inventory should be restored: RETURN_IN must reference the refund.

### 86. Complimentary Replacement

Rule ID: POS-086

If a customer receives a replacement item: Do not erase the original transaction. Use a clear workflow such as replacement order or 100% approved discount order with reason.

### 87. Suspended Orders

Rule ID: POS-087

Cashier may HOLD an unpaid order. Examples: Customer forgot wallet; Needs additional item later; Table order temporarily parked.

### 88. Resume Held Order

Rule ID: POS-088

Held order can be resumed from the same branch subject to permissions.

### 89. Held Order Expiry

Rule ID: POS-089

Branch can configure cleanup policy. Expired held orders should be CANCELLED with explicit system reason. Never delete silently.

### 90. Cash Movement

Rule ID: POS-090

Cash drawer supports CASH_IN and CASH_OUT. Examples: Petty cash added; Supplier cash payment; Cash pickup. Reason is required.

### 91. Cash Drawer Open

Rule ID: POS-091

Manual drawer opening without sale should generate CASH_DRAWER_OPENED audit event if hardware supports detection.

### 92. Shift Close

Rule ID: POS-092

Cashier selects Close Shift → Stop / finalize pending cash workflow → Count actual cash → System calculates expected cash → Compare → Record difference → Close Shift.

### 93. Expected Cash

Rule ID: POS-093

Conceptually: Opening Cash + Cash Sales + Cash In - Cash Refunds - Cash Out = Expected Closing Cash.

### 94. Cash Difference

Rule ID: POS-094

Actual Cash - Expected Cash = Cash Difference. Example: Expected 2,850; Actual 2,820; Difference -30 SAR.

### 95. Shift Difference Rules

Rule ID: POS-095

Branch may configure Tolerance = 5 SAR. If difference exceeds tolerance: Manager review required.

### 96. Open Orders at Shift Close

Rule ID: POS-096

Recommended rule: Do not allow shift close while unresolved paid/active cashier transactions exist. Held orders may be handled according to branch policy.

### 97. Business Date

Rule ID: POS-097

Transaction stores created_at and business_date. Example: Created 2026-09-12 01:15; Business Date 2026-09-11 according to branch cutoff.

### 98. Business Day Cutoff

Rule ID: POS-098

Branch setting: business_day_cutoff. Example: 04:00. Transactions before 04:00 may belong to the previous operational day.

### 99. Owner Live Update

Rule ID: POS-099

After server confirms sale: SaleCompleted → Real-Time Event → Owner Dashboard. Owner may see +47 SAR, Branch Abha, without needing to refresh.

### 100. Analytics Update

Rule ID: POS-100

Sale contributes to Gross Sales, Net Sales, Order Count, Average Order Value, Product Sales, Category Sales, Branch Sales, Profit, Margin.

### 101. Profit Update

Rule ID: POS-101

Profit Engine uses transaction snapshots: Net Revenue - Cost Snapshot = Gross Profit. Never recalculate historical sale profit using today's ingredient cost.

### 102. Alert Evaluation

Rule ID: POS-102

After completion, rules may evaluate Low Stock, Negative Stock, Unusual Discount, Unusual Refund, High Sales, Margin Drop, Cash Variance.

### 103. AI Interaction

Rule ID: POS-103

AI should not participate in completing a normal sale. POS sale path remains deterministic. AI may later help with Explain anomaly, Recommend action, Summarize shift, but cannot be a dependency for checkout.

### 104. POS Failure Rule

Rule ID: POS-104

A failure in AI, Analytics, Forecasting, Notification must NOT block a valid sale.

### 105. Critical Dependencies

Rule ID: POS-105

A sale depends only on the essential transaction path: POS → Order → Payment → Sale Completion. Secondary processing is asynchronous where possible.

### 106. Atomicity

Rule ID: POS-106

Critical server transaction should ensure no invalid half-state such as Order completed but authoritative payment missing, or Refund completed but refund amount not recorded.

### 107. Retry Rule

Rule ID: POS-107

Safe operations may retry automatically. Unsafe operations require idempotency. Especially Payment, Sale Completion, Refund, Offline Import.

### 108. API Command Style

Rule ID: POS-108

Important actions should be explicit commands. Examples: POST /orders; POST /orders/{id}/confirm; POST /orders/{id}/payments; POST /orders/{id}/complete; POST /orders/{id}/cancel; POST /orders/{id}/refunds. Avoid generic APIs such as PATCH order.status = COMPLETED.

### 109. State Transition Rule

Rule ID: POS-109

Only backend domain services may perform state transitions. Clients request actions. Clients do not dictate final state.

### 110. Order State Machine

Rule ID: POS-110

DRAFT → CONFIRMED → PAID → COMPLETED → PARTIALLY_REFUNDED / REFUNDED. DRAFT and CONFIRMED may transition to CANCELLED. Implementation may internally combine PAID and completion timing where appropriate, but payment and order state remain conceptually distinct.

### 111. Payment State Machine

Rule ID: POS-111

PENDING → AUTHORIZED → CAPTURED → PARTIALLY_REFUNDED / REFUNDED. PENDING may transition to FAILED or VOIDED.

### 112. Shift State Machine

Rule ID: POS-112

OPEN → CLOSING → CLOSED. Exceptional: CANCELLED only under controlled administrative workflow.

### 113. Offline Sync State Machine

Rule ID: POS-113

PENDING → SYNCING → SYNCED. Failure: SYNCING → FAILED → PENDING after retry.

### 114. POS Permission Matrix

Rule ID: POS-114

Initial concept:

| Action | Cashier | Manager | Owner |
| --- | --- | --- | --- |
| Create Sale | Yes | Yes | Yes |
| Apply Small Discount | Yes | Yes | Yes |
| Large Discount | Approval | Yes | Yes |
| Cancel Draft | Yes | Yes | Yes |
| Cancel Confirmed | Approval | Yes | Yes |
| Refund | No / Limited | Yes | Yes |
| Inventory Adjustment | No | Optional | Yes |
| Close Shift | Yes | Yes | Yes |
| View Profit | No | Optional | Yes |
| Change Price | No | Optional | Yes |

Exact permissions remain configurable.

### 115. Error Handling

Rule ID: POS-115

Errors should be actionable. Bad: Error 500. Good: This payment has already been processed. Or: Your shift is closed. Open a shift before taking payment.

### 116. POS Error Categories

Rule ID: POS-116

VALIDATION, AUTHORIZATION, PAYMENT, NETWORK, SYNC, HARDWARE, SERVER.

### 117. Network Status

Rule ID: POS-117

POS UI should clearly show ONLINE, OFFLINE, SYNCING, SYNC ISSUE without distracting the cashier.

### 118. Sync Issue UX

Rule ID: POS-118

Do not show technical stack traces. Show: 3 transactions waiting to sync. Admin/diagnostic screen may expose deeper details.

### 119. Printer Failure UX

Rule ID: POS-119

Show: Sale completed successfully. Receipt could not be printed. Button: REPRINT.

### 120. Hardware Abstraction

Rule ID: POS-120

Create hardware interfaces for ReceiptPrinter, CashDrawer, BarcodeScanner, PaymentTerminal, CustomerDisplay. This prevents POS business logic from being tied to one device vendor.

### 121. Barcode Flow

Rule ID: POS-121

Scan Barcode → Resolve Product / Variant → Add to Order. If multiple matches occur: Show selection.

### 122. Barcode Not Found

Rule ID: POS-122

Cashier sees Product not found. If permission allows: Quick Product Lookup, but not arbitrary product creation from cashier in MVP.

### 123. Customer Display

Rule ID: POS-123

Future support: Items, Subtotal, Discount, Tax, Total, Payment Status, kept separate from cashier application state rendering.

### 124. Receipt Number

Rule ID: POS-124

Receipt/order numbering should be human-friendly. Example: ABH01-260911-00452, while primary database identity remains UUID.

### 125. Duplicate Receipt Number

Rule ID: POS-125

Database uniqueness must prevent duplicate business receipt identifiers within their configured scope.

### 126. Order Number Strategy

Rule ID: POS-126

Suggested components: Branch Code, Business Date, Sequence. Example: ABH-260911-0452.

### 127. POS Startup

Rule ID: POS-127

Load Local Config → Validate Device → Load Cached Catalog → Check Session → Check Shift → Start Background Sync → Open POS. POS should not wait for all analytics or noncritical remote services.

### 128. Catalog Sync

Rule ID: POS-128

Catalog sync should support Incremental Sync rather than downloading all data each time. Example cursor: catalog_version.

### 129. Configuration Versioning

Rule ID: POS-129

Important configuration can have versions: catalog_version, pricing_version, tax_version. POS records which version it was using when appropriate.

### 130. Emergency Fallback

Rule ID: POS-130

If backend is temporarily unavailable but device is already activated and local credentials/config are valid: POS should still allow safe offline operation according to policy.

### 131. Device Revocation

Rule ID: POS-131

If terminal is revoked: Server marks REVOKED. When device reconnects: POS locks transaction capability. Unsynced legitimate transactions should be safely handled before destructive local cleanup.

### 132. Local Data Protection

Rule ID: POS-132

Sensitive local POS data should be minimized. Local storage should use platform-supported secure storage for credentials/tokens. Never store raw passwords.

### 133. Receipt Reconciliation

Rule ID: POS-133

Every completed receipt can be traced to Order, Payments, Cashier, Shift, Terminal, Branch, Inventory Movements, Profit Snapshot.

### 134. Sale Traceability

Rule ID: POS-134

Given an order_id, the system should answer: Who sold it? Where? Which terminal? Which shift? What was sold? At what price? Which discount? Which payment? What inventory changed? What was the cost? What was the profit? Was anything refunded?

### 135. Business Rule Priority

Rule ID: POS-135

When rules conflict, preserve in this order: 1. Financial truth; 2. Auditability; 3. Customer transaction integrity; 4. Inventory truth; 5. Operational convenience; 6. UI convenience.

### 136. Never Do

Rule ID: POS-136

Never Delete a completed sale; Overwrite historical sale price; Overwrite historical sale cost; Retry payment without idempotency; Hide cash differences; Use AI as financial authority; Silently discard offline transactions; Allow client to force server state.

### 137. MVP POS Screens

Rule ID: POS-137

Initial screens: Login, Open Shift, POS Home, Product Search, Cart, Modifiers, Discount Approval, Payment, Success / Receipt, Held Orders, Order History, Refund, Shift Summary, Close Shift, Sync Status, Settings / Device Info.

### 138. POS Home Design

Rule ID: POS-138

Main screen should contain only Categories, Products, Search, Cart, Checkout. Secondary actions stay behind More or contextual menus.

### 139. Checkout Screen

Rule ID: POS-139

Show Subtotal, Discount, Tax, Total, Payment Methods. Avoid unnecessary charts, analytics, or management data.

### 140. Success Screen

Rule ID: POS-140

After payment: ✓ Payment Successful; Order #452; 47.00 SAR. Actions: New Order; Print. Then automatically return to new order after configured delay if desired.

### 141. Owner vs Cashier Separation

Rule ID: POS-141

Cashier sees Operational information only. Owner sees Profit, Trends, Alerts, Recommendations, AI. Do not overload the cashier with owner analytics.

### 142. Event Sequence for Standard Sale

Rule ID: POS-142

ShiftOpened → OrderCreated → OrderItemAdded → OrderItemAdded → OrderConfirmed → PaymentCreated → PaymentCaptured → SaleCompleted → InventoryConsumed → ProfitSnapshotCreated → AnalyticsUpdated → OwnerFeedUpdated. Some secondary events may run asynchronously.

### 143. Standard Sale Example

Rule ID: POS-143

Customer buys 2 × Spanish Latte. Unit price 18 SAR. Subtotal 36 SAR. Discount 0. Tax included/configured according to fiscal policy. Customer pays CARD. System captures 36, completes order, snapshots cost, consumes recipe ×2, updates sales, updates owner dashboard.

### 144. Example Inventory Consumption

Rule ID: POS-144

Recipe per Latte: Coffee 18g, Milk 250ml, Cup 1, Lid 1. Quantity sold: 2. Consumption: Coffee -36g, Milk -500ml, Cup -2, Lid -2.

### 145. Example Profit Snapshot

Rule ID: POS-145

Suppose Revenue = 36 SAR; Cost = 11 SAR. Then Gross Profit = 25 SAR. This snapshot remains unchanged even if milk prices rise tomorrow.

### 146. Example Offline Sale

Rule ID: POS-146

Internet lost → Customer buys for 28 SAR cash → POS completes locally → Receipt prints → client_transaction_id stored → Internet returns → Transaction syncs once → Server assigns canonical order ID. No duplicate sale should be created.

### 147. Example Refund

Rule ID: POS-147

Original Order = 80 SAR. Manager refunds 20 SAR. System: Refund = 20; Order = PARTIALLY_REFUNDED; Payment remaining net = 60. If returned goods are reusable: RETURN_IN. Otherwise inventory remains consumed.

### 148. MVP Acceptance Criteria

Rule ID: POS-148

The POS core is considered ready only when the following scenario works end-to-end: Activate Terminal → Login Cashier → Open Shift → Sell Product → Apply Modifier → Apply Valid Discount → Pay Cash → Print Receipt → Inventory Decreases → Profit Snapshot Created → Owner Sees Sale → Go Offline → Sell Again → Reconnect → Sync Without Duplicate → Refund Transaction → Close Shift → Cash Difference Calculated.

### 149. Final POS Principle

Rule ID: POS-149

The cashier's experience should feel like Tap → Tap → Pay → Done, while the system behind those taps performs Authorization, Pricing, Tax, Payment, Audit, Inventory, Costing, Profit, Events, Analytics, Sync without making the cashier think about any of it.

### 150. Architectural Decision

Rule ID: POS-150

The POS is not merely a front-end screen. It is the operational source where trusted business events begin. Therefore every transaction must be designed so it can later support Accounting, Inventory Intelligence, Fraud Detection, Forecasting, Multi-Branch Analytics, AI Recommendations without changing the fundamental transaction model.
