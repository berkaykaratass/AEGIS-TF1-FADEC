/**
 * @file turbine_blade.scad
 * @brief High-Pressure Turbine (HPT) Blade 3D Model
 * @details Models a single HPT blade with cooling channels, tip shroud, and fir-tree locking root.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

use <../utils/airfoil_profiles.scad>
use <../utils/parametric_helpers.scad>

module firtree_root(width, height, length, show_fea=false) {
    // Models a Christmas-tree profile root for turbine disc mounting
    translate([0, 0, -height/2.0])
    color(show_fea ? [0.9, 0.1, 0.1] : [0.72, 0.73, 0.75]) // Red for high FEA stress in fir-tree slots
    linear_extrude(height=length, center=true)
    polygon(points=[
        // Bottom narrow waist
        [-width * 0.40, -height * 0.50],
        [width * 0.40, -height * 0.50],
        // First lob
        [width * 0.50, -height * 0.25],
        [width * 0.30, -height * 0.20],
        // Second lob
        [width * 0.50, height * 0.10],
        [width * 0.25, height * 0.15],
        // Platform top flange
        [width * 0.35, height * 0.45],
        [-width * 0.35, height * 0.45],
        // Second lob (left side)
        [-width * 0.25, height * 0.15],
        [-width * 0.50, height * 0.10],
        // First lob (left side)
        [-width * 0.30, -height * 0.20],
        [-width * 0.50, -height * 0.25]
    ]);
}

module turbine_blade(chord=30, span=35, stagger_angle=50, twist=18, show_fea=false, cutaway=false) {
    root_w = 10;
    platform_h = 4;

    difference() {
        union() {
            // Main blade body with subtracted cooling chambers
            difference() {
                union() {
                    // 1. Fir-Tree Root
                    rotate([0, 0, stagger_angle])
                    firtree_root(width=root_w, height=platform_h, length=chord, show_fea=show_fea);

                    // Platform block
                    rotate([0, 0, stagger_angle])
                    translate([0, 0, platform_h/2.0])
                    color(show_fea ? [0.9, 0.5, 0.1] : [0.65, 0.65, 0.67]) // Orange for platform stress
                    cube([root_w * 1.5, root_w * 1.5, platform_h * 0.4], center=true);

                    // 2. Blade Body (Layered structure: Nickel Superalloy Core + Ceramic TBC Coating)
                    translate([0, 0, platform_h])
                    rotate([0, 0, stagger_angle]) {
                        // A. Nickel Superalloy Core
                        color(show_fea ? [0.15, 0.7, 0.2] : [0.52, 0.55, 0.58]) // Dark gray superalloy
                        linear_extrude(height=span, twist=-twist, slices=25, scale=0.8)
                        polygon(points=naca_profile_points(chord=chord * 0.98, max_t=0.138, m=0.06, p=0.4, n=15));
                        
                        // B. Ceramic Thermal Barrier Coating (TBC) (Cream-white outer shell)
                        color([0.96, 0.95, 0.90, 0.40]) // Semi-transparent YSZ ceramic coating layer
                        difference() {
                            linear_extrude(height=span, twist=-twist, slices=25, scale=0.8)
                            polygon(points=naca_profile_points(chord=chord * 1.02, max_t=0.142, m=0.06, p=0.4, n=15));
                            
                            // Subtract inner core to prevent overlap
                            translate([0, 0, -0.1])
                            linear_extrude(height=span + 0.2, twist=-twist, slices=25, scale=0.8)
                            polygon(points=naca_profile_points(chord=chord * 0.97, max_t=0.136, m=0.06, p=0.4, n=15));
                        }
                    }

                    // 3. Tip Shroud
                    translate([0, 0, platform_h + span - 1])
                    rotate([0, 0, stagger_angle - twist])
                    color(show_fea ? [0.15, 0.7, 0.2] : [0.52, 0.55, 0.58])
                    linear_extrude(height=2, center=false)
                    scale([1.1, 1.2, 1])
                    polygon(points=naca_profile_points(chord=chord * 0.8, max_t=0.12, m=0.06, p=0.4, n=10));
                }

                // 4. Internal Cooling Passages (Serpentine Tunnels & Slot) to prevent melting
                rotate([0, 0, stagger_angle]) {
                    // Upward passage 1 (X = chord * 0.22)
                    translate([chord * 0.22, 0, -2])
                    cylinder(h=span + 10, r=1.5, $fn=16);
                    
                    // Downward passage 2 (X = chord * 0.46)
                    translate([chord * 0.46, 0, 4])
                    cylinder(h=span - 6, r=1.5, $fn=16);
                    
                    // Upward passage 3 (X = chord * 0.68)
                    translate([chord * 0.68, 0, -2])
                    cylinder(h=span + 10, r=1.2, $fn=16);
                    
                    // U-bend at tip (connecting 1 and 2)
                    translate([chord * 0.34, 0, span + 1.5])
                    rotate([0, 90, 0])
                    cylinder(h=chord * 0.24, r=1.5, center=true, $fn=16);
                    
                    // U-bend at root (connecting 2 and 3)
                    translate([chord * 0.57, 0, 5.0])
                    rotate([0, 90, 0])
                    cylinder(h=chord * 0.22, r=1.2, center=true, $fn=16);
                    
                    // Trailing edge slots
                    translate([chord * 0.78, -0.6, -2])
                    cube([chord * 0.08, 1.2, span + 10]);
                }

                // 5. Showerhead Film Cooling Holes on Leading Edge & Pressure Side
                rotate([0, 0, stagger_angle]) {
                    for (z_f = [platform_h + 4 : 4.5 : platform_h + span - 4]) {
                        // Leading edge holes (angled outwards)
                        translate([chord * 0.03, -0.6, z_f])
                        rotate([20, 90, 45])
                        cylinder(h=10, r=0.35, center=true, $fn=8);
                        
                        translate([chord * 0.03, 0.6, z_f])
                        rotate([-20, 90, -45])
                        cylinder(h=10, r=0.35, center=true, $fn=8);
                        
                        // Pressure side cooling holes
                        translate([chord * 0.35, -1.8, z_f])
                        rotate([10, 90, 20])
                        cylinder(h=10, r=0.35, center=true, $fn=8);
                        
                        translate([chord * 0.65, -1.2, z_f])
                        rotate([10, 90, 15])
                        cylinder(h=10, r=0.35, center=true, $fn=8);
                    }
                }
            }

            // Add back the inner Turbulators and trailing edge Pin-Fins (survive the cutouts)
            rotate([0, 0, stagger_angle]) {
                // Turbulators in passage 1 (X = chord * 0.22) - rings of outer r=1.5, inner r=1.1
                color([0.52, 0.55, 0.58])
                for (z_t = [6 : 4 : span - 4]) {
                    translate([chord * 0.22, 0, z_t])
                    difference() {
                        cylinder(h=0.6, r=1.5, center=true, $fn=16);
                        cylinder(h=0.8, r=1.1, center=true, $fn=16);
                    }
                }
                
                // Turbulators in passage 2 (X = chord * 0.46)
                color([0.52, 0.55, 0.58])
                for (z_t = [8 : 4 : span - 8]) {
                    translate([chord * 0.46, 0, z_t])
                    difference() {
                        cylinder(h=0.6, r=1.5, center=true, $fn=16);
                        cylinder(h=0.8, r=1.1, center=true, $fn=16);
                    }
                }

                // Pin-fins in trailing edge slot (X = chord * 0.78 to 0.86)
                // Small cylinders of diameter 0.8 traversing the 1.2mm slot width (from Y=-0.6 to +0.6)
                color([0.52, 0.55, 0.58])
                for (xp = [chord * 0.79 : 2.5 : chord * 0.85]) {
                    for (zp = [5 : 3.5 : span - 5]) {
                        translate([xp, 0, zp])
                        rotate([90, 0, 0])
                        cylinder(h=1.2, r=0.4, center=true, $fn=8);
                    }
                }
            }
        }

        // 6. Section Cut / Cutaway to show internal cooling passages in cross-section
        if (cutaway) {
            rotate([0, 0, stagger_angle])
            translate([-chord * 0.5, 0, -platform_h - 10])
            cube([chord * 2.0, chord * 2.0, span + platform_h + 20]);
        }
    }
}

// Preview
color("darkgray")
turbine_blade();
