/**
 * @file exhaust_nozzle.scad
 * @brief Complete Exhaust Nozzle Assembly with Tail Cone
 * @details Models the outer cowl and the aerodynamic center body (tail cone)
 *          forming an annular exhaust passage.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

use <../utils/parametric_helpers.scad>
use <convergent_nozzle.scad>

/**
 * @brief Annular exhaust nozzle assembly
 * @param inlet_dia Inlet passage diameter (mm)
 * @param exit_dia Throat exit diameter (mm)
 * @param cone_length Center tail cone length (mm)
 */
module exhaust_nozzle(inlet_dia=180, exit_dia=130, cone_length=180) {
    // 1. Outer Convergent Nozzle Cowl
    convergent_nozzle(inlet_diameter=inlet_dia, exit_diameter=exit_dia, length=100);

    // 2. Aerodynamic Center Tail Cone
    color("darkslategray")
    translate([cone_length / 2.0 - 40, 0, 0]) // Position along nozzle axis
    rotate([0, 90, 0])
    union() {
        // Cylindrical mounting base
        cylinder(h=40, r=inlet_dia * 0.40 / 2.0, center=true, $fn=64);
        
        // Tapered aerodynamic tail cone shape
        translate([0, 0, 20])
        cylinder(h=cone_length - 40, r1=inlet_dia * 0.40 / 2.0, r2=2, center=false, $fn=64);
    }

    // 3. Center Body Support Struts
    color("gray")
    for (i = [0 : 3]) {
        angle = i * 90.0;
        rotate([angle, 0, 0])
        translate([0, (inlet_dia * 0.40 / 2.0 + inlet_dia / 2.0) / 2.0, 0])
        cube([6, (inlet_dia / 2.0 - inlet_dia * 0.40 / 2.0), 30], center=true);
    }
}

// Preview
exhaust_nozzle();
