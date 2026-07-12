/**
 * @file parametric_helpers.scad
 * @brief Parametric 3D Modeling Utility Library
 * @details Contains shared constants, modules, and functions for geometric arraying,
 *          rounded cylinders, and coordinate transformations.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

// Global Constants
PI = 3.14159265358979323846;
GOLDEN_RATIO = 1.618033988749894;
TOLERANCE = 0.05;

// Functions
function deg2rad(d) = d * PI / 180.0;
function rad2deg(r) = r * 180.0 / PI;
function lerp(a, b, t) = a + (b - a) * t;

// Modules

/**
 * @brief Distributes children shapes in a circular array
 * @param n Number of instances
 * @param radius Radius of array circle
 */
module circular_array(n, radius) {
    for (i = [0 : n - 1]) {
        angle = i * 360.0 / n;
        rotate([0, 0, angle])
        translate([radius, 0, 0])
        children();
    }
}

/**
 * @brief Distributes children shapes in a linear array along X-axis
 * @param n Number of instances
 * @param spacing Distance between instances
 */
module linear_array(n, spacing) {
    for (i = [0 : n - 1]) {
        translate([i * spacing, 0, 0])
        children();
    }
}

/**
 * @brief Hollow cylinder (tube) along Z-axis
 * @param h Tube height
 * @param outer_r Outer radius
 * @param inner_r Inner radius
 * @param fn Resolution
 */
module tube(h, outer_r, inner_r, fn=64) {
    difference() {
        cylinder(h=h, r=outer_r, center=true, $fn=fn);
        cylinder(h=h + TOLERANCE * 2.0, r=inner_r, center=true, $fn=fn);
    }
}

/**
 * @brief Torus shape centered at origin
 * @param R Major radius (ring center distance)
 * @param r Minor radius (cross section radius)
 * @param fn Resolution
 */
module torus(R, r, fn=64) {
    rotate_extrude($fn=fn)
    translate([R, 0, 0])
    circle(r=r, $fn=fn);
}

/**
 * @brief Rounded cylinder (filleted top and bottom edges) using Minkowski
 * @param h Height
 * @param r Radius
 * @param fillet_r Edge radius
 * @param fn Resolution
 */
module rounded_cylinder(h, r, fillet_r, fn=64) {
    minkowski() {
        cylinder(h = h - 2.0 * fillet_r, r = r - fillet_r, center = true, $fn = fn);
        sphere(r = fillet_r, $fn = fn);
    }
}

/**
 * @brief 2D fillet helper
 * @param r Fillet radius
 */
module fillet_2d(r) {
    difference() {
        square([r, r]);
        translate([r, r])
        circle(r=r, $fn=64);
    }
}

/**
 * @brief 2D chamfer helper
 * @param size Chamfer length
 */
module chamfer_2d(size) {
    polygon(points=[[0,0], [size,0], [0,size]]);
}

/**
 * @brief Ball bearing assembly (inner ring, outer ring, balls)
 */
module bearing_assembly(inner_dia, outer_dia, width, num_balls=10) {
    color("silver")
    difference() {
        // Outer ring
        cylinder(h=width, r=outer_dia / 2.0, center=true, $fn=64);
        cylinder(h=width + 1.0, r=(outer_dia + inner_dia)/4.0 + (outer_dia - inner_dia)/8.0 * 0.8, center=true, $fn=64);
    }
    color("silver")
    difference() {
        // Inner ring
        cylinder(h=width, r=(outer_dia + inner_dia)/4.0 - (outer_dia - inner_dia)/8.0 * 0.8, center=true, $fn=64);
        cylinder(h=width + 1.0, r=inner_dia / 2.0, center=true, $fn=64);
    }
    // Balls (arranged in circular array)
    color([0.9, 0.92, 0.95]) // Chrome steel bearing balls
    let (ball_radius = (outer_dia - inner_dia) / 8.0, pitch_radius = (outer_dia + inner_dia) / 4.0) {
        circular_array(n=num_balls, radius=pitch_radius)
        sphere(r=ball_radius * 0.95, $fn=32);
    }
}

/**
 * @brief Bolted assembly flange with hexagonal head bolts
 */
module bolted_flange(outer_r, inner_r, thickness, num_bolts=16, bolt_r=2.5) {
    color("darkgray")
    difference() {
        // Flange ring
        cylinder(h=thickness, r=outer_r, center=true, $fn=128);
        cylinder(h=thickness + 1.0, r=inner_r, center=true, $fn=128);
        
        // Bolt holes
        circular_array(n=num_bolts, radius=(outer_r + inner_r)/2.0)
        cylinder(h=thickness + 2.0, r=bolt_r, center=true, $fn=16);
    }
    // Hexagonal bolts
    color([0.72, 0.73, 0.75]) // Hardened steel zinc-plated bolts
    circular_array(n=num_bolts, radius=(outer_r + inner_r)/2.0)
    translate([0, 0, thickness/2.0])
    cylinder(h=bolt_r * 1.5, r=bolt_r * 1.6, center=false, $fn=6);
}

/**
 * @brief Dovetail slot profile shape for cutting blade roots
 */
module dovetail_slot_profile(width, height) {
    polygon(points=[
        [-width * 0.76 / 2.0, height/2.0],
        [width * 0.76 / 2.0, height/2.0],
        [width/2.0, -height/2.0],
        [-width/2.0, -height/2.0]
    ]);
}

/*
// Preview Examples
translate([0, 0, 0]) {
    // Tube example
    color("teal") tube(h=30, outer_r=15, inner_r=12);
    
    // Torus example
    translate([45, 0, 0])
    color("crimson") torus(R=20, r=4);

    // Rounded Cylinder example
    translate([-45, 0, 0])
    color([0.75, 0.65, 0.4]) rounded_cylinder(h=25, r=10, fillet_r=2.0);

    // Bearing example
    translate([0, 45, 0])
    bearing_assembly(inner_dia=20, outer_dia=40, width=12);

    // Bolted Flange example
    translate([0, -45, 0])
    bolted_flange(outer_r=30, inner_r=20, thickness=6, num_bolts=12);
}
*/

