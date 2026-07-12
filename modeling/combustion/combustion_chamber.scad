/**
 * @file combustion_chamber.scad
 * @brief Annular Combustion Chamber 3D Model
 * @details Models inner and outer liners with dilution, primary, and secondary holes,
 *          along with fuel injector mounting flanges.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

use <../utils/parametric_helpers.scad>

module wiggle_strip(radius, height, thickness=0.8, wave_count=60, amplitude=1.2) {
    color([0.5, 0.45, 0.4]) // metallic oxide look
    union() {
        for (i = [0 : wave_count - 1]) {
            angle = i * 360.0 / wave_count;
            rotate([0, 0, angle])
            translate([radius + amplitude * sin(i * 360.0 * 4.0 / wave_count), 0, 0])
            cube([thickness, radius * 2.0 * PI / wave_count * 1.1, height], center=true);
        }
    }
}

/**
 * @brief Annular combustion chamber assembly
 * @param outer_diameter Outer wall diameter (mm)
 * @param inner_diameter Inner wall diameter (mm)
 * @param length Combustion chamber length (mm)
 * @param num_injectors Number of fuel injector inlets (e.g. 12)
 */
module combustion_chamber(outer_diameter=200, inner_diameter=120, length=140, num_injectors=12) {
    outer_r = outer_diameter / 2.0;
    inner_r = inner_diameter / 2.0;
    thickness = 1.5; // sheet metal thickness

    translate([length / 2.0, 0, 0])
    rotate([0, 90, 0]) // Align combustor along X-axis
    union() {
        difference() {
            union() {
                // 1. Outer Liner Wall
                color([0.35, 0.32, 0.3]) // Burnt superalloy grey-brown
                tube(h=length, outer_r=outer_r, inner_r=outer_r - thickness, fn=128);
                
                // 2. Inner Liner Wall
                color([0.3, 0.28, 0.26]) // Heavily burnt inner liner
                tube(h=length, outer_r=inner_r + thickness, inner_r=inner_r, fn=128);
                
                // 3. Combustor Dome (Closed front cap)
                color([0.4, 0.37, 0.35]) // Dark steel dome cap
                translate([0, 0, -length / 2.0])
                difference() {
                    cylinder(h=8, r=outer_r, center=true, $fn=128);
                    cylinder(h=10, r=inner_r, center=true, $fn=128);
                }
            }

            // --- Perforations for Combustion Aerodynamics ---
            
            // 4. Primary holes (Small, near front for pilot flame mixing)
            circular_array(n=24, radius=outer_r - 2)
            translate([0, 0, -length/2.0 + 20])
            rotate([90, 0, 0])
            cylinder(h=10, r=3, center=true, $fn=16);

            circular_array(n=24, radius=inner_r + 2)
            translate([0, 0, -length/2.0 + 20])
            rotate([90, 0, 0])
            cylinder(h=10, r=3, center=true, $fn=16);

            // 5. Secondary holes (Medium, mid section)
            circular_array(n=18, radius=outer_r - 2)
            translate([0, 0, -length/2.0 + 55])
            rotate([90, 0, 0])
            cylinder(h=10, r=5, center=true, $fn=16);

            circular_array(n=18, radius=inner_r + 2)
            translate([0, 0, -length/2.0 + 55])
            rotate([90, 0, 0])
            cylinder(h=10, r=5, center=true, $fn=16);

            // 6. Dilution holes (Large, near turbine inlet for cooling)
            circular_array(n=12, radius=outer_r - 2)
            translate([0, 0, -length/2.0 + 105])
            rotate([90, 0, 0])
            cylinder(h=10, r=8, center=true, $fn=16);

            circular_array(n=12, radius=inner_r + 2)
            translate([0, 0, -length/2.0 + 105])
            rotate([90, 0, 0])
            cylinder(h=10, r=8, center=true, $fn=16);

            // 7. Injector Ports in Dome
            circular_array(n=num_injectors, radius=(outer_r + inner_r) / 2.0)
            translate([0, 0, -length/2.0])
            cylinder(h=20, r=6, center=true, $fn=32);

            // 8. Micro-Film Cooling Holes on Outer Liner (staggered laser-drilled matrix)
            for (z_c = [-length/2.0 + 12 : 8 : length/2.0 - 12]) {
                let (row_idx = round((z_c + length/2.0) / 8),
                     shift_angle = (row_idx % 2) * (360.0 / 32)) {
                    circular_array(n=16, radius=outer_r + 1)
                    translate([0, 0, z_c])
                    rotate([90, 0, shift_angle])
                    cylinder(h=8, r=0.8, center=true, $fn=8);
                }
            }

            // 9. Micro-Film Cooling Holes on Inner Liner
            for (z_c = [-length/2.0 + 12 : 8 : length/2.0 - 12]) {
                let (row_idx = round((z_c + length/2.0) / 8),
                     shift_angle = (row_idx % 2) * (360.0 / 24)) {
                    circular_array(n=12, radius=inner_r - 1)
                    translate([0, 0, z_c])
                    rotate([90, 0, shift_angle])
                    cylinder(h=8, r=0.8, center=true, $fn=8);
                }
            }
        }

