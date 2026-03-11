import numpy as np
import sys
import os
sys.path.append(os.path.abspath("."))

from src import calcs

def test_kn_lookup():
    # FRn=1.4, psi=38 -> 1.80
    Kn = calcs.get_Kn(1.4, 38.0)
    print(f"Kn(1.4, 38) = {Kn:.3f} (Expected ~1.80)")
    # FRn=1.4, psi=50 -> 1.95
    Kn2 = calcs.get_Kn(1.4, 50.0)
    print(f"Kn(1.4, 50) = {Kn2:.3f} (Expected ~1.95)")
    assert abs(Kn - 1.80) < 0.05
    assert abs(Kn2 - 1.95) < 0.05

def test_kc_lookup():
    # FR=9 -> 1.05
    Kc = calcs.get_Kc(9.0)
    print(f"Kc(9.0) = {Kc:.3f} (Expected ~1.05)")
    assert abs(Kc - 1.05) < 0.02

def test_kt_lookup():
    # FRt=2.7, theta=10 -> 0.72
    Kt = calcs.get_Kt(2.7, 10.0)
    print(f"Kt(2.7, 10) = {Kt:.3f} (Expected ~0.72)")
    # FRt=2.7, theta=18 -> 1.28
    Kt2 = calcs.get_Kt(2.7, 18.0)
    print(f"Kt(2.7, 18) = {Kt2:.3f} (Expected ~1.28)")
    assert abs(Kt - 0.72) < 0.05
    assert abs(Kt2 - 1.28) < 0.05

def test_aero_tubular():
    # Dummy geometry with areas
    geom = {
        "l": 10.0, "d": 1.0,
        "Ln": 1.5, "Lc": 6.0, "Lt": 2.5,
        "S_wet_nose": 5.0, "S_wet_cabin": 18.0, "S_wet_tail": 6.0
    }
    op = {"V": 100.0, "nu": 1.5e-5, "rho": 1.225, "Mach": 0.3}
    tub_params = {"psi": 40.0, "theta": 15.0}
    
    res = calcs.aero_tubular(geom, op, tub_params)
    print("Aero Result:", res)
    assert res["CD_fus"] > 0
    assert res["Drag"] > 0

if __name__ == "__main__":
    print("Running tests...")
    test_kn_lookup()
    test_kc_lookup()
    test_kt_lookup()
    test_aero_tubular()
    print("All tests passed!")
