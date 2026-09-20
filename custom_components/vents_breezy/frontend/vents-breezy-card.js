const CARD_NAME = "vents-breezy-card";

const icon = (name) => `<ha-icon icon="mdi:${name}" aria-hidden="true"></ha-icon>`;

class VentsBreezyCard extends HTMLElement {
  static getConfigForm() {
    return {
      schema: [
        { name: "entity", required: true, selector: { entity: { domain: "fan" } } },
        { name: "name", selector: { text: {} } },
        {
          type: "expandable",
          name: "entities",
          title: "Entity overrides",
          schema: [
            { name: "airflow", selector: { entity: { domain: "select" } } },
            { name: "heater", selector: { entity: { domain: "switch" } } },
            { name: "humidity", selector: { entity: { domain: "sensor" } } },
            { name: "filter", selector: { entity: { domain: "binary_sensor" } } },
            { name: "reset_filter", selector: { entity: { domain: "button" } } },
          ],
        },
      ],
      computeLabel: (schema) => ({
        entity: "Fan entity",
        name: "Card title",
        airflow: "Airflow mode",
        heater: "Heater",
        humidity: "Humidity",
        filter: "Filter status",
        reset_filter: "Reset filter timer",
      })[schema.name],
    };
  }

  static getStubConfig(hass) {
    const entity = hass
      ? Object.keys(hass.states).find((entityId) => {
          const state = hass.states[entityId];
          return entityId.startsWith("fan.") &&
            state.attributes.preset_modes?.includes("night") &&
            state.attributes.preset_modes?.includes("turbo");
        })
      : undefined;
    return entity ? { entity } : {};
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._entities = {};
    this._pending = new Set();
    this._sliderValue = null;
    this._sliderActive = false;
    this.shadowRoot.addEventListener("click", (event) => this._handleClick(event));
    this.shadowRoot.addEventListener("input", (event) => this._handleSliderInput(event));
    this.shadowRoot.addEventListener("change", (event) => this._handleSliderChange(event));
    this.shadowRoot.addEventListener("keydown", (event) => this._handleKeydown(event));
  }

  setConfig(config) {
    if (!config.entity || !config.entity.startsWith("fan.")) {
      throw new Error("Select a VENTS Breezy fan entity");
    }
    this._config = { ...config };
    this._entities = { fan: config.entity, ...(config.entities || {}) };
    this._registryFan = null;
    this._discoverEntities();
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._discoverEntities();
    // Replacing the range input while a pointer is dragging it interrupts the
    // gesture. The final change event performs the render after the drag.
    if (!this._sliderActive) this._render();
  }

  getCardSize() {
    return 7;
  }

  getGridOptions() {
    return { rows: 7, columns: 6, min_rows: 6, min_columns: 3 };
  }

  async _discoverEntities() {
    if (!this._hass || !this._config?.entity || this._registryFan === this._config.entity) return;
    this._registryFan = this._config.entity;
    try {
      const registry = await this._hass.callWS({ type: "config/entity_registry/list" });
      const fan = registry.find((entry) => entry.entity_id === this._config.entity);
      if (!fan?.device_id) return;
      const siblings = registry.filter(
        (entry) => entry.device_id === fan.device_id && entry.platform === "vents_breezy"
      );
      const find = (domain, suffix) => siblings.find((entry) =>
        entry.entity_id.startsWith(`${domain}.`) && entry.unique_id?.endsWith(suffix)
      )?.entity_id || siblings.find((entry) => entry.entity_id.startsWith(`${domain}.`))?.entity_id;
      const overrides = this._config.entities || {};
      this._entities = {
        fan: this._config.entity,
        airflow: overrides.airflow || find("select", "_airflow"),
        heater: overrides.heater || find("switch", "_heater"),
        humidity: overrides.humidity || find("sensor", "_humidity"),
        filter: overrides.filter || find("binary_sensor", "_filter"),
        reset_filter: overrides.reset_filter || find("button", "_reset_filter"),
      };
      this._render();
    } catch (error) {
      // The explicit editor overrides still keep the card fully usable.
      console.debug("VENTS Breezy card entity discovery failed", error);
    }
  }

