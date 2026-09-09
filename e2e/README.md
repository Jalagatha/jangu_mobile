# Jangu storefront — Cypress E2E

UI-driven end-to-end harness. Drives the storefront in a real browser; no local
Django server required (it targets the deployed site by default).

## Setup

    cd e2e
    npm install
    cp cypress.env.json.example cypress.env.json   # optional: override testPassword

## Run

    npm run e2e         # headless, against https://jango-backend.onrender.com
    npm run e2e:open    # interactive runner

Target another environment with CYPRESS_BASE_URL:

    CYPRESS_BASE_URL=http://localhost:8000 npm run e2e

## account-smoke.cy.js

1. Registers the shopper `0701588030` / `JanguTest2026!` (or confirms it already
   exists — the spec is re-runnable).
2. Logs out, then logs back in with those credentials.
3. While logged in: opens the first in-stock product, adds it to the cart, and
   asserts the cart shows the line.

The first green run creates the account on the target database. Render's free
tier wipes its SQLite on every deploy, so after a redeploy the next run
re-creates it.

CI is not wired up (GitHub Actions is disabled on this repo). Run it locally.
