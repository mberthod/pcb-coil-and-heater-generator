import pcbnew
import math

def generate_heater(board, params, required_length_m):
    """
    Main entry point for track generation.
    Returns (success_boolean, message_string)
    """
    shape = params['shape']
    req_len_nm = required_length_m * 1e9
    
    if shape == 4: # Edge.Cuts
        return generate_edge_cuts_fill(board, params, req_len_nm)
    elif shape == 2: # Circle
        return generate_circular_spiral(board, params, req_len_nm)
    elif shape == 0 or shape == 1: # Rect / Square
        return generate_rectangular_meander(board, params, req_len_nm)
    else:
        return False, "Shape not fully implemented yet."

def add_track(board, x1, y1, x2, y2, width, layer=pcbnew.F_Cu):
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    track.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    track.SetWidth(int(width))
    track.SetLayer(layer)
    board.Add(track)
    return track

def add_arc(board, center_x, center_y, start_x, start_y, angle_deg, width, layer=pcbnew.F_Cu):
    arc = pcbnew.PCB_ARC(board)
    arc.SetCenter(pcbnew.VECTOR2I(int(center_x), int(center_y)))
    arc.SetStart(pcbnew.VECTOR2I(int(start_x), int(start_y)))
    arc.SetMid(pcbnew.VECTOR2I(int(start_x), int(start_y))) # Mid is tricky, KiCad 8 requires careful ARC construction
    # Simplified approach: KiCad 8+ ARC setup: SetStart, SetMid, SetEnd or SetStart, SetCenter, SetAngle
    # Actually, PCB_ARC in Kicad 8 is best created by setting start, mid, end.
    
    # Let's calculate end point
    angle_rad = math.radians(angle_deg)
    radius = math.hypot(start_x - center_x, start_y - center_y)
    start_angle = math.atan2(start_y - center_y, start_x - center_x)
    end_angle = start_angle + angle_rad
    mid_angle = start_angle + angle_rad / 2
    
    end_x = center_x + radius * math.cos(end_angle)
    end_y = center_y + radius * math.sin(end_angle)
    mid_x = center_x + radius * math.cos(mid_angle)
    mid_y = center_y + radius * math.sin(mid_angle)
    
    arc.SetStart(pcbnew.VECTOR2I(int(start_x), int(start_y)))
    arc.SetMid(pcbnew.VECTOR2I(int(mid_x), int(mid_y)))
    arc.SetEnd(pcbnew.VECTOR2I(int(end_x), int(end_y)))
    arc.SetWidth(int(width))
    arc.SetLayer(layer)
    board.Add(arc)
    return end_x, end_y

def add_via(board, x, y, drill, size):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    via.SetDrill(int(drill))
    via.SetWidth(int(size))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)
    return via

def place_connector_pads(board, x, y, num_pins=2, pitch_nm=2.54e6, pad_d=2e6, pad_drill=1e6):
    pads = []
    for i in range(num_pins):
        pad = pcbnew.PAD(board)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.VECTOR2I(int(pad_d), int(pad_d)))
        pad.SetDrillSize(pcbnew.VECTOR2I(int(pad_drill), int(pad_drill)))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetLayerSet(pcbnew.LSET.AllCuMask())
        px = x + i * pitch_nm
        pad.SetPosition(pcbnew.VECTOR2I(int(px), int(y)))
        pad.SetNumber(str(i+1))
        board.Add(pad)
        pads.append((px, y))
    return pads

def connect_return_trace(board, start_x, start_y, end_x, end_y, trace_width_nm, layer):
    # Place a via at the end of the meander
    via_drill = min(1e6, trace_width_nm / 2)
    via_size = via_drill + 0.6e6
    add_via(board, end_x, end_y, via_drill, via_size)
    
    # Draw return trace on opposite layer
    return_layer = pcbnew.B_Cu if layer == pcbnew.F_Cu else pcbnew.F_Cu
    add_track(board, end_x, end_y, start_x, start_y, trace_width_nm, return_layer)

