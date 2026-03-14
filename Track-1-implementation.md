Work on the in this folder.
all necessary settings are already in 

/home/oladosu/Nngriid/busbar-viewer/.env

You are implementing Phase 1 of a React + Vite + TypeScript IoT dashboard that connects directly from the browser to AWS IoT Core.

Objective:
Build a working guest-access dashboard that opens directly in the browser, connects to AWS IoT Core over MQTT via secure WebSockets, subscribes to the topic `ecwa_dt/events`, and displays raw incoming messages reliably.

This phase is only about transport, connection management, raw ingestion, and a simple debug UI. Do not build a polished analytics dashboard yet.

==================================================
PROJECT CONTEXT
==================================================

System context:
- A gateway aggregates data from 10 metering devices.
- The gateway publishes collated data to a single AWS IoT Core topic: `ecwa_dt/events`.
- The frontend must receive and display this stream directly from AWS IoT Core.
- There is no dedicated backend for this phase.
- There is no login page and no user sign-in flow.
- The dashboard should be accessible by simply opening the app URL in a browser.

Authentication and authorization:
- Use Amazon Cognito Identity Pool with unauthenticated guest access enabled.
- Do not use Cognito User Pools.
- Do not create any sign-in or sign-up flow.
- Do not use IoT device certificates or private keys in the frontend.
- The browser must obtain temporary AWS credentials from the Cognito Identity Pool and use them to connect to AWS IoT Core over MQTT over WSS.
- The frontend is strictly read-only.

Transport:
- Direct browser connection to AWS IoT Core using MQTT over secure WebSockets.
- Subscribe to `ecwa_dt/events`.
- No HTTP polling.
- No backend proxy.

Hosting:
- GitHub Pages is the first hosting target.
- Keep the app portable so it can later be hosted on S3 + CloudFront with minimal changes.
- Handle GitHub Pages base path correctly.
- Do not hardcode assumptions that only work at the domain root.

==================================================
NON-NEGOTIABLE CONSTRAINTS
==================================================

- Do not switch to a backend architecture.
- Do not suggest a backend proxy.
- Do not use Cognito User Pools.
- Do not store AWS IoT X.509 certificates or private keys in the browser.
- Do not add authentication pages.
- Do not skip credential refresh logic.
- Do not skip reconnect and resubscribe logic.
- Do not jump ahead into a fancy dashboard before raw ingestion works.
- Write real code, not pseudocode.

==================================================
TECH STACK
==================================================

Use:
- React
- Vite
- TypeScript
- Browser-compatible AWS credential handling
- Browser-compatible MQTT-over-WSS client for AWS IoT Core

Code requirements:
- Strict TypeScript
- Small reusable modules
- Clean separation of concerns
- Strong runtime error handling
- Minimal but useful comments
- Easy manual testing
- No dead code
- No unnecessary libraries

==================================================
CONFIGURATION
==================================================

Use environment variables for deployment-specific values.

Expected env variables:
- VITE_AWS_REGION
- VITE_COGNITO_IDENTITY_POOL_ID
- VITE_AWS_IOT_ENDPOINT
- VITE_IOT_TOPIC=ecwa_dt/events
- VITE_APP_TITLE
- VITE_BASE_PATH

Important:
- The app URL visited by users is the GitHub Pages URL.
- The AWS IoT endpoint is not the browser URL; it is used internally by the app for MQTT-over-WSS.
- The implementation must work correctly under a GitHub Pages project path such as `/busbar-viewer/`.
- The code should remain portable later to S3/CloudFront root hosting.

==================================================
IMPLEMENTATION PHASES
==================================================

PHASE 0 — architecture
1. Briefly state the architecture being implemented.
2. Assume the payload schema may evolve.
3. Build connection and ingestion first.
4. Add a normalization layer that preserves raw payloads even if the schema is incomplete.

PHASE 1 — project structure
1. Organize the app into folders such as:
   - src/config
   - src/lib/aws
   - src/lib/iot
   - src/hooks
   - src/components
   - src/types
   - src/utils
2. Provide all required package installation commands.
3. Provide a working Vite configuration suitable for GitHub Pages first.
4. Keep the code portable for later CloudFront/S3 hosting.

PHASE 2 — guest credentials via Cognito Identity Pool
1. Implement guest credential acquisition using Cognito Identity Pool unauthenticated identities.
2. Create a reusable credentials module that:
   - acquires temporary AWS credentials
   - exposes expiration time when available
   - refreshes credentials before expiry
   - can be safely used by the IoT connection layer
3. No user login.
4. No User Pools.
5. No hardcoded secrets.

