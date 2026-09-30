# Shilatech Autospares integration

JARVIS connects to Shilatech through the web application's existing JSON APIs. Actions follow Shilatech's pages and departments rather than automating its browser interface.

| Section | Typical actions |
| --- | --- |
| Dashboard | View sales, open orders, low-stock counts and recent orders |
| Shop | Search/filter the public product catalog |
| Orders | List orders; create only with explicit confirmation |
| Operations | View or submit authorized operational actions |
| Warehouse | View stock and fulfillment operations |
| Delivery | View and process authorized delivery work |
| POS | Search stock and view receipts; record sales with confirmation |
| Workshop | View and update garage job cards |
| Finance | View a period or submit ledger records |
| Receivables | View and submit authorized receivable records |
| Payroll | View and submit authorized payroll records |
| HR / My HR | View and submit authorized HR records |
| Approvals | View requests or submit decisions/requests |
| Garage | View and update customer garage records |
| VIN | Look up a VIN |

## Configuration

Configure the deployed site URL and a dedicated, least-privilege staff account:

```bash
SHILATECH_URL=https://your-shilatech-domain.example
SHILATECH_EMAIL=jarvis.staff@example.com
SHILATECH_PASSWORD=use-a-secret-manager
```

A session cookie can be supplied instead of credentials:

```bash
SHILATECH_SESSION_COOKIE='shilatech_session=...'
```

Credentials are read from the process environment only. They are not accepted in model tool arguments, written to JARVIS configuration files, or returned in action results. Use HTTPS outside local development.

## Safety

Read actions execute immediately. Any create/update/submit/process action requires:

1. an exact payload;
2. explicit user confirmation of that change; and
3. `confirmed=true` in the resulting tool call.

The bridge does not expose login, logout, password, or M-Pesa payment-initiation endpoints. Shilatech's server-side role checks remain authoritative, so the configured account can only use its assigned departments.

## Examples

- “Search Shilatech for in-stock Jeep brake pads.”
- “Show the Shilatech low-stock dashboard.”
- “List warehouse work awaiting processing.”
- “Look up VIN … in Shilatech.”
- “Show this month's finance ledger.”
