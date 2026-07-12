/**
 * @file main_shaft.scad
 * @brief Turbojet Engine Main Rotor Shaft
 * @details Models a hollow central shaft with bearing journals and drive splines.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

include <../utils/parametric_helpers.scad>

/**
 * @brief Main engine rotor shaft
 * @param length Total length (mm)
 * @param outer_dia Central tube diameter (mm)
 * @param inner_dia Central hollow bore diameter (mm)
 */
module main_shaft(length=520, outer_dia=45, inner_dia=35) {
    color("silver")
    rotate([0, 90, 0]) // Align shaft along X-axis
    difference() {
        union() {
            // 1. Primary Shaft Tube
            cylinder(h=length, r=outer_dia / 2.0, center=true, $fn=64);

            // 2. Front Bearing Journal (slightly thicker)
            translate([0, 0, -length / 2.0 + 30])
            cylinder(h=40, r=(outer_dia + 4) / 2.0, center=true, $fn=64);

            // 3. Rear Bearing Journal
            translate([0, 0, length / 2.0 - 60])
            cylinder(h=30, r=(outer_dia + 4) / 2.0, center=true, $fn=64);

            // 4. Drive Splines at compressor stage locking point (radial ribs)
            translate([0, 0, -length / 2.0 + 80])
            for (i = [0 : 23]) {
                angle = i * 360.0 / 24;
                rotate([0, 0, angle])
                translate([outer_dia / 2.0 + 1.0, 0, 0])
                cube([2, 1.5, 30], center=true);
            }

            // 5. Drive Splines at turbine stage locking point
            translate([0, 0, length / 2.0 - 90])
            for (i = [0 : 23]) {
                angle = i * 360.0 / 24;
                rotate([0, 0, angle])
                translate([outer_dia / 2.0 + 1.0, 0, 0])
                cube([2, 1.5, 20], center=true);
            }
        }

        // 6. Central Hollow Core (Bore) for weight reduction and cooling airflow
        cylinder(h=length + TOLERANCE * 4.0, r=inner_dia / 2.0, center=true, $fn=64);
    }
}

// Preview
main_shaft();
