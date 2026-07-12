/**
 * @file airfoil_profiles.scad
 * @brief NACA 4-digit Airfoil Profile Generator
 * @details Computes camber lines and thickness coordinates for compressor and turbine blades.
 * 
 * Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
 */

// Generate x coordinates spacing from 0 to chord
function airfoil_x_coords(chord, n) = [ for (i = [0 : n]) chord * (1.0 - cos(i * 90.0 / n)) ];

// Standard NACA thickness distribution
function naca_thickness(x, chord, max_t) = 
    let (
        xc = x / chord,
        a0 = 0.2969,
        a1 = -0.1260,
        a2 = -0.3516,
        a3 = 0.2843,
        a4 = -0.1015,
        term = a0 * sqrt(xc) + a1 * xc + a2 * pow(xc, 2) + a3 * pow(xc, 3) + a4 * pow(xc, 4)
    )
    (max_t / 0.2) * chord * term;

// NACA Camber line (m = max camber, p = position of max camber, c = chord)
function naca_camber(x, chord, m, p) =
    (x < p * chord) ?
    (m * (x / pow(p, 2.0)) * (2.0 * p - (x / chord))) :
    (m * ((chord - x) / pow(1.0 - p, 2.0)) * (1.0 + (x / chord) - 2.0 * p));

// Camber line derivative/slope angle (theta)
function naca_camber_slope(x, chord, m, p) =
    let (
        dy_dx = (x < p * chord) ?
                ((2.0 * m) / pow(p, 2.0)) * (p - (x / chord)) :
                ((2.0 * m) / pow(1.0 - p, 2.0)) * (p - (x / chord))
    )
    atan(dy_dx);

// Calculate upper and lower coordinates
function naca_profile_points(chord, max_t, m, p, n=30) =
    let (
        x_vals = airfoil_x_coords(chord, n),
        upper_pts = [ for (i = [0 : n]) 
            let (
                x = x_vals[i],
                yt = naca_thickness(x, chord, max_t),
                yc = naca_camber(x, chord, m, p),
                theta = naca_camber_slope(x, chord, m, p)
            )
            [x - yt * sin(theta), yc + yt * cos(theta)]
        ],
        lower_pts = [ for (i = [n : -1 : 0]) 
            let (
                x = x_vals[i],
                yt = naca_thickness(x, chord, max_t),
                yc = naca_camber(x, chord, m, p),
                theta = naca_camber_slope(x, chord, m, p)
            )
            [x + yt * sin(theta), yc - yt * cos(theta)]
        ]
    )
    concat(upper_pts, lower_pts);

/**
 * @brief Extrudes a 2D NACA airfoil into 3D
 * @param chord Blade chord (length)
 * @param span Blade span (height)
 * @param max_t Maximum thickness ratio (e.g. 0.12)
 * @param camber Maximum camber ratio (e.g. 0.04)
 * @param camber_pos Position of maximum camber ratio (e.g. 0.40)
 */
module naca_airfoil_solid(chord, span, max_t, camber, camber_pos, n=20) {
    pts = naca_profile_points(chord, max_t, camber, camber_pos, n);
    linear_extrude(height=span, center=true)
    polygon(points=pts);
}

// Evaluates a cubic Bezier curve in 2D or 3D at parameter t (0 <= t <= 1)
function bezier_eval(p0, p1, p2, p3, t) = 
    (1.0 - t)*(1.0 - t)*(1.0 - t)*p0 + 
    3.0*(1.0 - t)*(1.0 - t)*t*p1 + 
    3.0*(1.0 - t)*t*t*p2 + 
    t*t*t*p3;

// Generates a list of n points along a cubic Bezier curve
function bezier_curve_points(p0, p1, p2, p3, n=15) = 
    [ for (i = [0 : n]) bezier_eval(p0, p1, p2, p3, i / n) ];

// Preview
color("cornflowerblue")
naca_airfoil_solid(chord=40, span=60, max_t=0.12, camber=0.04, camber_pos=0.4);
