/**
 * @file engine_assembly.scad
 * @brief Complete Turbojet Engine Assembly Model
 * @details Integrates all sub-components (compressor, combustor, turbine, shaft,
 *          nozzle, EHD grids) into a unified assembly with cross-section and exploded views.
 *          Features 3D FEA stress heatmaps, CFD flow streamlines, split casings, FADEC ECU, 
 *          fuel manifolds, accessory gearbox, starter motor, lubrication lines, wiring harnesses,
 *          accessory pumps, vibration sensor ports, and heat shields.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

// Import Sub-modules
include <utils/parametric_helpers.scad>
use <compressor/axial_compressor.scad>
use <combustion/combustion_chamber.scad>
use <combustion/fuel_injector.scad>
use <turbine/turbine_stage.scad>
use <nozzle/exhaust_nozzle.scad>
use <shaft/main_shaft.scad>
use <ehd/ehd_actuator.scad>

// --- Global Assembly Configurations ---
THERMAL_STATE = "COLD_BUILD"; // "COLD_BUILD" (20C) or "MAX_TAKEOFF" (950C)
cross_section = true;      // Cut the model in half to see internal flow path
exploded = false;          // Separate components along the axis to inspect fittings
show_labels = false;       // Text labels (non-functional helper)

// --- Advanced Engineering Overlays ---
show_fea = true;             // High-stress FEA coloring on blades (Red/Orange/Green)
show_cfd_flow = true;        // CFD Streamlines & Exhaust Shock Diamonds
show_gdt_annotations = true; // 3D GD&T (PMI) annotations & leaders

// Positions along the engine axis (X-axis)
inlet_pos = -20;
compressor_pos = 0;
combustor_pos = 140;
turbine_pos = 300 + ((THERMAL_STATE == "MAX_TAKEOFF") ? 4.2 : 0.0);
nozzle_pos = 340;
ehd_pos = -35;
shaft_pos = 175;

// --- CFD Flow Line Helper Module ---
module cfd_streamline(start_r, end_r, start_x, end_x, turns, num_points, base_color) {
    color(base_color)
    for (i = [0 : num_points - 2]) {
        t1 = i / (num_points - 1);
        t2 = (i + 1) / (num_points - 1);
        
        x1 = start_x + (end_x - start_x) * t1;
        x2 = start_x + (end_x - start_x) * t2;
        
        r1 = start_r + (end_r - start_r) * t1;
        r2 = start_r + (end_r - start_r) * t2;
        
        theta1 = t1 * turns * 360.0;
        theta2 = t2 * turns * 360.0;
        
        y1 = r1 * cos(theta1);
        z1 = r1 * sin(theta1);
        y2 = r2 * cos(theta2);
        z2 = r2 * sin(theta2);
        
        // Draw thin segment
        hull() {
            translate([x1, y1, z1]) sphere(r=1.2, $fn=8);
            translate([x2, y2, z2]) sphere(r=1.2, $fn=8);
        }
    }
}

// --- Supersonic Shock Diamonds Helper Module ---
module shock_diamonds(pos_x, pos_y, pos_z, start_r, length, num_diamonds=4) {
    color([0.2, 0.8, 1.0, 0.35]) // Supersonic exhaust cyan plume
    for (i = [0 : num_diamonds - 1]) {
        dx = i * length * 1.5;
        r = start_r * pow(0.8, i);
        translate([pos_x + dx, pos_y, pos_z]) {
            // Convergent cone
            rotate([0, 90, 0])
            cylinder(h=length/2.0, r1=r, r2=r*0.4, center=false, $fn=32);
            // Divergent cone
            translate([length/2.0, 0, 0])
            rotate([0, 90, 0])
            cylinder(h=length/2.0, r1=r*0.4, r2=r*0.8, center=false, $fn=32);
        }
    }
}

// --- 3D GD&T (PMI) Annotation Leader Module ---
module gdt_leader(start_pt, end_pt, symbol, value, datum) {
    // Draw leader line
    color([0.15, 0.15, 0.15])
    hull() {
        translate(start_pt) sphere(r=0.8, $fn=8);
        translate(end_pt) sphere(r=0.8, $fn=8);
    }
    
    // Draw leader dot arrow tip
    color([0.1, 0.1, 0.1])
    translate(start_pt)
    sphere(r=2.0, $fn=8);
    
    // Draw feature control frame box
    translate(end_pt)
    rotate([90, 0, 90])
    color([0.98, 0.98, 0.98]) // White plate
    difference() {
        cube([40, 12, 1.5], center=true);
        // Draw frame border
        translate([0, 0, 0.2])
        color([0.1, 0.1, 0.1])
        difference() {
            cube([38, 10, 1.6], center=true);
            cube([37, 9, 1.8], center=true);
        }
        // Draw text annotation
        translate([0, 0, 0.5])
        linear_extrude(height=1.0)
        text(str(symbol, " | ", value, " | ", datum), size=5.0, font="Liberation Sans:style=Bold", halign="center", valign="center");
    }
}

// --- Dual Redundant AI-FADEC ECU System ---
module fadec_ecu_box() {
    // Primary and Secondary FADEC ECU Chassis (side-by-side)
    for (y_off = [-9, 9]) {
        translate([0, y_off, 0])
        color([0.20, 0.20, 0.22]) // Dark industrial military finish
        union() {
            // Main ECU chassis
            cube([44, 15, 11], center=true);
            
            // Cooling fins
            for (i = [-5 : 5]) {
                translate([i * 3.5, 0, 5.5])
                cube([1.0, 13, 2.0], center=true);
            }
            
            // MIL-DTL-38999 Circular Connectors
            color([0.8, 0.55, 0.3]) {
                translate([-22.0, -3.5, -2])
                rotate([0, 90, 0])
                cylinder(h=3, r=3, center=true, $fn=16);
                
                translate([-22.0, 3.5, -2])
                rotate([0, 90, 0])
                cylinder(h=3, r=2.5, center=true, $fn=16);
            }
            
            // LED Telemetry Status Indicators (Green = Online, Blue = AI Engine Active)
            color(y_off > 0 ? [0.1, 0.9, 0.2] : [0.1, 0.5, 0.9])
            translate([15, 4, 5.6])
            cylinder(h=1.2, r=1.2, center=true, $fn=16);
            
            // Mounting brackets
            color("silver")
            for (x = [-18, 18]) {
                translate([x, y_off > 0 ? 9.5 : -9.5, -5.5])
                difference() {
                    cube([8, 4, 1.5], center=true);
                    cylinder(h=3, r=1.5, center=true, $fn=12);
                }
            }
        }
    }
    
    // Environmental Cooling Air Duct running from the compressor casing into FADEC
    color([0.65, 0.68, 0.7]) {
        translate([12, 0, -9.0])
        difference() {
            cube([8, 28, 8], center=true);
            cube([6, 26, 10], center=true); // hollow passage
        }
        
        // Bleed adapter flange
        translate([12, 0, -12.5])
        cylinder(h=2, r=4.5, center=true, $fn=24);
    }
}

// --- External Fuel Piping Manifold ---
module fuel_manifold_system(radius=88) {
    // Primary circular distributor pipe
    color([0.8, 0.8, 0.82]) // Stainless steel tube
    rotate([0, 90, 0])
    torus(R=radius, r=3.0, fn=64);
    
    // 12 Secondary bent copper feed lines running to fuel injectors
    color([0.76, 0.42, 0.28]) // Polished copper feed lines
    for (i = [0 : 11]) {
        angle = i * 360.0 / 12;
        rotate([angle, 0, 0])
        translate([0, radius, 0])
        // Bend inwards and translate downstream (X-axis) to meet injectors at radius 75, X = 15
        hull() {
            sphere(r=1.5, $fn=16);
            translate([15, -13, 0]) sphere(r=1.5, $fn=16);
        }
    }
}

// --- Casing Longitudinal Split Flange ---
module split_casing_flange(length, width=8, thickness=6) {
    color([0.5, 0.52, 0.55]) // Matching casing grey
    difference() {
        // Flange bar
        translate([length/2.0, 0, 0])
        cube([length, width, thickness], center=true);
        
        // Hexagonal bolt holes along split-line
        for (x = [12 : 20 : length - 12]) {
            translate([x, 0, 0])
            cylinder(h=thickness + 2.0, r=2.2, center=true, $fn=16);
        }
    }
    
    // Hex bolts assembly
    color([0.72, 0.73, 0.75])
    for (x = [12 : 20 : length - 12]) {
        translate([x, 0, thickness/2.0])
        cylinder(h=3.5, r=3.5, center=false, $fn=6);
    }
}

// --- Accessory Gearbox (AGB) Casing ---
module accessory_gearbox() {
    color([0.42, 0.44, 0.47]) // Cast aircraft-alloy gearbox casing
    union() {
        // Main gearbox housing
        cube([38, 48, 16], center=true);
        
        // Cast reinforcement rib matrix
        for (y = [-20 : 10 : 20]) {
            translate([0, y, 8.5])
            cube([34, 1.5, 1.5], center=true);
        }
        for (x = [-14 : 10 : 14]) {
            translate([x, 0, 8.5])
            cube([1.5, 44, 1.5], center=true);
        }
        
        // Mounting brackets attaching AGB to compressor casing
        color("darkgray") {
            translate([14, 22, 6.0]) difference() { cube([6, 6, 5], center=true); cylinder(h=8, r=1.8, center=true, $fn=12); }
            translate([-14, 22, 6.0]) difference() { cube([6, 6, 5], center=true); cylinder(h=8, r=1.8, center=true, $fn=12); }
            translate([14, -22, 6.0]) difference() { cube([6, 6, 5], center=true); cylinder(h=8, r=1.8, center=true, $fn=12); }
            translate([-14, -22, 6.0]) difference() { cube([6, 6, 5], center=true); cylinder(h=8, r=1.8, center=true, $fn=12); }
        }

        // Accessory mounting pads / drive faces
        // Fuel pump drive pad (Aft-Left)
        translate([-10, -18, -8.0])
        cylinder(h=4, r=7.5, center=true, $fn=24);
        
        // Lube oil pump drive pad (Aft-Right)
        translate([-10, 18, -8.0])
        cylinder(h=4, r=7.0, center=true, $fn=24);
        
        // Starter generator drive pad (Forward-Left)
        translate([10, -11, -8.0])
        cylinder(h=4, r=9.0, center=true, $fn=32);
        
        // High-Capacity AI Alternator drive pad (Forward-Right)
        translate([10, 13, -8.0])
        cylinder(h=4, r=8.5, center=true, $fn=24);
    }
}

// --- Radial Drive Shaft (RDS) Casing ---
module radial_drive_shaft_housing() {
    color([0.5, 0.52, 0.55]) // Cast matching titanium casing color
    difference() {
        // Outer RDS protective tube
        cylinder(h=64, r=7.5, center=true, $fn=32);
        // Inner bore passage
        cylinder(h=66, r=6.0, center=true, $fn=32);
    }
    
    // Internal rotating drive shaft
    color("silver")
    cylinder(h=62, r=4.0, center=true, $fn=16);
    
    // Upper and lower bolting flanges
    color("darkgray") {
        translate([0, 0, 31])
        cylinder(h=2, r=10.5, center=true, $fn=24);
        translate([0, 0, -31])
        cylinder(h=2, r=10.5, center=true, $fn=24);
    }
}

// --- Electrical Starter Generator Motor ---
module starter_generator_motor() {
    color([0.22, 0.22, 0.24]) // Matte black starter housing
    union() {
        // Main cylindrical housing with heat fin grooves
        difference() {
            rotate([0, 90, 0])
            cylinder(h=34, r=8.5, center=true, $fn=32);
            
            // cooling fin grooves
            for (i = [-4 : 4]) {
                rotate([0, 90, 0])
                translate([0, 0, i * 3.5])
                tube(h=1.0, outer_r=9.0, inner_r=8.0, fn=32);
            }
        }
        
        // Electrical terminal box
        translate([-6, 0, 8.5])
        cube([14, 10, 5], center=true);
        
        // Copper connection lugs
        color([0.8, 0.5, 0.2]) {
            translate([-6, -3, 11]) cylinder(h=2, r=1, center=true, $fn=12);
            translate([-6, 3, 11]) cylinder(h=2, r=1, center=true, $fn=12);
        }
    }
}

// --- High-Capacity Alternator for AI-FADEC Power ---
module ai_alternator_unit() {
    color([0.28, 0.29, 0.31]) // Anodized alternator body
    union() {
        // Alternator core
        rotate([0, 90, 0])
        cylinder(h=24, r=8.0, center=true, $fn=24);
        
        // Liquid cooling jacket (denoted by electric blue color)
        color([0.1, 0.45, 0.85])
        rotate([0, 90, 0])
        tube(h=14, outer_r=9.0, inner_r=8.0, fn=24);
        
        // High voltage output terminal box
        color([0.15, 0.15, 0.15])
        translate([0, 0, 8.0])
        cube([8, 8, 4], center=true);
    }
}

// --- Accessory Pumps (Fuel & Oil Pumps mounted on AGB) ---
module gearbox_pumps() {
    // Fuel Pump (placed on aft-left drive pad relative to AGB origin)
    translate([-10, -18, -12])
    color([0.25, 0.26, 0.28])
    union() {
        rotate([0, 90, 0])
        cylinder(h=16, r=6.5, center=true, $fn=24);
        // Outlet piping elbow
        translate([8, 0, 4])
        sphere(r=2.2, $fn=16);
    }
    
    // Oil Pump (placed on aft-right drive pad relative to AGB origin)
    translate([-10, 18, -11])
    color([0.3, 0.32, 0.34])
    union() {
        rotate([0, 90, 0])
        cylinder(h=14, r=6.0, center=true, $fn=24);
        // Scavenge port block
        translate([7, 0, -3])
        cube([3, 4, 4], center=true);
    }
}

// --- qEEG Neuromorphic Vibration Sensor Ports ---
module vibration_sensor_port(label) {
    union() {
        // 1. Threaded hexagonal adapter base
        color([0.35, 0.37, 0.4]) // Hex base plate
        cylinder(h=3.0, r=5.5, center=false, $fn=6);
        
        // 2. Threaded neck collar
        color("silver")
        translate([0, 0, 3.0])
        cylinder(h=3.0, r=3.8, center=false, $fn=24);
        
        // 3. Transducer core housing
        color("darkgray")
        translate([0, 0, 6.0])
        cylinder(h=5.5, r=4.2, center=false, $fn=24);
        
        // 4. Blue neuromorphic cable connector cap (qEEG indicator)
        color([0.1, 0.3, 0.85])
        translate([0, 0, 11.5])
        cylinder(h=2.5, r=3.0, center=false, $fn=16);
        
        // 5. Small brass contact terminal
        color([0.8, 0.55, 0.3])
        translate([0, 0, 14.0])
        cylinder(h=1.5, r=0.9, center=false, $fn=12);
    }
}

// --- Concentric Casing Heat Shield (Double-Wall Thermal Protection) ---
module heat_shield(length=210) {
    // 1. Outer Radiation Shield Wrap
    color([0.45, 0.47, 0.5, 0.28]) // Semi-transparent titanium foil
    tube(h=length, outer_r=103, inner_r=102, fn=128);
    
    // 2. Inner Insulation Shield Wrap
    color([0.38, 0.4, 0.43, 0.35]) // Darker heat-resistant Inconel shield
    tube(h=length - 12, outer_r=100.5, inner_r=99.5, fn=128);
    
    // 3. Spacers & Standoffs (Inter-wall mechanical links)
    color("darkgray")
    for (i = [0 : 5]) {
        angle = i * 60.0;
        rotate([0, 0, angle])
        for (z = [-length/3.0, 0, length/3.0]) {
            translate([0, 101.25, z])
            cube([6, 1.5, 8], center=true);
        }
    }
}

// --- Bearing Compartment Housing (Karter) ---
module bearing_compartment_housing(outer_r=32.5, casing_r=85, width=20, is_front=true) {
    color([0.45, 0.47, 0.5]) // Cast grey alloy
    union() {
        // Inner housing ring enclosing the bearing outer race
        difference() {
            cylinder(h=width, r=outer_r + 6, center=true, $fn=64);
            cylinder(h=width + 2, r=outer_r, center=true, $fn=64);
            // Oil scavenge/drain hole at bottom
            translate([0, -outer_r - 2, 0])
            rotate([90, 0, 0])
            cylinder(h=10, r=2, center=true, $fn=16);
        }
        
        // Lab sealing ring flanges
        for (offset = [-width/2.0, width/2.0]) {
            translate([0, 0, offset])
            difference() {
                cylinder(h=2, r=outer_r + 2, center=true, $fn=64);
                cylinder(h=3, r=outer_r - 2, center=true, $fn=64);
            }
        }
        
        // Structural support struts (connecting the housing to the outer casing)
        for (i = [0 : 3]) {
            rotate([0, 0, i * 90 + (is_front ? 45 : 0)])
            translate([0, (outer_r + casing_r) / 2.0, 0])
            cube([6, casing_r - outer_r - 6, width * 0.4], center=true);
        }
    }
}

// --- Compressor Diffuser Duct (OGV -> Diffuser) ---
module compressor_diffuser_duct(start_x=120, end_x=140, inner_r1=45, outer_r1=78, inner_r2=55, outer_r2=95) {
    color("darkgray")
    difference() {
        // Outer diverging wall
        hull() {
            translate([start_x, 0, 0])
            rotate([0, 90, 0])
            cylinder(h=0.1, r=outer_r1, center=true, $fn=128);
            
            translate([end_x, 0, 0])
            rotate([0, 90, 0])
            cylinder(h=0.1, r=outer_r2, center=true, $fn=128);
        }
        
        // Subtract outer wall thickness
        hull() {
            translate([start_x - 1, 0, 0])
            rotate([0, 90, 0])
            cylinder(h=0.1, r=outer_r1 - 1.5, center=true, $fn=128);
            
            translate([end_x + 1, 0, 0])
            rotate([0, 90, 0])
            cylinder(h=0.1, r=outer_r2 - 1.5, center=true, $fn=128);
        }
        
        // Inner diverging wall (plug)
        hull() {
            translate([start_x, 0, 0])
            rotate([0, 90, 0])
            cylinder(h=0.1, r=inner_r1, center=true, $fn=128);
            
            translate([end_x, 0, 0])
            rotate([0, 90, 0])
            cylinder(h=0.1, r=inner_r2, center=true, $fn=128);
        }
    }
    
    // Outlet Guide Vanes (OGV) inside the duct
    color("silver")
    for (v = [0 : 23]) {
        angle = v * 360 / 24;
        rotate([angle, 0, 0])
        translate([start_x + 8, (outer_r1 + inner_r1)/2.0, 0])
        rotate([15, 0, 0]) // slight camber angle
        cube([12, outer_r1 - inner_r1 - 1, 1.2], center=true);
    }
}

// --- Turbine Exhaust Case (TEC) Struts ---
module turbine_exhaust_case(start_x=320, end_x=340, inner_r=39, outer_r1=75, outer_r2=85, num_struts=8) {
    color([0.35, 0.36, 0.38]) // High-temperature metal
    union() {
        // Outer case ring (diverging)
        hull() {
            translate([start_x, 0, 0])
            rotate([0, 90, 0])
            tube(h=0.1, outer_r=outer_r1, inner_r=outer_r1 - 2.0, fn=128);
            
            translate([end_x, 0, 0])
            rotate([0, 90, 0])
            tube(h=0.1, outer_r=outer_r2, inner_r=outer_r2 - 2.0, fn=128);
        }
        
        // Inner hub ring
        translate([(start_x + end_x)/2.0, 0, 0])
        rotate([0, 90, 0])
        tube(h=end_x - start_x, outer_r=inner_r + 2.0, inner_r=inner_r, fn=64);
        
        // Aerodynamic Struts (deswirl/structural struts)
        for (i = [0 : num_struts - 1]) {
            angle = i * 360.0 / num_struts;
            rotate([angle, 0, 0])
            translate([(start_x + end_x)/2.0, (outer_r1 + inner_r)/2.0, 0])
            rotate([8, 0, 0]) // deswirl angle
            scale([1, 1.25, 1])
            cube([end_x - start_x - 2, (outer_r1 + outer_r2)/2.0 - inner_r - 3, 2.5], center=true);
        }
    }
}

// --- GE9X-Style Bypass Cowl & Guide Struts ---
module bypass_duct_structure() {
    // Outer Bypass Fan Cowl with convergent nozzle (A18 exit area contraction)
    color([0.25, 0.28, 0.32, 0.28]) {
        // Straight section (X = -85 to X = 55)
        translate([-15, 0, 0])
        rotate([0, 90, 0])
        tube(h=140, outer_r=116, inner_r=114, fn=128);
        
        // Convergent nozzle section (X = 55 to X = 85)
        translate([55, 0, 0])
        rotate([0, 90, 0])
        convergent_nozzle(h=30, r1_in=114, r1_out=116, r2_in=108.3, r2_out=110.3, fn=128);
    }
    
    // Aerodynamic Bypass Guide Vanes / Struts (19 structural guide vanes for Tyler-Sofrin acoustic suppression)
    color([0.5, 0.52, 0.55])
    translate([10, 0, 0])
    for (i = [0 : 18]) {
        rotate([i * 360.0 / 19.0, 0, 0])
        translate([0, 99.5, 0]) // spans core (85) to cowl (114)
        rotate([10, 0, 0])     // slight angle for deswirl
        cube([10, 28, 1.8], center=true);
    }
}

// --- Variable Stator Vane (VSV) Actuation Ring & Linkages ---
module vsv_actuation_system() {
    for (x_offset = [15, 35, 55]) {
        // Actuator synchronization ring around compressor casing (metallic blue titanium)
        color([0.2, 0.7, 0.9])
        translate([x_offset, 0, 0])
        rotate([0, 90, 0])
        tube(h=2.4, outer_r=88.5, inner_r=86.2, fn=64);
        
        // 12 linkage arms connecting the ring to individual variable guide vanes (anodized gold)
        color([0.85, 0.65, 0.15])
        for (i = [0 : 11]) {
            rotate([i * 30, 0, 0])
            translate([x_offset, 86.5, 0])
            rotate([0, 25, 0]) // link angle
            cube([1.2, 4.0, 1.2], center=true);
        }
        
        // Hydraulic actuator cylinder piston on side of rings (bronze)
        color([0.72, 0.52, 0.28])
        translate([x_offset, 87.8, 8])
        rotate([90, 0, 0])
        cylinder(h=6.0, r=0.9, center=true, $fn=12);
    }
    
    // Master synchronization push-rod connecting all three actuation rings
    color("darkgray")
    translate([35, 89.2, 8])
    rotate([0, 90, 0])
    cylinder(h=48, r=1.2, center=true, $fn=12);
}

// --- Pneumatic Bleed Air Duct System ---
module bleed_air_system() {
    color([0.80, 0.81, 0.83]) // Stainless steel bleed pipes
    union() {
        // Bleed air collector port on compressor stage 4 (X = 75)
        translate([75, 45, 60])
        rotate([35, 0, 0])
        cylinder(h=12, r=3.0, $fn=16);
        
        // Main bypass duct pipe routing extracted air to turbine case for cooling
        hull() {
            translate([75, 45, 60]) sphere(r=2.5, $fn=12);
            translate([150, 55, 65]) sphere(r=2.5, $fn=12);
        }
        hull() {
            translate([150, 55, 65]) sphere(r=2.5, $fn=12);
            translate([280, 50, 60]) sphere(r=2.5, $fn=12);
        }
        hull() {
            translate([280, 50, 60]) sphere(r=2.5, $fn=12);
            translate([322, 42, 42]) sphere(r=2.0, $fn=12); // feeds into turbine pre-swirler
        }
        
        // P-Clamps supporting the bleed air pipe along the casing (preventing vibration)
        p_clamp(120, 52.5, 62.5, 0, -5, 45, pipe_r=2.5);
        p_clamp(200, 53.0, 61.5, 0, -5, 45, pipe_r=2.5);
        p_clamp(260, 51.5, 59.5, 0, -5, 45, pipe_r=2.5);
        
        // Inline pressure regulating bleed valve
        translate([200, 54, 63])
        color("silver")
        cube([8, 8, 8], center=true);
    }
}

module engine_solid_assembly() {
    // 1. Central Dual-Spool Coaxial Rotor Shafts
    translate([exploded ? shaft_pos - 150 : shaft_pos, 0, 0]) {
        // LP Shaft (N1) - Long internal shaft (DO=22.0mm, DI=12.0mm) - stiffened for rotordynamics
        main_shaft(length=540, outer_dia=22, inner_dia=12);
        
        // HP Shaft (N2) - Shorter, wider outer coaxial shaft
        // Spans from compressor rear (X = 20) to turbine front (X = 300)
        translate([-15, 0, 0]) // centered at global X = 160
        color("darkgray")
        rotate([0, 90, 0])
        difference() {
            union() {
                cylinder(h=280, r=18, center=true, $fn=64); // Outer diameter 36mm
                // Add labyrinth seal rotor part at X = 114 (local Z = -46)
                translate([0, 0, -46])
                stepped_labyrinth_seal_rotor(radial_clearance = (THERMAL_STATE == "MAX_TAKEOFF" ? 0.05 : 0.20), length=12);
            }
            cylinder(h=282, r=12.2, center=true, $fn=64); // Inner diameter 24.4mm (LP shaft clearance, resolved overlap)
        }
        
        // Inter-Spool Roller Bearing Journal (NODE_B3) - Mechanical support journal in the middle
        // Located at yanma odası altı (combustor mid-point, around X = -35 relative to shaft center)
        translate([-35, 0, 0])
        color("orange")
        rotate([0, 90, 0])
        difference() {
            cylinder(h=15, r=12.2, center=true, $fn=64); // fits inner HP bore (r=12.2)
            cylinder(h=16, r=11.1, center=true, $fn=64); // fits outer LP radius (r=11.0)
        }
    }

    // 2. Axial Compressor (6 Stages)
    translate([exploded ? compressor_pos - 60 : compressor_pos, 0, 0])
    color(show_fea ? [1, 1, 1] : [0.5, 0.52, 0.55]) // Highlight white to see FEA stress color
    axial_compressor(num_stages=6, tip_radius=85, stage_length=20, show_fea=show_fea);

    // 3. Combustion Chamber
    translate([exploded ? combustor_pos : combustor_pos, 0, 0])
    color([0.38, 0.35, 0.33]) // Burnt Inconel superalloy dark brown/grey
    combustion_chamber(outer_diameter=190, inner_diameter=110, length=120, num_injectors=12);

    // 4. Fuel Injector Assembly (12 injectors arrayed around dome)
    translate([exploded ? combustor_pos - 30 : combustor_pos, 0, 0])
    circular_array(n=12, radius=75)
    fuel_injector(body_diameter=10, tip_diameter=4, length=35);

    // 5. Turbine Stage (NGV + Rotor)
    translate([exploded ? turbine_pos + 60 : turbine_pos, 0, 0])
    turbine_stage(num_ngv=28, num_rotor_blades=32, show_fea=show_fea);

    // 6. Exhaust Nozzle cowl + Tail cone
    translate([exploded ? nozzle_pos + 150 : nozzle_pos, 0, 0])
    exhaust_nozzle(inlet_dia=170, exit_dia=110, cone_length=150);

    // 7. EHD Boundary Layer Grid Actuator
    translate([exploded ? ehd_pos - 100 : ehd_pos, 0, 0])
    ehd_actuator(gap_distance=20, num_emitters=12, housing_diameter=174);

    // 8. Ball Bearing Assemblies & Compartment Housings on Shaft Journals
    // Front Bearing (at X = -65)
    translate([exploded ? ehd_pos - 40 : -65, 0, 0])
    rotate([0, 90, 0]) {
        bearing_assembly(inner_dia=26, outer_dia=65, width=15, num_balls=10);
        bearing_compartment_housing(outer_r=32.5, casing_r=114, width=20, is_front=true);
    }

    // Rear Bearing (at X = 385)
    translate([exploded ? nozzle_pos + 80 : 385 + ((THERMAL_STATE == "MAX_TAKEOFF") ? 4.2 : 0.0), 0, 0])
    rotate([0, 90, 0]) {
        bearing_assembly(inner_dia=26, outer_dia=65, width=15, num_balls=10);
        bearing_compartment_housing(outer_r=32.5, casing_r=90, width=20, is_front=false);
    }

    // 8. Labyrinth Seal Stator land at X = 114
    translate([exploded ? -30 : 0, 0, 0])
    translate([114, 0, 0])
    stepped_labyrinth_seal_stator(length=12);

    // 8a. Compressor Diffuser Duct (OGV → diffuser duct, X = 120 to 140)
    translate([exploded ? -30 : 0, 0, 0])
    compressor_diffuser_duct(start_x=120, end_x=140, inner_r1=45, outer_r1=78, inner_r2=55, outer_r2=95);

    // 8c. Pre-diffuser Flow-Splitter Snout at X = 137.5
    translate([exploded ? combustor_pos - 15 : 0, 0, 0])
    pre_diffuser_snout();

    // 8b. Turbine Exhaust Case (TEC) Struts (X = 320 to 340)
    translate([exploded ? turbine_pos + 105 : 0, 0, 0])
    turbine_exhaust_case(start_x=320, end_x=340, inner_r=39, outer_r1=75, outer_r2=85);

    // 9. Bolted Connection Flanges for Casing Joints
    // Compressor Front Flange (X = -26)
    translate([exploded ? compressor_pos - 90 : -26, 0, 0])
    rotate([0, 90, 0])
    bolted_flange(outer_r=95, inner_r=85, thickness=8, num_bolts=18);

    // Compressor-Combustor Junction Flange (X = 114)
    translate([exploded ? combustor_pos - 40 : 114, 0, 0])
    rotate([0, 90, 0])
    bolted_flange(outer_r=95, inner_r=85, thickness=8, num_bolts=18);

    // Combustor Rear Flange (X = 200)
    translate([exploded ? combustor_pos + 40 : 200, 0, 0])
    rotate([0, 90, 0])
    bolted_flange(outer_r=100, inner_r=90, thickness=8, num_bolts=24);

    // Turbine-Nozzle Junction Slip-Joint (X = 340)
    if (exploded) {
        translate([nozzle_pos + 60, 0, 0])
        rotate([0, 90, 0])
        bolted_flange(outer_r=95, inner_r=85, thickness=8, num_bolts=20);
    } else {
        casing_slip_joint(THERMAL_STATE);
    }

    // 10. BEODEV Aerospace Engraved Nameplate (placed on uncut side of compressor casing)
    translate([exploded ? compressor_pos + 40 : 40, -84, -10])
    rotate([0, 0, -90]) // face outward on Y-axis
    rotate([90, 0, 0])
    color([0.15, 0.15, 0.17]) // Dark titanium steel plaque
    difference() {
        cube([60, 20, 3], center=true);
        // Engrave text logo
        translate([0, 0, 1.0])
        linear_extrude(height=1.5, center=false)
        text("BEODEV", size=7, font="Liberation Sans:style=Bold", halign="center", valign="center");
    }

    // --- High-Fidelity Piping & Controls Subsystems (Plumbing/Wiring/Accessories Detail) ---
    if (!exploded) {
        // A. FADEC ECU Box mounted on top of outer bypass cowl
        translate([40, 0, 121.5])
        fadec_ecu_box();
        
        // B. External Fuel Manifold wrapping around combustion chamber inlet
        translate([125, 0, 0])
        fuel_manifold_system(radius=88);
        
        // C. Horizontal Split Casing Flanges (joining upper and lower halves of compressor)
        translate([-20, 89, 0])
        split_casing_flange(length=140);
        translate([-20, -89, 0])
        rotate([180, 0, 0])
        split_casing_flange(length=140);
        
        // D. Accessory Gearbox (AGB) mounted underneath the compressor casing
        translate([50, 0, -94])
        accessory_gearbox();
        
        // D2. Radial Drive Shaft (RDS) housing connecting main shaft to AGB
        translate([50, 0, -62])
        radial_drive_shaft_housing();

        // L. GE9X-Style Bypass Cowl & structural guide struts
        bypass_duct_structure();
        
        // M. Variable Stator Vane (VSV) Actuation Rings & Linkage arms
        vsv_actuation_system();
        
        // N. Pneumatic Bleed Air Ducting
        bleed_air_system();
        
        // E. Starter Generator Motor mounted on AGB forward-left pad
        translate([60, -11, -111])
        starter_generator_motor();
        
        // E2. High-Capacity AI Alternator mounted on AGB forward-right pad
        translate([60, 13, -106])
        ai_alternator_unit();

        // F. Fuel Pump & Oil Pump mounted on AGB aft-left/aft-right drive pads
        translate([50, 0, -94])
        gearbox_pumps();
        
        // G. qEEG Neuromorphic Vibration Sensor Ports (transducers mounted on bearing compartments for direct imbalance tracking)
        // Sensor Port 1 (Front Bearing Chamber - Accelerometer & Proximity probe)
        translate([-65, -45, 0])
        rotate([0, 0, -90])
        rotate([0, 90, 0])
        vibration_sensor_port(label="N1_BRG_FRONT");
        
        // Sensor Port 2 (Mid Spool - Compressor Exit casing vibration monitor)
        translate([80, -73, 10])
        rotate([0, 0, -90])
        rotate([0, 90, 0])
        vibration_sensor_port(label="N1_SENS_2");
        
        // Sensor Port 3 (Rear Bearing Chamber - High Temp proximity sensor)
        translate([385, -45, 0])
        rotate([0, 0, -90])
        rotate([0, 90, 0])
        vibration_sensor_port(label="N1_BRG_REAR");
        
        // H. Concentric Heat Shield (Insulation wrap around combustion chamber & turbine)
        translate([220, 0, 0])
        rotate([0, 90, 0])
        heat_shield(length=190);
        
        // I. Lubrication Oil Piping (from AGB oil pump pad to front/rear bearings)
        color([0.8, 0.8, 0.82]) { // Steel oil lines
            // Front Bearing Feed Line (routed inside struts at X = 10)
            hull() { translate([40, 18, -105]) sphere(r=1.2, $fn=8); translate([10, 115, -20]) sphere(r=1.2, $fn=8); }
            hull() { translate([10, 115, -20]) sphere(r=1.2, $fn=8); translate([10, 114, 0]) sphere(r=1.2, $fn=8); }
            hull() { translate([10, 114, 0]) sphere(r=1.2, $fn=8); translate([10, 85, 0]) sphere(r=1.2, $fn=8); }
            hull() { translate([10, 85, 0]) sphere(r=1.2, $fn=8); translate([-65, 0, -32.5]) sphere(r=1.2, $fn=8); }
            
            // Rear Bearing Feed Line (AGB right pad [40, 18, -105] to X = 385)
            hull() { translate([40, 18, -105]) sphere(r=1.2, $fn=8); translate([210, 30, -70]) sphere(r=1.2, $fn=8); }
            hull() { translate([210, 30, -70]) sphere(r=1.2, $fn=8); translate([385, 0, -32.5]) sphere(r=1.2, $fn=8); }
            
            // P-Clamps supporting the oil pipe along the casing
            p_clamp(130, 24.5, -74.0, 0, 5, -15, pipe_r=1.2);
            p_clamp(220, 24.5, -74.0, 0, 5, -15, pipe_r=1.2);
            p_clamp(310, 22.0, -72.0, 0, 5, -15, pipe_r=1.2);
        }
        
        // I2. Fuel Supply Pipe (from AGB Fuel Pump [40, -18, -106] to Combustor Fuel Manifold [125, -88, 0])
        color([0.8, 0.8, 0.82]) {
            hull() { translate([40, -18, -106]) sphere(r=1.5, $fn=8); translate([75, -45, -90]) sphere(r=1.5, $fn=8); }
            hull() { translate([75, -45, -90]) sphere(r=1.5, $fn=8); translate([110, -75, -60]) sphere(r=1.5, $fn=8); }
            hull() { translate([110, -75, -60]) sphere(r=1.5, $fn=8); translate([125, -88, 0]) sphere(r=1.5, $fn=8); }
        }
        
        // I3. Hydraulic Actuation Lines (runs along the side of the engine compressor casing)
        color([0.7, 0.75, 0.8]) {
            // Line 1: AGB to front compressor guide vane actuators
            hull() { translate([45, 12, -94]) sphere(r=1.1, $fn=8); translate([45, 65, -70]) sphere(r=1.1, $fn=8); }
            hull() { translate([45, 65, -70]) sphere(r=1.1, $fn=8); translate([20, 85, 20]) sphere(r=1.1, $fn=8); }
            hull() { translate([20, 85, 20]) sphere(r=1.1, $fn=8); translate([-20, 85, 10]) sphere(r=1.1, $fn=8); }
            
            // Line 2: AGB to mid-stage bleed ports
            hull() { translate([42, 14, -94]) sphere(r=1.1, $fn=8); translate([42, 62, -73]) sphere(r=1.1, $fn=8); }
            hull() { translate([42, 62, -73]) sphere(r=1.1, $fn=8); translate([18, 82, 17]) sphere(r=1.1, $fn=8); }
            hull() { translate([18, 82, 17]) sphere(r=1.1, $fn=8); translate([-22, 82, 7]) sphere(r=1.1, $fn=8); }
        }
        
        // J. Electrical Wiring Harnesses (flexible black conduits from FADEC ECU connectors)
        color([0.15, 0.15, 0.15]) { // Black wire harnesses
            // Harness 1: FADEC to Compressor Speed Sensor (X = -65, routed through struts at X = 10)
            hull() { translate([18, -12, 124.5]) sphere(r=1.0, $fn=8); translate([10, -115, 20]) sphere(r=1.0, $fn=8); }
            hull() { translate([10, -115, 20]) sphere(r=1.0, $fn=8); translate([10, -114, 0]) sphere(r=1.0, $fn=8); }
            hull() { translate([10, -114, 0]) sphere(r=1.0, $fn=8); translate([10, -85, 0]) sphere(r=1.0, $fn=8); }
            hull() { translate([10, -85, 0]) sphere(r=1.0, $fn=8); translate([-65, -10, -30]) sphere(r=1.0, $fn=8); }
            
            // Harness 2: FADEC to Fuel Actuator (X = 125, along outer cowl surface)
            hull() { translate([18, -12, 124.5]) sphere(r=1.0, $fn=8); translate([85, -115, 20]) sphere(r=1.0, $fn=8); }
            hull() { translate([85, -115, 20]) sphere(r=1.0, $fn=8); translate([125, -15, 78]) sphere(r=1.0, $fn=8); }
            
            // Harness 3: FADEC to EGT thermocouple bank (X = 340, along outer cowl)
            hull() { translate([18, -12, 124.5]) sphere(r=1.0, $fn=8); translate([85, -115, 20]) sphere(r=1.0, $fn=8); }
            hull() { translate([85, -115, 20]) sphere(r=1.0, $fn=8); translate([210, -100, 40]) sphere(r=1.0, $fn=8); }
            hull() { translate([210, -100, 40]) sphere(r=1.0, $fn=8); translate([340, -10, 82]) sphere(r=1.0, $fn=8); }
            
            // Harness 4: FADEC to Starter Generator Motor (X = 60, Y = -11, Z = -108, runs along outer cowl)
            hull() { translate([18, 12, 124.5]) sphere(r=1.0, $fn=8); translate([60, 115, 20]) sphere(r=1.0, $fn=8); }
            hull() { translate([60, 115, 20]) sphere(r=1.0, $fn=8); translate([60, 115, -20]) sphere(r=1.0, $fn=8); }
            hull() { translate([60, 115, -20]) sphere(r=1.0, $fn=8); translate([60, -8, -100.5]) sphere(r=1.0, $fn=8); }
 
            // Harness 5: FADEC to qEEG Front Bearing Sensor (X = -65, Y = -45, routed inside struts at X = 10)
            hull() { translate([18, -12, 124.5]) sphere(r=0.9, $fn=8); translate([10, -114, 0]) sphere(r=0.9, $fn=8); }
            hull() { translate([10, -114, 0]) sphere(r=0.9, $fn=8); translate([10, -85, 0]) sphere(r=0.9, $fn=8); }
            hull() { translate([10, -85, 0]) sphere(r=0.9, $fn=8); translate([-65, -59, 0]) sphere(r=0.9, $fn=8); }
 
            // Harness 6: FADEC to qEEG Compressor Exit Sensor (X = 80, Y = -73)
            hull() { translate([18, -12, 124.5]) sphere(r=0.9, $fn=8); translate([80, -115, 20]) sphere(r=0.9, $fn=8); }
            hull() { translate([80, -115, 20]) sphere(r=0.9, $fn=8); translate([80, -87, 10]) sphere(r=0.9, $fn=8); }
            
            // Harness 7: FADEC to qEEG Rear Bearing Sensor (X = 385, Y = -45)
            hull() { translate([18, -12, 124.5]) sphere(r=0.9, $fn=8); translate([85, -115, 20]) sphere(r=0.9, $fn=8); }
            hull() { translate([85, -115, 20]) sphere(r=0.9, $fn=8); translate([280, -42, 40]) sphere(r=0.9, $fn=8); }
            hull() { translate([280, -42, 40]) sphere(r=0.9, $fn=8); translate([385, -59, 0]) sphere(r=0.9, $fn=8); }
            
            // Harness 8: FADEC to AI Alternator (X = 60, Y = 13, Z = -106)
            hull() { translate([18, 12, 124.5]) sphere(r=1.0, $fn=8); translate([60, 115, 20]) sphere(r=1.0, $fn=8); }
            hull() { translate([60, 115, 20]) sphere(r=1.0, $fn=8); translate([60, 13, -98.0]) sphere(r=1.0, $fn=8); }
        }
 
        // K. High-Voltage Red Power line for EHD plasma Actuators (Inlet, X = -35)
        color([0.9, 0.1, 0.1]) {
            hull() { translate([18, 12, 124.5]) sphere(r=1.4, $fn=8); translate([-35, 115, 0]) sphere(r=1.4, $fn=8); }
        }
        
        // K2. High-Voltage Red Power line for EHD plasma Actuators (Nozzle exit, X = 435)
        color([0.9, 0.1, 0.1]) {
            hull() { translate([18, 12, 124.5]) sphere(r=1.4, $fn=8); translate([210, 100, 40]) sphere(r=1.4, $fn=8); }
            hull() { translate([210, 100, 40]) sphere(r=1.4, $fn=8); translate([435, 60, 0]) sphere(r=1.4, $fn=8); }
        }
        
        // Spiral piping & wiring harness spaghettis wrapping around casing for realism
        spiral_tube(start_x=-80, end_x=40, radius=117, turns=1.0, pipe_r=1.5, base_color=[0.15, 0.15, 0.15]); // FADEC data
        spiral_tube(start_x=0, end_x=110, radius=86, turns=1.5, pipe_r=2.0, base_color=[0.8, 0.8, 0.83]);    // P3 Bleed
        spiral_tube(start_x=110, end_x=200, radius=104, turns=1.2, pipe_r=2.5, base_color=[0.95, 0.75, 0.1]); // Fuel Line
        
        // M. Nozzle EHD Plasma Actuator Electrodes
        translate([435, 0, 0])
        rotate([0, 90, 0]) {
            // Emitter ring (gold)
            color([0.85, 0.7, 0.2])
            tube(h=2.0, outer_r=61, inner_r=59.5, fn=64);
            
            // Collector ring (copper)
            translate([0, 0, 10])
            color([0.76, 0.42, 0.28])
            tube(h=5.0, outer_r=60.5, inner_r=58.5, fn=64);
            
            // Insulating ceramic collar
            translate([0, 0, 5])
            color([0.9, 0.9, 0.88])
            tube(h=18.0, outer_r=63, inner_r=61.2, fn=64);
        }
    }

    // --- CFD Streamlines Overlay ---
    if (show_cfd_flow && !exploded) {
        // Cold air entering compressor (spiral blue lines)
        cfd_streamline(start_r=78, end_r=50, start_x=-25, end_x=110, turns=2.0, num_points=40, base_color=[0.2, 0.6, 0.9, 0.6]);
        cfd_streamline(start_r=78, end_r=50, start_x=-25, end_x=110, turns=-2.0, num_points=40, base_color=[0.1, 0.5, 0.8, 0.6]);
        
        // High temp combustion gas (hot orange lines in combustor)
        cfd_streamline(start_r=75, end_r=75, start_x=115, end_x=260, turns=0.8, num_points=25, base_color=[0.95, 0.45, 0.1, 0.65]);
        cfd_streamline(start_r=75, end_r=75, start_x=115, end_x=260, turns=-0.8, num_points=25, base_color=[0.95, 0.35, 0.15, 0.65]);
        
        // Expansion gas passing turbine into exhaust (hot red lines)
        cfd_streamline(start_r=75, end_r=58, start_x=265, end_x=340, turns=1.2, num_points=20, base_color=[0.9, 0.15, 0.1, 0.7]);
        
        // Supersonic Exhaust shock diamonds at nozzle exit (X = 440)
        shock_diamonds(pos_x=442, pos_y=0, pos_z=0, start_r=52, length=18, num_diamonds=4);
    }

    // --- 3D GD&T (PMI) Annotations Overlay ---
    if (show_gdt_annotations && !exploded) {
        // 1. Shaft Front Journal Fit & roughness annotation
        gdt_leader(start_pt=[-65, 0, -32.5], end_pt=[-65, 0, -110], symbol="FIT: g6", value="Ra 0.8", datum="A");
        
        // 2. Front Bearing housing bore fit & runout
        gdt_leader(start_pt=[-65, 0, 32.5], end_pt=[-65, 0, 110], symbol="RUNOUT", value="0.005 | H7", datum="A");
        
        // 3. Compressor flange flatness & roughness
        gdt_leader(start_pt=[114, 0, 95], end_pt=[114, 0, 145], symbol="FLAT", value="0.010 | Ra 1.6", datum="B");
        
        // 4. Turbine disk runout & concentricity fit
        gdt_leader(start_pt=[300, 65, 0], end_pt=[300, 115, 0], symbol="CONC", value="0.012 | H7/h6", datum="A-B");
        
        // 5. Rear Journal bearing fit & roughness
        gdt_leader(start_pt=[385, 0, -32.5], end_pt=[385, 0, -110], symbol="FIT: r6", value="Ra 0.4", datum="A");
    }
}

// Main Draw Execution
if (cross_section) {
    difference() {
        engine_solid_assembly();
        // Cutaway half-block (cuts Z > 0 region to reveal internals)
        translate([200, 0, 200])
        cube([700, 500, 400], center=true);
    }
} else {
    engine_solid_assembly();
}

// --- Convergent Bypass Nozzle Helper Module ---
module convergent_nozzle(h, r1_in, r1_out, r2_in, r2_out, fn=128) {
    difference() {
        cylinder(h=h, r1=r1_out, r2=r2_out, center=false, $fn=fn);
        translate([0, 0, -0.1])
        cylinder(h=h+0.2, r1=r1_in, r2=r2_in, center=false, $fn=fn);
    }
}

// --- P-Clamp Mounting Bracket Helper Module ---
module p_clamp(x, y, z, rx, ry, rz, pipe_r=2.5) {
    translate([x, y, z])
    rotate([rx, ry, rz]) {
        // Clamp loop (silver steel outer metal band)
        color("silver")
        difference() {
            cylinder(h=3, r=pipe_r + 1.2, center=true, $fn=16);
            cylinder(h=4, r=pipe_r, center=true, $fn=16);
        }
        // Black rubber cushion (inner liner)
        color([0.15, 0.15, 0.15])
        difference() {
            cylinder(h=2.8, r=pipe_r + 0.2, center=true, $fn=16);
            cylinder(h=3.2, r=pipe_r, center=true, $fn=16);
        }
        // Mounting leg / tab (bolted to casing)
        color("silver")
        translate([0, -(pipe_r + 2.0), 0])
        union() {
            cube([2, 4, 1.5], center=true);
            // Hex bolt head representation
            translate([0, -1, 1.0])
            cylinder(h=1.0, r=0.8, center=true, $fn=6);
        }
    }
}

// --- Spiral Helical Tube Helper Module ---
module spiral_tube(start_x, end_x, radius, turns, pipe_r, base_color, num_points=120) {
    color(base_color)
    for (i = [0 : num_points - 2]) {
        t1 = i / (num_points - 1);
        t2 = (i + 1) / (num_points - 1);
        
        x1 = start_x + (end_x - start_x) * t1;
        x2 = start_x + (end_x - start_x) * t2;
        
        theta1 = t1 * turns * 360.0;
        theta2 = t2 * turns * 360.0;
        
        y1 = radius * cos(theta1);
        z1 = radius * sin(theta1);
        y2 = radius * cos(theta2);
        z2 = radius * sin(theta2);
        
        hull() {
            translate([x1, y1, z1]) sphere(r=pipe_r, $fn=8);
            translate([x2, y2, z2]) sphere(r=pipe_r, $fn=8);
        }
    }
}

// --- Stepped Labyrinth Seal Modules ---
module stepped_labyrinth_seal_rotor(radial_clearance=0.2, length=12) {
    cylinder(h=length, r=20.0 - radial_clearance, center=true, $fn=64);
    for (z = [-length/2 + 1.5 : 3.0 : length/2]) {
        translate([0, 0, z])
        cylinder(h=0.6, r1=20.0 - radial_clearance, r2=22.0 - radial_clearance, center=true, $fn=64);
    }
}

module stepped_labyrinth_seal_stator(length=12) {
    color([0.5, 0.52, 0.55, 0.4]) // semi-transparent casing land
    rotate([0, 90, 0])
    difference() {
        cylinder(h=length, r=25.0, center=true, $fn=64);
        cylinder(h=length + 2.0, r=22.0, center=true, $fn=64);
    }
}

// --- Pre-diffuser Flow-Splitter Snout Module ---
module pre_diffuser_snout() {
    color([0.65, 0.68, 0.70])
    translate([137.5, 0, 0])
    rotate([0, 90, 0])
    difference() {
        union() {
            // Core splitter (20% flow to swirler)
            cylinder(h=5.0, r1=76.0, r2=75.0, center=true, $fn=128);
            // Outer splitter (40% flow to outer cooling liner)
            cylinder(h=5.0, r1=85.0, r2=92.0, center=true, $fn=128);
            // Inner splitter (40% flow to inner cooling liner)
            cylinder(h=5.0, r1=65.0, r2=58.0, center=true, $fn=128);
            
            // Supporting struts connecting the splitters
            for (i = [0 : 5]) {
                rotate([0, 0, i * 60])
                translate([0, 75, 0])
                cube([1.2, 34, 5.0], center=true);
            }
        }
        // Hollow center clearance
        cylinder(h=6.0, r=53.0, center=true, $fn=128);
    }
}

// --- Casing Slip-Joint Module ---
module casing_slip_joint(thermal_state="COLD_BUILD") {
    axial_shift = (thermal_state == "MAX_TAKEOFF") ? 4.2 : 0.0;
    
    // Turbine Casing Male Sleeve (shifts with turbine)
    translate([330 + axial_shift, 0, 0])
    color([0.45, 0.47, 0.5])
    rotate([0, 90, 0])
    difference() {
        cylinder(h=20, r=84.8, center=true, $fn=128);
        cylinder(h=22, r=81.8, center=true, $fn=128);
    }
    
    // Exhaust Nozzle Female Sleeve (remains static)
    translate([345, 0, 0])
    color([0.5, 0.52, 0.55])
    rotate([0, 90, 0])
    difference() {
        cylinder(h=20, r=88.5, center=true, $fn=128);
        cylinder(h=22, r=85.0, center=true, $fn=128);
    }
}
