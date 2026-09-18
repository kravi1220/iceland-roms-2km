#!/usr/bin/env python3
"""
Convert the full-depth ROMS-vs-Argo colocation NetCDFs
(roms_at_argo/roms_at_argo_<WMO_ID>.nc: time x depth arrays of model/observed
temperature & salinity) into one JSON per float for the interactive depth
profile view: a "fill" plot (mean/min/max envelope across all colocated
profiles) and a "single profile" view (pick one profile date).
"""
import glob
import json
import os

import netCDF4 as nc
import numpy as np

SRC_GLOB = "/Volumes/Expansion/MFRI_Work/roms_at_argo/roms_at_argo_*.nc"
OUT_DIR = "/Volumes/Expansion/MFRI_Work/iceland-roms-2km/data/argo_profiles"

SITE_FLOAT_IDS = {
    "3901851", "3901988", "4902117", "4902119", "5903392", "5903395", "5904173",
    "5904176", "6900429", "6901129", "6901167", "6901169", "6901170", "6901176",
    "6901190", "6901191", "6901194", "6901201", "6901208", "6901564", "6901566",
    "6901724", "6901752", "6901910", "6901921", "6901923", "6902694", "6902726",
    "6902728", "6902730", "6902754", "6902755", "6902808", "6902868", "6902910",
    "6902912",
}


def _clean(arr):
    arr = np.asarray(arr, dtype=float)
    return [None if np.isnan(x) else round(float(x), 4) for x in arr]


def _clean2d(arr):
    return [_clean(row) for row in np.asarray(arr, dtype=float)]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    n_written = 0
    for path in sorted(glob.glob(SRC_GLOB)):
        fid = path.rsplit("_", 1)[-1].replace(".nc", "")
        if fid not in SITE_FLOAT_IDS:
            continue

        with nc.Dataset(path) as d:
            depth = np.asarray(d.variables["depth"][:], dtype=float)
            t = d.variables["time"]
            dates = nc.num2date(t[:], t.units, calendar=getattr(t, "calendar", "standard"),
                                 only_use_cftime_datetimes=False)
            dates = [dt.strftime("%Y-%m-%d") for dt in dates]

            model_temp = np.asarray(d.variables["temp"][:], dtype=float)
            obs_temp = np.asarray(d.variables["argo_temp"][:], dtype=float)
            model_salt = np.asarray(d.variables["salt"][:], dtype=float)
            obs_salt = np.asarray(d.variables["argo_salt"][:], dtype=float)
            bathy = float(d.roms_bathymetry_m) if hasattr(d, "roms_bathymetry_m") else None

        def stats(arr):
            with np.errstate(all="ignore"):
                return dict(mean=_clean(np.nanmean(arr, axis=0)),
                            min=_clean(np.nanmin(arr, axis=0)),
                            max=_clean(np.nanmax(arr, axis=0)))

        payload = dict(
            float_id=fid,
            depth=_clean(depth),
            dates=dates,
            n_profiles=len(dates),
            bathymetry_m=bathy,
            profiles=dict(
                model_temp=_clean2d(model_temp), obs_temp=_clean2d(obs_temp),
                model_salt=_clean2d(model_salt), obs_salt=_clean2d(obs_salt),
            ),
            stats=dict(
                model_temp=stats(model_temp), obs_temp=stats(obs_temp),
                model_salt=stats(model_salt), obs_salt=stats(obs_salt),
            ),
        )
        with open(os.path.join(OUT_DIR, f"{fid}.json"), "w") as f:
            json.dump(payload, f)
        n_written += 1

    print(f"[OUT] wrote {n_written} profile JSON files to {OUT_DIR}")
    missing = SITE_FLOAT_IDS - {p.rsplit("_", 1)[-1].replace(".nc", "")
                                 for p in glob.glob(SRC_GLOB)}
    if missing:
        print(f"[WARN] no full-depth colocation found for: {sorted(missing)}")


if __name__ == "__main__":
    main()
