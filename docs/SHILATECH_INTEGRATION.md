# Shilatech ↔ JARVIS Integration Plan (v1)

Status: **planning only** — no code in this document is wired yet.

## 0. Model

A single Python adapter `actions/shilatech.py` = a thin HTTPS client to the deployed
Shilatech app, exposed to Gemini as one tool `shilatech` with an `action` parameter
(the `game_updater` pattern). No submodule, no vendoring — Shilatech stays a separate
service; JARVIS is a client.

## 1. Auth — dedicated staff service account

- Provision one Shilatech account (role = staff/admin), e.g. `jarvis-bot@shilatech...`.
- Store credentials in the secret store / `config/api_keys.json` (never in code):
  - `SHILATECH_BASE_URL` (e.g. `https://<vercel-domain>`)
  - `SHILATECH_EMAIL`, `SHILATECH_PASSWORD`
- Session lifecycle: `POST /api/auth/login {email,password}` → capture the
  `shilatech_session` HttpOnly cookie → attach it to every subsequent request via a
  `requests.Session`. JWT is valid 7 days; on any 401, re-login once and retry.
  Cache the cookie **in memory only**.

Caveat surfaced by the code: an admin account is auto-promoted only if it matches
`ADMIN_EMAIL` on the server. For staff endpoints, make sure the service account's role
actually clears each endpoint's role gate (some check `role !== 'customer'`, others need
warehouse/admin).

## 2. Endpoint → action map (full scope)

| JARVIS action | HTTP call | Auth | Type |
| --- | --- | --- | --- |
| `search_parts` | `GET /api/products?q=&brand=&category=&inStock=` | none | read |
| `check_stock` / `price` | `GET /api/products?q=` (read stock/price) | none | read |
| `fitment` | `GET /api/catalog-parts?vehicleId=&q=`, `GET /api/vin` | none | read |
| `shipping_quote` | `GET /api/shipping/quote` | none | read |
| `list_orders` | `GET /api/orders` | session | read |
| `business_overview` | `GET /api/admin/overview` | staff | read |
| `low_stock` | `GET /api/admin/products` (filter stock) / warehouse overview | staff | read |
| `sales_today` | `GET /api/admin/orders` / `/api/finance-ledger` | staff | read |
| `place_order` | `POST /api/orders` | session | mutation |
| `pos_sale` | `POST /api/pos` | staff | mutation |
| `update_product` | `POST/PUT /api/admin/products` | admin | mutation |

Exact fields for the admin/warehouse/POST bodies to be confirmed against those handlers
when we build — only `products`, `orders`, `auth`, `catalog-parts`, `health`, `lib/auth`
have been fully read so far.

## 3. Tool declaration (sketch)

```json
{ "name": "shilatech",
  "description": "Shilatech Autospares store + warehouse. Look up parts/stock/price, fitment by VIN, orders, business overview, low-stock & sales, and (with confirmation) place orders / POS sales.",
  "parameters": { "type":"OBJECT", "properties": {
     "action": {"type":"STRING","description":"search_parts|check_stock|price|fitment|list_orders|business_overview|low_stock|sales_today|place_order|pos_sale|update_product"},
     "query":  {"type":"STRING"}, "brand":{"type":"STRING"}, "category":{"type":"STRING"},
     "in_stock":{"type":"BOOLEAN"}, "vin":{"type":"STRING"},
     "items":{"type":"ARRAY"}, "customer":{"type":"OBJECT"},
     "confirm":{"type":"BOOLEAN","description":"required true for mutations"}
  }, "required":["action"] }
}
```

## 4. The 4 `main.py` wiring points

1. **Lazy import** (~line 39–58): `shilatech = _lazy_action("actions.shilatech", "shilatech")`
2. **Declaration**: append the block above to the tool list (~line 737).
3. **Dispatcher** (~line 1644):
   `elif name == "shilatech": r = await asyncio.to_thread(lambda: shilatech(parameters=args, speak=self.speak))`
4. **Sets** (~line 1106 / 1735): add `"shilatech"` to `mutating` (so calls preserve order);
   decide `CLOUD_SAFE_ACTIONS` inclusion (read actions are cloud-safe; keep mutations local-only).

## 5. Mutation safety (because scope = full)

- Every mutation (`place_order`, `pos_sale`, `update_product`) requires `confirm=true` and a
  spoken read-back before executing ("Placing an order for 4× Jeep front brake pads,
  KES 12,800 total, deliver to… — confirm?"). This matches how other risky actions gate.
- Long ops report progress via `self.speak`, like `game_updater`/`flight_finder`.
- Idempotency: server generates `order_no`; JARVIS should **not** retry POSTs blindly on
  timeout — surface the uncertainty instead.

## 6. Ad-studio hook (the payoff)

`search_parts` returns `imageUrl`, `price`, `stock` → this is the data feed for the future
`ad_studio`: pick in-stock SKU → generate creative (`GEMINI_IMAGE_MODEL`) → post via
Meta Graph/WhatsApp. Build `actions/shilatech.py` first so the product feed exists before
`ad_studio`.

## 7. Rollout order

1. Adapter + login/session + `search_parts`/`check_stock` (public, zero risk) — verify
   against live `/api/health`.
2. Add staff reads (`business_overview`, `low_stock`, `sales_today`) with the service account.
3. Add gated mutations (`place_order`, `pos_sale`, `update_product`) with confirmation.
4. Wire product feed into `ad_studio`.

## 8. Prereqs / to confirm at build time

- Live `SHILATECH_BASE_URL` + a provisioned staff service account.
- Confirm request/response shapes for the admin/warehouse/POS handlers.
- Decide whether any Shilatech-side change is wanted later (an API-key path) — not needed
  for v1 with the service account.

## Build sequence (broader roadmap)

`JAUTOMATIC` submodule + `actions/job_search.py` → `actions/shilatech.py` → `ad_studio` on top of both.