        // 10. Swirler Nozzles at Dome Injector Ports
        color("silver")
        circular_array(n=num_injectors, radius=(outer_r + inner_r) / 2.0)
        translate([0, 0, -length/2.0 + 2.0])
        difference() {
            cylinder(h=6.0, r=8.0, center=true, $fn=24);
            cylinder(h=8.0, r=5.5, center=true, $fn=24);
            // Swirler vanes inside
            for (v = [0 : 7]) {
                rotate([0, 0, v * 45])
                translate([6.5, 0, 0])
                rotate([25, 0, 0])
                cube([1.0, 3.0, 5.0], center=true);
            }
        }

        // 11. Annular Flame Envelope (glowing semi-transparent torus representing the fire)
        color([1.0, 0.42, 0.1, 0.42]) // Hot glowing orange flame
        translate([0, 0, 10.0]) // slightly downstream from dome
        rotate_extrude($fn=64)
        translate([(outer_r + inner_r) / 2.0, 0, 0])
        scale([0.8, 1.3]) // stretch along length (Z-axis)
        circle(r=(outer_r - inner_r) * 0.35, $fn=32);

        // 12. Wiggle-strip Cooling Bands on Inner Liner
        translate([0, 0, -length / 2.0 + 35])
        wiggle_strip(radius=inner_r + thickness + 0.5, height=6.0, wave_count=72, amplitude=1.2);
        
        translate([0, 0, -length / 2.0 + 80])
        wiggle_strip(radius=inner_r + thickness + 0.5, height=6.0, wave_count=72, amplitude=1.2);

        // 13. Eyelet Grommet Reinforcement Flanges for Dilution Holes
        // Outer dilution hole grommets
        color("grey")
        circular_array(n=12, radius=outer_r)
        translate([0, 0, -length/2.0 + 105])
        rotate([90, 0, 0])
        difference() {
            cylinder(h=thickness * 3.0, r=10.5, center=true, $fn=24);
            cylinder(h=thickness * 4.0, r=8.0, center=true, $fn=24);
        }

        // Inner dilution hole grommets
        color("grey")
        circular_array(n=12, radius=inner_r)
        translate([0, 0, -length/2.0 + 105])
        rotate([90, 0, 0])
        difference() {
            cylinder(h=thickness * 3.0, r=10.5, center=true, $fn=24);
            cylinder(h=thickness * 4.0, r=8.0, center=true, $fn=24);
        }

        // 14. Splash Plate Fuel Atomizers (Deflectors)
        color("darkgray")
        circular_array(n=num_injectors, radius=(outer_r + inner_r) / 2.0)
        translate([0, 0, -length/2.0 + 8.0]) {
            // Deflector disk
            difference() {
                cylinder(h=1.0, r=10.0, center=true, $fn=24);
                cylinder(h=2.0, r=4.5, center=true, $fn=24);
                // Atomizer holes/slots
                for (a = [0 : 5]) {
                    rotate([0, 0, a * 60])
                    translate([7.0, 0, 0])
                    cylinder(h=2.0, r=1.0, center=true, $fn=8);
                }
            }
            // Supporting legs/struts connecting back to dome/swirler
            for (leg = [0 : 2]) {
                rotate([0, 0, leg * 120])
                translate([8.5, 0, -3.0])
                cube([1.2, 1.2, 6.0], center=true);
            }
        }
    }
}

// Preview
combustion_chamber();
