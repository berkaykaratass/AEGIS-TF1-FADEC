/**
 * @file fuel_injector.scad
 * @brief Fuel Injector Nozzle 3D Model
 * @details Models a duplex fuel injector with atomizing swirl vanes and mounting flange.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

use <../utils/parametric_helpers.scad>

/**
 * @brief Single fuel injector nozzle assembly
 * @param body_diameter Diameter of primary injector stalk (mm)
 * @param tip_diameter Atomizer nozzle tip diameter (mm)
 * @param length Stalk insertion length (mm)
 */
module fuel_injector(body_diameter=12, tip_diameter=6, length=50) {
    color([0.8, 0.82, 0.85]) // Polished steel injector body
    rotate([90, 0, 0]) // Align horizontally for insertion mapping
    difference() {
        union() {
            // 1. Mounting Flange
            cylinder(h=4, r=body_diameter * 1.5, center=true, $fn=64);
            
            // Flange bolt ears
            translate([body_diameter * 1.2, 0, 0])
            cylinder(h=4, r=4, center=true, $fn=16);
            translate([-body_diameter * 1.2, 0, 0])
            cylinder(h=4, r=4, center=true, $fn=16);

            // 2. Injector Stalk Body
            translate([0, 0, length / 2.0])
            cylinder(h=length, r=body_diameter / 2.0, center=true, $fn=32);

            // 3. Tapered Nozzle Tip
            translate([0, 0, length])
            cylinder(h=8, r1=body_diameter / 2.0, r2=tip_diameter / 2.0, center=false, $fn=32);
            
            // Swirl Vane housing ring at tip
            translate([0, 0, length + 4])
            cylinder(h=4, r=body_diameter * 0.7 / 2.0, center=true, $fn=32);
        }

        // 4. Internal fuel feed gallery (hollow path)
        translate([0, 0, -2])
        cylinder(h=length + 10, r=body_diameter * 0.4 / 2.0, center=false, $fn=32);

        // Flange bolt holes
        translate([body_diameter * 1.2, 0, 0])
        cylinder(h=10, r=2, center=true, $fn=16);
        translate([-body_diameter * 1.2, 0, 0])
        cylinder(h=10, r=2, center=true, $fn=16);
    }
}

// Preview
fuel_injector();
