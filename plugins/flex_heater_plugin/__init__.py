import pcbnew
import os

from .plugin import FlexHeaterPlugin

# Register the plugin to KiCad
plugin = FlexHeaterPlugin()
plugin.register()
