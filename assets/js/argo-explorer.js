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

    async function tryLoadJSON(url) {
      try {
        return await loadJSON(url);
      } catch (e) {
        return null;
      }
    }

    async function selectFloat(id) {
      const seq = ++requestSeq;
      if (current) markers[current].setStyle({ fillColor: DEFAULT_COLOR, radius: 6 });
      current = id;
      markers[id].setStyle({ fillColor: SELECTED_COLOR, radius: 8 });
      map.panTo(markers[id].getLatLng());
      Array.from(listEl.children).forEach((li) => li.classList.toggle("active", li.dataset.id === id));

      const [series, profile] = await Promise.all([
        loadJSON(`../data/argo/${id}.json`),
        tryLoadJSON(`../data/argo_profiles/${id}.json`),
      ]);
      if (seq !== requestSeq) return; // a newer selection started while this one was loading
      renderPanel(series, profile);
    }

    function renderPanel(data, profile) {
      document.getElementById("panel-empty").style.display = "none";
      const panel = document.getElementById("panel-content");
      panel.style.display = "block";
      document.getElementById("panel-title").textContent = `Argo float ${data.float_id}`;
      const ns = data.lat >= 0 ? "N" : "S";
      const ew = data.lon >= 0 ? "E" : "W";
      document.getElementById("panel-meta").textContent =
        `${Math.abs(data.lat).toFixed(3)}°${ns}, ${Math.abs(data.lon).toFixed(3)}°${ew} · ${data.n_days} colocated days`;
      document.getElementById("panel-link").href = `float_${data.float_id}.html`;

      const viewSel = document.getElementById("view-select");
      const varSel = document.getElementById("var-select");
      const depthSel = document.getElementById("depth-select");
      const depthControl = document.getElementById("depth-control");
      const profileModeSel = document.getElementById("profile-mode-select");
      const profileModeControl = document.getElementById("profile-mode-control");
      const dateSel = document.getElementById("profile-date-select");
      const dateControl = document.getElementById("profile-date-control");

      depthSel.innerHTML = data.depths.map((d) => `<option value="${d}">${d} m</option>`).join("");
      viewSel.querySelector('option[value="profile"]').disabled = !profile;
      if (!profile && viewSel.value === "profile") viewSel.value = "timeseries";
      if (profile) {
        dateSel.innerHTML = profile.dates.map((d) => `<option value="${d}">${d}</option>`).join("");
      }

      function updateControlVisibility() {
        const isProfile = viewSel.value === "profile";
        depthControl.style.display = isProfile ? "none" : "";
        profileModeControl.style.display = isProfile ? "" : "none";
        dateControl.style.display = isProfile && profileModeSel.value === "single" ? "" : "none";
      }

      function drawTimeSeries() {
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

      function drawProfileFill() {
        const variable = varSel.value;
        const depth = profile.depth;
        const modStats = profile.stats[`model_${variable}`];
        const obsStats = profile.stats[`obs_${variable}`];
        const traces = [
          { x: modStats.min, y: depth, mode: "lines", line: { color: "rgba(0,0,0,0)" }, showlegend: false, hoverinfo: "skip" },
          { x: modStats.max, y: depth, mode: "lines", line: { color: "rgba(0,0,0,0)" }, fill: "tonextx",
            fillcolor: "rgba(41,128,185,0.22)", name: "ROMS range", hoverinfo: "skip" },
          { x: modStats.mean, y: depth, mode: "lines", line: { color: "#2980b9", width: 2 }, name: "ROMS mean" },
          { x: obsStats.min, y: depth, mode: "lines", line: { color: "rgba(0,0,0,0)" }, showlegend: false, hoverinfo: "skip" },
          { x: obsStats.max, y: depth, mode: "lines", line: { color: "rgba(0,0,0,0)" }, fill: "tonextx",
            fillcolor: "rgba(192,57,43,0.18)", name: "Argo range", hoverinfo: "skip" },
          { x: obsStats.mean, y: depth, mode: "lines", line: { color: "#c0392b", width: 2 }, name: "Argo mean" },
        ];
        Plotly.newPlot("chart", traces, {
          margin: { t: 10, r: 15, l: 55, b: 40 },
          xaxis: { title: variable === "temp" ? "Temperature (°C)" : "Salinity (PSU)" },
          yaxis: { title: "Depth (m)", autorange: "reversed" },
          legend: { orientation: "h", y: 1.12 },
          height: 420,
        }, { responsive: true, displayModeBar: false });
      }

      function drawSingleProfile() {
        const variable = varSel.value;
        const depth = profile.depth;
        const dateIdx = profile.dates.indexOf(dateSel.value);
        const modArr = profile.profiles[`model_${variable}`][dateIdx];
        const obsArr = profile.profiles[`obs_${variable}`][dateIdx];
        const traces = [
          { x: modArr, y: depth, mode: "lines+markers", name: "ROMS", line: { color: "#2980b9", width: 2 }, marker: { size: 4 } },
          { x: obsArr, y: depth, mode: "lines+markers", name: "Argo", line: { color: "#c0392b", width: 2 }, marker: { size: 4 } },
        ];
        Plotly.newPlot("chart", traces, {
          margin: { t: 10, r: 15, l: 55, b: 40 },
          xaxis: { title: variable === "temp" ? "Temperature (°C)" : "Salinity (PSU)" },
          yaxis: { title: "Depth (m)", autorange: "reversed" },
          legend: { orientation: "h", y: 1.12 },
          height: 420,
        }, { responsive: true, displayModeBar: false });
      }

      function draw() {
        updateControlVisibility();
        if (viewSel.value === "timeseries") {
          drawTimeSeries();
        } else if (profileModeSel.value === "fill") {
          drawProfileFill();
        } else {
          drawSingleProfile();
        }
      }

      viewSel.onchange = draw;
      varSel.onchange = draw;
      depthSel.onchange = draw;
      profileModeSel.onchange = draw;
      dateSel.onchange = draw;
      draw();
    }

    // Pre-select the first float so the panel isn't empty on load.
    if (floats.length) selectFloat(floats[0].float_id);
  }

  document.addEventListener("DOMContentLoaded", main);
})();
