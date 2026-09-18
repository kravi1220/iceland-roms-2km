async function loadJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error("Failed to load " + url);
  return r.json();
}

function renderLegend(bathyMeta, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `
    <div class="legend-bar" style="background:linear-gradient(to right, #440154, #3b528b, #21918c, #5ec962, #fde725)"></div>
    <div class="legend-labels"><span>0 m</span><span>${bathyMeta.depth_label}</span><span>${Math.round(bathyMeta.vmax)} m</span></div>
  `;
}

function addBathyLayer(map, bathyMeta, imageUrl) {
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 10,
  }).addTo(map);
  L.imageOverlay(imageUrl, bathyMeta.bounds, { opacity: 0.82 }).addTo(map);
  map.fitBounds(bathyMeta.bounds);
  return map;
}
