import numpy as np

def hermite_spline(x, p0, p1, m0, m1, L):
    """Cubic Hermite Spline between 0 and L."""
    t = x / L
    h00 = 2*t**3 - 3*t**2 + 1
    h10 = t**3 - 2*t**2 + t
    h01 = -2*t**3 + 3*t**2
    h11 = t**3 - t**2
    return h00*p0 + h10*L*m0 + h01*p1 + h11*L*m1

def simple_transport_nose(Ln, R, psi_deg, hw=0.0, bluntness=0.2, N=200):
    """
    Simplified asymmetric nose profile with filleted tip control.
    Bluntness Bn controls the rounding of the tip (0 = sharp, 1 = full fillet).
    """
    x = np.linspace(0.0, Ln, N)
    s = x / Ln
    
    # Anchor Tip (hw limited to cabin height)
    hw = np.clip(hw, -0.95 * R, 0.95 * R)
    
    
    # Shape exponent p: controls bluntness
    # p=1.0 (Bn=0) -> Sharp (Parabolic-like)
    # p=0.5 (Bn=1) -> Round (Elliptic/Radome)
    # p<0.5 (Bn>1) -> Super-blunt (Squarish)
    # Mapping: p = 1 / (1 + Bn)
    p = 1.0 / (1.0 + max(0.0, bluntness))
    
    # Normalized shape profile F(s)
    # F(0)=0, F(1)=1, F'(1)=0
    # F'(0) is finite if p=1, infinite if p=0.5
    f = (s**p) * ((p + 1.0) - p * s)
    
    # Boundary profiles
    z_up = hw + (R - hw) * f
    z_low = hw - (R + hw) * f
    y = R * f
    
    # Derive z_off and y (radius)
    z_off = (z_up + z_low) / 2.0
    # Using the same f for y ensures radial consistency (no bulge > R)
    
    return x, y, z_off

def transport_tail_profile(Lt, R_root, theta_deg, hu=0.0, R_tip=0.0, N=200, x0=0.0):
    """
    Tapered tail with upsweep at angle theta_deg and tip radius R_tip.
    Returns x, y (radius), and z_off (vertical offset).
    Strictly constrained to stay within the cabin's radial footprint (R_root).
    """
    s = np.linspace(0.0, 1.0, N)
    x = x0 + s * Lt
    
    # Radius profile with closure control
    # Smooth transition from R_root to R_tip
    # Using cosine shape for best surface finish or power law? 
    # Let's use a robust power-law blending:
    # y = R_tip + (R_root - R_tip) * (1 - s^1.5)
    y = R_tip + (R_root - R_tip) * (1.0 - s**1.5)
    
    # Upsweep (Z offset) logic
    # hu is the final vertical offset of the tip center.
    # We clip hu + R_tip to not exceed R_root (radial constraint)
    # i.e., top of tail tip (z_tip + y_tip) <= R_root and bottom >= -R_root
    max_hu = R_root - R_tip
    hu = np.clip(hu, -max_hu, max_hu)
    
    z_tip = hu if hu != 0 else Lt * np.tan(np.radians(theta_deg))
    
    # Recalculate z_tip clipping if derived from theta?
    # Let's invoke strict constraint on the final offset:
    z_tip = np.clip(z_tip, -max_hu, max_hu)

    # Smooth z_offset curve
    b_term = Lt * np.tan(np.radians(theta_deg))
    a_term = z_tip - b_term
    z_off = a_term * (s**2) + b_term * s
    
    return x, y, z_off

def haack_nose(Ln, R, C=0.333, N=200):
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
    
def surface_area_revolution(x, y):
    """Calcula área mojada de una superficie de revolución dada por x, y."""
    if len(x) < 2: return 0.0
    dydx = np.gradient(y, x)
    # S = 2*pi * integral(y * sqrt(1 + y'^2) dx)
    return 2.0 * np.pi * np.trapezoid(y * np.sqrt(1.0 + dydx**2), x)

