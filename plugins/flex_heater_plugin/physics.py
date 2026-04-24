import math

MATERIALS = {
    "Copper": 1.678e-8,
    "Brass": 7.1e-8,
    "Stainless Steel (SUS304)": 7.2e-7,
    "FeCrAl": 1.45e-6,
    "Nickel": 6.99e-8
}

def calculate_required_length(target_v, target_p, trace_width_mm, copper_oz=1.0, material="Copper"):
    """
    Calculates required trace length in meters for given Voltage, Power, and Material.
    """
    if target_p <= 0:
        return 0, 0
        
    target_r = (target_v ** 2) / target_p
    
    # 1 Oz of copper is ~35 micrometers (0.035 mm). We use this as the reference thickness.
    t_m = 0.035e-3 * copper_oz
    w_m = trace_width_mm / 1000.0
    
    rho = MATERIALS.get(material, 1.678e-8)
    
    # R = rho * (L / (w * t))  =>  L = R * t * w / rho
    L_m = target_r * t_m * w_m / rho
    
    return L_m, target_r
