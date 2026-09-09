const user = require("../fixtures/test-user.json");
const password = Cypress.env("testPassword") || "JanguTest2026!";

describe("Storefront account: seed + verify +256701588030", () => {
  before(() => {
    // Pay the Render free-tier cold start once, before the real steps.
    cy.request({
      url: "/api/schema/",
      timeout: 120000,
      retryOnStatusCodeFailure: true,
    })
      .its("status")
      .should("eq", 200);
  });

  it("registers +256701588030, or confirms it already exists", () => {
    cy.visit("/register/");
    cy.get("#id_phone").clear().type(user.phone);
    cy.get("#id_first_name").clear().type(user.firstName);
    cy.get("#id_last_name").clear().type(user.lastName);
    cy.get("#id_password1").clear().type(password, { log: false });
    cy.get("#id_password2").clear().type(password, { log: false });
    cy.get('form[method="post"] button[type="submit"]').click();

    cy.location("pathname", { timeout: 30000 }).then((pathname) => {
      if (pathname !== "/register/") {
        // Redirected away -> account created and auto-logged-in.
        cy.get('form[action*="logout"]').should("exist");
        return;
      }
      // Still on /register/ -- the only acceptable reason is a duplicate phone.
      cy.get(".errorlist")
        .invoke("text")
        .then((text) => {
          expect(text, "register error text").to.match(/already exists/i);
          cy.log("account +256701588030 already present -- skipping creation");
        });
    });
  });

  it("logs in with the seeded credentials", () => {
    cy.ensureLoggedOut();
    cy.login(user.phone, password);
    cy.location("pathname").should("not.eq", "/login/");
    cy.get('form[action*="logout"]').should("exist");
    cy.get(".site-header .header-actions").should("contain.text", user.firstName);
  });

  it("completes a shopper smoke journey while logged in", () => {
    // testIsolation:false keeps the login from the previous test. Re-login only
    // if this spec is run in isolation (e.g. with --spec on this file alone and
    // Cypress starting mid-describe on a retry).
    cy.visit("/");
    cy.get("body").then(($body) => {
      if (!$body.find('form[action*="logout"]').length) {
        cy.login(user.phone, password);
      }
    });

    cy.visit("/");
    cy.get(".product-grid a.product-card")
      .filter(":not(:has(.oos))")
      .first()
      .click();
    cy.location("pathname").should("match", /^\/p\//);

    cy.get("body").then(($body) => {
      if ($body.find("select[data-variant-select]").length) {
        cy.get("select[data-variant-select] option[data-in-stock='1']")
          .first()
          .then(($opt) => {
            cy.get("select[data-variant-select]").select(String($opt.val()));
          });
      }
    });

    cy.get("button[data-add-btn]").click();

    cy.location("pathname").should("eq", "/cart/");
    cy.get("ul.messages").should("contain.text", "Added");
    cy.get("table.cart-table tbody tr").its("length").should("be.gte", 1);
  });
});