def build_fuselage(cfg_geom: dict, cfg_builder: dict):
    """
    Devuelve un dict con {x, y, L, R, l, d, ld, ...} usando tus funciones existentes.
    Soporta modo 'fractions' (clásico) o 'tubular' (parametrización explícita tubular).
    """
    # Common base param
    d = float(cfg_geom["d"])
    R = d/2.0
    
    # Check if we should use Tubular parametrization (explicit lengths/FR)
    # or the classic relative (fractional) one.
    # We detect this by checking if specific keys are provided in cfg_builder 
    # or a "parametrization_method" flag. For now, let's assume if "use_tubular" is true
    # or if we have "FRn" keys. But let's look for "parametrization_method".
    
    method = cfg_builder.get("parametrization_method", "fractions")
    
    if method == "tubular":
        # New explicit lengths
        Ln = float(cfg_builder.get("Ln", 0.5))
        Lt = float(cfg_builder.get("Lt", 0.5))
        Lc = float(cfg_builder.get("Lc", 0.5))
        
        hw = float(cfg_builder.get("hw", 0.1))
        hu = float(cfg_builder.get("hu", 0.1))
        psi = float(cfg_builder.get("psi", 45.0))
        theta = float(cfg_builder.get("theta", 12.0))
        
        l = Ln + Lc + Lt
    else:
        # Classic mode
        l = float(cfg_geom["l"])
        Ln_frac = float(cfg_builder.get("Ln_frac", 0.2))
        Lt_frac = float(cfg_builder.get("Lt_frac", 0.3))
        enforce = cfg_builder.get("enforce_tail_angle", True)
        alpha_max = float(cfg_builder.get("alpha_max_deg", 15.0))
        
        r_tip = float(cfg_builder.get("r_tip", 0.0))

        Ln = Ln_frac * l
        Lt = Lt_frac * l

        if enforce:
            Lt_min = min_tail_length_for_angle(alpha_max, R, r_tip)
            if Lt < Lt_min:
                Lt = Lt_min

        Lc = max(0.0, l - Ln - Lt)
    
    # Common generation properties
    C_haack = float(cfg_builder.get("C_haack", 0.0))
    Nn = int(cfg_builder.get("Nn", 40))
    Nt = int(cfg_builder.get("Nt", 40))
    r_tip = float(cfg_builder.get("r_tip", 0.0))
    
    # Read/Default new parameters for BOTH modes
    psi = float(cfg_builder.get("psi", 45.0)) # Entry angle
    theta = float(cfg_builder.get("theta", 12.0)) # Upsweep angle
    hw = float(cfg_builder.get("hw", 0.0))      # Nose offset
    hu = float(cfg_builder.get("hu", 0.1))      # Tail offset
    # Reuse 'rn' from tubular as Bluntness for Simple Nose
    # Fractional UI will write to 'rn' or we need a new key? 
    # Let's check config usage. config_form binds to 'rn'.
    bluntness = float(cfg_builder.get("rn", 0.2)) 
    
    nose_type = cfg_builder.get("nose_type", "Haack") # "Haack" or "Simple"

    # Generate Nose Segments
    if method == "tubular":
        # Tubular uses Simple Nose by default (since double nose replacement)
        x_n, y_n, z_n = simple_transport_nose(Ln, R, psi, hw=hw, bluntness=bluntness, N=Nn)
    else:
        # Fractional mode can choose
        if nose_type == "Simple":
            x_n, y_n, z_n = simple_transport_nose(Ln, R, psi, hw=hw, bluntness=bluntness, N=Nn)
        else:
            x_n, y_n = haack_nose(Ln, R, C=C_haack, N=Nn)
            z_n = np.zeros_like(x_n) # Haack is symmetric (no offset supported currently)
    
    if Lc > 1e-6:
        x_c = np.linspace(Ln, Ln + Lc, 40)
        y_c = np.full_like(x_c, R)
        z_c = np.zeros_like(x_c)
    else:
        x_c = np.array([Ln])
        y_c = np.array([R])
        z_c = np.array([0.0])
        
    # Generate Tail Segments
    # Use transport_tail_profile for both modes to support hu, theta, and R_tip
    # For fractional, Ln+Lc is the start.
    x_t, y_t, z_t = transport_tail_profile(Lt, R, theta, hu=hu, R_tip=r_tip, N=Nt, x0=Ln+Lc)

    # Concatenate
    x_prof, y_prof = np.array([]), np.array([])
    z_prof = np.array([])
    
    # Custom concat for z_offset
    def concat_3(xs, ys, zs, x_add, y_add, z_add):
        if xs.size > 0 and x_add.size > 0 and xs[-1] == x_add[0]:
             return np.concatenate([xs, x_add[1:]]), np.concatenate([ys, y_add[1:]]), np.concatenate([zs, z_add[1:]])
        return np.concatenate([xs, x_add]), np.concatenate([ys, y_add]), np.concatenate([zs, z_add])

    x_prof, y_prof, z_prof = concat_3(x_prof, y_prof, z_prof, x_n, y_n, z_n)
    x_prof, y_prof, z_prof = concat_3(x_prof, y_prof, z_prof, x_c, y_c, z_c)
    x_prof, y_prof, z_prof = concat_3(x_prof, y_prof, z_prof, x_t, y_t, z_t)

    # Calculate wetted areas for components
    S_wet_nose = surface_area_revolution(x_n, y_n)
    # Cylinder area is simple: 2*pi*R*Lc
    S_wet_cabin = 2.0 * np.pi * R * Lc if Lc > 0 else 0.0
    S_wet_tail = surface_area_revolution(x_t, y_t)

    return {
        "x": x_prof, "y": y_prof, "z_offset": z_prof,
        "L": l, "R": R, "l": l, "d": d, "ld": l/d if d>0 else 0,
        "Ln": Ln, "Lc": Lc, "Lt": Lt, "r_tip": r_tip,
        "S_wet_nose": S_wet_nose,
        "S_wet_cabin": S_wet_cabin,
        "S_wet_tail": S_wet_tail
    }
