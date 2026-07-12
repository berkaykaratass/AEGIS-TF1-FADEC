CXX=g++
CXXFLAGS=-Wall -Wextra -std=c++17 -pedantic -fno-exceptions -fno-rtti -fno-threadsafe-statics -fno-use-cxa-atexit -fvisibility=hidden -Icore/include

CC=gcc
CFLAGS=-Wall -Wextra -std=c11 -pedantic -lm -Icore/include

SRC_C=core/src/brayton_thermo.c \
      core/src/compressor_map.c \
      core/src/ehd_thrust.c \
      core/src/fadec_hal.c \
      core/src/fadec_assert.c \
      core/src/sensor_interface.c \
      core/src/rtos_tasks.c \
      core/src/cyber_defense.c \
      core/src/surge_predictor.c \
      core/src/engine_start.c \
      core/src/thrust_modes.c \
      core/src/fuel_schedule.c \
      core/src/vane_schedule.c \
      core/src/dual_channel.c \
      core/src/arinc429.c \
      core/src/triple_buffer.c \
      core/src/fdir_sensor.c \
      core/src/cognitive_engine.c \
      core/src/actuator_control.c \
      core/src/cyber_watermark.c \
      core/src/creep_governor.c \
      core/src/active_clearance.c \
      core/src/main.c \
      security/crypto/databus_encryption.c

SRC_CXX=core/src/model_based_control.cpp \
        core/src/safety_monitor.cpp \
        core/src/fadec_control.cpp \
        core/src/engine_system.cpp

OBJ_C=$(SRC_C:.c=.o)
OBJ_CXX=$(SRC_CXX:.cpp=.o)
OBJ=$(OBJ_C) $(OBJ_CXX)

all: core lib

core: $(OBJ)
	$(CXX) $(CXXFLAGS) -o fadec_core $(OBJ)

lib: $(OBJ)
	$(CXX) -shared -o libfadec.dylib $(OBJ)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

sim:
	PYTHONPATH=. uvicorn simulation.digital_twin.twin_api:app --host 0.0.0.0 --port 8024 --reload

dashboard:
	open simulation/visualization/dashboard.html

test:
	python3 -m pytest tests/

lint-c:
	cppcheck --enable=all core/src/

export-stl:
	mkdir -p modeling/exports
	/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o modeling/exports/engine_assembly.stl modeling/engine_assembly.scad -D "cross_section=false"
	/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o modeling/exports/compressor.stl modeling/compressor/axial_compressor.scad
	/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o modeling/exports/combustor.stl modeling/combustion/combustion_chamber.scad
	/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o modeling/exports/turbine.stl modeling/turbine/turbine_stage.scad
	@echo "STL models successfully exported to modeling/exports/ directory for Siemens NX integration."

# Cross-compiler definitions for ARM Cortex-R5F
CROSS_CC=arm-none-eabi-gcc
CROSS_CXX=arm-none-eabi-g++
CROSS_CFLAGS=-Wall -Wextra -std=c11 -pedantic -mthumb -mcpu=cortex-r5 -mfloat-abi=hard -mfpu=vfpv3-d16 -ffunction-sections -fdata-sections -Icore/include
CROSS_CXXFLAGS=-Wall -Wextra -std=c++17 -pedantic -fno-exceptions -fno-rtti -fno-threadsafe-statics -fno-use-cxa-atexit -mthumb -mcpu=cortex-r5 -mfloat-abi=hard -mfpu=vfpv3-d16 -ffunction-sections -fdata-sections -Icore/include

cross-compile:
	@echo "Starting Cross-Compilation for ARM Cortex-R5F..."
	@mkdir -p build_r5f
	@for file in $(SRC_C); do \
		echo "Cross-compiling C file: $$file"; \
		$(CROSS_CC) $(CROSS_CFLAGS) -c $$file -o build_r5f/$$(basename $$file .c).o || exit 1; \
	done
	@for file in $(SRC_CXX); do \
		echo "Cross-compiling C++ file: $$file"; \
		$(CROSS_CXX) $(CROSS_CXXFLAGS) -c $$file -o build_r5f/$$(basename $$file .cpp).o || exit 1; \
	done
	@echo "Linking objects into relocatable binary libfadec_r5f.o..."
	arm-none-eabi-ld -r -o libfadec_r5f.o build_r5f/*.o
	@echo "ARM Cortex-R5F target build completed successfully."

clean:
	rm -f $(OBJ) fadec_core libfadec.dylib libfadec_r5f.o
	rm -rf modeling/exports build_r5f
