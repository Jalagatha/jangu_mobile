const { defineConfig } = require("cypress");

module.exports = defineConfig({
  e2e: {
    baseUrl: process.env.CYPRESS_BASE_URL || "https://jango-backend.onrender.com",
    specPattern: "cypress/e2e/**/*.cy.js",
    supportFile: "cypress/support/e2e.js",
    fixturesFolder: "cypress/fixtures",
    testIsolation: false,
    pageLoadTimeout: 120000,
    defaultCommandTimeout: 15000,
    video: false,
    screenshotOnRunFailure: true,
    // Absorbs free-tier cold-start variance, not flake suppression -- a "passed on attempt 2/3" line is a yellow flag worth checking.
    retries: { runMode: 2, openMode: 0 },
  },
});
