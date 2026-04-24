import wx
import pcbnew
import gettext
import os
import math

from .physics import calculate_required_length
from .generator import generate_heater

# Setup i18n
_ = gettext.gettext

class FlexHeaterDialog(wx.Dialog):
    def __init__(self, parent, board):
        super(FlexHeaterDialog, self).__init__(parent, title=_("JLCPCB Flex Heater Generator"), size=(500, 600))
        self.board = board
        self.InitUI()

    def InitUI(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Title
        title_font = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title = wx.StaticText(panel, label=_("Configure Flex Heater"))
        title.SetFont(title_font)
        vbox.Add(title, flag=wx.ALL|wx.ALIGN_CENTER, border=10)

        # Main settings Sizer
        fgs = wx.FlexGridSizer(10, 2, 10, 15)

        # Shape Selection
        fgs.Add(wx.StaticText(panel, label=_("Shape:")), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.shape_choice = wx.Choice(panel, choices=[_("Rectangle"), _("Square"), _("Circle"), _("Oval"), _("Fill Edge.Cuts")])
        self.shape_choice.SetSelection(0)
        fgs.Add(self.shape_choice, flag=wx.EXPAND)

        # Connector
        fgs.Add(wx.StaticText(panel, label=_("Connector Type:")), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.conn_choice = wx.Choice(panel, choices=[_("2-Pin (Power Only)"), _("3-Pin (Power + NTC)")])
        self.conn_choice.SetSelection(0)
        self.conn_choice.Bind(wx.EVT_CHOICE, self.OnConnChange)
        fgs.Add(self.conn_choice, flag=wx.EXPAND)

        # NTC Size
        self.ntc_label = wx.StaticText(panel, label=_("NTC Size:"))
        fgs.Add(self.ntc_label, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.ntc_choice = wx.Choice(panel, choices=["0402", "0603", "0805", "1206"])
        self.ntc_choice.SetSelection(1)
        fgs.Add(self.ntc_choice, flag=wx.EXPAND)
        self.ntc_label.Disable()
        self.ntc_choice.Disable()

        # Material
        fgs.Add(wx.StaticText(panel, label=_("Heater Conductor:")), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.mat_choice = wx.Choice(panel, choices=["Copper", "Stainless Steel (SUS304)", "FeCrAl", "Brass", "Nickel"])
        self.mat_choice.SetSelection(0)
        fgs.Add(self.mat_choice, flag=wx.EXPAND)

        # Substrate
        fgs.Add(wx.StaticText(panel, label=_("Base Substrate:")), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.sub_choice = wx.Choice(panel, choices=["Polyimide (PI) - Max 200°C", "Silicone Rubber - Max 260°C"])
        self.sub_choice.SetSelection(0)
        fgs.Add(self.sub_choice, flag=wx.EXPAND)

        # Voltage
        fgs.Add(wx.StaticText(panel, label=_("Target Voltage (V):")), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.val_v = wx.TextCtrl(panel, value="24.0")
        fgs.Add(self.val_v, flag=wx.EXPAND)

        # Power
        fgs.Add(wx.StaticText(panel, label=_("Target Power (W):")), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.val_w = wx.TextCtrl(panel, value="12.0")
        fgs.Add(self.val_w, flag=wx.EXPAND)

        # Trace Width
        fgs.Add(wx.StaticText(panel, label=_("Trace Width (mm):")), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.val_width = wx.TextCtrl(panel, value="0.5")
        fgs.Add(self.val_width, flag=wx.EXPAND)

        # Trace Spacing
        fgs.Add(wx.StaticText(panel, label=_("Trace Spacing (mm):")), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.val_spacing = wx.TextCtrl(panel, value="0.5")
        fgs.Add(self.val_spacing, flag=wx.EXPAND)

        # Dimensions (Only for standard shapes)
        self.dim1_label = wx.StaticText(panel, label=_("Width / Diameter (mm):"))
        fgs.Add(self.dim1_label, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.val_dim1 = wx.TextCtrl(panel, value="100.0")
        fgs.Add(self.val_dim1, flag=wx.EXPAND)

        self.dim2_label = wx.StaticText(panel, label=_("Height (mm):"))
        fgs.Add(self.dim2_label, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.val_dim2 = wx.TextCtrl(panel, value="100.0")
        fgs.Add(self.val_dim2, flag=wx.EXPAND)

        fgs.AddGrowableCol(1, 1)
        vbox.Add(fgs, proportion=1, flag=wx.ALL|wx.EXPAND, border=15)

        # JLCPCB Hints
        hint_text = _("JLCPCB Flex Limits: Min Trace 0.15mm | Min Space 0.2mm")
        hint = wx.StaticText(panel, label=hint_text)
        hint.SetForegroundColour(wx.Colour(100, 100, 100))
        vbox.Add(hint, flag=wx.ALL|wx.ALIGN_CENTER, border=5)

        # Buttons
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_calc = wx.Button(panel, label=_("Calculate Info"))
        btn_generate = wx.Button(panel, label=_("Generate Tracks"))
        btn_cancel = wx.Button(panel, label=_("Cancel"))

        btn_calc.Bind(wx.EVT_BUTTON, self.OnCalculate)
        btn_generate.Bind(wx.EVT_BUTTON, self.OnGenerate)
        btn_cancel.Bind(wx.EVT_BUTTON, self.OnCancel)

        hbox.Add(btn_calc, flag=wx.RIGHT, border=5)
        hbox.Add(btn_generate, flag=wx.RIGHT, border=5)
        hbox.Add(btn_cancel)

        vbox.Add(hbox, flag=wx.ALIGN_CENTER|wx.BOTTOM, border=15)

        # Event binding for Shape
        self.shape_choice.Bind(wx.EVT_CHOICE, self.OnShapeChange)

        panel.SetSizer(vbox)

    def OnConnChange(self, e):
        if self.conn_choice.GetSelection() == 1:
            self.ntc_label.Enable()
            self.ntc_choice.Enable()
        else:
            self.ntc_label.Disable()
            self.ntc_choice.Disable()

    def OnShapeChange(self, e):
        sel = self.shape_choice.GetSelection()
        if sel == 4: # Edge Cuts
            self.dim1_label.Disable()
            self.val_dim1.Disable()
            self.dim2_label.Disable()
            self.val_dim2.Disable()
        elif sel == 2 or sel == 1: # Circle or Square
            self.dim1_label.Enable()
            self.val_dim1.Enable()
            self.dim2_label.Disable()
            self.val_dim2.Disable()
        else:
            self.dim1_label.Enable()
            self.val_dim1.Enable()
            self.dim2_label.Enable()
            self.val_dim2.Enable()

    def get_params(self):
        try:
            return {
                "shape": self.shape_choice.GetSelection(),
                "conn": self.conn_choice.GetSelection(),
                "ntc": self.ntc_choice.GetStringSelection(),
                "material": self.mat_choice.GetStringSelection(),
                "substrate": self.sub_choice.GetSelection(),
                "v": float(self.val_v.GetValue()),
                "w": float(self.val_w.GetValue()),
                "width": float(self.val_width.GetValue()),
                "spacing": float(self.val_spacing.GetValue()),
                "dim1": float(self.val_dim1.GetValue()),
                "dim2": float(self.val_dim2.GetValue())
            }
        except ValueError:
            wx.MessageBox(_("Please enter valid numbers."), _("Error"), wx.OK | wx.ICON_ERROR)
            return None

    def OnCalculate(self, e):
        p = self.get_params()
        if not p: return

        if p['width'] < 0.15 or p['spacing'] < 0.2:
            wx.MessageBox(_("Values are below JLCPCB Flex minimums! (0.15mm trace, 0.2mm space)"), _("Warning"), wx.OK | wx.ICON_WARNING)

        req_len, req_res = calculate_required_length(p['v'], p['w'], p['width'], 1.0, p['material'])
        
        # Approximate Power Density
        area_cm2 = 0
        if p['shape'] == 2: # Circle
            area_cm2 = math.pi * ((p['dim1']/20.0)**2)
        elif p['shape'] in [0, 1]: # Rect/Square
            area_cm2 = (p['dim1']/10.0) * (p['dim2']/10.0)
        
        density_msg = ""
        if area_cm2 > 0:
            density = p['w'] / area_cm2
            density_msg = f"\nEstimated Power Density: {density:.2f} W/cm²"
            if p['substrate'] == 0 and density > 0.8: # PI limit warning heuristic
                density_msg += _("\nWARNING: High density for Polyimide! Watch max temperature (200°C).")
            elif p['substrate'] == 1 and density > 1.2: # Silicone limit warning
                density_msg += _("\nWARNING: High density for Silicone! Watch max temperature (260°C).")

        msg = _(f"Material: {p['material']}\nTarget Resistance: {req_res:.2f} Ω\nRequired Trace Length: {req_len:.2f} meters") + density_msg
        wx.MessageBox(msg, _("Calculation Results"), wx.OK | wx.ICON_INFORMATION)

    def OnGenerate(self, e):
        p = self.get_params()
        if not p: return
        
        req_len, req_res = calculate_required_length(p['v'], p['w'], p['width'], 1.0, p['material'])
        
        try:
            success, message = generate_heater(self.board, p, req_len)
            if success:
                wx.MessageBox(_("Heater generated successfully!\n\n") + message, _("Success"), wx.OK | wx.ICON_INFORMATION)
                pcbnew.Refresh()
                self.Close()
            else:
                wx.MessageBox(_("Generation failed: ") + message, _("Error"), wx.OK | wx.ICON_ERROR)
        except Exception as ex:
             wx.MessageBox(_("Error during generation: ") + str(ex), _("Fatal Error"), wx.OK | wx.ICON_ERROR)

    def OnCancel(self, e):
        self.Close()
