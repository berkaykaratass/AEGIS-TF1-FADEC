/**
 * @file compressor_blade.scad
 * @brief Compressor Blade Geometry Generator
 * @details Models a single twisted compressor blade with a dovetail attachment root.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

use <../utils/airfoil_profiles.scad>
use <../utils/parametric_helpers.scad>

module dovetail_root(width, height, length, show_fea=false) {
    // Standard dovetail slot connector
    translate([0, 0, -height/2.0])
    difference() {
        union() {
            // Dovetail shape: flared base
            color(show_fea ? [0.9, 0.1, 0.1] : [0.72, 0.73, 0.75]) // Red for FEA stress concentration
            linear_extrude(height=length, center=true)
            polygon(points=[
                [-width/2.0, -height/2.0],
                [width/2.0, -height/2.0],
                [width * 0.75 / 2.0, height/2.0],
                [-width * 0.75 / 2.0, height/2.0]
            ]);
            // platform base plate
            translate([0, 0, height/2.0])
            color(show_fea ? [0.9, 0.5, 0.1] : [0.65, 0.65, 0.67]) // Orange for platform stress
            cube([width * 1.5, width * 1.5, height * 0.3], center=true);
        }
    }
}

module blade_body(chord, span, twist, root_t_ratio, tip_t_ratio, camber, camber_pos, lean_angle, scale_factor, is_blisk=false, show_fea=false) {
    slices = 10;
    dz = span / slices;
    
    color(show_fea ? [0.15, 0.7, 0.2] : [0.8, 0.82, 0.85])
    for (i = [0 : slices-1]) {
        z1 = i * dz;
        z2 = (i + 1) * dz;
        
        t1 = root_t_ratio + (tip_t_ratio - root_t_ratio) * (i / slices);
        t2 = root_t_ratio + (tip_t_ratio - root_t_ratio) * ((i + 1) / slices);
        
        s1 = 1.0 - (1.0 - scale_factor) * (i / slices);
        s2 = 1.0 - (1.0 - scale_factor) * ((i + 1) / slices);
        
        rot1 = -twist * (i / slices);
        rot2 = -twist * ((i + 1) / slices);
        
        // Bezier S-sweep & lean curve for Stage 0 Fan (Blisk)
        p0 = [0.0, 0.0];
        p1 = [0.0, 2.0];
        p2 = [chord * 0.15, 5.0];
        p3 = [chord * 0.35, 9.0]; // organic forward sweep and lean at tip
        
        pos1 = (is_blisk) ? bezier_eval(p0, p1, p2, p3, i / slices) : [0.0, z1 * tan(lean_angle)];
        pos2 = (is_blisk) ? bezier_eval(p0, p1, p2, p3, (i + 1) / slices) : [0.0, z2 * tan(lean_angle)];
        
        sweep_x1 = pos1[0];
        lean_y1  = pos1[1];
        sweep_x2 = pos2[0];
        lean_y2  = pos2[1];
        
        hull() {
            translate([sweep_x1, lean_y1, z1])
            rotate([0, 0, rot1])
            scale([s1, s1, 1])
            linear_extrude(height=0.1)
            polygon(points=naca_profile_points(chord=chord, max_t=t1, m=camber, p=camber_pos, n=30));
            
            translate([sweep_x2, lean_y2, z2])
            rotate([0, 0, rot2])
            scale([s2, s2, 1])
            linear_extrude(height=0.1)
            polygon(points=naca_profile_points(chord=chord, max_t=t2, m=camber, p=camber_pos, n=30));
        }
    }
}

/**
 * @brief Single compressor blade with twist, linear thickness taper, lean angle and dovetail root
 * @param chord Chord width (mm)
 * @param span Blade height (mm)
 * @param stagger_angle Base rotation angle (deg)
 * @param twist Total twist angle top-to-bottom (deg)
 * @param thickness_ratio Thickness relative to chord (e.g. 0.08) - fallback/default
 * @param is_blisk Enable blended fillet root (no dovetail platform)
 * @param show_fea Enable FEA stress heatmap coloring
 * @param lean_angle Angle of lean in degrees (def 4)
 * @param root_thickness_ratio Thickness ratio at the blade root (def 0.12)
 * @param tip_thickness_ratio Thickness ratio at the blade tip (def 0.06)
 */
module compressor_blade(chord=25, span=40, stagger_angle=30, twist=15, thickness_ratio=0.08, is_blisk=false, show_fea=false, lean_angle=4, root_thickness_ratio=0.12, tip_thickness_ratio=0.06) {
    root_width = 8;
    platform_h = 3;
    
    // Use thickness_ratio to scale the default root/tip thickness if default was changed by caller
    actual_root_t = (thickness_ratio != 0.08) ? thickness_ratio * (0.12 / 0.08) : root_thickness_ratio;
    actual_tip_t = (thickness_ratio != 0.08) ? thickness_ratio * (0.06 / 0.08) : tip_thickness_ratio;

    if (is_blisk) {
        // 1. Blended fillet transition collar for Integrally Bladed Rotor (Blisk)
        color(show_fea ? [0.9, 0.5, 0.1] : [0.7, 0.72, 0.75])
        translate([0, 0, 0])
        cylinder(h=2.2, r1=root_width * 1.0, r2=root_width * 0.65, center=false, $fn=16);
        
        // 2. Highly curved, swept Blisk blade body (e.g. Stage 0 Front Fan)
        translate([0, 0, 1.8])
        rotate([0, 0, stagger_angle])
        blade_body(chord=chord, span=span, twist=twist, root_t_ratio=actual_root_t, tip_t_ratio=actual_tip_t, camber=0.06, camber_pos=0.4, lean_angle=lean_angle, scale_factor=0.52, is_blisk=true, show_fea=show_fea);
    } else {
        // 1. Dovetail connector at base
        translate([0, 0, 0])
        rotate([0, 0, stagger_angle])
        dovetail_root(width=root_width, height=platform_h, length=chord, show_fea=show_fea);

        // 2. Twisted Blade body with lean and thickness taper
        translate([0, 0, platform_h])
        rotate([0, 0, stagger_angle])
        blade_body(chord=chord, span=span, twist=twist, root_t_ratio=actual_root_t, tip_t_ratio=actual_tip_t, camber=0.04, camber_pos=0.4, lean_angle=lean_angle, scale_factor=0.68, is_blisk=false, show_fea=show_fea);
    }
}

// Preview
color("lightsteelblue")
compressor_blade();