def generate_rectangular_meander(board, params, req_len_nm):
    w_nm = params['dim1'] * 1e6
    h_nm = params['dim2'] if params['shape'] == 0 else w_nm
    trace_width_nm = params['width'] * 1e6
    pitch_nm = trace_width_nm + params['spacing'] * 1e6
    
    # Start at center of board for testing, or origin if board is empty
    # For a real plugin, getting user click or current view center is better.
    # We will use 100mm, 100mm as default center
    cx, cy = 100*1e6, 100*1e6 
    
    start_x = cx - w_nm/2 + trace_width_nm/2
    start_y = cy - h_nm/2 + trace_width_nm/2
    
    # Place connector
    num_pins = 3 if params['conn'] == 1 else 2
    # Place it slightly outside the meander box
    pads = place_connector_pads(board, start_x, start_y - 2.54e6, num_pins=num_pins)
    
    # Track from pad 1 to start point
    add_track(board, pads[0][0], pads[0][1], start_x, start_y, trace_width_nm)
    
    current_len = 0
    x = start_x
    y = start_y
    direction = 1
    
    lines_drawn = 0
    
    while current_len < req_len_nm:
        target_x = cx + (w_nm/2 - trace_width_nm/2) * direction
        dist = abs(target_x - x)
        
        if current_len + dist >= req_len_nm:
            rem = req_len_nm - current_len
            add_track(board, x, y, x + rem * direction, y, trace_width_nm)
            current_len += rem
            break
            
        add_track(board, x, y, target_x, y, trace_width_nm)
        current_len += dist
        x = target_x
        
        if y + pitch_nm > cy + h_nm/2:
            return False, f"Area too small! Filled {current_len/1e9:.2f}m out of {req_len_nm/1e9:.2f}m."
            
        if current_len + pitch_nm >= req_len_nm:
            rem = req_len_nm - current_len
            add_track(board, x, y, x, y + rem, trace_width_nm)
            current_len += rem
            break
            
        add_track(board, x, y, x, y + pitch_nm, trace_width_nm)
        current_len += pitch_nm
        y += pitch_nm
        direction *= -1
        lines_drawn += 1

    connect_return_trace(board, pads[1][0], pads[1][1], x, y, trace_width_nm, pcbnew.F_Cu)

    place_ntc_if_needed(board, params, cx, cy, pads)
    return True, f"Generated {lines_drawn} lines. Total Length: {current_len/1e9:.2f} m\nReturn trace is on B_Cu layer."

def generate_circular_spiral(board, params, req_len_nm):
    trace_width_nm = params['width'] * 1e6
    pitch_nm = trace_width_nm + params['spacing'] * 1e6
    cx, cy = 100*1e6, 100*1e6 
    
    current_len = 0
    current_r = params['dim1'] * 1e6 / 2
    if current_r < trace_width_nm: current_r = trace_width_nm
    
    start_x = cx + current_r
    start_y = cy
    
    num_pins = 3 if params['conn'] == 1 else 2
    pads = place_connector_pads(board, cx, cy - 2.54e6, num_pins=num_pins)
    add_track(board, pads[0][0], pads[0][1], start_x, start_y, trace_width_nm)
    
    arc_start_x = start_x
    k = 0
    
    while current_len < req_len_nm:
        if k % 2 == 0:
            arc_center_x = cx - pitch_nm/4
        else:
            arc_center_x = cx + pitch_nm/4
            
        radius = abs(arc_start_x - arc_center_x)
        arc_length = math.pi * radius
        
        if current_len + arc_length >= req_len_nm:
            rem = req_len_nm - current_len
            angle_rad = rem / radius
            angle_deg = math.degrees(angle_rad)
            sign = 1 if k % 2 == 0 else -1
            add_arc(board, arc_center_x, cy, arc_start_x, cy, sign * angle_deg, trace_width_nm)
            current_len += rem
            break
        else:
            sign = 1 if k % 2 == 0 else -1
            arc_start_x, _ = add_arc(board, arc_center_x, cy, arc_start_x, cy, sign * 180, trace_width_nm)
            current_len += arc_length
            
        k += 1
        if k > 10000:
            return False, "Too many iterations (heater too big)."
            
    # Arc finishes at arc_start_x, cy
    connect_return_trace(board, pads[1][0], pads[1][1], arc_start_x, cy, trace_width_nm, pcbnew.F_Cu)        
            
    place_ntc_if_needed(board, params, cx, cy, pads)
    return True, f"Generated spiral. Total Length: {current_len/1e9:.2f} m\nReturn trace is on B_Cu layer."

