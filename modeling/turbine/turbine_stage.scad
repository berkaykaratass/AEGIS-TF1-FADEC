/**
 * @file turbine_stage.scad
 * @brief Complete High-Pressure Turbine Stage
 * @details Assemblies the NGV (stator) ring and the spinning turbine rotor (disk + blades).
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

use <../utils/parametric_helpers.scad>
use <turbine_disk.scad>
use <turbine_blade.scad>

/**
 * @brief Turbine stage assembly
 * @param num_ngv Number of Nozzle Guide Vanes in stator ring (e.g. 32)
 * @param num_rotor_blades Number of rotor blades (e.g. 36)
 * @param show_fea Enable FEA stress heatmap coloring
 */
module turbine_stage(num_ngv=32, num_rotor_blades=36, show_fea=false) {
    outer_r = 90;
    inner_r = 65;
    span = outer_r - inner_r;
    stage_gap = 18;

    // 1. Stator Ring: Nozzle Guide Vanes (NGV)
    color([0.45, 0.47, 0.5]) // Slate grey heat resistant superalloy NGV ring
    translate([-stage_gap, 0, 0]) {
        // Inner and outer shroud bands
        rotate([0, 90, 0]) {
            tube(h=10, outer_r=outer_r + 1.5, inner_r=outer_r, fn=128);
            tube(h=10, outer_r=inner_r + 1.2, inner_r=inner_r, fn=128); // Adjusted inner shroud band to match clearance
        }

        // Circular array of NGV blades
        for (i = [0 : num_ngv - 1]) {
            angle = i * 360.0 / num_ngv;
            rotate([angle, 0, 0])
            translate([0, inner_r + 1.2, 0]) // 1.2 mm thermal expansion gap at the hub
            rotate([0, -90, 0])
            turbine_blade(chord=18, span=span - 1.2, stagger_angle=-20, twist=5, show_fea=show_fea);
        }
    }

    // 2. Rotor Disk Assembly
    translate([0, 0, 0])
    rotate([0, 90, 0]) // Align disk axis with X-axis
    turbine_disk(num_blades=num_rotor_blades, outer_radius=inner_r, bore_radius=18, show_fea=show_fea);

    // 2A. Turbine Blade Forward & Aft Axial Lock Plates (Blade Retainers)
    translate([-7.5, 0, 0])
    rotate([0, 90, 0])
    blade_lock_plates(outer_radius=inner_r);
    
    translate([7.5, 0, 0])
    rotate([0, 90, 0])
    blade_lock_plates(outer_radius=inner_r);

    // 2B. Secondary Cooling Flow: Stationary Preswirler Ring (injects cool bleed air tangentially)
    translate([-11.5, 0, 0])
    rotate([0, 90, 0])
    cooling_preswirler_ring(radius=26);

    // 2C. Secondary Flow Path Seal: Labyrinth Knife-Edge Seal Ring (prevents hot gas leakage)
    translate([9.5, 0, 0])
    rotate([0, 90, 0])
    labyrinth_seal(inner_r=22, outer_r=33, length=9);

    // 3. Spinning Rotor Blades Array
    color([0.52, 0.55, 0.58]) // Forged single crystal turbine blades
    for (i = [0 : num_rotor_blades - 1]) {
        angle = i * 360.0 / num_rotor_blades;
        rotate([angle, 0, 0])
        translate([0, inner_r, 0]) // starts at hub disk outer radius
        rotate([0, -90, 0])
        turbine_blade(chord=20, span=span - 1.2, stagger_angle=40, twist=15, show_fea=show_fea); // 1.2 mm tip clearance at casing
    }
}

// --- Turbine Blade Axial Lock Plates (Blade Retainers) ---
module blade_lock_plates(outer_radius=65, thickness=1.5) {
    color([0.3, 0.32, 0.35]) // Dark hardened lock plate steel
    difference() {
        // Retainer ring plate face
        cylinder(h=thickness, r=outer_radius + 2, center=true, $fn=128);
        // inner shaft clearance
        cylinder(h=thickness + 1.0, r=outer_radius - 8, center=true, $fn=128);
        // locking relief slots around outer rim
        for (i = [0 : 35]) {
            rotate([0, 0, i * 10])
            translate([outer_radius + 1.2, 0, 0])
            cube([4.0, 1.8, thickness + 2.0], center=true);
        }
    }
}

// --- Secondary Flow: Coolant Preswirler Ring ---
module cooling_preswirler_ring(radius=28) {
    color([0.48, 0.5, 0.52]) // Heat resistant alloy preswirler housing
    difference() {
        // Preswirler housing outer ring
        cylinder(h=6.0, r=radius + 7, center=true, $fn=64);
        // Inner shaft cavity clearance
        cylinder(h=8.0, r=radius, center=true, $fn=64);
        
        // Tangential preswirler ports (angled nozzles)
        for (i = [0 : 17]) {
            angle = i * 20.0;
            rotate([0, 0, angle])
            translate([radius + 3.5, 0, 0])
            rotate([0, 30, 45]) // tilted tangentially to match spool spin
            cylinder(h=10, r=1.1, center=true, $fn=12);
        }
    }
}

// --- Labyrinth Seal Ring (Labirent Salmastra) ---
module labyrinth_seal(inner_r=22, outer_r=38, length=12) {
    color([0.65, 0.65, 0.67]) // Knife-edge metallic seal teeth
    difference() {
        union() {
            // Main seal sleeve ring
            cylinder(h=length, r=outer_r, center=true, $fn=64);
            // Labirent teeth (knife edges)
            for (z = [-length/3.0, 0, length/3.0]) {
                translate([0, 0, z])
                cylinder(h=0.8, r=outer_r + 2.2, center=true, $fn=64);
            }
        }
        // Shaft bore passage
        cylinder(h=length + 2.0, r=inner_r, center=true, $fn=64);
    }
}

// Preview
turbine_stage();
