async function loadJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error("Failed to load " + url);
  return r.json();
}

// The bathymetry overlay is rendered with matplotlib's reversed-viridis
// colormap (viridis_r) scaled linearly from 0 m to bathyMeta.vmax: shallow
// water is yellow, the deepest water dark purple. These are 11 evenly spaced
// samples of that same colormap, so the legend matches the map.
const DEPTH_LEGEND_STOPS = [
  "#fde725", "#bddf26", "#7ad151", "#44bf70", "#22a884", "#21908d",
  "#2a788e", "#355f8d", "#414487", "#482475", "#440154",
];

function renderLegend(bathyMeta, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const vmax = bathyMeta.vmax;
  const step = 500;
  let ticks = "";
  for (let d = 0; d <= vmax + 1e-6; d += step) {
    const pct = (d / vmax) * 100;
    const shift = d === 0 ? "0" : d >= vmax - 1e-6 ? "-100%" : "-50%";
    ticks += `<span style="left:${pct}%;transform:translateX(${shift})">${d}</span>`;
  }
  el.innerHTML = `
    <div class="legend-bar" style="background:linear-gradient(to right, ${DEPTH_LEGEND_STOPS.join(", ")})"></div>
    <div class="legend-ticks">${ticks}</div>
    <div class="legend-title">${bathyMeta.depth_label}</div>
  `;
}

function mercatorY(latDeg) {
  return Math.log(Math.tan(Math.PI / 4 + (latDeg * Math.PI) / 360));
}

// Hover/click readout of the model's true depth (metres) at the cursor,
// decoded from a raster where each ocean pixel stores round(h) as R*256+G.
// It lets the colour on the map be checked against the actual number.
function addDepthReadout(map, bathyMeta, depthUrl) {
  const [[south, west], [north, east]] = bathyMeta.bounds;
  const mySouth = mercatorY(south);
  const myNorth = mercatorY(north);
  const img = new Image();
  let data = null;
  let W = 0, H = 0;
  img.onload = () => {
    W = img.naturalWidth;
    H = img.naturalHeight;
    const c = document.createElement("canvas");
    c.width = W;
    c.height = H;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(img, 0, 0);
    try {
      data = ctx.getImageData(0, 0, W, H).data;
    } catch (e) {
      data = null;
    }
  };
  img.src = depthUrl;

  const ctl = L.control({ position: "bottomleft" });
  ctl.onAdd = () => {
    const div = L.DomUtil.create("div", "depth-readout");
    div.textContent = "Hover or tap the map for model depth";
    return div;
  };
  ctl.addTo(map);
  const box = () => ctl.getContainer();

  const show = (e) => {
    if (!data) return;
    const { lat, lng } = e.latlng;
    if (lng < west || lng > east || lat < south || lat > north) {
      box().textContent = "Outside model domain";
      return;
    }
    const x = Math.min(W - 1, Math.floor(((lng - west) / (east - west)) * W));
    const y = Math.min(H - 1, Math.floor(((myNorth - mercatorY(lat)) / (myNorth - mySouth)) * H));
    const i = (y * W + x) * 4;
    if (data[i + 3] === 0) {
      box().textContent = "Land / outside model grid";
      return;
    }
    const depth = data[i] * 256 + data[i + 1];
    box().textContent = `Model depth: ${depth} m  (${lat.toFixed(2)}°N, ${Math.abs(lng).toFixed(2)}°${lng < 0 ? "W" : "E"})`;
  };
  map.on("mousemove", show);
  map.on("click", show);
}

function addBathyLayer(map, bathyMeta, imageUrl) {
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 16,
    maxNativeZoom: 19,
    detectRetina: true,
  }).addTo(map);
  // Fully opaque: any transparency would blend the depth colours with the
  // basemap underneath (light-blue ocean, beige land, white ice), so the same
  // depth would show a different colour in different places and never match
  // the legend. Land stays transparent, so the basemap still shows there.
  L.imageOverlay(imageUrl, bathyMeta.bounds, { opacity: 1 }).addTo(map);
  map.fitBounds(bathyMeta.bounds);
  if (bathyMeta.depth_png) {
    addDepthReadout(map, bathyMeta, imageUrl.replace(/[^/]*$/, bathyMeta.depth_png));
  }
  return map;
}