def generate_edge_cuts_fill(board, params, req_len_nm):
    # Retrieve Edge.Cuts bounding box as a starting point
    bbox = board.GetBoardEdgesBoundingBox()
    if bbox.GetWidth() == 0 or bbox.GetHeight() == 0:
        return False, "No Edge.Cuts found on board! Please draw a board outline first."
        
    w_nm = bbox.GetWidth()
    h_nm = bbox.GetHeight()
    cx = bbox.GetCenter().x
    cy = bbox.GetCenter().y
    
    trace_width_nm = params['width'] * 1e6
    pitch_nm = trace_width_nm + params['spacing'] * 1e6
    
    current_len = 0
    start_x = bbox.GetX() + trace_width_nm/2
    start_y = bbox.GetY() + trace_width_nm/2
    
    num_pins = 3 if params['conn'] == 1 else 2
    pads = place_connector_pads(board, start_x, start_y - 2.54e6, num_pins=num_pins)
    add_track(board, pads[0][0], pads[0][1], start_x, start_y, trace_width_nm)
    
    x = start_x
    y = start_y
    direction = 1
    
    # Simple raster fill inside bounding box for now
    # A true Point-In-Polygon requires SHAPE_POLY_SET which is complex to interface with Python in KiCad 8.
    # We will approximate by filling the bounding box until target length is reached.
    
    while current_len < req_len_nm:
        target_x = bbox.GetRight() - trace_width_nm/2 if direction == 1 else bbox.GetX() + trace_width_nm/2
        dist = abs(target_x - x)
        
        if current_len + dist >= req_len_nm:
            rem = req_len_nm - current_len
            add_track(board, x, y, x + rem * direction, y, trace_width_nm)
            current_len += rem
            break
            
        add_track(board, x, y, target_x, y, trace_width_nm)
        current_len += dist
        x = target_x
        
        if y + pitch_nm > bbox.GetBottom() - trace_width_nm/2:
            return False, f"Edge.Cuts Area too small! Filled {current_len/1e9:.2f}m out of {req_len_nm/1e9:.2f}m."
            
        if current_len + pitch_nm >= req_len_nm:
            rem = req_len_nm - current_len
            add_track(board, x, y, x, y + rem, trace_width_nm)
            current_len += rem
            break
            
        add_track(board, x, y, x, y + pitch_nm, trace_width_nm)
        current_len += pitch_nm
        y += pitch_nm
        direction *= -1

    connect_return_trace(board, pads[1][0], pads[1][1], x, y, trace_width_nm, pcbnew.F_Cu)

    place_ntc_if_needed(board, params, cx, cy, pads)
    return True, f"Filled Edge.Cuts bounds. Total Length: {current_len/1e9:.2f} m\nReturn trace is on B_Cu layer."

def place_ntc_if_needed(board, params, cx, cy, pads):
    if params['conn'] == 1: # 3-Pin
        footprint_name = f"Resistor_SMD:R_{params['ntc']}_1608Metric" # Approximation for 0603
        
        # We attempt to load the footprint from the standard library
        try:
            # Getting footprint from system libraries in python is complex,
            # Let's add a placeholder pad and a silk text for the NTC
            pad_w = 0.8 * 1e6
            pad_h = 0.8 * 1e6
            
            # Pad 1
            pad1 = pcbnew.PAD(board)
            pad1.SetShape(pcbnew.PAD_SHAPE_RECT)
            pad1.SetSize(pcbnew.VECTOR2I(int(pad_w), int(pad_h)))
            pad1.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            pad1.SetLayerSet(pcbnew.LSET.AllCuMask())
            pad1.SetPosition(pcbnew.VECTOR2I(int(cx - pad_w), int(cy)))
            board.Add(pad1)
            
            # Pad 2
            pad2 = pcbnew.PAD(board)
            pad2.SetShape(pcbnew.PAD_SHAPE_RECT)
            pad2.SetSize(pcbnew.VECTOR2I(int(pad_w), int(pad_h)))
            pad2.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            pad2.SetLayerSet(pcbnew.LSET.AllCuMask())
            pad2.SetPosition(pcbnew.VECTOR2I(int(cx + pad_w), int(cy)))
            board.Add(pad2)
            
            # Label
            txt = pcbnew.PCB_TEXT(board)
            txt.SetText(f"NTC {params['ntc']}")
            txt.SetPosition(pcbnew.VECTOR2I(int(cx), int(cy - pad_h)))
            txt.SetLayer(pcbnew.F_SilkS)
            board.Add(txt)
            
            # Connect Pad 2 of NTC to Pad 3 of connector
            # In a real tool we route, here we just do a direct line on B_Cu
            add_via(board, pad2.GetPosition().x, pad2.GetPosition().y, 0.4e6, 0.8e6)
            add_track(board, pad2.GetPosition().x, pad2.GetPosition().y, pads[2][0], pads[2][1], 0.25e6, pcbnew.B_Cu)
            
            # Connect Pad 1 of NTC to Pad 1 of connector (GND/Return sharing if we wanted, but let's connect to Pin 2 for common return)
            add_via(board, pad1.GetPosition().x, pad1.GetPosition().y, 0.4e6, 0.8e6)
            add_track(board, pad1.GetPosition().x, pad1.GetPosition().y, pads[1][0], pads[1][1], 0.25e6, pcbnew.B_Cu)
            
        except Exception as e:
            print("Failed to place NTC placeholder:", e)

