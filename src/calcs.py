import numpy as np

def cf_laminar(ReL: float) -> float:
    """Cf laminar promedio en placa: Cf ≈ 1.328 / sqrt(Re_L)."""

    if ReL <= 0: return np.nan
    return 1.328 / np.sqrt(ReL)

def cf_turb_ittc(ReL: float) -> float:
    """Cf turbulento liso (ITTC/Hoerner): 0.455/(log10 Re)^2.58 - 1700/Re."""
    if ReL <= 0: return np.nan
    val = 0.455 / (np.log10(ReL)**2.58) - 1700.0/ReL
    return max(val, 0.0)

def cf_transition_hoerner(ReL: float, k: float = 1700.0) -> float:
    """Corrección de transición de Hoerner: Cf ≈ Cf_turb - k/sqrt(ReL)."""
    if ReL <= 0: return np.nan
    val = cf_turb_ittc(ReL) - k/np.sqrt(ReL)
    return max(val, 0.0)

def hoerner_factor_frontal(l_over_d: float) -> float:
    """Factor F tal que CD_frontal = Cf * F (Hoerner, sobre área frontal)."""
    d_over_l = 1.0 / l_over_d
    return 3.0*l_over_d + 4.5*np.sqrt(d_over_l) + 21.0*(d_over_l**2)

def delta_cd_base(dB_over_d: float) -> float:
    """Incremento de CD_frontal por base plana: ΔCD ≈ 0.029 * (dB/d)^2."""
    return 0.029 * (dB_over_d**2)

def s_wet_approx(l: float, d: float) -> float:
    """Área mojada aproximada de cuerpo de revolución: S_wet ≈ 0.75 π d l."""
    return 0.75*np.pi*d*l

def areas(l: float, d: float):
    S_frontal = 0.25*np.pi*d**2
    S_wet = s_wet_approx(l, d)
    return S_frontal, S_wet

def aero_from_geometry(geom: dict, op: dict, cf_model: dict) -> dict:
    l = float(geom["l"]); d = float(geom["d"])
    V = float(op["V"]); rho = float(op["rho"]); nu = float(op["nu"])
    mode = cf_model["mode"]; k_transition = cf_model["k_transition"]; k3d = cf_model["threeD_correction"]
    ReL = V*l/nu

    if mode == "laminar":
        Cf = cf_laminar(ReL)
    elif mode == "transition":
        Cf = cf_transition_hoerner(ReL, k_transition)
    else:
        Cf = cf_turb_ittc(ReL)

    Cf_eff = Cf * k3d
    F = hoerner_factor_frontal(l/d)
    CD_clean = Cf_eff * F
    CD_base = delta_cd_base(op.get("base_ratio", 0.0)) if op.get("base_ratio", 0.0) > 0 else 0.0
    CD_total = CD_clean + CD_base
    S_f, S_w = areas(l, d)
    q = 0.5 * rho * V * V
    D_clean = q * CD_clean * S_f
    D_base = q * CD_base * S_f
    D_total = q * CD_total * S_f

    return {
        "ReL": ReL, "Cf": Cf, "Cf_eff": Cf_eff, "F": F,
        "CD_clean": CD_clean, "CD_base": CD_base, "CD_total": CD_total,
        "S_f": S_f, "S_w": S_w, "q": q, "D_clean": D_clean, "D_base": D_base, "D_total": D_total
    }

def geom_integrals(geom: dict, include_base: bool) -> dict:
    x = geom["x"]; y = geom["y"]
    dydx = np.gradient(y, x)
    S_lateral = 2.0*np.pi*np.trapezoid(y*np.sqrt(1.0 + dydx**2), x)
    A_base = np.pi*(y[-1]**2)
    S_total = S_lateral + (A_base if include_base else 0.0)
    V_solid = np.pi*np.trapezoid(y**2, x)
    xS_lateral = 2.0*np.pi*np.trapezoid(x*y*np.sqrt(1.0 + dydx**2), x)
    x_tail = float(x[-1]); xS_total = xS_lateral + (A_base*x_tail if include_base else 0.0)
    x_cg_surface = xS_total / S_total if S_total>0 else np.nan
    xV = np.pi*np.trapezoid(x*y**2, x)
    x_cg_volume = xV / V_solid if V_solid>0 else np.nan
    return {"S_lateral": S_lateral, "S_total": S_total, "V": V_solid,
            "x_cg_surface": x_cg_surface, "x_cg_volume": x_cg_volume}

def mass_from_surface(S_total: float, mass_cfg: dict) -> dict:
    sigma = (mass_cfg["sigma_surface"] if mass_cfg["use_surface_density"]
             else mass_cfg["rho_material"]*mass_cfg["t_skin"])
    m_shell = sigma * S_total
    W_shell = m_shell * mass_cfg["g"]
    return {"sigma": sigma, "m_shell": m_shell, "W_shell": W_shell}
