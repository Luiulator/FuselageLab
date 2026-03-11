import os
import json
import numpy as np
from . import build, calcs
from .utils import save_profile_csv, save_results_json


def run_case(cfg: dict) -> dict:
       # 1) Geometría
    geom = build.build_fuselage(cfg["geom"], cfg["builder"])   # devuelve x,y,R,L,...

    # 2) Aerodinámica
    method = cfg["builder"].get("parametrization_method", "fractions")
    if method == "tubular":
        # Pass builder config as tub_params since it contains psi, theta
        aero = calcs.aero_tubular(geom, cfg["op"], cfg["builder"])
    else:
        aero = calcs.aero_from_geometry(geom, cfg["op"], cfg["cf_model"])

    # 3) Integrales geométricas + masa
    integrals = calcs.geom_integrals(geom, cfg["mass"]["include_base_disk_area"])
    mass = calcs.mass_from_surface(integrals["S_total"], cfg["mass"])

    # 4) Exportación
    if cfg["io"]["export_csv"]:
        save_profile_csv(geom, cfg["io"]["csv_path"])

    # 5) Empaquetar resultados
    # La GUI ahora muestra gráficos 2D interactivos bajo demanda a partir del payload.

    # 6) Empaquetar resultados
    payload = {"geom": geom, "aero": aero, "integrals": integrals, "mass": mass}
    save_results_json(payload, "results/data/resultados.json")
    return payload
