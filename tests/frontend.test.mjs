// Execute the standalone card in fresh module contexts, modelling page refreshes.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const source = await readFile(
  new URL("../www/vents-breezy-card.js", import.meta.url),
  "utf8"
);

function page() {
  const elements = new Map();
  return vm.createContext({
    HTMLElement: class {
      attachShadow() {
        this.shadowRoot = { innerHTML: "", addEventListener() {}, querySelector() { return null; } };
      }
      dispatchEvent() {}
    },
    HTMLButtonElement: class {},
    CustomEvent: class {},
    document: {
      createElement() {
        return {
          textContent: "",
          get innerHTML() { return this.textContent.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll('"', "&quot;"); },
        };
      },
    },
    customElements: {
      get: (name) => elements.get(name),
      define(name, cls) {
        assert.equal(elements.has(name), false, "Duplicate custom element definition");
        elements.set(name, cls);
      },
    },
    window: {},
    console: { info() {}, debug() {} },
  });
}

async function load(context, url) {
  const module = new vm.SourceTextModule(source, { context, identifier: url });
  await module.link(() => assert.fail("The standalone card must not depend on remote imports"));
  await module.evaluate();
}

test("dashboard resource alone registers the card on every fresh page", async () => {
  for (let refresh = 0; refresh < 20; refresh++) {
    const context = page();
    await load(context, "/local/vents-breezy-card.js");
    const Card = context.customElements.get("vents-breezy-card");
    assert.equal(typeof Card, "function");
    const card = new Card();
    card.setConfig({ entity: "fan.breezy" });
    assert.match(card.shadowRoot.innerHTML, /Loading VENTS Breezy/);
    assert.equal(context.window.customCards.length, 1);
  }
});

test("duplicate module evaluations are harmless", async () => {
  const context = page();
  await load(context, "/local/vents-breezy-card.js");
  const original = context.customElements.get("vents-breezy-card");
  await load(context, "/local/vents-breezy-card.js?reload=1");
  assert.equal(context.customElements.get("vents-breezy-card"), original);
  assert.equal(context.window.customCards.length, 1);
});

async function remote({ panel = true, overrides = {}, panelState = "50" } = {}) {
  const context = page();
  await load(context, "/local/vents-breezy-card.js");
  const Card = context.customElements.get("vents-breezy-card");
  const card = new Card();
  const calls = [];
  const states = {
    "fan.breezy": { state: "off", attributes: { percentage: 33 } },
    "select.airflow": { state: "extract", attributes: {} },
  };
  // Put another number and panel selects first, so discovery must use suffixes.
  const registry = [
    { entity_id: "fan.breezy", device_id: "breezy", platform: "vents_breezy" },
    { entity_id: "number.other", device_id: "breezy", platform: "vents_breezy", unique_id: "123_other" },
  ];
  if (panel) {
    for (const [domain, key, state] of [
      ["number", "panel_brightness", panelState],
      ["select", "panel_backlight_mode", "auto"],
      ["select", "panel_display", "on"],
    ]) {
      registry.push({ entity_id: `${domain}.${key}`, device_id: "breezy", platform: "vents_breezy", unique_id: `123_${key}` });
      states[`${domain}.${key}`] = { state, attributes: {} };
    }
  }
  registry.push({ entity_id: "select.airflow", device_id: "breezy", platform: "vents_breezy", unique_id: "123_airflow" });
  card.setConfig({ entity: "fan.breezy", entities: overrides });
  card.hass = {
    states,
    callWS: async () => registry,
    callService: async (domain, service, data) => calls.push({ domain, service, ...data }),
  };
  await card._discoverEntities();
  return { card, calls, context, states, registry };
}

test("panel controls discover by exact suffix and work while the fan is off", async () => {
  const { card, calls } = await remote();
  assert.equal(card._entities.airflow, "select.airflow");
  assert.equal(card._entities.panel_brightness, "number.panel_brightness");
  assert.match(card.shadowRoot.innerHTML, /LED panel/);
  assert.match(card.shadowRoot.innerHTML, /id="panel-brightness"[^>]+value="50"[^>]+aria-label="LED panel brightness" >/);

  await card._handleSliderChange({ target: { id: "panel-brightness", value: "75" } });
  assert.deepEqual(calls, [{ domain: "number", service: "set_value", entity_id: "number.panel_brightness", value: 75 }]);
});

test("panel mode and display clicks target their own select, leaving airflow intact", async () => {
  const { card, calls, context } = await remote();
  for (const [key, option] of [["panel_backlight_mode", "auto"], ["panel_display", "off"], ["panel_display", "off_interval"]]) {
    const button = new context.HTMLButtonElement();
    button.dataset = { panel: key, option };
    await card._handleClick({ composedPath: () => [button] });
  }
  assert.deepEqual(calls.map((call) => ({ ...call })), [
    { domain: "select", service: "select_option", entity_id: "select.panel_backlight_mode", option: "auto" },
    { domain: "select", service: "select_option", entity_id: "select.panel_display", option: "off" },
    { domain: "select", service: "select_option", entity_id: "select.panel_display", option: "off_interval" },
  ]);
});

test("panel dragging updates only its label and survives state and discovery renders", async () => {
  const { card } = await remote();
  const outputs = { "#speed-value": { textContent: "33%" }, "#panel-brightness-value": { textContent: "50%" } };
  card.shadowRoot.querySelector = (selector) => outputs[selector];
  const html = card.shadowRoot.innerHTML;
  card._handleSliderInput({ target: { id: "panel-brightness", value: "80" } });
  card.hass = card._hass;
  card._render();
  assert.equal(card.shadowRoot.innerHTML, html);
  assert.equal(outputs["#panel-brightness-value"].textContent, "80%");
  assert.equal(outputs["#speed-value"].textContent, "33%");
  assert.equal(card._sliderValue, 33);
  await card._handleSliderChange({ target: { id: "panel-brightness", value: "80" } });
  assert.equal(card._sliderActive, false);
});

test("missing panel entities are hidden without falling back to unrelated controls", async () => {
  const { card } = await remote({ panel: false });
  assert.equal(card._entities.panel_brightness, undefined);
  assert.equal(card._entities.panel_backlight_mode, undefined);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /<section class="panel">/);
});

for (const state of ["unknown", "unavailable", "0", "101"]) {
  test(`panel brightness ${state} disables the slider`, async () => {
    const { card } = await remote({ panelState: state });
    assert.match(card.shadowRoot.innerHTML, /id="panel-brightness"[^>]+disabled/);
  });
}

test("explicit panel overrides survive discovery and keyboard changes use the override", async () => {
  const { card, calls, states } = await remote({ overrides: { panel_brightness: "number.custom" } });
  states["number.custom"] = { state: "60", attributes: {} };
  card._handleKeydown({ key: "Enter", target: { id: "panel-brightness", value: "60" } });
  assert.equal(card._entities.panel_brightness, "number.custom");
  assert.equal(calls[0].entity_id, "number.custom");
  assert.equal(calls[0].value, 60);
});
