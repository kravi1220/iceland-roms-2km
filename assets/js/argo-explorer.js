(function () {
  const DEFAULT_COLOR = "#e67e22";
  const SELECTED_COLOR = "#27ae60";
  let requestSeq = 0;

  async function main() {
    const [bathy, floats] = await Promise.all([
      loadJSON("../data/bathymetry_overlay.json"),
      loadJSON("../data/argo_floats.json"),
    ]);

    const map = L.map("map", { scrollWheelZoom: false });
    addBathyLayer(map, bathy, "../assets/img/overview/bathymetry_overlay.png");
    renderLegend(bathy, "legend");

    const markers = {};
    const listEl = document.getElementById("float-list");
    floats
      .slice()
      .sort((a, b) => a.float_id.localeCompare(b.float_id))
      .forEach((f) => {
        const m = L.circleMarker([f.lat, f.lon], {
          radius: 6, color: "#fff", weight: 1.5, fillColor: DEFAULT_COLOR, fillOpacity: 0.9,
        }).addTo(map);
        m.bindTooltip(`Float ${f.float_id}`);
        m.on("click", () => selectFloat(f.float_id));
        markers[f.float_id] = m;

        const li = document.createElement("li");
        li.textContent = `${f.float_id}  (${f.n_days} days)`;
        li.dataset.id = f.float_id;
        li.addEventListener("click", () => selectFloat(f.float_id));
        listEl.appendChild(li);
      });

    let current = null;

    async function selectFloat(id) {
      const seq = ++requestSeq;
      if (current) markers[current].setStyle({ fillColor: DEFAULT_COLOR, radius: 6 });
      current = id;
      markers[id].setStyle({ fillColor: SELECTED_COLOR, radius: 8 });
      map.panTo(markers[id].getLatLng());
      Array.from(listEl.children).forEach((li) => li.classList.toggle("active", li.dataset.id === id));

      const data = await loadJSON(`../data/argo/${id}.json`);
      if (seq !== requestSeq) return; // a newer selection started while this one was loading
      renderPanel(data);
    }

    function renderPanel(data) {
      document.getElementById("panel-empty").style.display = "none";
      const panel = document.getElementById("panel-content");
      panel.style.display = "block";
      document.getElementById("panel-title").textContent = `Argo float ${data.float_id}`;
      const ns = data.lat >= 0 ? "N" : "S";
      const ew = data.lon >= 0 ? "E" : "W";
      document.getElementById("panel-meta").textContent =
        `${Math.abs(data.lat).toFixed(3)}°${ns}, ${Math.abs(data.lon).toFixed(3)}°${ew} · ${data.n_days} colocated days`;
      document.getElementById("panel-link").href = `float_${data.float_id}.html`;

      const depthSel = document.getElementById("depth-select");
      depthSel.innerHTML = data.depths.map((d) => `<option value="${d}">${d} m</option>`).join("");

      const varSel = document.getElementById("var-select");

      function draw() {
        const depth = parseInt(depthSel.value, 10);
        const variable = varSel.value;
        const s = data.series;
        const obsKey = `obs_${variable}_${depth}`;
        const modKey = `model_${variable}_${depth}`;
        const traces = [
          { x: s.date, y: s[modKey], mode: "lines", name: "ROMS", line: { color: "#2980b9", width: 1.6 } },
          { x: s.date, y: s[obsKey], mode: "markers", name: "Argo", marker: { color: "#c0392b", size: 5 } },
        ];
        Plotly.newPlot("chart", traces, {
          margin: { t: 10, r: 15, l: 55, b: 40 },
          yaxis: { title: variable === "temp" ? "Temperature (°C)" : "Salinity (PSU)" },
          xaxis: { rangeslider: { thickness: 0.08 }, type: "date" },
          legend: { orientation: "h", y: 1.12 },
          height: 340,
        }, { responsive: true, displayModeBar: false });
      }
      depthSel.onchange = draw;
      varSel.onchange = draw;
      draw();
    }

    // Pre-select the first float so the panel isn't empty on load.
    if (floats.length) selectFloat(floats[0].float_id);
  }

  document.addEventListener("DOMContentLoaded", main);
})();
