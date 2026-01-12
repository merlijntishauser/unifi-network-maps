class UnifiNetworkMapCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.svg_url || !config.data_url) {
      throw new Error("svg_url and data_url are required");
    }
    this._config = config;
    this._data = null;
    this._root = this.attachShadow({ mode: "open" });
    this._render();
    this._loadData();
  }

  set hass(_hass) {
    // No-op for now; reserved for future HA integration.
  }

  getCardSize() {
    return 6;
  }

  _render() {
    if (!this._root) {
      return;
    }
    const title = this._config.title ? `<h3>${this._config.title}</h3>` : "";
    const dataStatus = this._data
      ? `Loaded ${this._data.devices?.length || 0} devices`
      : "Loading data...";
    this._root.innerHTML = `
      <style>
        .container { font-family: var(--mdc-typography-body1-font-family, sans-serif); }
        .map { width: 100%; overflow: auto; }
        img, svg { width: 100%; height: auto; display: block; }
        .meta { font-size: 0.85rem; color: var(--secondary-text-color, #666); margin-top: 0.5rem; }
        .details { font-size: 0.85rem; margin-top: 0.5rem; }
        .details strong { display: block; margin-bottom: 0.2rem; }
        .details code { font-family: var(--mdc-typography-code-font-family, monospace); }
      </style>
      <div class="container">
        ${title}
        <div class="map">
          <img src="${this._config.svg_url}" alt="UniFi network map" />
        </div>
        <div class="meta">${dataStatus}</div>
        <div class="details">${this._detailsMarkup()}</div>
      </div>
    `;
  }

  async _loadData() {
    try {
      const response = await fetch(this._config.data_url);
      if (!response.ok) {
        throw new Error(`Failed to load data: ${response.status}`);
      }
      this._data = await response.json();
      this._render();
      await this._wireSvg();
    } catch (err) {
      this._data = { devices: [] };
      if (this._root) {
        const meta = this._root.querySelector(".meta");
        if (meta) {
          meta.textContent = "Failed to load data";
        }
      }
      // eslint-disable-next-line no-console
      console.warn("unifi-network-map: data load failed", err);
    }
  }

  async _wireSvg() {
    const img = this._root?.querySelector("img");
    if (!img) {
      return;
    }
    const response = await fetch(this._config.svg_url);
    if (!response.ok) {
      return;
    }
    const svgText = await response.text();
    const container = img.parentElement;
    if (!container) {
      return;
    }
    container.innerHTML = svgText;
    const svg = container.querySelector("svg");
    if (!svg) {
      return;
    }
    const deviceNodes = svg.querySelectorAll("[data-device-id]");
    deviceNodes.forEach((node) => {
      node.style.cursor = "pointer";
      node.addEventListener("click", () => {
        const id = node.getAttribute("data-device-id");
        if (id) {
          this._selectDevice(id);
        }
      });
    });
  }

  _selectDevice(deviceId) {
    if (!this._data || !Array.isArray(this._data.devices)) {
      return;
    }
    const device = this._data.devices.find((entry) => entry.id === deviceId);
    if (!device) {
      return;
    }
    this._selected = device;
    this._render();
  }

  _detailsMarkup() {
    if (!this._selected) {
      return "Select a device to see details.";
    }
    const name = this._selected.name || "Unknown";
    const model = this._selected.model || "-";
    const ip = this._selected.ip || "-";
    return `
      <strong>${name}</strong>
      <div>Model: <code>${model}</code></div>
      <div>IP: <code>${ip}</code></div>
    `;
  }
}

customElements.define("unifi-network-map", UnifiNetworkMapCard);
