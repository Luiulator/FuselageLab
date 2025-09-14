import numpy as np

def haack_nose(Ln, R, C=0.0, N=200):
    """Perfil Haack (LD/LV) paramétrico con longitud Ln y radio R (y(Ln)=R)."""

    theta = np.linspace(0.0, np.pi, N)

    # Definimos la parametrización de Haack
    x = 0.5 * Ln * (1 - np.cos(theta))
    y = (R/np.sqrt(np.pi)) * np.sqrt(theta - 0.5*np.sin(2*theta) + C*(np.sin(theta)**3))

    # Hay que garantizar y[0]=0 numéricamente
    y[0] = 0.0
    return x, y

def tail_cosine(Lt, R_root, R_tip=0.0, N=200, x0=0.0):
    """Cola con espaciado cosenoidal (asegura pendiente nula en raíz y punta). x0 es inicio de la cola."""

    s = np.linspace(0.0, 1.0, N)
    x = x0 + s * Lt
    
    y = R_tip + (R_root - R_tip) * 0.5 * (1.0 + np.cos(np.pi * s))

    return x, y

def max_tail_angle_deg(Lt, R_root, R_tip=0.0):

    """Ángulo máx. del boattail (aprox. ocurre en s=0.5 para ley coseno)."""
    # dy/dx|max = (0.5*pi*(R_root - R_tip)) / Lt

    tan_alpha_max = 0.5*np.pi*(R_root - R_tip)/Lt
    return np.degrees(np.arctan(tan_alpha_max)), tan_alpha_max

def min_tail_length_for_angle(alpha_deg, R_root, R_tip=0.0):

    """Longitud mínima de cola para no superar un ángulo dado (ley coseno)."""
    tan_alpha = np.tan(np.radians(alpha_deg))
    return 0.5*np.pi*(R_root - R_tip)/tan_alpha if tan_alpha > 0 else np.inf

def concat_no_duplicate(xs, ys, x_add, y_add):
    """Concatena evitando duplicar el primer punto nuevo si coincide con el último actual."""

    if xs.size > 0 and x_add.size > 0 and xs[-1] == x_add[0] and ys[-1] == y_add[0]:
        return np.concatenate([xs, x_add[1:]]), np.concatenate([ys, y_add[1:]])
    else:
        return np.concatenate([xs, x_add]), np.concatenate([ys, y_add])
    
def build_fuselage(cfg_geom: dict, cfg_builder: dict):
    """
    Devuelve un dict con {x, y, L, R, l, d, ld, ...} usando tus funciones existentes.
    """
    l = float(cfg_geom["l"]); d = float(cfg_geom["d"]); R = d/2.0
    Ln_frac = cfg_builder["Ln_frac"]; Lt_frac = cfg_builder["Lt_frac"]
    C_haack = cfg_builder["C_haack"]; Nn = cfg_builder["Nn"]
    r_tip = cfg_builder["r_tip"]; Nt = cfg_builder["Nt"]
    enforce = cfg_builder["enforce_tail_angle"]; alpha_max = cfg_builder["alpha_max_deg"]

    Ln = Ln_frac * l
    Lt = Lt_frac * l

    if enforce:
        Lt_min = min_tail_length_for_angle(alpha_max, R, r_tip)
        if Lt < Lt_min:
            Lt = Lt_min

    Lc = max(0.0, l - Ln - Lt)

    x_n, y_n = haack_nose(Ln, R, C=C_haack, N=Nn)
    if Lc > 0:
        x_c = np.linspace(Ln, Ln + Lc, 60); y_c = np.full_like(x_c, R)
    else:
        x_c = np.array([Ln]); y_c = np.array([R])
    x_t, y_t = tail_cosine(Lt, R_root=R, R_tip=r_tip, N=Nt, x0=Ln+Lc)

    x_prof, y_prof = np.array([]), np.array([])
    x_prof, y_prof = concat_no_duplicate(x_prof, y_prof, x_n, y_n)
    x_prof, y_prof = concat_no_duplicate(x_prof, y_prof, x_c, y_c)
    x_prof, y_prof = concat_no_duplicate(x_prof, y_prof, x_t, y_t)

    return {
        "x": x_prof, "y": y_prof,
        "L": l, "R": R, "l": l, "d": d, "ld": l/d,
        "Ln": Ln, "Lc": Lc, "Lt": Lt, "r_tip": r_tip
    }
