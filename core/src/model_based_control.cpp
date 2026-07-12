/**
 * @file model_based_control.cpp
 * @brief Extended Kalman Filter (EKF) State Estimator with Joseph Stabilization & Certified LUT Fallback
 * 
 * @compliance DO-178C DAL A / MISRA C++:2008
 */

#include "engine_system.hpp"
#include "model_based_control.h"
extern "C" {
#include "fadec_assert.h"
}
#include <cmath>

#define ENV_N1_MIN  0.0
#define ENV_N1_MAX  38500.0   /* 110% design speed */
#define ENV_T2_MIN  200.0
#define ENV_T2_MAX  340.0
#define ENV_P2_MIN  0.1
#define ENV_P2_MAX  1.1

/* Precomputed grid points for certified steady-state engine performance mapping */
static constexpr double GRID_N1[3] = {15000.0, 33000.0, 35000.0};
static constexpr double GRID_T2[2] = {250.0, 300.0};
static constexpr double GRID_P2[2] = {0.3, 1.0};

/* 3D grid values for T4.1 (index order: N1(3), T2(2), P2(2)) */
static constexpr double LUT_T41[3][2][2] = {
    /* N1 = 15000 */
    {
        { 600.0, 620.0 }, /* T2=250: P2=0.3, P2=1.0 */
        { 650.0, 670.0 }  /* T2=300: P2=0.3, P2=1.0 */
    },
    /* N1 = 33000 */
    {
        { 1100.0, 1150.0 },
        { 1200.0, 1250.0 }
    },
    /* N1 = 35000 */
    {
        { 1400.0, 1450.0 },
        { 1500.0, 1550.0 }
    }
};

/* 3D grid values for Stall Margin (index order: N1(3), T2(2), P2(2)) */
static constexpr double LUT_STALL[3][2][2] = {
    /* N1 = 15000 */
    {
        { 0.35, 0.36 },
        { 0.34, 0.35 }
    },
    /* N1 = 33000 */
    {
        { 0.28, 0.29 },
        { 0.26, 0.27 }
    },
    /* N1 = 35000 */
    {
        { 0.22, 0.23 },
        { 0.20, 0.21 }
    }
};

namespace FADEC {

    static void get_lut_state(double n1_rpm, double t2_k, double p2_bar, double x_out[3]) {
        double clamped_n1 = n1_rpm;
        if (clamped_n1 < ENV_N1_MIN) { clamped_n1 = ENV_N1_MIN; }
        if (clamped_n1 > ENV_N1_MAX) { clamped_n1 = ENV_N1_MAX; }

        double clamped_t2 = t2_k;
        if (clamped_t2 < ENV_T2_MIN) { clamped_t2 = ENV_T2_MIN; }
        if (clamped_t2 > ENV_T2_MAX) { clamped_t2 = ENV_T2_MAX; }

        double clamped_p2 = p2_bar;
        if (clamped_p2 < ENV_P2_MIN) { clamped_p2 = ENV_P2_MIN; }
        if (clamped_p2 > ENV_P2_MAX) { clamped_p2 = ENV_P2_MAX; }

        int32_t i = 0;
        if (clamped_n1 < GRID_N1[1]) {
            i = 0;
        } else {
            i = 1;
        }

        double w_n1 = (clamped_n1 - GRID_N1[i]) / (GRID_N1[i+1] - GRID_N1[i]);
        double w_t2 = (clamped_t2 - GRID_T2[0]) / (GRID_T2[1] - GRID_T2[0]);
        double w_p2 = (clamped_p2 - GRID_P2[0]) / (GRID_P2[1] - GRID_P2[0]);

        double c000 = LUT_T41[i][0][0];
        double c001 = LUT_T41[i][0][1];
        double c010 = LUT_T41[i][1][0];
        double c011 = LUT_T41[i][1][1];
        double c100 = LUT_T41[i+1][0][0];
        double c101 = LUT_T41[i+1][0][1];
        double c110 = LUT_T41[i+1][1][0];
        double c111 = LUT_T41[i+1][1][1];

        double t41_interp = 
            (1.0 - w_n1) * ((1.0 - w_t2) * ((1.0 - w_p2) * c000 + w_p2 * c001) + w_t2 * ((1.0 - w_p2) * c010 + w_p2 * c011)) +
            w_n1 * ((1.0 - w_t2) * ((1.0 - w_p2) * c100 + w_p2 * c101) + w_t2 * ((1.0 - w_p2) * c110 + w_p2 * c111));

        double s000 = LUT_STALL[i][0][0];
        double s001 = LUT_STALL[i][0][1];
        double s010 = LUT_STALL[i][1][0];
        double s011 = LUT_STALL[i][1][1];
        double s100 = LUT_STALL[i+1][0][0];
        double s101 = LUT_STALL[i+1][0][1];
        double s110 = LUT_STALL[i+1][1][0];
        double s111 = LUT_STALL[i+1][1][1];

        double stall_interp = 
            (1.0 - w_n1) * ((1.0 - w_t2) * ((1.0 - w_p2) * s000 + w_p2 * s001) + w_t2 * ((1.0 - w_p2) * s010 + w_p2 * s011)) +
            w_n1 * ((1.0 - w_t2) * ((1.0 - w_p2) * s100 + w_p2 * s101) + w_t2 * ((1.0 - w_p2) * s110 + w_p2 * s111));

        x_out[0] = clamped_n1;
        x_out[1] = t41_interp;
        x_out[2] = stall_interp;
    }

