# src/configio.py
from __future__ import annotations
import json
import os

_DEF = {
    "geom": {
        "l": 37.5,
        "d": 4.0,
        "base_ratio": 0.0
    },
    "op": {
        "V": 10.0,
        "rho": 1.225,
        "nu": 1.5e-5
    },
    "cf_model": {
        "mode": "turbulent",           # "laminar" | "transition" | "turbulent"
        "k_transition": 1700.0,
        "threeD_correction": 1.07
    },
    "builder": {
        "Ln_frac": 0.25,
        "C_haack": 1.0/3.0,
        "Nn": 200,
        "Lt_frac": 0.25,
        "r_tip": 0.0,
        "enforce_tail_angle": True,
        "alpha_max_deg": 13.0,
        "Nt": 200,
        "FRn": 1.5,
        "FRt": 2.5,
        "Lc": 22.0,
        "Ln": 6.0,
        "Lt": 9.5,
        "hw": -0.4,
        "hu": 1.8,
        "rn": 0.1,
        "use_double_nose": True,
        "psi": 40.0,
        "theta": 15.0,
        "nose_type": "Haack",
        "parametrization_method": "tubular"
    },
    "mass": {
        "use_surface_density": False,
        "sigma_surface": 1.0,
        "rho_material": 1250.0,
        "t_skin": 0.0005,
        "include_base_disk_area": False,
        "g": 9.81
    },
    "io": {
        "export_csv": True,
        "csv_path": "results/data/fuselaje_xy.csv"
    }
}

def _deep_default(dst: dict, src: dict) -> dict:
    """Rellena dst con defaults de src sin machacar valores ya presentes."""
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
        else:
            if isinstance(v, dict) and isinstance(dst[k], dict):
                _deep_default(dst[k], v)
    return dst

def _validate(cfg: dict) -> None:
    # Geometría
    l = cfg["geom"]["l"]; d = cfg["geom"]["d"]
    if not (isinstance(l, (int, float)) and l > 0): raise ValueError("geom.l debe ser > 0")
    if not (isinstance(d, (int, float)) and d > 0): raise ValueError("geom.d debe ser > 0")
    if not (cfg["geom"]["base_ratio"] >= 0.0): raise ValueError("geom.base_ratio debe ser ≥ 0")

    # Operación
    V = cfg["op"]["V"]; rho = cfg["op"]["rho"]; nu = cfg["op"]["nu"]
    if V <= 0:  raise ValueError("op.V debe ser > 0")
    if rho <= 0: raise ValueError("op.rho debe ser > 0")
    if nu <= 0:  raise ValueError("op.nu debe ser > 0")

    # Cf model
    mode = cfg["cf_model"]["mode"]
    if mode not in ("laminar", "transition", "turbulent"):
        raise ValueError("cf_model.mode debe ser 'laminar' | 'transition' | 'turbulent'")
    if cfg["cf_model"]["threeD_correction"] <= 0.0:
        raise ValueError("cf_model.threeD_correction debe ser > 0")

    # Builder
    if not (0 < cfg["builder"]["Ln_frac"] < 1): raise ValueError("builder.Ln_frac en (0,1)")
    if not (0 < cfg["builder"]["Lt_frac"] < 1): raise ValueError("builder.Lt_frac en (0,1)")
    if cfg["builder"]["Nn"] < 10 or cfg["builder"]["Nt"] < 10:
        raise ValueError("Nn/Nt deben ser ≥ 10")
    if cfg["builder"]["alpha_max_deg"] <= 0:
        raise ValueError("alpha_max_deg debe ser > 0")
    
    # Tubular checks
    if cfg["builder"].get("FRn", 0) <= 0: cfg["builder"]["FRn"] = 1.5
    if cfg["builder"].get("FRt", 0) <= 0: cfg["builder"]["FRt"] = 2.5
    if cfg["builder"].get("Ln", 0) <= 0:  cfg["builder"]["Ln"] = 0.5
    if cfg["builder"].get("Lt", 0) <= 0:  cfg["builder"]["Lt"] = 0.5
    if cfg["builder"].get("Lc", 0) < 0:   cfg["builder"]["Lc"] = 0.5
    if cfg["builder"].get("hw", -1e6) == -1e6: cfg["builder"]["hw"] = 0.1
    if cfg["builder"].get("hu", -1e6) == -1e6: cfg["builder"]["hu"] = 0.1
    if cfg["builder"].get("rn", -1) < 0: cfg["builder"]["rn"] = 0.1
    if "use_double_nose" not in cfg["builder"]: cfg["builder"]["use_double_nose"] = False
    if cfg["builder"].get("psi", 0) < 10: cfg["builder"]["psi"] = 45.0
    if cfg["builder"].get("theta", -1) < 0: cfg["builder"]["theta"] = 12.0

    # Mass
    if cfg["mass"]["use_surface_density"]:
        if cfg["mass"]["sigma_surface"] <= 0: raise ValueError("sigma_surface debe ser > 0")
    else:
        if cfg["mass"]["rho_material"] <= 0 or cfg["mass"]["t_skin"] <= 0:
            raise ValueError("rho_material y t_skin deben ser > 0")
    if cfg["mass"]["g"] <= 0: raise ValueError("g debe ser > 0")


def _ensure_dirs(cfg: dict) -> None:
    os.makedirs("results/data", exist_ok=True)
    # Normaliza csv_path a results/data si sólo dieron un nombre
    csv_path = cfg["io"]["csv_path"]
    if not os.path.isabs(csv_path) and not csv_path.startswith("results/"):
        cfg["io"]["csv_path"] = os.path.join("results", "data", csv_path)

def load_config(path: str = "config.json") -> dict:
    with open(path, "r") as f:
        cfg = json.load(f)
    _deep_default(cfg, _DEF)
    # Arrastra base_ratio (puede vivir en geom o op según tu historia)
    cfg["op"]["base_ratio"] = cfg["geom"].get("base_ratio", cfg["op"].get("base_ratio", 0.0))
    _validate(cfg)
    _ensure_dirs(cfg)
    return cfg
