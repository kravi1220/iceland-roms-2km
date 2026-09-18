#!/usr/bin/env python3
"""
Convert the per-float ROMS-vs-Argo colocation NetCDFs
(roms_at_argo_at_single_depth/roms_at_argo_<WMO_ID>.nc) into small JSON files
for the interactive map/chart front end: one file per float with date-indexed
model & observed temperature/salinity at each colocated depth.

Also writes data/argo_floats.json, the marker index for the Leaflet map.
"""
import glob
import json
import os

import netCDF4 as nc
import numpy as np

SRC_GLOB = "/Volumes/Expansion/MFRI_Work/roms_at_argo_at_single_depth/roms_at_argo_*.nc"
OUT_DIR = "/Volumes/Expansion/MFRI_Work/iceland-roms-2km/data/argo"
INDEX_PATH = "/Volumes/Expansion/MFRI_Work/iceland-roms-2km/data/argo_floats.json"

# floats already featured on the static site (kept as the marker set)
SITE_FLOAT_IDS = {
    "3901851", "3901988", "4902117", "4902119", "5903392", "5903395", "5904173",
    "5904176", "6900429", "6901129", "6901167", "6901169", "6901170", "6901176",
    "6901190", "6901191", "6901194", "6901201", "6901208", "6901564", "6901566",
    "6901724", "6901752", "6901910", "6901921", "6901923", "6902694", "6902726",
    "6902728", "6902730", "6902754", "6902755", "6902808", "6902868", "6902910",
    "6902912",
}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    index = []
    n_written = 0

    for path in sorted(glob.glob(SRC_GLOB)):
        with nc.Dataset(path) as d:
            if not hasattr(d, "float_id"):
                continue
            fid = str(int(d.float_id))
            if fid not in SITE_FLOAT_IDS:
                continue

            lat, lon = float(d.fixed_lat), float(d.fixed_lon)
            # target_depths_m is stored as a stringified list ("[20.0, 50.0]"); every
            # file in this dataset uses the same two depths, so parse it robustly.
            depths = [float(x) for x in str(d.target_depths_m).strip("[]").split(",")]
            t = d.variables["time"]
            dates = nc.num2date(t[:], t.units, calendar=getattr(t, "calendar", "standard"),
                                 only_use_cftime_datetimes=False)
            dates = [dt.strftime("%Y-%m-%d") for dt in dates]

            series = {"date": dates}
            for dep in depths:
                dep_i = int(dep)
                for var, key in (("temp", "temp"), ("salt", "salt")):
                    mvar = f"{var}_{dep_i}m"
                    ovar = f"argo_{var}_{dep_i}m"
                    if mvar in d.variables:
                        series[f"model_{key}_{dep_i}"] = _clean(d.variables[mvar][:])
                    if ovar in d.variables:
                        series[f"obs_{key}_{dep_i}"] = _clean(d.variables[ovar][:])

            payload = dict(float_id=fid, lat=lat, lon=lon, depths=depths,
                           n_days=len(dates), series=series)
            with open(os.path.join(OUT_DIR, f"{fid}.json"), "w") as f:
                json.dump(payload, f)
            index.append(dict(float_id=fid, lat=lat, lon=lon, n_days=len(dates), depths=depths))
            n_written += 1

    with open(INDEX_PATH, "w") as f:
        json.dump(index, f, indent=2)

    print(f"[OUT] wrote {n_written} per-float JSON files to {OUT_DIR}")
    print(f"[OUT] wrote {INDEX_PATH} ({len(index)} floats)")
    missing = SITE_FLOAT_IDS - {r["float_id"] for r in index}
    if missing:
        print(f"[WARN] no single-depth colocation found for: {sorted(missing)}")


def _clean(arr):
    arr = np.asarray(arr, dtype=float)
    return [None if (np.isnan(x)) else round(float(x), 4) for x in arr]


if __name__ == "__main__":
    main()
