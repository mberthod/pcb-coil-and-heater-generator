import pcbnew
import FootprintWizardBase
import math
import json
import os

from .PCBTraceComponent import *

class CoilHeaterGenerator(PCBTraceComponent):
    center_x = 0
    center_y = 0

    json_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "CoilHeaterGenerator.json"
    )

    GetName = lambda self: "Coil Heater Generator"
    GetDescription = lambda self: "Generates a circular spiral heating element based on V/W."
    GetValue = lambda self: "Coil Heater"

    def GenerateParameterList(self):
        defaults = {
            "Heater specs": {
                "Target Voltage (V)": 24.0,
                "Target Power (W)": 12.0,
                "Layer": "F_Cu",
                "Direction": True,
            },
            "Install Info": {
                "Inner Radius": 10000000,
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
        self.AddParam("Heater specs", "Direction", self.uBool, defaults["Heater specs"].get("Direction", True), hint="True for CW, False for CCW")

        self.AddParam("Install Info", "Inner Radius", self.uMM, pcbnew.ToMM(defaults["Install Info"]["Inner Radius"]))

        self.AddParam("Fab Specs", "Trace Width", self.uMM, pcbnew.ToMM(defaults["Fab Specs"]["Trace Width"]), min_value=0)
        self.AddParam("Fab Specs", "Trace Spacing", self.uMM, pcbnew.ToMM(defaults["Fab Specs"]["Trace Spacing"]), min_value=0)
        self.AddParam("Fab Specs", "Pad Drill", self.uMM, pcbnew.ToMM(defaults["Fab Specs"]["Pad Drill"]), min_value=0)
        self.AddParam("Fab Specs", "Pad Annular Ring", self.uMM, pcbnew.ToMM(defaults["Fab Specs"]["Pad Annular Ring"]), min_value=0)
        self.AddParam("Fab Specs", "Copper Thickness (Oz.Cu.)", self.uFloat, defaults["Fab Specs"].get("Copper Thickness (Oz.Cu.)", 1.0), min_value=0.01)

    def CheckParameters(self):
        self.target_v = self.parameters["Heater specs"]["Target Voltage (V)"]
        self.target_p = self.parameters["Heater specs"]["Target Power (W)"]
        self.layer = getattr(pcbnew, self.parameters["Heater specs"]["Layer"])
        self.clockwise_bool = self.parameters["Heater specs"]["Direction"]

        self.inner_r = self.parameters["Install Info"]["Inner Radius"]

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

        target_r = (self.target_v ** 2) / self.target_p
        t_m = TRACE_THICKNESS_1OZ * self.copper_thickness
        w_m = self.trace_width / 1e9
        L_m = target_r * t_m * w_m / RHO
        target_L_nm = L_m * 1e9

        self.draw.SetLayer(self.layer)
        self.draw.SetLineThickness(self.trace_width)

        current_len_nm = 0.0
        
        # KiCad doesn't have an Archimedean spiral primitive, so we approximate with semi-circles
        # We start at inner_r + trace_width/2
        
        current_r = self.inner_r + self.trace_width / 2
        
        # Start pad pos
        start_x = self.center_x + current_r
        start_y = self.center_y
        pad1_pos = pcbnew.VECTOR2I(int(start_x), int(start_y))

        k = 0
        
        # We will use 180 degree arcs that slightly offset their center
        # to grow by 'pitch' every full turn (so pitch/2 every half turn)
        
        arc_start_x = start_x
        
        while current_len_nm < target_L_nm:
            # Arc from arc_start_x to opposite side
            
            # The radius of this semi circle is current_r + pitch/4
            # Center offsets back and forth by pitch/4
            
            if k % 2 == 0:
                arc_center_x = self.center_x - pitch/4
            else:
                arc_center_x = self.center_x + pitch/4
                
            radius = abs(arc_start_x - arc_center_x)
            
            arc_length = math.pi * radius
            
            if current_len_nm + arc_length >= target_L_nm:
                # We need a partial arc
                remaining = target_L_nm - current_len_nm
                angle_rad = remaining / radius
                angle_deg = math.degrees(angle_rad)
                
                # Determine sign of angle based on iteration and CW/CCW
                sign = 1 if k % 2 == 0 else -1
                actual_angle_deg = sign * angle_deg * self.cw_multiplier
                
                self.draw.Arc(
                    arc_center_x,
                    self.center_y,
                    arc_start_x,
                    self.center_y,
                    pcbnew.EDA_ANGLE(-actual_angle_deg, pcbnew.DEGREES_T)
                )
                
                # Calculate end point for the pad
                end_angle_rad = angle_rad if k % 2 == 0 else math.pi + angle_rad
                if not self.clockwise_bool:
                    end_angle_rad = -end_angle_rad
                    
                end_x = arc_center_x + radius * math.cos(end_angle_rad)
                end_y = self.center_y - radius * math.sin(end_angle_rad) # - because y is down in kicad
                
                pad2_pos = pcbnew.VECTOR2I(int(end_x), int(end_y))
                current_len_nm += remaining
                break
                
            else:
                # Full 180 arc
                sign = 1 if k % 2 == 0 else -1
                actual_angle_deg = sign * 180 * self.cw_multiplier
                
                self.draw.Arc(
                    arc_center_x,
                    self.center_y,
                    arc_start_x,
                    self.center_y,
                    pcbnew.EDA_ANGLE(-actual_angle_deg, pcbnew.DEGREES_T)
                )
                
                arc_start_x = arc_center_x - sign * radius
                current_len_nm += arc_length
                
            k += 1
            if k > 10000:
                break

        self.trace_length = current_len_nm

        self.PlacePad(1, pad1_pos, pad_d, self.pad_hole)
        self.PlacePad(2, pad2_pos, pad_d, self.pad_hole)

        self.GenerateNetTiePadGroup()

        # Labels
        self.draw.SetLayer(pcbnew.F_Fab)
        self.draw.Value(0, 0, pcbnew.FromMM(1))
        self.draw.SetLayer(pcbnew.F_SilkS)
        self.draw.Reference(0, 0, pcbnew.FromMM(1))

        fab_text_s = (
            f"Coil Heater\n"
            f"Target: {self.target_v}V, {self.target_p}W\n"
            f"Length: {self.trace_length/1e6:.2f} mm\n"
            f"Turns approx: {k/2:.1f}\n"
            f"Trace Width/Space: {self.trace_width/1e6}/{self.trace_space/1e6}\n"
        )
        self.DrawText(fab_text_s, pcbnew.User_2)
        
        basic_fab_text_s = (
            f"R(@25C & {self.copper_thickness:.1f} Oz Cu): {self.GetResistance():.4f} Ohms\n"
            f"Power @ {self.target_v}V: {(self.target_v**2) / self.GetResistance():.1f} W"
        )
        self.DrawText(basic_fab_text_s, pcbnew.F_SilkS)
