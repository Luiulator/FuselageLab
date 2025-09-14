{
  "geom": {
    "l": 1.10,          // [m] fuselage total length
    "d": 0.18,          // [m] maximum fuselage diameter
    "base_ratio": 0.0   // ratio dB/d; 0 = closed tail, >0 = truncated base (e.g. 0.6 means base diameter = 0.6*d)
  },

  "op": {
    "V": 10.0,          // [m/s] flight velocity
    "rho": 1.225,       // [kg/m³] air density
    "nu": 1.5e-5        // [m²/s] kinematic viscosity of air
  },

  "cf_model": {
    "mode": "turbulent",     // "laminar", "turbulent", or "transition"
    "k_transition": 1700.0,  // Hoerner transition correction parameter (only if mode = "transition")
    "threeD_correction": 1.07 // multiplier to account for 3D effects in fuselage drag (≈1.05–1.10 typical)
  },

  "builder": {
    "Ln_frac": 0.25,        // nose length as fraction of fuselage length
    "C_haack": 0.3333333333,// Haack series parameter (0 = LD-Haack, ~1/3 = LV-Haack)
    "Nn": 200,              // number of points to discretize the nose profile

    "Lt_frac": 0.25,        // tail length as fraction of fuselage length (adjusted if angle too steep)
    "r_tip": 0.0,           // [m] tail tip radius (0 = sharp point, >0 = truncated base)
    "enforce_tail_angle": true, // if true, automatically lengthens tail to respect alpha_max_deg
    "alpha_max_deg": 13.0,  // [deg] maximum allowed tail angle
    "Nt": 200               // number of points to discretize the tail profile
  },

  "mass": {
    "use_surface_density": false, // true: use surface density σ; false: use ρ·t formulation
    "sigma_surface": 1.0,         // [kg/m²] shell surface density (if use_surface_density = true)

    "rho_material": 1250.0,       // [kg/m³] material density (if use_surface_density = false)
    "t_skin": 0.0005,             // [m] skin thickness (if use_surface_density = false)

    "include_base_disk_area": false, // if true, adds the tail base disk area to wetted surface
    "g": 9.81                     // [m/s²] gravity acceleration (for shell weight)
  },

  "io": {
    "export_csv": true,           // export fuselage profile (x,y) to CSV
    "csv_path": "results/data/fuselaje_xy.csv" // path for exported profile
  },

  "plots": {
    "make_plots": true,           // generate dashboard plot
    "dpi": 140                    // resolution of plot
  }
}
