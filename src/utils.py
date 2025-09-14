# src/utils.py
from __future__ import annotations
import json
import os
from datetime import datetime
import struct
from typing import Tuple
import numpy as np

def _default_np(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    return str(o)

def save_profile_csv(geom: dict, path: str) -> None:
    """Guarda columnas x,y en CSV (perfil superior)."""
    x = np.asarray(geom["x"]); y = np.asarray(geom["y"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    header = "x_m,y_m  # Perfil superior (revolución eje x)."
    np.savetxt(path, np.column_stack([x, y]), delimiter=",", header=header, comments="")
    print(f"[OK] CSV perfil: {path}")

def save_results_json(payload: dict, path: str, pretty: bool = True) -> None:
    """Guarda resultados en JSON (compatible con numpy)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        if pretty:
            json.dump(payload, f, indent=2, default=_default_np)
        else:
            json.dump(payload, f, separators=(",", ":"), default=_default_np)
    print(f"[OK] JSON resultados: {path}")

def stamp_name(basename: str, suffix: str = "", ext: str = "") -> str:
    """Devuelve nombre con timestamp: foo_2025-09-06_121530Z[_suffix].ext"""
    ts = datetime.utcnow().strftime("%Y-%m-%d_%H%M%SZ")
    name = f"{basename}_{ts}"
    if suffix:
        name += f"_{suffix}"
    if ext and not ext.startswith("."):
        ext = "." + ext
    return name + ext

# --- STL / mesh utilities ---

def revolve_profile_to_mesh(x: np.ndarray, r: np.ndarray, n_theta: int = 128) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create a triangular surface mesh by revolving the profile (x, r) around the x-axis.

    Returns (V, F):
    - V: float64 array (N, 3) of vertices
    - F: int32 array (M, 3) of triangle vertex indices
    """
    x = np.asarray(x, dtype=float)
    r = np.asarray(r, dtype=float)
    if x.ndim != 1 or r.ndim != 1 or x.size != r.size or x.size < 2:
        raise ValueError("revolve_profile_to_mesh: x and r must be 1D arrays with same length >= 2")
    if n_theta < 3:
        raise ValueError("revolve_profile_to_mesh: n_theta must be >= 3")

    theta = np.linspace(0.0, 2.0*np.pi, num=n_theta, endpoint=False)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    n_ax = x.size
    n_ang = n_theta

    # Build grid vertices
    V = np.empty((n_ax * n_ang, 3), dtype=float)
    idx = 0
    for i in range(n_ax):
        xi = float(x[i])
        ri = float(r[i])
        V[idx:idx+n_ang, 0] = xi
        V[idx:idx+n_ang, 1] = ri * cos_t
        V[idx:idx+n_ang, 2] = ri * sin_t
        idx += n_ang

    # Triangles (two per quad), wrap around in angular direction
    def vid(i: int, j: int) -> int:
        return i * n_ang + j

    faces = []
    for i in range(n_ax - 1):
        for j in range(n_ang):
            jn = (j + 1) % n_ang
            p0 = vid(i, j)
            p1 = vid(i + 1, j)
            p2 = vid(i + 1, jn)
            p3 = vid(i, jn)
            # Consistent winding
            faces.append((p0, p1, p2))
            faces.append((p0, p2, p3))

    F = np.asarray(faces, dtype=np.int32)
    return V, F


def _facet_normals(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    """Compute per-facet normals (unnormalized)."""
    v0 = V[F[:, 0], :]
    v1 = V[F[:, 1], :]
    v2 = V[F[:, 2], :]
    n = np.cross(v1 - v0, v2 - v0)
    # Normalize safely; zero-area facets get zero normal
    lens = np.linalg.norm(n, axis=1)
    nz = lens > 0
    n_norm = np.zeros_like(n)
    n_norm[nz] = n[nz] / lens[nz][:, None]
    return n_norm


def save_stl_ascii(path: str, V: np.ndarray, F: np.ndarray, solid_name: str = "fuselage") -> None:
    """Write an ASCII STL file from vertices and triangle indices."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    N = _facet_normals(V, F)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"solid {solid_name}\n")
        for (i0, i1, i2), (nx, ny, nz) in zip(F, N):
            f.write(f"  facet normal {nx:.6e} {ny:.6e} {nz:.6e}\n")
            f.write("    outer loop\n")
            x0, y0, z0 = V[i0]
            x1, y1, z1 = V[i1]
            x2, y2, z2 = V[i2]
            f.write(f"      vertex {x0:.6e} {y0:.6e} {z0:.6e}\n")
            f.write(f"      vertex {x1:.6e} {y1:.6e} {z1:.6e}\n")
            f.write(f"      vertex {x2:.6e} {y2:.6e} {z2:.6e}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write(f"endsolid {solid_name}\n")


def save_stl_binary(path: str, V: np.ndarray, F: np.ndarray, solid_name: str = "fuselage") -> None:
    """Write a binary STL file from vertices and triangle indices (little-endian)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    N = _facet_normals(V, F)
    header = (solid_name[:79]).ljust(80, " ").encode("ascii", errors="ignore")
    tri_count = F.shape[0]
    with open(path, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", tri_count))
        for (i0, i1, i2), (nx, ny, nz) in zip(F, N):
            # normal + v0 + v1 + v2 + attribute count
            rec = struct.pack(
                "<12fH",
                float(nx), float(ny), float(nz),
                float(V[i0, 0]), float(V[i0, 1]), float(V[i0, 2]),
                float(V[i1, 0]), float(V[i1, 1]), float(V[i1, 2]),
                float(V[i2, 0]), float(V[i2, 1]), float(V[i2, 2]),
                0,
            )
            f.write(rec)


def export_fuselage_stl(geom: dict, path: str, ascii: bool = True, n_theta: int = 128, name: str = "fuselage") -> None:
    """Convenience: revolve fuselage and save STL (ASCII or binary)."""
    V, F = revolve_profile_to_mesh(geom["x"], geom["y"], n_theta=n_theta)
    if ascii:
        save_stl_ascii(path, V, F, solid_name=name)
    else:
        save_stl_binary(path, V, F, solid_name=name)
    print(f"[OK] STL saved: {path} ({'ASCII' if ascii else 'binary'})")
