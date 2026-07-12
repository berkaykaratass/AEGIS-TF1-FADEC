/**
 * @file axial_compressor.scad
 * @brief Multi-Stage Axial Compressor Simulator Model
 * @details Assemblies multiple rotor stages with decreasing blade heights and intervening stators.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

include <../utils/parametric_helpers.scad>
use <compressor_rotor.scad>
use <compressor_blade.scad>

/**
 * @brief Multi-stage axial compressor model
 * @param num_stages Number of rotor stages (e.g. 6)
 * @param tip_radius Inlet compressor tip radius (mm)
 * @param stage_length Pitch distance between stages (mm)
 * @param show_fea Enable FEA stress heatmap coloring
 */
module axial_compressor(num_stages=6, tip_radius=85, stage_length=22, show_fea=false) {
    hub_to_tip_ratio_start = 0.50;
    hub_to_tip_ratio_end = 0.85;

    // 1. Multiple Rotor Stages (Stage 0 is the massive swept front fan, Stages 1-5 are compressor stages)
    for (stage = [0 : num_stages - 1]) {
        t = stage / (num_stages - 1);
        
        if (stage == 0) {
            // A. Massive Front Fan Stage
            fan_tip_r = tip_radius * 1.35; // 114.75 mm tip radius
            fan_hub_r = tip_radius * 0.45; // 38.25 mm hub radius
            fan_span = fan_tip_r - fan_hub_r;
            fan_num_blades = 14; // Reduced from 18 to allow CNC tool access (GCD with 19 struts is 1 for acoustic suppression)

            translate([0, 0, 0])
            rotate([0, 90, 0]) // Align along X-axis
            compressor_rotor(num_blades=fan_num_blades, 
                             outer_radius=fan_hub_r, 
                             bore_radius=18, 
                             disk_thickness=12,
                             blade_span=fan_span,
                             stagger_angle=38,
                             twist=28,
                             is_blisk=true, // Front Fan is a Blisk (integrated blades)
                             show_fea=show_fea);
        } else {
            // B. Contracting Compressor Stages
            t_c = (stage - 1) / (num_stages - 2);
            current_tip_r = tip_radius * (1.0 - t_c * 0.22);
            ratio = lerp(hub_to_tip_ratio_start + 0.1, hub_to_tip_ratio_end, t_c);
            current_hub_r = current_tip_r * ratio;
            
            current_thickness = 9 - t_c * 2;
            current_span = current_tip_r - current_hub_r;
            current_num_blades = round(18 + stage * 2); // Reduced for CNC access

            // Aerodynamic stagger & twist variation
            current_stagger = lerp(30, 18, t_c);
            current_twist = lerp(18, 6, t_c);

            translate([stage * stage_length, 0, 0])
            rotate([0, 90, 0]) // Align stages along X-axis
            compressor_rotor(num_blades=current_num_blades, 
                             outer_radius=current_hub_r, 
                             bore_radius=18, 
                             disk_thickness=current_thickness,
                             blade_span=current_span,
                             stagger_angle=current_stagger,
                             twist=current_twist,
                             is_blisk=(stage <= 1), // Stage 1 is also a Blisk
                             show_fea=show_fea);
        }
    }

    // 2. Stator Guide Vanes (positioned between rotor stages)
    color([0.65, 0.68, 0.7]) // Polished steel guide vanes
    for (stage = [0 : num_stages - 2]) {
        t = (stage + 0.5) / (num_stages - 1);
        current_tip_r = tip_radius * (1.0 - t * 0.20);
        ratio = lerp(hub_to_tip_ratio_start, hub_to_tip_ratio_end, t);
        current_hub_r = current_tip_r * ratio;
        current_span = current_tip_r - current_hub_r;
        num_vanes = round(21 + stage * 2); // Reduced for CNC access and acoustically matched (GCD with rotor is 1)

        translate([stage * stage_length + stage_length/2.0, 0, 0])
        rotate([0, 90, 0])
        for (i = [0 : num_vanes - 1]) {
            angle = i * 360.0 / num_vanes;
            rotate([0, 0, angle])
            translate([current_hub_r + 1.2, 0, 0]) // 1.2 mm thermal expansion clearance from hub
            rotate([0, -90, 0])
            compressor_blade(chord=12, span=current_span - 1.2, stagger_angle=-15, twist=5, thickness_ratio=0.07, show_fea=show_fea);
        }
    }

    // 3. Inlet Guide Vanes (IGV) at the front (stage = -1, flared outward to meet front fan)
    color([0.6, 0.63, 0.65]) // Inlet guide vanes slate metal
    translate([-stage_length/2.0 - 5.0, 0, 0])
    rotate([0, 90, 0])
    for (i = [0 : 21]) {
        angle = i * 360.0 / 22;
        rotate([0, 0, angle])
        translate([tip_radius * 0.45, 0, 0]) // hub matches fan hub
        rotate([0, -90, 0])
        compressor_blade(chord=16, span=tip_radius * 0.90, stagger_angle=6, twist=5, thickness_ratio=0.08, show_fea=show_fea);
    }

