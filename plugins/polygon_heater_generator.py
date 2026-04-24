import pcbnew
import FootprintWizardBase
import math
import json
import os

from .PCBTraceComponent import *

class PolygonHeaterGenerator(PCBTraceComponent):
    center_x = 0
    center_y = 0

    json_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "PolygonHeaterGenerator.json"
    )

    GetName = lambda self: "Polygon Heater Generator"
    GetDescription = lambda self: "Generates square, rectangular, or triangular heating elements based on V/W."
    GetValue = lambda self: "Polygon Heater"

    def GenerateParameterList(self):
        defaults = {
            "Heater specs": {
                "Shape": "Square", # Square, Rectangle, Triangle
                "Target Voltage (V)": 24.0,
                "Target Power (W)": 12.0,
                "Layer": "F_Cu",
                "Direction": True,
            },
            "Install Info": {
                "Inner Width/Radius": 10000000,
                "Inner Height (Rect)": 20000000,
            },
            "Fab Specs": {
                "Trace Width": 500000,
                "Trace Spacing": 500000,
                "Pad Drill": 800000,
                "Pad Annular Ring": 400000,
                "Copper Thickness (Oz.Cu.)": 1.0,
            },
        }

        if os.path.exists(self.json_file):
            with open(self.json_file, "r") as f:
                saved = json.load(f)
                for k in defaults.keys():
                    if k in saved:
                        defaults[k].update(saved[k])

        self.AddParam("Heater specs", "Shape", self.uString, defaults["Heater specs"].get("Shape", "Square"), hint="Square, Rectangle, or Triangle")
        self.AddParam("Heater specs", "Target Voltage (V)", self.uFloat, defaults["Heater specs"].get("Target Voltage (V)", 24.0))
        self.AddParam("Heater specs", "Target Power (W)", self.uFloat, defaults["Heater specs"].get("Target Power (W)", 12.0))
        self.AddParam("Heater specs", "Layer", self.uString, defaults["Heater specs"]["Layer"], hint="Layer name. Uses '_' instead of '.'")
        self.AddParam("Heater specs", "Direction", self.uBool, defaults["Heater specs"].get("Direction", True), hint="True for CW, False for CCW")

        self.AddParam("Install Info", "Inner Width/Radius", self.uMM, pcbnew.ToMM(defaults["Install Info"]["Inner Width/Radius"]))
        self.AddParam("Install Info", "Inner Height (Rect)", self.uMM, pcbnew.ToMM(defaults["Install Info"]["Inner Height (Rect)"]))

        self.AddParam("Fab Specs", "Trace Width", self.uMM, pcbnew.ToMM(defaults["Fab Specs"]["Trace Width"]), min_value=0)
        self.AddParam("Fab Specs", "Trace Spacing", self.uMM, pcbnew.ToMM(defaults["Fab Specs"]["Trace Spacing"]), min_value=0)
        self.AddParam("Fab Specs", "Pad Drill", self.uMM, pcbnew.ToMM(defaults["Fab Specs"]["Pad Drill"]), min_value=0)
        self.AddParam("Fab Specs", "Pad Annular Ring", self.uMM, pcbnew.ToMM(defaults["Fab Specs"]["Pad Annular Ring"]), min_value=0)
        self.AddParam("Fab Specs", "Copper Thickness (Oz.Cu.)", self.uFloat, defaults["Fab Specs"].get("Copper Thickness (Oz.Cu.)", 1.0), min_value=0.01)

    def CheckParameters(self):
        self.shape_str = self.parameters["Heater specs"]["Shape"].strip().lower()
        self.target_v = self.parameters["Heater specs"]["Target Voltage (V)"]
        self.target_p = self.parameters["Heater specs"]["Target Power (W)"]
        self.layer = getattr(pcbnew, self.parameters["Heater specs"]["Layer"])
        self.clockwise_bool = self.parameters["Heater specs"]["Direction"]

        self.inner_w = self.parameters["Install Info"]["Inner Width/Radius"]
        self.inner_h = self.parameters["Install Info"]["Inner Height (Rect)"]

        self.trace_width = self.parameters["Fab Specs"]["Trace Width"]
        self.trace_space = self.parameters["Fab Specs"]["Trace Spacing"]
        self.pad_hole = self.parameters["Fab Specs"]["Pad Drill"]
        self.pad_ann_ring = self.parameters["Fab Specs"]["Pad Annular Ring"]
        self.copper_thickness = self.parameters["Fab Specs"]["Copper Thickness (Oz.Cu.)"]

        with open(self.json_file, "w") as f:
            json.dump(self.parameters, f, indent=4)

    def BuildThisFootprint(self):
        self.trace_length = 0
        self.vias = 0

        self.cw_multiplier = 1 if self.clockwise_bool else -1

        pad_d = self.pad_ann_ring * 2 + self.pad_hole
        pitch = self.trace_width + self.trace_space

        if self.shape_str.startswith("rect"):
            N = 4
            angles = [0, math.pi/2, math.pi, 3*math.pi/2]
            base_r = [self.inner_w / 2, self.inner_h / 2, self.inner_w / 2, self.inner_h / 2]
        elif self.shape_str.startswith("tri"):
            N = 3
            angles = [math.pi/2, 7*math.pi/6, 11*math.pi/6] # 90, 210, 330 deg
            base_r = [self.inner_w / 2, self.inner_w / 2, self.inner_w / 2]
        else: # Square
            N = 4
            angles = [0, math.pi/2, math.pi, 3*math.pi/2]
            base_r = [self.inner_w / 2, self.inner_w / 2, self.inner_w / 2, self.inner_w / 2]

        if self.clockwise_bool:
            angles = [-a for a in angles]

        def get_intersection(k1, k2):
            j1 = k1 % N
            j2 = k2 % N
            theta1 = angles[j1]
            theta2 = angles[j2]
            r1 = base_r[j1] + (k1 / N) * pitch
            r2 = base_r[j2] + (k2 / N) * pitch

            D = math.sin(theta2 - theta1)
            if abs(D) < 1e-6:
                return 0, 0

            x = (r1 * math.sin(theta2) - r2 * math.sin(theta1)) / D
            y = (r2 * math.cos(theta1) - r1 * math.cos(theta2)) / D
            return x, -y # Invert Y for KiCad coordinates

        points = []
        points.append(get_intersection(-1, 0))

        target_r = (self.target_v ** 2) / self.target_p
        t_m = TRACE_THICKNESS_1OZ * self.copper_thickness
        w_m = self.trace_width / 1e9
        L_m = target_r * t_m * w_m / RHO
        target_L_nm = L_m * 1e9

        self.draw.SetLayer(self.layer)
        self.draw.SetLineThickness(self.trace_width)

        k = 0
        current_len_nm = 0.0

        while True:
            next_point = get_intersection(k, k+1)
            dist = math.hypot(next_point[0] - points[-1][0], next_point[1] - points[-1][1])
            
            if current_len_nm + dist >= target_L_nm:
                remaining = target_L_nm - current_len_nm
                ratio = remaining / dist
                final_x = points[-1][0] + ratio * (next_point[0] - points[-1][0])
                final_y = points[-1][1] + ratio * (next_point[1] - points[-1][1])
                points.append((final_x, final_y))
                current_len_nm += remaining
                break
                
            points.append(next_point)
            current_len_nm += dist
            k += 1
            
            if k > 100000:
                break

        # Draw traces
        for i in range(len(points)-1):
            self.draw.Line(points[i][0], points[i][1], points[i+1][0], points[i+1][1])

        self.trace_length = current_len_nm

        # Place pads
        pad1_pos = pcbnew.VECTOR2I(int(points[0][0]), int(points[0][1]))
        pad2_pos = pcbnew.VECTOR2I(int(points[-1][0]), int(points[-1][1]))
        
        self.PlacePad(1, pad1_pos, pad_d, self.pad_hole)
        self.PlacePad(2, pad2_pos, pad_d, self.pad_hole)

        self.GenerateNetTiePadGroup()

        # Labels
        self.draw.SetLayer(pcbnew.F_Fab)
        self.draw.Value(0, 0, pcbnew.FromMM(1))
        self.draw.SetLayer(pcbnew.F_SilkS)
        self.draw.Reference(0, 0, pcbnew.FromMM(1))

        fab_text_s = (
            f"Polygon Heater ({self.shape_str})\n"
            f"Target: {self.target_v}V, {self.target_p}W\n"
            f"Length: {self.trace_length/1e6:.2f} mm\n"
            f"Turns approx: {k/N:.1f}\n"
            f"Trace Width/Space: {self.trace_width/1e6}/{self.trace_space/1e6}\n"
        )
        self.DrawText(fab_text_s, pcbnew.User_2)
        
        basic_fab_text_s = (
            f"R(@25C & {self.copper_thickness:.1f} Oz Cu): {self.GetResistance():.4f} Ohms\n"
            f"Power @ {self.target_v}V: {(self.target_v**2) / self.GetResistance():.1f} W"
        )
        self.DrawText(basic_fab_text_s, pcbnew.F_SilkS)
