You are implementing Phase 2 of an existing React + Vite + TypeScript dashboard that already works in Phase 1:
- browser connects directly to AWS IoT Core over MQTT via WSS
- guest Cognito Identity Pool auth already works
- topic subscription to ecwa_dt/events already works
- raw messages already appear in the existing debug console

Your job now is to build the production-facing dashboard UI and the state merge logic for the actual payload structure.

==================================================
PHASE 2 OBJECTIVE
==================================================

Build a responsive, mobile-friendly dashboard that:
1. Consumes the existing Phase 1 raw message stream
2. Merges sparse incremental updates into a persistent in-memory state
3. Renders:
   - gateway overview
   - 12 BUSBAR device cards/list items
   - per-BUSBAR terminal view for 15 terminals
4. Shows last seen date/time clearly at gateway, busbar, and terminal levels
5. Keeps the existing raw debug console, but moves it under Advanced / Diagnostics rather than the main screen
6. Works well on desktop, tablet, and mobile phones

Do not break the existing Phase 1 transport/auth code. Build on top of it.

==================================================
ACTUAL PAYLOAD SHAPE
==================================================

The inbound message payload is a JSON array containing mixed record types.

The complete payload structure is inside:
/home/oladosu/Nngriid/busbar-viewer/data-format.md

Record type A — Gateway record
Example:
{
  "deviceId": "ND1234561",
  "device_desc": "Gateway",
  "LoRa_SNR": "10.0",
  "No_of_subDevices": "12"
}

Record type B — BUSBAR device record
Example:
{
  "deviceId": "BB0010",
  "device_desc": "busbar",
  "gps_status": 1,
  "satellites": 7,
  "latitude": 0.0,
  "longitude": 0.0,
  "altitude": 412.5,
  "speed": 0.8,
  "gps_timestamp": 1234567890,
  "master_chip_Temp": 10.0,
  "slave_1_chip_Temp": 10.0,
  "slave_2_chip_Temp": 10.0,
  "thermistor_Temp": 10.0,
  "ext_Rg_I_red": 0.0,
  "ext_Rg_I_yellow": 0.0,
  "ext_Rg_I_blue": 0.0,
  "frequency": 50.0,
  "LORA_RSSI": 10.0,
  "error_flags": 0,
  "multi_paths": 0
}

Record type C — Terminal record
Example:
{
  "terminal_id": "BB0010-1",
  "voltage": 220,
  "current": 0,
  "power_factor": 0,
  "active_power": 0,
  "reactive_power": 0,
  "apparent_power": 0,
  "active_energy": 0,
  "reactive_energy": 0,
  "apparent_energy": 0,
  "harmonic_energy": 0,
  "overload_status": 0
}

Terminal key semantics:
- terminal_id format is BUSBAR_ID-terminalNo
- example: BB0010-1 belongs to BUSBAR BB0010, terminal 1
- each BUSBAR has 15 terminals
- there are 12 BUSBAR devices total

==================================================
UPDATE BEHAVIOR RULES
==================================================

These rules are critical:

1. The gateway does NOT always send a full snapshot.
2. Only device or terminal records that have at least one changed parameter may be uploaded.
3. Whenever at least one terminal record for a BUSBAR is uploaded, the BUSBAR device record for that same BUSBAR will also be uploaded.
4. Every 2 minutes, the gateway uploads a full packet containing the whole state, so a newly opened dashboard can eventually reconstruct everything even before more changes happen.

This means:
- the UI must NOT render directly from the latest raw packet
- the frontend must maintain a merged latest-known-state model
- sparse updates must patch existing state without wiping unchanged fields
- a newly opened dashboard may initially be incomplete until the next full packet arrives

==================================================
REQUIRED ARCHITECTURE
==================================================

Use a normalized client-side state store.

You may use Zustand if not already used. If the Phase 1 app already uses another state solution, extend that cleanly instead of introducing unnecessary complexity.

Create and maintain these state domains:

1. gateway
2. busbarsById
3. terminalsByBusbarId
4. recentRawMessages
5. connection state
6. ui state (selected busbar, filters, panel state, advanced/debug open state)