    static void joseph_update(double P[3][3], const double h[3], double r, const double K[3]) {
        double I_Kh[3][3];
        for (int32_t i = 0; i < 3; i++) {
            for (int32_t j = 0; j < 3; j++) {
                double delta = (i == j) ? 1.0 : 0.0;
                I_Kh[i][j] = delta - (K[i] * h[j]);
            }
        }

        double temp[3][3];
        for (int32_t i = 0; i < 3; i++) {
            for (int32_t j = 0; j < 3; j++) {
                double sum = 0.0;
                for (int32_t k = 0; k < 3; k++) {
                    sum += I_Kh[i][k] * P[k][j];
                }
                temp[i][j] = sum;
            }
        }

        for (int32_t i = 0; i < 3; i++) {
            for (int32_t j = 0; j < 3; j++) {
                double sum = 0.0;
                for (int32_t k = 0; k < 3; k++) {
                    sum += temp[i][k] * I_Kh[j][k];
                }
                P[i][j] = sum + (K[i] * r * K[j]);
            }
        }
    }

    static void inflate_covariance(double P[3][3]) {
        for (int32_t i = 0; i < 3; i++) {
            if (P[i][i] < 1e-5) {
                P[i][i] += 1e-4;
            }
        }
    }

    bool StateEstimator::is_positive_definite(const double P[3][3]) {
        bool is_pd = true;

        if ((P[0][0] <= 0.0) || (P[1][1] <= 0.0) || (P[2][2] <= 0.0)) {
            is_pd = false;
        }
        else {
            double minor_01 = (P[0][0] * P[1][1]) - (P[0][1] * P[0][1]);
            double minor_02 = (P[0][0] * P[2][2]) - (P[0][2] * P[0][2]);
            double minor_12 = (P[1][1] * P[2][2]) - (P[1][2] * P[1][2]);

            if ((minor_01 <= 0.0) || (minor_02 <= 0.0) || (minor_12 <= 0.0)) {
                is_pd = false;
            }
            else {
                double det3x3 = (P[0][0] * minor_12)
                              - (P[0][1] * ((P[0][1] * P[2][2]) - (P[0][2] * P[1][2])))
                              + (P[0][2] * ((P[0][1] * P[1][2]) - (P[0][2] * P[1][1])));
                if (det3x3 <= 0.0) {
                    is_pd = false;
                }
            }
        }
        return is_pd;
    }

    void StateEstimator::init(EstimatorState* state) {
        if (state != nullptr) {
            state->x[0] = 0.0;
            state->x[1] = 288.15;
            state->x[2] = 0.35;

            state->estimated_t41_k = 288.15;
            state->estimated_stall_margin = 0.35;
            state->fallback_active = false;
            state->consecutive_failures = 0U;

            for (int32_t i = 0; i < 3; i++) {
                for (int32_t j = 0; j < 3; j++) {
                    state->P[i][j] = (i == j) ? 1.0 : 0.0;
                }
            }

            state->Q[0][0] = 100.0;
            state->Q[1][1] = 1.0;
            state->Q[2][2] = 0.0001;

            state->R[0][0] = 2.0;
            state->R[1][1] = 0.01;
        }
    }

