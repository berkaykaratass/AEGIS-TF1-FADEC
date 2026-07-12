/**
 * @file engine_system.hpp
 * @brief Parent Engine System Composition & Sequential Control Loop
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C++:2008
 */

#ifndef ENGINE_SYSTEM_HPP
#define ENGINE_SYSTEM_HPP

#include "fadec_types.hpp"

namespace FADEC {

    class StateEstimator {
    public:
        void init(EstimatorState* state);
        void update(EstimatorState* state, 
                    double fuel_flow_pct, 
                    double vane_angle_deg, 
                    double measured_n1_rpm, 
                    bool n1_valid,
                    double measured_p3_bar, 
                    bool p3_valid, 
                    double dt);
        static bool is_positive_definite(const double P[3][3]);
    };

    class SafetyKernel {
    public:
        void init(SafetyState* state);
        int32_t process_stt(SafetyState* state,
                            const SensorState* raw_sensors,
                            uint32_t cbit_flags,
                            double requested_wf_pct,
                            double* safe_wf_pct,
                            double dt);
    };

    class WatermarkMonitor {
    public:
        void init(CyberState* state);
        void update(CyberState* state, double control_input, double measured_value);
    };

    class FadecController {
    public:
        void init(EngineState* state);
        void update(EngineState* state, const SensorState* sensors, ActuatorState* actuators, double dt);
    };

    class Engine {
    public:
        void init();
        
        /**
         * @brief Sequential execution pipeline:
         *        FDIR -> EKF -> Control Laws -> Watermark -> Safety Kernel -> Actuators
         */
        void step(const SensorState* sensors, ActuatorState* actuators, uint32_t cbit_flags, double dt);

        EngineState state;
    };

} // namespace FADEC

#endif // ENGINE_SYSTEM_HPP
