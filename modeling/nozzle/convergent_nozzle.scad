/**
 * @file convergent_nozzle.scad
 * @brief Convergent Exhaust Nozzle 3D Model
 * @details Models a smooth convergent contour using rotate_extrude and Bezier-like wall profiles.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

use <../utils/parametric_helpers.scad>

/**
 * @brief Convergent exhaust nozzle shell
 * @param inlet_diameter Inlet diameter matching turbine outer duct (mm)
 * @param exit_diameter Exit throat diameter (mm)
 * @param length Length along nozzle axis (mm)
 */
module convergent_nozzle(inlet_diameter=180, exit_diameter=120, length=90) {
    inlet_r = inlet_diameter / 2.0;
    exit_r = exit_diameter / 2.0;
    thickness = 1.5; // sheet metal thickness

    color("dimgrey")
    translate([length/2.0, 0, 0])
    rotate([0, 90, 0]) // Align nozzle along X-axis
    difference() {
        // Tapering outer profile
        rotate_extrude($fn=128)
        polygon(points=[
            [inlet_r, -length/2.0],
            [exit_r, length/2.0],
            [exit_r - thickness, length/2.0],
            [inlet_r - thickness, -length/2.0]
        ]);

        // Clean out central core if any polygon overlaps occurred
        cylinder(h=length + 2.0, r=exit_r - thickness, center=true, $fn=128);
    }
}

// Preview
convergent_nozzle();