    void StateEstimator::update(EstimatorState* state, 
                                double fuel_flow_pct, 
                                double vane_angle_deg, 
                                double measured_n1_rpm, 
                                bool n1_valid,
                                double measured_p3_bar, 
                                bool p3_valid, 
                                double dt) {
        FADEC_PRE(state != nullptr, state);
        FADEC_PRE(dt > 0.0, state);
        FADEC_PRE(fuel_flow_pct >= 0.0 && fuel_flow_pct <= 100.0, state);
        FADEC_PRE(vane_angle_deg >= -45.0 && vane_angle_deg <= 45.0, state);

        if ((state != nullptr) && (dt > 0.0)) {
            if (state->fallback_active) {
                double x_lut[3];
                get_lut_state(measured_n1_rpm, 288.15, 1.013, x_lut);
                state->x[0] = x_lut[0];
                state->x[1] = x_lut[1];
                state->x[2] = x_lut[2];
                state->estimated_t41_k = state->x[1];
                state->estimated_stall_margin = state->x[2];
                return;
            }

            double x0_prev = state->x[0];
            double x1_prev = state->x[1];
            double x2_prev = state->x[2];

            double a_speed, b_speed_wf, b_speed_vane;
            double a_temp, b_temp_wf;
            double a_stall, b_stall_wf, b_stall_vane;

            if (x0_prev < 30000.0) {
                a_speed = 0.12; b_speed_wf = 700.0; b_speed_vane = 1.5;
                a_temp = 0.4; b_temp_wf = 20.0;
                a_stall = 0.15; b_stall_wf = -0.0004; b_stall_vane = 0.0015;
            }
            else if (x0_prev < 38000.0) {
                a_speed = 0.15; b_speed_wf = 800.0; b_speed_vane = 2.0;
                a_temp = 0.5; b_temp_wf = 25.0;
                a_stall = 0.20; b_stall_wf = -0.0005; b_stall_vane = 0.0020;
            }
            else {
                a_speed = 0.18; b_speed_wf = 900.0; b_speed_vane = 2.5;
                a_temp = 0.6; b_temp_wf = 30.0;
                a_stall = 0.25; b_stall_wf = -0.0006; b_stall_vane = 0.0025;
            }

            state->x[0] = (1.0 - (a_speed * dt)) * x0_prev + (b_speed_wf * dt) * fuel_flow_pct + (b_speed_vane * dt) * vane_angle_deg;
            state->x[1] = (1.0 - (a_temp * dt)) * x1_prev + (b_temp_wf * dt) * fuel_flow_pct + (288.15 * a_temp * dt);
            state->x[2] = (1.0 - (a_stall * dt)) * x2_prev + (b_stall_wf * dt) * fuel_flow_pct + (b_stall_vane * dt) * vane_angle_deg + (0.35 * a_stall * dt);

            double F00 = 1.0 - (a_speed * dt);
            double F11 = 1.0 - (a_temp * dt);
            double F22 = 1.0 - (a_stall * dt);

            double P_prev[3][3];
            for (int32_t i = 0; i < 3; i++) {
                for (int32_t j = 0; j < 3; j++) {
                    P_prev[i][j] = state->P[i][j];
                }
            }

            double P_pred[3][3];
            P_pred[0][0] = (F00 * P_prev[0][0] * F00) + (state->Q[0][0] * dt);
            P_pred[0][1] = (F00 * P_prev[0][1] * F11);
            P_pred[0][2] = (F00 * P_prev[0][2] * F22);

            P_pred[1][0] = P_pred[0][1];
            P_pred[1][1] = (F11 * P_prev[1][1] * F11) + (state->Q[1][1] * dt);
            P_pred[1][2] = (F11 * P_prev[1][2] * F22);

            P_pred[2][0] = P_pred[0][2];
            P_pred[2][1] = P_pred[1][2];
            P_pred[2][2] = (F22 * P_prev[2][2] * F22) + (state->Q[2][2] * dt);

            for (int32_t i = 0; i < 3; i++) {
                for (int32_t j = 0; j < 3; j++) {
                    state->P[i][j] = P_pred[i][j];
                }
            }

            bool correction_ok = true;

            if (n1_valid) {
                double h[3] = {1.0, 0.0, 0.0};
                double r = state->R[0][0];
                double y = measured_n1_rpm - state->x[0];

                double S = state->P[0][0] + r;
                double S_inv = (S > 1e-12) ? (1.0 / S) : 0.0;

                double mahalanobis_dist_sq = (y * y) * S_inv;
                if (mahalanobis_dist_sq > 9.0) {
                    correction_ok = false;
                } else {
                    double K[3];
                    K[0] = state->P[0][0] * S_inv;
                    K[1] = state->P[1][0] * S_inv;
                    K[2] = state->P[2][0] * S_inv;

                    state->x[0] += K[0] * y;
                    state->x[1] += K[1] * y;
                    state->x[2] += K[2] * y;

                    joseph_update(state->P, h, r, K);
                }
            }

            if (p3_valid && correction_ok) {
                double h2 = 1.013 + (state->x[0] * 1e-4 * (state->x[1] / 300.0));
                double y = measured_p3_bar - h2;

                double H10 = 3.3333333333333335e-7 * state->x[1];
                double H11 = 3.3333333333333335e-7 * state->x[0];
                double h[3] = {H10, H11, 0.0};
                double r = state->R[1][1];

                double S = (h[0] * h[0] * state->P[0][0])
                         + (h[0] * h[1] * state->P[0][1])
                         + (h[1] * h[0] * state->P[1][0])
                         + (h[1] * h[1] * state->P[1][1])
                         + r;
                double S_inv = (S > 1e-12) ? (1.0 / S) : 0.0;

                double mahalanobis_dist_sq = (y * y) * S_inv;
                if (mahalanobis_dist_sq > 9.0) {
                    correction_ok = false;
                } else {
                    double K[3];
                    K[0] = ((state->P[0][0] * h[0]) + (state->P[0][1] * h[1])) * S_inv;
                    K[1] = ((state->P[1][0] * h[0]) + (state->P[1][1] * h[1])) * S_inv;
                    K[2] = ((state->P[2][0] * h[0]) + (state->P[2][1] * h[1])) * S_inv;

                    state->x[0] += K[0] * y;
                    state->x[1] += K[1] * y;
                    state->x[2] += K[2] * y;

                    joseph_update(state->P, h, r, K);
                }
            }

            inflate_covariance(state->P);

            bool is_pd = is_positive_definite(state->P);
            FADEC_INV(is_pd, state);

            if (!is_pd || !correction_ok) {
                state->consecutive_failures++;
                if (state->consecutive_failures >= 50U) {
                    state->fallback_active = true;
                }
            } else {
                state->consecutive_failures = 0U;
            }

            FADEC_POST(state->x[0] >= 0.0, state);
            FADEC_POST(state->x[1] >= 0.0, state);
            FADEC_POST(state->x[2] >= 0.0 && state->x[2] <= 1.0, state);

            state->estimated_t41_k = state->x[1];
            state->estimated_stall_margin = state->x[2];
        }
    }

} // namespace FADEC

/* extern "C" Wrappers for absolute link-time compatibility */
extern "C" {

    void mbc_init(MBC_State_t *state) {
        FADEC::StateEstimator estimator;
        estimator.init(reinterpret_cast<FADEC::EstimatorState*>(state));
    }

    void mbc_ekf_step(MBC_State_t *state, 
                      double fuel_flow_pct, 
                      double vane_angle_deg, 
                      double measured_n1_rpm, 
                      bool n1_valid,
                      double measured_p3_bar, 
                      bool p3_valid, 
                      double dt) {
        FADEC::StateEstimator estimator;
        estimator.update(reinterpret_cast<FADEC::EstimatorState*>(state),
                         fuel_flow_pct,
                         vane_angle_deg,
                         measured_n1_rpm,
                         n1_valid,
                         measured_p3_bar,
                         p3_valid,
                         dt);
    }

    bool mbc_ekf_is_positive_definite(const double P[3][3]) {
        return FADEC::StateEstimator::is_positive_definite(P);
    }

}
