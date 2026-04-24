from .coil_generator import CoilGeneratorID2L
CoilGeneratorID2L().register()

from .coil_generator import CoilGenerator1L1T
CoilGenerator1L1T().register()

from .flux_neutral_coil_generator import FluxNeutralCoilGen
FluxNeutralCoilGen().register()

from .polygon_coil_generator import PolygonCoilGenerator
PolygonCoilGenerator().register()

from .polygon_heater_generator import PolygonHeaterGenerator
PolygonHeaterGenerator().register()

from .meander_heater_generator import MeanderHeaterGenerator
MeanderHeaterGenerator().register()

from .coil_heater_generator import CoilHeaterGenerator
CoilHeaterGenerator().register()

try:
    from . import flex_heater_plugin
except Exception as e:
    import traceback
    traceback.print_exc()
