(function () {
  const LAND_COLOR = "#a89f78";
  const WALL_COLOR = "#9aa1a8";
  const BOTTOM_COLOR_SCALE = [[0, "#eef0f1"], [1, "#7d8288"]];
  // Plotly's built-in "Turbo" colorscale name doesn't render correctly for
  // surface traces in this Plotly.js version (renders as near-uniform), so
  // spell it out explicitly.
  const TURBO_SCALE = [
    [0.0, "#30123b"], [0.17, "#4145ab"], [0.33, "#26bce1"],
    [0.5, "#3fef8d"], [0.67, "#e1dd37"], [0.83, "#fb7e21"], [1.0, "#7a0403"],
  ];

  async function main() {
    const d = await loadJSON("data/bathymetry_3d.json");

    const lonSpan = d.bounds.lon_max - d.bounds.lon_min;
    const latSpan = d.bounds.lat_max - d.bounds.lat_min;
    const padLon = lonSpan * 0.08;
    const padLat = latSpan * 0.08;

    const oceanTop = {
      type: "surface",
      x: d.lon, y: d.lat, z: d.ocean_z,
      surfacecolor: d.ocean_color,
      cmin: d.sst_range[0], cmax: d.sst_range[1],
      colorscale: TURBO_SCALE,
      showscale: false,
      lighting: { ambient: 0.75, diffuse: 0.5, specular: 0.1 },
      hovertemplate: "SST %{surfacecolor:.1f}°C<extra></extra>",
      name: "Sea surface temperature",
    };

    const landTop = {
      type: "surface",
      x: d.lon, y: d.lat, z: d.land_z,
      surfacecolor: d.land_z.map((row) => row.map((v) => (v === null ? null : 1))),
      cmin: 0, cmax: 1,
      colorscale: [[0, LAND_COLOR], [1, LAND_COLOR]],
      showscale: false,
      lighting: { ambient: 0.9, diffuse: 0.3 },
      hoverinfo: "skip",
      name: "Land",
    };

    const seafloor = {
      type: "surface",
      x: d.lon, y: d.lat, z: d.bottom_z,
      colorscale: BOTTOM_COLOR_SCALE,
      showscale: false,
      lighting: { ambient: 0.7, diffuse: 0.6, specular: 0.05 },
      hovertemplate: "Depth-side relief<extra></extra>",
      name: "Seafloor relief",
    };

    const wall = {
      type: "mesh3d",
      x: d.wall.x, y: d.wall.y, z: d.wall.z,
      i: d.wall.i, j: d.wall.j, k: d.wall.k,
      color: WALL_COLOR,
      flatshading: true,
      lighting: { ambient: 0.8, diffuse: 0.4 },
      hoverinfo: "skip",
      name: "Domain wall",
    };

    const coastTraces = d.coastlines.map((c) => ({
      type: "scatter3d",
      mode: "lines",
      x: c.lon, y: c.lat, z: c.lon.map(() => 0.02),
      line: { color: "#2b2216", width: 3 },
      hoverinfo: "skip",
      showlegend: false,
    }));

    const layout = {
      margin: { t: 0, r: 0, b: 0, l: 0 },
      paper_bgcolor: "rgba(0,0,0,0)",
      scene: {
        xaxis: { visible: false, range: [d.bounds.lon_min - padLon, d.bounds.lon_max + padLon] },
        yaxis: { visible: false, range: [d.bounds.lat_min - padLat, d.bounds.lat_max + padLat] },
        zaxis: { visible: false, range: [d.bounds.z_min * 1.15, Math.max(lonSpan, latSpan) * 0.06] },
        // Orthographic projection: no perspective distortion, so the slab
        // reads like a scientific block diagram and frames reliably.
        aspectmode: "manual",
        aspectratio: { x: 1.7, y: 1, z: 0.45 },
        camera: {
          eye: { x: 1.2, y: -1.5, z: 0.9 },
          center: { x: 0, y: 0, z: -0.1 },
          projection: { type: "orthographic" },
        },
      },
    };

    const gd = document.getElementById("bathy3d");
    await Plotly.newPlot(gd, [seafloor, wall, oceanTop, landTop, ...coastTraces], layout, {
      responsive: true,
      displayModeBar: true,
      modeBarButtonsToRemove: ["toImage"],
    });

    // Plotly's gl3d projection can be mis-applied on the very first paint
    // (the box renders tiny/mis-framed) until something forces a genuine
    // recompute. A plain timer isn't reliable, so re-assert the camera on
    // several real, independent signals: the plot actually scrolling into
    // view, any user interaction with it, and a window resize -- whichever
    // fires first fixes it, and repeated calls are harmless.
    let fixed = false;
    const fixCamera = () => {
      if (fixed) return;
      fixed = true;
      Plotly.relayout(gd, { "scene.camera": JSON.parse(JSON.stringify(layout.scene.camera)) });
    };

    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          fixCamera();
          io.disconnect();
        }
      });
      io.observe(gd);
    }
    gd.addEventListener("mouseenter", fixCamera, { once: true });
    gd.addEventListener("touchstart", fixCamera, { once: true });
    window.addEventListener("resize", fixCamera, { once: true });
    window.addEventListener("scroll", fixCamera, { once: true, passive: true });
    setTimeout(fixCamera, 1200);
  }

  document.addEventListener("DOMContentLoaded", main);
})();