Each stored entity must include:
- data fields
- lastSeenAt (ISO timestamp based on browser receive time)
- freshness status derived from lastSeenAt
- lastChangedAt if feasible
- source packet metadata if useful

==================================================
STATE MERGE LOGIC
==================================================

Implement robust merge logic.

For every inbound MQTT message:
1. Parse the message payload as JSON array
2. For each record:
   - if record.device_desc === "Gateway", merge into gateway state
   - if record.device_desc === "busbar" and record.deviceId exists, merge into the matching BUSBAR
   - if record.terminal_id exists, parse it into:
     - busbarId
     - terminalNumber
     then merge into the matching terminal under that BUSBAR

Rules:
- merging must be field-level, not replace-whole-object unless necessary
- undefined fields in a sparse record must NOT erase prior stored values
- if a terminal update is received for a BUSBAR whose terminal map does not yet exist, initialize it
- if a BUSBAR appears before all its terminals have ever been seen, still render it correctly
- if the first packet after page load is sparse, keep partial state and show that a full snapshot is still pending
- preserve recent raw messages for diagnostics

Add a boolean or derived state such as:
- hasReceivedFullEnoughSnapshot
or
- initialHydrationComplete

Do not assume the first packet is complete.

==================================================
LAST SEEN / FRESHNESS REQUIREMENTS
==================================================

The UI must show last seen date/time clearly.

Required at:
- gateway level
- each BUSBAR level
- each terminal level in details view
- optionally each terminal card if compact enough

Display both:
- relative time, e.g. "updated 12s ago"
- full local date/time, e.g. "2026-03-14 14:32:19"

Define derived freshness states:
- live: updated within 30 seconds
- recent: 30 seconds to 2 minutes
- stale: more than 2 minutes
- offline/suspect: more than 5 minutes

These thresholds should be constants in one place.

Use these freshness states consistently in badges/colors/icons across the app.

==================================================
UI REQUIREMENTS
==================================================

The app must be mobile responsive and operationally useful.

Main information architecture:

A. Top-level Dashboard page
B. BUSBAR detail view
C. Advanced / Diagnostics area containing the old Phase 1 debug console

Do not leave the old debug console as the main page.

--------------------------------------
A. TOP-LEVEL DASHBOARD PAGE
--------------------------------------

Desktop/tablet layout:
- top summary strip/cards
- busbar overview section
- selected BUSBAR preview or side panel

Mobile layout:
- stacked summary cards
- stacked BUSBAR cards
- detail navigation into BUSBAR view
- no dense multi-column layout on narrow screens

Top summary cards should include:
- Gateway ID
- Number of BUSBARs known
- Number of BUSBARs currently stale/offline
- Number of overloaded terminals total
- Gateway last seen
- Connection status
- "Awaiting full snapshot" indicator if applicable

BUSBAR overview section:
- render all 12 BUSBARs as cards or list items
- each BUSBAR card should show:
  - BUSBAR ID
  - freshness badge
  - last seen time
  - frequency
  - LORA_RSSI
  - satellites
  - error_flags indicator
  - overload count among its terminals
  - count of terminals seen so far out of 15
- include search/filter/sort controls:
  - search by BUSBAR ID
  - filter stale only
  - filter overloaded only
  - filter error only
  - sort by ID / last seen / overload count

--------------------------------------
B. BUSBAR DETAIL VIEW
--------------------------------------

When a BUSBAR is selected, open a dedicated detail view/panel/page.

Show:
1. BUSBAR summary header
   - deviceId
   - freshness badge
   - last seen date/time
   - frequency
   - LORA_RSSI
   - gps_status
   - satellites
   - latitude / longitude / altitude / speed
   - gps_timestamp
   - temperatures:
     - master_chip_Temp
     - slave_1_chip_Temp
     - slave_2_chip_Temp
     - thermistor_Temp
   - ext_Rg_I_red / yellow / blue
   - error_flags
   - multi_paths

