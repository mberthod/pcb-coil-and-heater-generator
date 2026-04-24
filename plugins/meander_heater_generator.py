import pcbnew
import FootprintWizardBase
import math
import json
import os

from .PCBTraceComponent import *

class MeanderHeaterGenerator(PCBTraceComponent):
    center_x = 0
    center_y = 0

    json_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "MeanderHeaterGenerator.json"
    )

    GetName = lambda self: "Meander Heater Generator"
    GetDescription = lambda self: "Generates a serpentine (zig-zag) heating element within a specific bounding box."
    GetValue = lambda self: "Meander Heater"

    def GenerateParameterList(self):
        defaults = {
            "Heater specs": {
                "Target Voltage (V)": 24.0,
                "Target Power (W)": 12.0,
                "Layer": "F_Cu",
            },
            "Bounding Box": {
                "Max Width": 100000000,
                "Max Height": 100000000,
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

        self.AddParam("Heater specs", "Target Voltage (V)", self.uFloat, defaults["Heater specs"].get("Target Voltage (V)", 24.0))
        self.AddParam("Heater specs", "Target Power (W)", self.uFloat, defaults["Heater specs"].get("Target Power (W)", 12.0))
        self.AddParam("Heater specs", "Layer", self.uString, defaults["Heater specs"]["Layer"], hint="Layer name. Uses '_' instead of '.'")

        self.AddParam("Bounding Box", "Max Width", self.uMM, pcbnew.ToMM(defaults["Bounding Box"]["Max Width"]))
        self.AddParam("Bounding Box", "Max Height", self.uMM, pcbnew.ToMM(defaults["Bounding Box"]["Max Height"]))

        self.AddParam("Fab Specs", "Trace Width", self.uMM, pcbnew.ToMM(defaults["Fab Specs"]["Trace Width"]), min_value=0)
        self.AddParam("Fab Specs", "Trace Spacing", self.uMM, pcbnew.ToMM(defaults["Fab Specs"]["Trace Spacing"]), min_value=0)
        self.AddParam("Fab Specs", "Pad Drill", self.uMM, pcbnew.ToMM(defaults["Fab Specs"]["Pad Drill"]), min_value=0)
        self.AddParam("Fab Specs", "Pad Annular Ring", self.uMM, pcbnew.ToMM(defaults["Fab Specs"]["Pad Annular Ring"]), min_value=0)
        self.AddParam("Fab Specs", "Copper Thickness (Oz.Cu.)", self.uFloat, defaults["Fab Specs"].get("Copper Thickness (Oz.Cu.)", 1.0), min_value=0.01)

    def CheckParameters(self):
        self.target_v = self.parameters["Heater specs"]["Target Voltage (V)"]
        self.target_p = self.parameters["Heater specs"]["Target Power (W)"]
        self.layer = getattr(pcbnew, self.parameters["Heater specs"]["Layer"])

        self.max_w = self.parameters["Bounding Box"]["Max Width"]
        self.max_h = self.parameters["Bounding Box"]["Max Height"]

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

        pad_d = self.pad_ann_ring * 2 + self.pad_hole
        pitch = self.trace_width + self.trace_space

        target_r = (self.target_v ** 2) / self.target_p
        t_m = TRACE_THICKNESS_1OZ * self.copper_thickness
        w_m = self.trace_width / 1e9
        L_m = target_r * t_m * w_m / RHO
        target_L_nm = L_m * 1e9

        self.draw.SetLayer(self.layer)
        self.draw.SetLineThickness(self.trace_width)

        current_len_nm = 0.0
        points = []
        
        # Start at top left
        start_x = self.center_x - self.max_w / 2 + self.trace_width / 2
        start_y = self.center_y - self.max_h / 2 + self.trace_width / 2
        
        current_x = start_x
        current_y = start_y
        points.append((current_x, current_y))

        direction = 1 # 1 for right, -1 for left
        
        max_x = self.center_x + self.max_w / 2 - self.trace_width / 2
        min_x = self.center_x - self.max_w / 2 + self.trace_width / 2
        max_y = self.center_y + self.max_h / 2 - self.trace_width / 2

        out_of_bounds = False

        while current_len_nm < target_L_nm:
            # Determine horizontal target
            target_x = max_x if direction == 1 else min_x
            dist_x = abs(target_x - current_x)

            if current_len_nm + dist_x >= target_L_nm:
                # We finish on this horizontal segment
                remaining = target_L_nm - current_len_nm
                current_x += remaining * direction
                points.append((current_x, current_y))
                current_len_nm += remaining
                break
            else:
                current_x = target_x
                points.append((current_x, current_y))
                current_len_nm += dist_x

            # Now step down vertically
            if current_y + pitch > max_y:
                out_of_bounds = True
                break

            if current_len_nm + pitch >= target_L_nm:
                # We finish on this vertical segment
                remaining = target_L_nm - current_len_nm
                current_y += remaining
                points.append((current_x, current_y))
                current_len_nm += remaining
                break
            else:
                current_y += pitch
                points.append((current_x, current_y))
                current_len_nm += pitch

            direction *= -1

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

        if out_of_bounds:
            warning_text = "WARNING: Bounding box too small!\n"
        else:
            warning_text = ""

        fab_text_s = (
            f"Meander Heater\n"
            f"{warning_text}"
            f"Target: {self.target_v}V, {self.target_p}W\n"
            f"Target Length: {target_L_nm/1e6:.2f} mm\n"
            f"Actual Length: {self.trace_length/1e6:.2f} mm\n"
            f"Trace Width/Space: {self.trace_width/1e6}/{self.trace_space/1e6}\n"
        )
        self.DrawText(fab_text_s, pcbnew.User_2)
        
        actual_res = self.GetResistance()
        if actual_res > 0:
            actual_power = (self.target_v**2) / actual_res
        else:
            actual_power = 0

        basic_fab_text_s = (
            f"R(@25C): {actual_res:.2f} Ohms\n"
            f"Power @ {self.target_v}V: {actual_power:.1f} W"
        )
        self.DrawText(basic_fab_text_s, pcbnew.F_SilkS)
