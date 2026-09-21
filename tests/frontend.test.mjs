// Execute the actual bundle in fresh module contexts, modelling page refreshes
// and both HA loaders evaluating different versioned URLs in either order.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const source = await readFile(
  new URL("../custom_components/vents_breezy/frontend/vents-breezy-card.js", import.meta.url),
  "utf8"
);

function page() {
  const elements = new Map();
  return vm.createContext({
    HTMLElement: class {
      attachShadow() {
        this.shadowRoot = { innerHTML: "", addEventListener() {} };
      }
    },
    customElements: {
      get: (name) => elements.get(name),
      define(name, cls) {
        assert.equal(elements.has(name), false, "Duplicate custom element definition");
        elements.set(name, cls);
      },
    },
    window: {},
    console: { info() {} },
  });
}

async function load(context, url) {
  const module = new vm.SourceTextModule(source, { context, identifier: url });
  await module.link(() => assert.fail("The bundled card must not depend on remote imports"));
  await module.evaluate();
}

test("dashboard resource alone registers the card on every fresh page", async () => {
  for (let refresh = 0; refresh < 20; refresh++) {
    const context = page();
    await load(context, "/vents_breezy/vents-breezy-card.js?v=0.2.3");
    const Card = context.customElements.get("vents-breezy-card");
    assert.equal(typeof Card, "function");
    const card = new Card();
    card.setConfig({ entity: "fan.breezy" });
    assert.match(card.shadowRoot.innerHTML, /Loading VENTS Breezy/);
    assert.equal(context.window.customCards.length, 1);
  }
});

test("frontend and dashboard module loads coexist in either order", async () => {
  for (const urls of [["current", "legacy"], ["legacy", "current"]]) {
    const context = page();
    await load(context, urls[0]);
    const original = context.customElements.get("vents-breezy-card");
    await load(context, urls[1]);
    assert.equal(context.customElements.get("vents-breezy-card"), original);
    assert.equal(context.window.customCards.length, 1);
  }
});
