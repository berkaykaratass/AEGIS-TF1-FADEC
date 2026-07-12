/**
 * @file compressor_rotor.scad
 * @brief Compressor Rotor Disc Assembly
 * @details Models a central rotor disc with circular arrayed blades and slot fittings.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

use <../utils/parametric_helpers.scad>
use <compressor_blade.scad>

/**
 * @brief Complete compressor rotor disc assembly
 * @param num_blades Number of blades (e.g. 24)
 * @param outer_radius Outer radius of the disc (mm)
 * @param bore_radius Central shaft hole radius (mm)
 * @param disk_thickness Thickness of the rotor hub (mm)
 * @param show_fea Enable FEA stress heatmap coloring
 */
module compressor_rotor(num_blades=24, outer_radius=80, bore_radius=25, disk_thickness=10, blade_span=35, stagger_angle=25, twist=12, is_blisk=false, show_fea=false) {
    // 1. Central Disc Hub
    color("silver")
    difference() {
        union() {
            // Main disc body
            cylinder(h=disk_thickness, r=outer_radius, center=true, $fn=128);
            // Hub reinforcement ring
            cylinder(h=disk_thickness * 1.5, r=bore_radius * 1.6, center=true, $fn=64);
        }
        
        // Central bore shaft hole
        cylinder(h=disk_thickness * 2.0, r=bore_radius, center=true, $fn=64);
        
        // Weight-reduction web cutouts
        web_radius = (outer_radius + bore_radius * 1.6) / 2.0;
        circular_array(n=6, radius=web_radius)
        cylinder(h=disk_thickness * 2.0, r=web_radius * 0.25, center=true, $fn=32);

        // Circular array of bolt holes in the web
        circular_array(n=8, radius=bore_radius * 1.3)
        cylinder(h=disk_thickness * 2.5, r=3, center=true, $fn=16);
        
        // Circular slots on outer rim for dovetail root fittings (skip if Integrally Bladed Rotor - Blisk)
        if (!is_blisk) {
            for (i = [0 : num_blades - 1]) {
                angle = i * 360.0 / num_blades;
                rotate([0, 0, angle])
                translate([outer_radius, 0, 0])
                rotate([90, 0, 90])
                linear_extrude(height=22, center=true)
                dovetail_slot_profile(width=8.0, height=3.0);
            }
        }
    }

    // 2. Circular Array of Blades
    color("lightsteelblue")
    for (i = [0 : num_blades - 1]) {
        angle = i * 360.0 / num_blades;
        rotate([0, 0, angle])
        translate([outer_radius, 0, -disk_thickness / 2.0])
        rotate([0, -90, 0])  // Align blade perpendicular to outer face of cylinder
        compressor_blade(chord=18, span=blade_span, stagger_angle=stagger_angle, twist=twist, thickness_ratio=0.08, is_blisk=is_blisk, show_fea=show_fea);
    }
}

// Preview
compressor_rotor();
