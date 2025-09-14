import os
import json
import numpy as np
from . import build, calcs, plots
from .utils import save_profile_csv, save_results_json


def run_case(cfg: dict) -> dict:
       # 1) Geometría
    geom = build.build_fuselage(cfg["geom"], cfg["builder"])   # devuelve x,y,R,L,...

    # 2) Aerodinámica
    aero = calcs.aero_from_geometry(geom, cfg["op"], cfg["cf_model"])

    # 3) Integrales geométricas + masa
    integrals = calcs.geom_integrals(geom, cfg["mass"]["include_base_disk_area"])
    mass = calcs.mass_from_surface(integrals["S_total"], cfg["mass"])

    # 4) Exportación
    if cfg["io"]["export_csv"]:
        save_profile_csv(geom, cfg["io"]["csv_path"])

    # 5) Gráficas (dashboard eliminado para interfaz en vivo en la GUI)
    # Se deja de generar la figura de "dashboard" en disco. La GUI ahora
    # muestra gráficos 2D interactivos bajo demanda.

    # 6) Empaquetar resultados
    payload = {"geom": geom, "aero": aero, "integrals": integrals, "mass": mass}
    save_results_json(payload, "results/data/resultados.json")
    return payload
