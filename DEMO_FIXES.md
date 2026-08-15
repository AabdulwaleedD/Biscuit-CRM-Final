# Biscuit CRM/ERP Prototype — Major Demo Fixes

## Fixed
1. Approval Center now selects by Approval ID, preventing duplicate/legacy Request IDs from approving the wrong record.
2. Approval Center only treats Submitted/Pending Approval records as pending.
3. Approval actions re-check the latest CSV status before changing a request.
4. Stock Request approval -> Warehouse Release -> Stock Transfer -> Completed is preserved.
5. Product ID/Product Name are preserved in approval records.
6. Expenditure request IDs and approval IDs are repaired and generated correctly.
7. ID generation now searches for the requested prefix instead of using the first ID column.
8. Inventory demo data is reconciled to a traceable movement ledger with Opening Stock records.
9. Product-level dashboard/report analysis now uses sale_items.csv, so Top Products can display correctly.
10. Audit log CSV is normalized and its IDs are generated safely.
11. Sidebar uses the supplied PNG icons.
12. Page headers and important dashboard sections now use the supplied PNG icons.
13. Dashboard now highlights wholesale/distribution KPIs including sales value, stock units, active trucks and active deliveries.

## Presentation note
This remains a PROTOTYPE / DEMO. The data is fictional. Production deployment should move persistence to a proper relational database and strengthen authentication, permissions, audit controls and document storage.

## QR / Inbound improvements
- Product Scanner now presents the camera prominently and decodes physical QR labels with OpenCV.
- Warehouse Release requires a QR scan matching the approved request's Product ID before the release button is enabled.
- Inbound Goods Receiving requires a QR scan matching the expected inbound Product ID before receipt can be posted.
- Confirmed inbound receipt adds actual received quantity to inventory and records the goods receipt movement/audit event.
- Simple Product Scanner lookups do not change stock; stock changes only through confirmed business transactions.
