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

# --- Tubular Fuselage Correlations ---

def cd_flat_plate_compressible(Re: float, M: float = 0.0) -> float:
    """
    C_D,fp according to provided formula:
    C_D,fp = 0.455 / ( [Log10(Re)]^2.58 * (1 + 0.144 M^2)^0.65 )
    """
    if Re <= 1.0: return 0.0 # Avoid log(0)
    
    # Calculate base term (incompressible turbulent skin friction)
    base = 0.455 / (np.log10(Re)**2.58)
    
    # Calculate compressibility factor
    comp = (1.0 + 0.144 * M**2)**0.65
    
    return base / comp

def get_Kn(FRn: float, psi: float) -> float:
    """
    Interpolates Kn from graph data (Kn vs FRn for various psi).
    Approximate ranges: FRn [1.0, 1.8], psi [38, 50].
    """
    # Clamping inputs to range
    FRn = np.clip(FRn, 1.1, 1.8)
    psi = np.clip(psi, 38.0, 50.0)
    
    # Data points approximation (FRn points: 1.1, 1.4, 1.7)
    # psi=38: 2.08, 1.80, 1.65
    # psi=44: 2.15, 1.85, 1.72
    # psi=50: 2.32, 1.95, 1.82
    
    # Base curve for psi=38
    kn_38_vals = [2.08, 1.80, 1.65]
    fr_vals = [1.1, 1.4, 1.7]
    
    # Base curve for psi=50
    kn_50_vals = [2.32, 1.95, 1.82]
    
    # Interpolate along FRn first
    kn_38 = np.interp(FRn, fr_vals, kn_38_vals)
    kn_50 = np.interp(FRn, fr_vals, kn_50_vals)
    
    # Interpolate along psi
    # Mapping psi [38, 50] to [0, 1]
    t = (psi - 38.0) / (50.0 - 38.0)
    return kn_38 + t * (kn_50 - kn_38)

def get_Kc(FR_total: float) -> float:
    """
    Interpolates Kc from graph data (Kc vs FR_total).
    Approximate range: FR [7, 12].
    """
    FR = np.clip(FR_total, 7.0, 12.0)
    
    # Data points approx:
    # FR=7: 1.22
    # FR=8: 1.12
    # FR=9: 1.05
    # FR=10: 1.02
    # FR=11: 1.00
    # FR=12: 1.00
    
    x_vals = [7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
    y_vals = [1.22, 1.12, 1.05, 1.02, 1.00, 1.00]
    
    return np.interp(FR, x_vals, y_vals)

def get_Kt(FRt: float, theta: float) -> float:
    """
    Interpolates Kt from graph data (Kt vs FRt for various theta).
    Approximate range: FRt [2.2, 3.2], theta [10, 18].
    """
    FRt = np.clip(FRt, 2.2, 3.2)
    theta = np.clip(theta, 10.0, 18.0)
    
    # Data points approx (FRt points: 2.2, 2.7, 3.2)
    # theta=10: 0.70, 0.72, 0.75
    # theta=18: 1.05, 1.28, 1.50
    
    kt_10_vals = [0.70, 0.72, 0.75]
    kt_18_vals = [1.05, 1.28, 1.50]
    fr_vals = [2.2, 2.7, 3.2]
    
    kt_10 = np.interp(FRt, fr_vals, kt_10_vals)
    kt_18 = np.interp(FRt, fr_vals, kt_18_vals)
    
    t = (theta - 10.0) / (18.0 - 10.0)
    return kt_10 + t * (kt_18 - kt_10)

def aero_tubular(geom: dict, op: dict, tub_params: dict) -> dict:
    """
    Calculates drag using the specific tubular fuselage correlations.
    """
    l = geom["l"]
    d = geom["d"]
    
    # Retrieve pre-calculated areas if available, or error out/approximate?
    # The build process MUST now return these.
    S_wet_nose = geom.get("S_wet_nose", 0.0)
    S_wet_cabin = geom.get("S_wet_cabin", 0.0)
    S_wet_tail = geom.get("S_wet_tail", 0.0)
    S_wet_total = S_wet_nose + S_wet_cabin + S_wet_tail
    
    # Frontal area
    S_front = 0.25 * np.pi * d**2
    
    if S_front <= 0 or S_wet_total <= 0:
        return {"CD_fus": 0.0, "Drag": 0.0}

    # Flow parameters
    V = float(op["V"])
    nu = float(op["nu"])
    rho = float(op["rho"])
    M = float(op.get("Mach", 0.0))
    
    Re_L = V * l / nu
    
    # C_D,fp
    CD_fp = cd_flat_plate_compressible(Re_L, M)
    
    # Geometric parameters for correlations
    Ln = geom.get("Ln", 0.0)
    Lt = geom.get("Lt", 0.0)
    
    FRn = Ln / d if d > 0 else 0
    FRt = Lt / d if d > 0 else 0
    FR = l / d if d > 0 else 0
    
    psi = float(tub_params.get("psi", 40.0))
    theta = float(tub_params.get("theta", 15.0))
    
    Kn = get_Kn(FRn, psi)
    Kc = get_Kc(FR)
    Kt = get_Kt(FRt, theta)
    
    # Formula:
    # CD_fus = CD_fp * (Swet/Sfront) * (Kn*Swet_n/Swet + Kc*Swet_c/Swet + Kt*Swet_t/Swet)
    
    term_nose = Kn * (S_wet_nose / S_wet_total)
    term_cabin = Kc * (S_wet_cabin / S_wet_total)
    term_tail = Kt * (S_wet_tail / S_wet_total)
    
    CD_fus = CD_fp * (S_wet_total / S_front) * (term_nose + term_cabin + term_tail)
    
    q = 0.5 * rho * V**2
    Drag = q * CD_fus * S_front
    
    return {
        "ReL": Re_L, "Mach": M,
        "CD_fp": CD_fp,
        "Kn": Kn, "Kc": Kc, "Kt": Kt,
        "S_wet_nose": S_wet_nose, "S_wet_cabin": S_wet_cabin, "S_wet_tail": S_wet_tail,
        "CD_fus": CD_fus, "Drag": Drag,
        "S_front": S_front, "S_wet": S_wet_total, "q": q
    }
