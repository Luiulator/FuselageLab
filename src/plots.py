import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from . import calcs

def dashboard(geom, aero, A_x, dA_dx, dpi=140, outdir="results/figs"):
    """
    geom: {"x": np.ndarray, "y": np.ndarray, "L": float, "R": float, "l": float, "d": float, "ld": float, ...}
    aero: {"Cf_eff": float, ...}
    """
    os.makedirs(outdir, exist_ok=True)

    x_prof = geom["x"]; y_prof = geom["y"]
    l = geom["l"]; d = geom["d"]; ld = geom["ld"]
    Cf_eff = aero["Cf_eff"]

    ld_grid = np.linspace(1.0, 10.0, 400)
    F_grid  = calcs.hoerner_factor_frontal(ld_grid)
    CD_grid = Cf_eff * F_grid

    fig = plt.figure(figsize=(12, 9), dpi=dpi)
    gs  = GridSpec(nrows=2, ncols=2, height_ratios=[1, 1.25], width_ratios=[1, 1],
                   hspace=0.4, wspace=0.30)

    ax_drag = fig.add_subplot(gs[0, 0])
    ax_drag.plot(ld_grid, CD_grid, lw=1.8)
    ax_drag.axvline(ld, linestyle="--", lw=1.0)
    ax_drag.set_xlabel("l/d"); ax_drag.set_ylabel(r"$C_D$ (área frontal)")
    ax_drag.set_title(r"$C_D$ vs thinness ratio (Hoerner)"); ax_drag.grid(True, alpha=0.3)

    gs_right = gs[0, 1].subgridspec(nrows=2, ncols=1, hspace=0.12)
    ax_area = fig.add_subplot(gs_right[0, 0]); ax_area.plot(x_prof, A_x, lw=1.8)
    ax_area.set_ylabel(r"$A(x)$ [m$^2$]"); ax_area.set_title("A(x)"); ax_area.grid(True, alpha=0.3)
    ax_dadx = fig.add_subplot(gs_right[1, 0], sharex=ax_area); ax_dadx.plot(x_prof, dA_dx, lw=1.8)
    ax_dadx.axhline(0, lw=0.8, linestyle="--"); ax_dadx.set_xlabel("x [m]")
    ax_dadx.set_ylabel(r"$\mathrm{d}A/\mathrm{d}x$ [m]"); ax_dadx.set_title("dA/dx"); ax_dadx.grid(True, alpha=0.3)

    ax_prof = fig.add_subplot(gs[1, :])
    ax_prof.plot(x_prof,  y_prof,  lw=2.0, label="+y")
    ax_prof.plot(x_prof, -y_prof,  lw=1.2, linestyle="--", label="−y")
    ax_prof.set_aspect("equal", adjustable="box")
    ax_prof.set_xlabel("x [m]"); ax_prof.set_ylabel("y [m]")
    ax_prof.set_title("Perfil del fuselaje (meridiano)"); ax_prof.grid(True, alpha=0.3); ax_prof.legend()

    fig.suptitle(f"Dashboard | L={l:.3f} m, D={d:.3f} m, l/d={ld:.2f} | Cf_eff={Cf_eff:.4f}", y=0.98, fontsize=12)
    figpath = os.path.join(outdir, "dashboard.png")
    fig.savefig(figpath, dpi=dpi)
    print(f"[OK] Figura: {figpath}")
    # plt.show()
