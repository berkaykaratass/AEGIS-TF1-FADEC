/**
 * @file ehd_actuator.scad
 * @brief Electrohydrodynamic (EHD) Flow Control Actuator
 * @details Models high-voltage corona discharge grids (wire emitter and collector rings)
 *          used for active boundary layer flow control around the engine cowl.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

use <../utils/parametric_helpers.scad>

/**
 * @brief EHD plasma flow control grid assembly
 * @param gap_distance Distance between wire emitter and collector rings (mm)
 * @param num_emitters Number of wire grid sectors (e.g. 8)
 * @param housing_diameter Inner cowl diameter to mount to (mm)
 */
module ehd_actuator(gap_distance=25, num_emitters=8, housing_diameter=210) {
    radius = housing_diameter / 2.0;
    casing_thickness = 3.0;

    // 1. High-Voltage Wire Emitter Grid Ring (Inlet position)
    color([0.7, 0.7, 0.73]) // Tungsten fine emitter wires
    translate([-gap_distance / 2.0, 0, 0])
    rotate([0, 90, 0]) {
        // Emitter grid ring structure
        tube(h=2, outer_r=radius - 2.0, inner_r=radius - 2.5, fn=128);
        
        // Emitter wires array (fine spokes)
        circular_array(n=num_emitters, radius=0)
        translate([0, 0, 0])
        rotate([0, 90, 0])
        cylinder(h=radius - 2.5, r=0.25, center=false, $fn=16);
    }

    // 2. Grounded Collector Plate Ring (Downstream position)
    color([0.65, 0.68, 0.7]) // Anodized aluminum collector sleeve
    translate([gap_distance / 2.0, 0, 0])
    rotate([0, 90, 0]) {
        // Thick collector plate sleeve
        tube(h=15, outer_r=radius - 1.0, inner_r=radius - 3.0, fn=128);
    }

    // 3. Insulating Spacers & Mounting Frame Casing
    color([0.88, 0.88, 0.86]) // Alumina ceramic insulating ring
    rotate([0, 90, 0])
    difference() {
        // Outer housing block
        tube(h=gap_distance + 20, outer_r=radius + casing_thickness, inner_r=radius - 0.5, fn=128);
        
        // Window cutouts for flow inspection and air ingestion access
        for (i = [0 : 3]) {
            angle = i * 90.0;
            rotate([0, 0, angle])
            translate([radius + 2, 0, 0])
            cube([10, radius * 0.5, gap_distance - 5], center=true);
        }
    }

    // 4. HV Connection Terminal Post
    color([0.8, 0.55, 0.3]) // Brass terminal connector
    translate([-gap_distance / 2.0, radius + 2, 0])
    rotate([90, 0, 0])
    cylinder(h=8, r=3, center=true, $fn=32);
}

// Preview
ehd_actuator();