  _state(key) {
    const entityId = this._entities[key];
    return entityId ? this._hass?.states[entityId] : undefined;
  }

  _displayName(fan) {
    if (this._config.name) return this._config.name;
    if (this._hass?.formatEntityName && fan) {
      return this._hass.formatEntityName(fan, [{ type: "entity" }]);
    }
    return fan?.attributes.friendly_name || "VENTS Breezy";
  }

  _render() {
    if (!this.shadowRoot || !this._config) return;
    if (!this._hass) {
      this.shadowRoot.innerHTML = `<ha-card><div class="loading">Loading VENTS Breezy…</div></ha-card>`;
      return;
    }

    const fan = this._state("fan");
    if (!fan) {
      this.shadowRoot.innerHTML = `<ha-card><div class="error">Entity ${this._config.entity} is unavailable</div></ha-card>`;
      return;
    }

    const available = fan.state !== "unavailable" && fan.state !== "unknown";
    const isOn = fan.state === "on";
    const preset = fan.attributes.preset_mode;
    const percentage = Math.max(1, Math.min(100, Number(fan.attributes.percentage) || 1));
    if (!this._sliderActive) this._sliderValue = percentage;
    const mode = preset === "night" || preset === "turbo" ? preset : "manual";
    const airflow = this._state("airflow");
    const heater = this._state("heater");
    const humidity = this._state("humidity");
    const filter = this._state("filter");
    const reset = this._state("reset_filter");
    const filterWarning = filter?.state === "on";
    const busy = this._pending.size > 0;

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <ha-card class="${isOn ? "is-on" : "is-off"} ${busy ? "is-busy" : ""}">
        <div class="header">
          <button class="identity" data-more-info="fan" aria-label="Open fan details">
            <span class="fan-icon">${icon("fan")}</span>
            <span><span class="title">${this._escape(this._displayName(fan))}</span>
            <span class="subtitle">${available ? (isOn ? `${percentage}% · ${mode === "manual" ? "Manual" : this._capitalize(mode)}` : "Off") : "Unavailable"}</span></span>
          </button>
          <button class="power ${isOn ? "active" : ""}" data-action="power" aria-label="Turn ${isOn ? "off" : "on"}" aria-pressed="${isOn}" ${available ? "" : "disabled"}>${icon("power")}</button>
        </div>

        <section class="intensity ${isOn ? "" : "muted"}">
          <div class="section-label"><span>Air intensity</span><output>${this._sliderValue}%</output></div>
          <div class="mode-group" role="group" aria-label="Air intensity mode">
            ${this._modeButton("night", "weather-night", "Night", mode, available)}
            ${this._modeButton("manual", "tune-variant", "Manual", mode, available)}
            ${this._modeButton("turbo", "rocket-launch-outline", "Turbo", mode, available)}
          </div>
          <div class="slider-row">
            ${icon("fan-speed-1")}
            <input id="speed" type="range" min="1" max="100" step="1" value="${this._sliderValue}" aria-label="Fan speed" ${available ? "" : "disabled"}>
            ${icon("fan-speed-3")}
          </div>
          <div class="speed-marks">
            ${[33, 67, 100].map((speed) => `<button data-speed="${speed}" ${available ? "" : "disabled"}>${speed === 33 ? "Low" : speed === 67 ? "Medium" : "High"}</button>`).join("")}
          </div>
        </section>

        ${airflow ? `<section>
          <div class="section-label"><span>Airflow</span><span class="state-label">${this._airflowLabel(airflow.state)}</span></div>
          <div class="airflow-grid" role="group" aria-label="Airflow mode">
            ${this._airflowButton("ventilation", "swap-horizontal", "Ventilate", airflow)}
            ${this._airflowButton("heat_recovery", "sync", "Recovery", airflow)}
            ${this._airflowButton("air_supply", "arrow-collapse-right", "Supply", airflow)}
            ${this._airflowButton("extract", "arrow-collapse-left", "Extract", airflow)}
          </div>
        </section>` : ""}

        <div class="status-grid">
          ${heater ? `<button class="status ${heater.state === "on" ? "active warm" : ""}" data-action="heater" aria-pressed="${heater.state === "on"}">
            ${icon("heat-wave")}<span><b>Heater</b><small>${heater.state === "on" ? "On" : "Off"}</small></span>
          </button>` : ""}
          ${humidity ? `<button class="status" data-more-info="humidity">${icon("water-percent")}<span><b>Humidity</b><small>${this._escape(humidity.state)}${humidity.attributes.unit_of_measurement || "%"}</small></span></button>` : ""}
          ${filter ? `<button class="status ${filterWarning ? "warning" : ""}" data-more-info="filter">${icon(filterWarning ? "air-filter" : "check-circle-outline")}<span><b>Filter</b><small>${filterWarning ? "Service needed" : "OK"}</small></span></button>` : ""}
          ${reset ? `<button class="status reset" data-action="reset-filter">${icon("restart-alert")}<span><b>Filter timer</b><small>Reset…</small></span></button>` : ""}
        </div>
        ${busy ? `<div class="progress" aria-label="Applying change"></div>` : ""}
      </ha-card>`;
  }

  _modeButton(value, iconName, label, activeMode, available) {
    return `<button class="mode ${activeMode === value ? "active" : ""}" data-mode="${value}" aria-pressed="${activeMode === value}" ${available ? "" : "disabled"}>${icon(iconName)}<span>${label}</span></button>`;
  }

  _airflowButton(value, iconName, label, state) {
    const disabled = state.state === "unavailable" || state.state === "unknown";
    return `<button class="airflow ${state.state === value ? "active" : ""}" data-airflow="${value}" aria-pressed="${state.state === value}" ${disabled ? "disabled" : ""}>${icon(iconName)}<span>${label}</span></button>`;
  }

  async _handleClick(event) {
    const button = event.composedPath().find((node) => node instanceof HTMLButtonElement);
    if (!button || button.disabled) return;
    if (button.dataset.moreInfo) return this._moreInfo(button.dataset.moreInfo);
    if (button.dataset.speed) return this._call("speed", "fan", "set_percentage", { percentage: Number(button.dataset.speed) });
    if (button.dataset.mode) {
      if (button.dataset.mode === "manual") {
        return this._call("mode", "fan", "set_percentage", { percentage: this._sliderValue || 33 });
      }
      return this._call("mode", "fan", "set_preset_mode", { preset_mode: button.dataset.mode });
    }
    if (button.dataset.airflow) return this._call("airflow", "select", "select_option", { option: button.dataset.airflow });
    if (button.dataset.action === "power") {
      return this._call("power", "fan", this._state("fan").state === "on" ? "turn_off" : "turn_on");
    }
    if (button.dataset.action === "heater") {
      return this._call("heater", "switch", this._state("heater").state === "on" ? "turn_off" : "turn_on");
    }
    if (button.dataset.action === "reset-filter") {
      if (window.confirm("Reset the filter timer? Only continue after cleaning or replacing the filter.")) {
        return this._call("reset", "button", "press");
      }
    }
  }

  _handleSliderInput(event) {
    if (event.target.id !== "speed") return;
    this._sliderActive = true;
    this._sliderValue = Number(event.target.value);
    const output = this.shadowRoot.querySelector("output");
    if (output) output.textContent = `${this._sliderValue}%`;
  }

  _handleSliderChange(event) {
    if (event.target.id !== "speed") return;
    this._sliderActive = false;
    this._call("speed", "fan", "set_percentage", { percentage: Number(event.target.value) });
  }

  _handleKeydown(event) {
    if (event.key === "Enter" && event.target.id === "speed") this._handleSliderChange(event);
  }

  async _call(pendingKey, domain, service, data = {}) {
    const key = domain === "fan" ? "fan" : domain === "select" ? "airflow" : domain === "switch" ? "heater" : "reset_filter";
    const entityId = this._entities[key];
    if (!entityId || this._pending.has(pendingKey)) return;
    this._pending.add(pendingKey);
    this._render();
    try {
      await this._hass.callService(domain, service, { entity_id: entityId, ...data });
    } catch (error) {
      this.dispatchEvent(new CustomEvent("hass-notification", { bubbles: true, composed: true, detail: { message: `VENTS Breezy: ${error.message || "command failed"}` } }));
    } finally {
      this._pending.delete(pendingKey);
      this._render();
    }
  }

  _moreInfo(key) {
    const entityId = this._entities[key];
    if (entityId) this.dispatchEvent(new CustomEvent("hass-more-info", { bubbles: true, composed: true, detail: { entityId } }));
  }

  _airflowLabel(value) {
    return ({ ventilation: "Ventilation", heat_recovery: "Heat recovery", air_supply: "Air supply", extract: "Extract" })[value] || this._capitalize(value);
  }

  _capitalize(value) {
    return value ? `${value[0].toUpperCase()}${value.slice(1).replaceAll("_", " ")}` : "";
  }

  _escape(value) {
    const element = document.createElement("span");
    element.textContent = String(value ?? "");
    return element.innerHTML;
  }

  _styles() {
    return `
      :host { --breezy-accent: var(--primary-color, #03a9f4); display: block; }
      * { box-sizing: border-box; }
      ha-card { position: relative; overflow: hidden; padding: 18px; color: var(--primary-text-color); }
      button { color: inherit; font: inherit; -webkit-tap-highlight-color: transparent; }
      button:focus-visible, input:focus-visible { outline: 2px solid var(--breezy-accent); outline-offset: 2px; }
      button:disabled { opacity: .42; cursor: not-allowed; }
      .header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 18px; }
      .identity { display: flex; min-width: 0; align-items: center; gap: 12px; padding: 0; border: 0; background: transparent; text-align: left; cursor: pointer; }
      .fan-icon, .power { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 50%; }
      .fan-icon { background: color-mix(in srgb, var(--breezy-accent) 14%, transparent); color: var(--breezy-accent); font-size: 24px; }
      .is-on .fan-icon ha-icon { animation: spin 2.2s linear infinite; }
      .title, .subtitle { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .title { font-size: 17px; font-weight: 600; }
      .subtitle { margin-top: 3px; color: var(--secondary-text-color); font-size: 13px; }
      .power { flex: none; border: 0; background: var(--secondary-background-color); cursor: pointer; font-size: 22px; transition: .2s ease; }
      .power.active { background: var(--breezy-accent); color: var(--text-primary-color, white); box-shadow: 0 4px 14px color-mix(in srgb, var(--breezy-accent) 32%, transparent); }
      section { margin-top: 17px; }
      .section-label { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 9px; font-size: 13px; font-weight: 600; }
      .section-label output, .state-label { color: var(--secondary-text-color); font-weight: 500; }
      .mode-group { display: grid; grid-template-columns: repeat(3, 1fr); padding: 4px; border-radius: 14px; background: var(--secondary-background-color); }
      .mode { display: flex; min-height: 44px; align-items: center; justify-content: center; gap: 7px; border: 0; border-radius: 11px; background: transparent; cursor: pointer; font-size: 13px; font-weight: 600; }
      .mode ha-icon { font-size: 19px; }
      .mode.active { background: var(--card-background-color); color: var(--breezy-accent); box-shadow: 0 2px 8px rgba(0,0,0,.12); }
      .slider-row { display: grid; grid-template-columns: 24px 1fr 24px; align-items: center; gap: 8px; margin-top: 13px; color: var(--secondary-text-color); }
      input[type=range] { width: 100%; accent-color: var(--breezy-accent); cursor: pointer; }
      .speed-marks { display: flex; justify-content: space-between; margin: 1px 25px 0; }
      .speed-marks button { border: 0; padding: 5px 7px; background: transparent; color: var(--secondary-text-color); cursor: pointer; font-size: 11px; }
      .muted .slider-row, .muted .speed-marks { opacity: .62; }
      .airflow-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 7px; }
      .airflow { display: flex; min-width: 0; min-height: 58px; flex-direction: column; align-items: center; justify-content: center; gap: 5px; border: 1px solid var(--divider-color); border-radius: 12px; background: transparent; cursor: pointer; font-size: 11px; }
      .airflow ha-icon { font-size: 21px; }
      .airflow.active { border-color: color-mix(in srgb, var(--breezy-accent) 45%, transparent); background: color-mix(in srgb, var(--breezy-accent) 12%, transparent); color: var(--breezy-accent); }
      .status-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 18px; }
      .status { display: flex; min-width: 0; align-items: center; gap: 10px; padding: 11px 12px; border: 1px solid var(--divider-color); border-radius: 12px; background: transparent; text-align: left; cursor: pointer; }
      .status ha-icon { flex: none; color: var(--secondary-text-color); font-size: 22px; }
      .status span { min-width: 0; }
      .status b, .status small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .status b { font-size: 13px; font-weight: 600; }
      .status small { margin-top: 2px; color: var(--secondary-text-color); font-size: 11px; }
      .status.active { border-color: color-mix(in srgb, var(--breezy-accent) 40%, transparent); background: color-mix(in srgb, var(--breezy-accent) 10%, transparent); }
      .status.warm ha-icon { color: var(--warning-color, #ff9800); }
      .status.warning { border-color: var(--error-color, #db4437); background: color-mix(in srgb, var(--error-color, #db4437) 9%, transparent); }
      .status.warning ha-icon, .status.warning small { color: var(--error-color, #db4437); }
      .progress { position: absolute; inset: auto 0 0; height: 3px; overflow: hidden; background: color-mix(in srgb, var(--breezy-accent) 20%, transparent); }
      .progress::after { content: ""; display: block; width: 35%; height: 100%; background: var(--breezy-accent); animation: progress 1s ease-in-out infinite; }
      .is-busy button { pointer-events: none; }
      .loading, .error { padding: 24px; color: var(--secondary-text-color); }
      .error { color: var(--error-color); }
      @keyframes spin { to { transform: rotate(360deg); } }
      @keyframes progress { from { transform: translateX(-100%); } to { transform: translateX(386%); } }
      @media (max-width: 350px) { .mode span { display: none; } .airflow-grid { grid-template-columns: repeat(2, 1fr); } }
      @media (prefers-reduced-motion: reduce) { .is-on .fan-icon ha-icon, .progress::after { animation: none; } }
    `;
  }
}

if (!customElements.get(CARD_NAME)) customElements.define(CARD_NAME, VentsBreezyCard);

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === CARD_NAME)) {
  window.customCards.push({
    type: CARD_NAME,
    name: "VENTS Breezy Remote",
    description: "A complete, device-aware remote for VENTS Breezy ventilation units.",
    preview: true,
    documentationURL: "https://github.com/lukybil/ha-vents-integration#dashboard-card",
    getEntitySuggestion: (hass, entityId) => {
      const state = hass.states[entityId];
      return entityId.startsWith("fan.") &&
        state?.attributes.preset_modes?.includes("night") &&
        state?.attributes.preset_modes?.includes("turbo")
        ? { config: { type: `custom:${CARD_NAME}`, entity: entityId } }
        : null;
    },
  });
}

console.info("%c VENTS BREEZY CARD %c 0.2.1 ", "color:white;background:#039be5;font-weight:700", "color:#039be5;background:#e1f5fe");
