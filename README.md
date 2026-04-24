# PCB Coil and Heater Generator

## Background

This project is a fork of the original KiCAD Coil Generator, massively expanded to include advanced flexible heater generation specifically tailored for modern manufacturing capabilities (like JLCPCB Flex Heaters). 
It includes both traditional **Footprint Wizards** for simple inductors and a powerful new **Action Plugin** to generate complete heating elements directly on your PCB.

## Features

### 1. JLCPCB Flex Heater Generator (Action Plugin)
Available directly in the PCB Editor (`Tools -> External Plugins`), this tool provides a complete graphical interface (GUI) to generate flexible heating elements:
- **Material Selection:** Copper, Stainless Steel (SUS304), FeCrAl, Brass, Nickel (automatically uses the correct electrical resistivity).
- **Substrate Alerts:** Choose between Polyimide (PI) or Silicone Rubber. The plugin warns you if the calculated power density (W/cm²) exceeds the safe operating limits for the selected substrate.
- **Shape Generation:** Automatically draws required traces for Rectangle, Square, Circle, Oval, or **Fills the Edge.Cuts boundary** with a dense meander pattern.
- **Connectivity:** Generates standard 2.54mm pitch connection pads. Supports **3-Pin connections** with automatic placement and routing of a central SMD NTC thermistor (0402, 0603, 0805, 1206).
- **Precision:** Uses Ohm's Law and specific material properties to calculate the exact trace length needed for your Target Voltage (V) and Power (W). Enforces JLCPCB minimums (0.15mm trace, 0.2mm space).

### 2. Footprint Wizards
Available in the Footprint Editor (`Create footprint using footprint wizard`):
- `PolygonCoilGenerator`: Generate square, rectangular, or triangular inductors by turn count.
- `PolygonHeaterGenerator`: Generate geometric heaters that stop exactly when target V/W length is reached.
- `MeanderHeaterGenerator`: Generate standard serpentine heating elements inside a strict bounding box.
- `CoilHeaterGenerator`: Generate a perfectly circular spiral heater matching target V/W.
- `CoilGeneratorID2L`, `CoilGenerator1L1T`, `FluxNeutralCoilGen`: Original legacy coil generators for inductance and flux-neutral applications.

## Installation

Clone this repository into your KiCad scripting plugins directory.
*(Tested with KiCad 8.0+)*

**Linux:**
```bash
git clone https://github.com/mberthod/pcb-coil-and-heater-generator.git ~/.local/share/kicad/8.0/scripting/plugins/pcb-coil-and-heater-generator
```

**Windows:**
Clone repo into `Documents\KiCad\8.0\scripting\plugins`

## Usage

1. **For the Action Plugin:** Open the PCB Editor, click on `Tools` -> `External Plugins` -> `JLCPCB Flex Heater Generator`.
2. **For Footprint Wizards:** Open the Footprint Editor, click the `Footprint Wizard` icon (the magic wand with a red star), and select the desired generator from the list.

## Version history

| Version | Description |
| ------- | ----------- |
| 0.1.0   | Initial fork from SK-Electronics-Consulting. Included basic 2-layer and single loop coils. |
| 0.2.0   | Added new footprint wizards (PolygonCoil, PolygonHeater, MeanderHeater, CoilHeater) with physical resistance/length calculations. |
| 0.3.0   | Added the JLCPCB Flex Heater Action Plugin (wxPython GUI, Edge.Cuts fill, NTC component placement, multi-material physics engine). |

## License

GPL-3.0 License
