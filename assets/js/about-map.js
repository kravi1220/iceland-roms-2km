(async function () {
  const bathy = await loadJSON("data/bathymetry_overlay.json");
  const map = L.map("map", { scrollWheelZoom: false });
  addBathyLayer(map, bathy, "assets/img/overview/bathymetry_overlay.png");
  renderLegend(bathy, "legend");
})();
