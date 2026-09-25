(function () {
  const LAND_COLOR = "#a89f78";
  const WALL_COLOR = "#9aa1a8";
  // Same reversed-viridis scale as the 2-D bathymetry map on About the Model
  // (util.js renderLegend): shallow (0 m) is yellow, the deepest water is
  // dark purple. Plotly's built-in colorscale names don't render correctly
  // in this Plotly.js version, so spell it out explicitly.
  const DEPTH_SCALE = [
    [0.0, "#fde725"], [0.1, "#bddf26"], [0.2, "#7ad151"], [0.3, "#44bf70"],
    [0.4, "#22a884"], [0.5, "#21908d"], [0.6, "#2a788e"], [0.7, "#355f8d"],
    [0.8, "#414487"], [0.9, "#482475"], [1.0, "#440154"],
  ];
  // Flat, unshaded lighting: shading would darken/brighten the depth colours
  // so they no longer match the legend.
  const FLAT_LIGHT = { ambient: 1, diffuse: 0, specular: 0, fresnel: 0, roughness: 1 };

  async function main() {
    const d = await loadJSON("data/bathymetry_3d.json?v=3");

    const lonSpan = d.bounds.lon_max - d.bounds.lon_min;
    const latSpan = d.bounds.lat_max - d.bounds.lat_min;
    const padLon = lonSpan * 0.08;
    const padLat = latSpan * 0.08;

    // Explicit triangle meshes (mesh3d): every vertex carries its own lon,
    // lat, z and depth, so colour, position and tooltip always agree.
    // (Plotly's 2-D-array "surface" trace mixed up the indices of a
    // curvilinear grid and showed the wrong depth at a location.)
    const depthMesh = (m, name) => ({
      type: "mesh3d",
      x: m.x, y: m.y, z: m.z,
      i: m.i, j: m.j, k: m.k,
      intensity: m.c,
      intensitymode: "vertex",
      cmin: d.depth_range[0], cmax: d.depth_range[1],
      colorscale: DEPTH_SCALE,
      showscale: false,
      flatshading: false,
      lighting: FLAT_LIGHT,
      hovertemplate: "Depth %{intensity:.0f} m<extra></extra>",
      name,
    });

    const oceanTop = depthMesh(d.ocean, "Bathymetry");
    const seafloor = depthMesh(d.seafloor, "Seafloor relief");

    const landTop = {
      type: "mesh3d",
      x: d.land.x, y: d.land.y, z: d.land.z,
      i: d.land.i, j: d.land.j, k: d.land.k,
      color: LAND_COLOR,
      flatshading: true,
      lighting: { ambient: 0.9, diffuse: 0.3 },
      hoverinfo: "skip",
      name: "Land",
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