2. Terminals section
   - render 15 terminals for the selected BUSBAR
   - desktop: use a neat grid
   - mobile: use stacked cards or accordion rows
   - each terminal card should show compact essentials only:
     - terminal number
     - voltage
     - current
     - active_power
     - power_factor
     - overload_status badge
     - last seen
   - clicking/tapping a terminal opens an expanded detail panel/modal/sheet showing:
     - reactive_power
     - apparent_power
     - active_energy
     - reactive_energy
     - apparent_energy
     - harmonic_energy
     - full last seen date/time

3. Change highlighting
   - recently updated BUSBAR cards should briefly highlight
   - recently updated terminal cards should briefly highlight
   - do not use aggressive animation; keep it professional

--------------------------------------
C. ADVANCED / DIAGNOSTICS
--------------------------------------

Move the existing Phase 1 debug console under:
- an "Advanced"
- "Diagnostics"
- or "Developer Tools" section

Keep all existing useful Phase 1 capabilities:
- raw message stream
- latest raw payload
- connection/debug state
- any existing connect/disconnect console functions if appropriate

But it should not dominate the main dashboard.

==================================================
RESPONSIVE DESIGN REQUIREMENTS
==================================================

The app must render cleanly on mobile phones.

Breakpoints:
- mobile: < 640px
- tablet: 640px to 1024px
- desktop: > 1024px

Required responsive behavior:

Mobile:
- single-column layout
- summary cards stacked
- BUSBAR cards stacked
- terminal cards stacked
- selected BUSBAR opens a detail page, drawer, or modal
- terminal expanded details open as modal or bottom sheet
- no horizontal overflow
- no huge tables as the default mobile layout

Tablet:
- 2-column card layouts where appropriate
- selected BUSBAR can still use stacked sections

Desktop:
- multi-column summary strip
- BUSBAR grid/list on the left or main area
- detail panel or full detail page for selected BUSBAR
- terminal grid can be 3 to 5 columns depending on available width

Accessibility:
- buttons and cards must be touch-friendly
- font sizes must remain readable on mobile
- use semantic labels and accessible contrast

==================================================
VISUAL / UX PRIORITIES
==================================================

Prioritize clarity over density.

Do NOT make the default screen a giant flat table of 180 terminals.

The default experience should be:
- overview first
- drill down into a BUSBAR
- then inspect terminals

You may add a secondary "Table" view later if helpful, but it must not replace the primary overview/detail design.

Include:
- empty states
- loading states
- "waiting for first packet"
- "waiting for full snapshot"
- stale/offline warnings
- malformed record warnings if packet parsing partly fails

==================================================
TYPES TO IMPLEMENT
==================================================

Create explicit TypeScript types/interfaces for:
- GatewayRecord
- BusbarRecord
- TerminalRecord
- ParsedInboundRecord union
- GatewayState
- BusbarState
- TerminalState
- FreshnessState
- DashboardStoreState

The parser should distinguish:
- gateway record
- busbar record
- terminal record
- unknown/invalid record

Do not crash the app on bad records.
Log them to diagnostics and continue.

==================================================
DELIVERABLES
==================================================

Provide output in this order:

1. Short architecture summary
2. Proposed updated file tree
3. State model design
4. Merge algorithm explanation
5. Full source code for all new/updated files
6. Notes on how the existing Phase 1 console is moved under Advanced/Diagnostics
7. Responsive design explanation
8. Any package install commands
9. Testing checklist using sparse updates and full 2-minute packets

==================================================
IMPLEMENTATION NOTES
==================================================

- Build on the existing Phase 1 codebase; do not rewrite transport/auth from scratch
- Keep code clean and production-oriented
- Prefer small reusable components
- Preserve the existing MQTT message feed and adapt it into the new normalized store
- Ensure the UI still works correctly if:
  - only one BUSBAR sends a changed packet
  - only some terminals are known so far
  - a user opens the page mid-cycle before the next full packet
  - packets arrive out of order by a few seconds
- Make last seen time a first-class concept throughout the app

Most important:
Implement the merge logic correctly so sparse updates never wipe previously known state.
