import pcbnew
import os
import wx

class FlexHeaterPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "JLCPCB Flex Heater Generator"
        self.category = "Modify PCB"
        self.description = "Generates advanced flexible heaters (Polyimide/Silicone) directly as PCB tracks."
        self.show_toolbar_button = True
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        if os.path.exists(icon_path):
            self.icon_file_name = icon_path

    def Run(self):
        # We need to import gui here to avoid importing wx when KiCad starts in command line mode
        from .gui import FlexHeaterDialog
        board = pcbnew.GetBoard()
        dialog = FlexHeaterDialog(None, board)
        dialog.ShowModal()
        dialog.Destroy()
