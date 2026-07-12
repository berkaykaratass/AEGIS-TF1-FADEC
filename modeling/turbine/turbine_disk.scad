/**
 * @file turbine_disk.scad
 * @brief High-Pressure Turbine (HPT) Disk
 * @details Models a central turbine disk with fir-tree slots for locking blades in place.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

use <../utils/parametric_helpers.scad>

/**
 * @brief Central turbine rotor disk
 * @param num_blades Number of blades to fit (e.g. 36)
 * @param outer_radius Outer rim radius (mm)
 * @param bore_radius Central shaft hole radius (mm)
 * @param show_fea Enable FEA stress heatmap coloring
 */
module turbine_disk(num_blades=36, outer_radius=90, bore_radius=30, show_fea=false) {
    disk_thickness = 14;

    difference() {
        union() {
            // 1. Core Disk Body
            color(show_fea ? [0.7, 0.7, 0.15] : [0.58, 0.6, 0.62]) // Yellow for medium stress in web/rim
            cylinder(h=disk_thickness, r=outer_radius, center=true, $fn=128);
            
            // Hub reinforcement collar
            color(show_fea ? [0.15, 0.7, 0.2] : [0.58, 0.6, 0.62]) // Green for low stress in hub
            cylinder(h=disk_thickness * 1.6, r=bore_radius * 1.5, center=true, $fn=64);
        }

        // Central bore shaft hole
        cylinder(h=disk_thickness * 2.5, r=bore_radius, center=true, $fn=64);

        // Circular array of bolt holes in the web
        circular_array(n=10, radius=bore_radius * 1.25)
        cylinder(h=disk_thickness * 2.5, r=3.5, center=true, $fn=16);

        // Weight-reduction web cutouts (tapered profiles)
        web_radius = (outer_radius + bore_radius * 1.5) / 2.0;
        circular_array(n=5, radius=web_radius)
        cylinder(h=disk_thickness * 1.2, r=web_radius * 0.22, center=true, $fn=32);

        // Fir-tree slots on outer rim to lock blade roots
        for (i = [0 : num_blades - 1]) {
            angle = i * 360.0 / num_blades;
            rotate([0, 0, angle])
            translate([outer_radius, 0, 0])
            rotate([90, 0, 90])
            linear_extrude(height=24, center=true)
            dovetail_slot_profile(width=8.0, height=3.0);
        }
    }
}

// Preview
turbine_disk();