PHASE 3 — AWS IoT Core connection over MQTT over WSS
1. Implement a reusable browser IoT connection service.
2. Connect to AWS IoT Core using MQTT over secure WebSockets.
3. Use temporary guest credentials from Cognito.
4. Support:
   - connect
   - disconnect
   - reconnect
   - subscribe
   - unsubscribe
   - resubscribe after reconnect
5. Generate a unique client ID per browser session.
6. Prevent duplicate client creation and duplicate subscriptions.

PHASE 4 — raw message ingestion
1. Subscribe to `ecwa_dt/events`.
2. Receive inbound messages.
3. Decode each payload as UTF-8 string.
4. Attempt JSON.parse.
5. If parsing succeeds:
   - keep parsed JSON
   - keep original raw text
6. If parsing fails:
   - keep raw text
   - keep parse error metadata
7. Keep a rolling in-memory buffer of the latest 100 messages.
8. Each message object should include:
   - id
   - topic
   - receivedAt
   - rawText
   - parsedJson (optional)
   - parseError (optional)

PHASE 5 — debug UI
Build a minimal developer-facing debug dashboard only.

Include:
- connection status
- connect button
- disconnect button
- current topic display
- total message count
- last message timestamp
- credential expiry display if available
- latest raw payload panel
- recent messages list
- clear messages button
- pause/resume auto-scroll if practical
- explicit error area for credential or socket failures

Do not build a polished analytics UI yet.

PHASE 6 — normalization layer
Create a generic normalization layer that can evolve later.

Define TypeScript types for:
- RawIoTMessage
- ParsedGatewayEnvelope
- MeterDeviceReading

Build a parser utility that:
- safely accepts unknown JSON
- extracts gateway-level metadata if present
- extracts device-level readings if present
- tolerates missing fields
- preserves unknown fields
- never discards the original payload

Do not over-assume the payload structure.

PHASE 7 — resilience
1. Refresh temporary AWS credentials before expiry.
2. Reconnect automatically on network or socket interruption.
3. Resubscribe to `ecwa_dt/events` after reconnect.
4. Prevent duplicate subscriptions after reconnect.
5. Handle malformed JSON safely.
6. Clean up subscriptions and sockets properly on component unmount.
7. Make connection state transitions explicit:
   - idle
   - connecting
   - connected
   - reconnecting
   - disconnected
   - error

PHASE 8 — deployment readiness
1. Make GitHub Pages the first deployment target.
2. Ensure static asset references and base-path behavior are correct for GitHub Pages.
3. Keep deployment-specific values isolated to config and env files.
4. Make later migration to S3/CloudFront straightforward.
5. Include GitHub Pages deployment instructions.
6. Include notes on what changes later for CloudFront/S3.

==================================================
AWS-SIDE ASSUMPTIONS
==================================================

Assume the following AWS resources are already configured manually:
- Cognito Identity Pool with unauthenticated guest access enabled
- Unauthenticated IAM role restricted to:
  - iot:Connect
  - iot:Subscribe
  - iot:Receive
- AWS IoT Core data endpoint for MQTT over WSS
- Topic access restricted to `ecwa_dt/events`

Document these assumptions clearly in the output.

Also include a warning:
- Since there is no sign-in, anyone who can open the dashboard URL and obtain guest credentials can receive whatever the guest role is allowed to subscribe to.
- This should therefore be treated as a public or shared dashboard unless security is tightened later.

==================================================
GITHUB PAGES FIRST
==================================================

Target GitHub Pages first.

Requirements:
- Build output must work under a project path like `/busbar-viewer/`
- Handle Vite base path correctly
- Avoid assumptions that the app is hosted at `/`
- If routing is needed, use a GitHub Pages-compatible approach or explain the choice
- Keep the code portable to CloudFront/S3 later

Also include:
- package.json scripts for dev, build, preview, and deployment
- exact GitHub Pages deployment steps
- notes for what changes later when moving to CloudFront/S3, especially:
  - base path
  - environment variables
  - hosting URL
  - cache invalidation

==================================================
OUTPUT FORMAT
==================================================

Return the result in this exact order:

1. Proposed file tree
2. Install commands
3. Full source code for all files
4. .env.example
5. vite.config.* contents
6. GitHub Pages deployment steps
7. AWS guest-access checklist
8. Explanation of credential refresh behavior
9. Explanation of reconnect and resubscribe behavior
10. Next-phase notes for evolving into an actual dashboard UI

Be concrete and implementation-focused.
Do not give a general tutorial.
Produce a complete working Phase 1 app.