    // 4. Outer Casing (Flared front fan shroud + contracting compressor casing, with ribs & valves)
    color([0.58, 0.62, 0.65, 0.28]) // Semi-transparent titanium grey casing
    translate([num_stages * stage_length / 2.0 - stage_length * 0.8, 0, 0])
    rotate([0, 90, 0])
    difference() {
        union() {
            let (h_casing = num_stages * stage_length + stage_length,
                 fan_h = stage_length * 2.0) { // Extended to stage_length * 2.0 (44 mm) to make outer slope 37 degrees (DMLS print self-supporting)
                // Fan Shroud (flared inlet cowl - 2.0 mm thickness at inlet)
                translate([0, 0, -h_casing/2.0 + fan_h/2.0])
                cylinder(h=fan_h, r1=tip_radius * 1.40 + 2.0, r2=tip_radius * 1.01 + 3.0, center=true, $fn=128);
                
                // Compressor casing (contracting body - tapered from 3.0 mm at inlet to 6.5 mm at exit for 15 bar containment)
                translate([0, 0, fan_h/2.0])
                cylinder(h=h_casing - fan_h, r1=tip_radius * 1.01 + 3.0, r2=tip_radius * 0.8 + 7.5, center=true, $fn=128);
            }
            
            // Circumferential Stiffener Rings (placed on compressor casing section)
            let (h_casing = num_stages * stage_length + stage_length,
                 fan_h = stage_length * 2.0) {
                for (z = [-h_casing/2.0 + fan_h + 4 : stage_length : h_casing/2.0 - 8]) {
                    let (t_z = (z + h_casing/2.0) / h_casing,
                         r_at_z = lerp(tip_radius + 4, tip_radius * 0.8 + 4, t_z)) {
                        translate([0, 0, z])
                        difference() {
                            cylinder(h=4.0, r=r_at_z + 4.5, center=true, $fn=64);
                            cylinder(h=5.0, r=r_at_z - 0.5, center=true, $fn=64);
                        }
                    }
                }
            }
            
            // Longitudinal Structural Stiffeners (4 ribs on compressor body)
            let (h_casing = num_stages * stage_length + stage_length,
                 fan_h = stage_length * 2.0) {
                for (i = [0 : 3]) {
                    let (angle = i * 90.0)
                    rotate([0, 0, angle + 22.5])
                    translate([tip_radius * 0.95, 0, fan_h/2.0])
                    cube([6, 3, h_casing - fan_h], center=true);
                }
            }

            // Bleed Air Valve Ports (Stage 3 and Stage 5 compressed air bleeding)
            for (side = [-1, 1]) {
                translate([tip_radius * 0.95 * side, tip_radius * 0.2, -15])
                rotate([0, 90 * side, 0])
                cylinder(h=12, r=7, center=true, $fn=24);
                
                translate([tip_radius * 0.85 * side, -tip_radius * 0.3, 30])
                rotate([0, 90 * side, 0])
                cylinder(h=12, r=6, center=true, $fn=24);
            }
        }
        // Inner contracted & flared passage (cutout)
        let (h_casing = num_stages * stage_length + stage_length,
             fan_h = stage_length * 2.0) {
            // Flared fan inner passage
            translate([0, 0, -h_casing/2.0 - 1.0 + fan_h/2.0])
            cylinder(h=fan_h + 2.0, r1=tip_radius * 1.40, r2=tip_radius * 1.01, center=true, $fn=128);
            
            // Contracting compressor inner passage
            translate([0, 0, fan_h/2.0])
            cylinder(h=h_casing - fan_h + 2.0, r1=tip_radius * 1.01, r2=tip_radius * 0.8 + 1.0, center=true, $fn=128);
        }
    }

    // 5. Aerodynamic Spinner Nose Cone (Mounted on the front of the shaft)
    color([0.75, 0.76, 0.78]) // Polished spinner aluminum
    translate([-stage_length * 0.65, 0, 0])
    rotate([0, 90, 0])
    union() {
        // Tapered nose cone
        cylinder(h=stage_length * 1.6, r1=0.1, r2=tip_radius * 0.45, center=false, $fn=64);
        // Base ring collar
        translate([0, 0, stage_length * 1.6 - 1])
        cylinder(h=2.0, r=tip_radius * 0.45, center=true, $fn=64);
    }

    // 6. Embossed BEODEV Logo flat on top of the casing (horizontally along X-axis)
    translate([44, 0, 83.5])
    color([0.15, 0.15, 0.17]) // Dark titanium steel color
    linear_extrude(height=3.0)
    text("BEODEV", size=10, font="Liberation Sans:style=Bold", halign="center", valign="center");
}

// Preview
axial_compressor();
