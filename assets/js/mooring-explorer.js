(function () {
  const DEFAULT_COLOR = "#8e44ad";
  const SELECTED_COLOR = "#27ae60";
  let requestSeq = 0;

  async function main() {
    const [bathy, index] = await Promise.all([
      loadJSON("data/bathymetry_overlay.json?v=2"),
      loadJSON("data/moorings.json"),
    ]);

    const map = L.map("map", { scrollWheelZoom: false });
    addBathyLayer(map, bathy, "assets/img/overview/bathymetry_overlay.png");
    renderLegend(bathy, "legend");

    // group station-deployments by physical mooring name
    const byName = {};
    index.forEach((rec) => {
      (byName[rec.name] = byName[rec.name] || []).push(rec);
    });

    const markers = {};
    const listEl = document.getElementById("site-list");
    Object.keys(byName).sort().forEach((name) => {
      const recs = byName[name];
      const lat = recs[0].lat, lon = recs[0].lon;
      const m = L.circleMarker([lat, lon], {
        radius: 7, color: "#fff", weight: 1.5, fillColor: DEFAULT_COLOR, fillOpacity: 0.9,
      }).addTo(map);
      m.bindTooltip(`${name} (${recs.length} deployment${recs.length > 1 ? "s" : ""})`);
      m.on("click", () => selectStation(name));
      markers[name] = m;

      const li = document.createElement("li");
      li.textContent = `${name} — ${recs.map((r) => r.deployment).join(", ")}`;
      li.dataset.name = name;
      li.addEventListener("click", () => selectStation(name));
      listEl.appendChild(li);
    });

    let current = null;

    function selectStation(name) {
      if (current) markers[current].setStyle({ fillColor: DEFAULT_COLOR, radius: 7 });
      current = name;
      markers[name].setStyle({ fillColor: SELECTED_COLOR, radius: 9 });
      map.panTo(markers[name].getLatLng());
      Array.from(listEl.children).forEach((li) => li.classList.toggle("active", li.dataset.name === name));

      document.getElementById("panel-empty").style.display = "none";
      const panel = document.getElementById("panel-content");
      panel.style.display = "block";
      document.getElementById("panel-title").textContent = name;

      const recs = byName[name];
      const depSel = document.getElementById("deployment-select");
      depSel.innerHTML = recs.map((r) => `<option value="${r.deployment}">${r.deployment}</option>`).join("");
      depSel.onchange = () => loadDeployment(recs);
      loadDeployment(recs);
    }

    async function loadDeployment(recs) {
      const seq = ++requestSeq;
      const dep = document.getElementById("deployment-select").value;
      const rec = recs.find((r) => r.deployment === dep) || recs[0];

      const data = await loadJSON(`data/moorings/${rec.file}`);
      if (seq !== requestSeq) return; // a newer selection started while this one was loading

      document.getElementById("panel-meta").textContent =
        `${rec.lat.toFixed(3)}°N, ${Math.abs(rec.lon).toFixed(3)}°W` +
        (rec.bdepth ? ` · bottom depth ${rec.bdepth} m` : "") +
        ` · ${rec.dist_km} km from nearest grid cell`;

      const varSel = document.getElementById("var-select");
      const hasTS = rec.mc_depths.length > 0;
      const hasCurrent = rec.adcp_depths.length > 0;
      varSel.innerHTML = [
        hasTS ? '<option value="temp">Temperature</option>' : "",
        hasTS ? '<option value="salt">Salinity</option>' : "",
        hasCurrent ? '<option value="speed">Current speed</option>' : "",
      ].join("");

      const depthSel = document.getElementById("depth-select");

      function refreshDepths() {
        const v = varSel.value;
        const depths = v === "speed" ? rec.adcp_depths : rec.mc_depths;
        depthSel.innerHTML = depths.map((d) => `<option value="${d}">${d} m</option>`).join("");
      }

      function draw() {
        const variable = varSel.value;
        const depth = parseInt(depthSel.value, 10);
        const s = data.series;
        const obsKey = `obs_${variable}_${depth}`;
        const modKey = `model_${variable}_${depth}`;
        const label = variable === "temp" ? "Temperature (°C)"
          : variable === "salt" ? "Salinity (PSU)" : "Current speed (m/s)";
        const traces = [
          { x: s.date, y: s[modKey], mode: "lines", name: "ROMS", line: { color: "#2980b9", width: 1.6 } },
          { x: s.date, y: s[obsKey], mode: "markers", name: "Mooring", marker: { color: "#c0392b", size: 4 } },
        ];
        Plotly.newPlot("chart", traces, {
          margin: { t: 10, r: 15, l: 55, b: 40 },
          yaxis: { title: label },
          xaxis: { rangeslider: { thickness: 0.08 }, type: "date" },
          legend: { orientation: "h", y: 1.12 },
          height: 340,
        }, { responsive: true, displayModeBar: false });
      }

      varSel.onchange = () => { refreshDepths(); draw(); };
      depthSel.onchange = draw;
      refreshDepths();
      draw();
    }

    const firstName = Object.keys(byName).sort()[0];
    if (firstName) selectStation(firstName);
  }

  document.addEventListener("DOMContentLoaded", main);
})();
