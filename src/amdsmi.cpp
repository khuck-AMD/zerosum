/*
 * MIT License
 *
 * Copyright (c) 2023-2025 University of Oregon, Kevin Huck
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#include "amdsmi.h"
#include "hip/hip_runtime.h"
#include <sstream>
#include <cstring>

#define MICROJOULES 1.0e-6

namespace {
std::vector<amdsmi_processor_handle> g_processors;
}

namespace zerosum {

    std::vector<uint32_t> initialize_amd_smi(void) {
        uint32_t deviceCount{0};
        uint32_t d{0}; // for AMDSMI_CALL support
        AMDSMI_CALL(amdsmi_init(AMDSMI_INIT_AMD_GPUS));
        amdsmi_version_t version;
        AMDSMI_CALL(amdsmi_get_lib_version(&version));

        uint32_t socketCount{0};
        AMDSMI_CALL(amdsmi_get_socket_handles(&socketCount, nullptr));
        std::vector<amdsmi_socket_handle> sockets(socketCount);
        AMDSMI_CALL(amdsmi_get_socket_handles(&socketCount, sockets.data()));
        g_processors.clear();
        for (auto socket : sockets) {
            uint32_t procCount{0};
            AMDSMI_CALL(amdsmi_get_processor_handles(socket, &procCount, nullptr));
            if (procCount == 0) {
                continue;
            }
            std::vector<amdsmi_processor_handle> procs(procCount);
            AMDSMI_CALL(amdsmi_get_processor_handles(socket, &procCount, procs.data()));
            g_processors.insert(g_processors.end(), procs.begin(), procs.end());
        }
        deviceCount = static_cast<uint32_t>(g_processors.size());
        if (ZeroSum::getInstance().getRank() == 0) {
            std::cout << "AMDSMI Version "
                << version.major << "."
                << version.minor << "."
                << version.release << " build "
                << version.build << ", Found "
                << deviceCount << " total devices" << std::endl;
        }
        // If HIP_VISIBLE_DEVICES is set, capture visible GPUs
        const char* gpu_visible_devices = getenv("ROCR_VISIBLE_DEVICES");
        std::vector<uint32_t> devices;
        if(gpu_visible_devices == NULL){
            for (uint32_t i = 0 ; i < deviceCount ; i++) {
                devices.push_back(i);
            }
        }
        else{
            if (ZeroSum::getInstance().getRank() == 0) {
                std::cout << "Visible devices: " << gpu_visible_devices << std::endl;
            }
            std::istringstream iss(gpu_visible_devices);
            std::string token;
            while (std::getline(iss, token, ',')) {
                uint32_t index = static_cast<uint32_t>(std::stol(token));
                if (index < deviceCount) {
                    devices.push_back(index);
                }
            }
        }
        return devices;
    }

    void finalize_amd_smi(void) {
        uint32_t d{0}; // for AMDSMI_CALL support
        AMDSMI_CALL(amdsmi_shut_down());
        g_processors.clear();
    }

    int ZeroSum::getgpustatus(void) {
        // create a scoped variable to initialize/finalize
        static ScopedAMDSMI doInit;
        uint64_t value{0};
        std::vector<std::map<std::string, std::string>> allfields;

        // map d to the real device ID - ROCm can see all of them!
        for (int32_t d : doInit.devices) {
            std::map<std::string, std::string> fields;
            if (static_cast<size_t>(d) >= g_processors.size()) {
                continue;
            }
            amdsmi_processor_handle ph = g_processors[d];
            /* Power, energy, temp, voltage */
            amdsmi_gpu_metrics_t pgpu_metrics;
            memset(&pgpu_metrics, 0, sizeof(amdsmi_gpu_metrics_t));
            AMDSMI_CALL(amdsmi_get_gpu_metrics_info(ph, &pgpu_metrics));
            fields.insert(std::pair(std::string("Power Average (W)"),
                std::to_string(double(pgpu_metrics.average_socket_power))));
            float counter_resolution = 0;
            uint64_t timestamp;
            uint64_t energy_count{0};
            AMDSMI_CALL(amdsmi_get_energy_count(ph, &energy_count, &counter_resolution, &timestamp));
            fields.insert(std::pair(std::string("Energy Average (J)"),
                std::to_string((double(energy_count)*counter_resolution)*MICROJOULES)));
            int64_t temperature;
            AMDSMI_CALL(amdsmi_get_temp_metric(ph, AMDSMI_TEMPERATURE_TYPE_EDGE, AMDSMI_TEMP_CURRENT, &temperature));
            fields.insert(std::pair(std::string("Temperature (C)"),
                std::to_string(double(temperature))));
            AMDSMI_CALL(amdsmi_get_gpu_volt_metric(ph, AMDSMI_VOLT_TYPE_VDDGFX, AMDSMI_VOLT_CURRENT, &temperature));
            fields.insert(std::pair(std::string("Voltage (mV)"),
                std::to_string((double(temperature)))));

            /* Memory */
            value = 0;
            AMDSMI_CALL(amdsmi_get_gpu_memory_total(ph, AMDSMI_MEM_TYPE_VRAM, &value));
            fields.insert(std::pair(std::string("Total VRAM Bytes"), std::to_string(value)));
            value = 0;
            AMDSMI_CALL(amdsmi_get_gpu_memory_usage(ph, AMDSMI_MEM_TYPE_VRAM, &value));
            fields.insert(std::pair(std::string("Used VRAM Bytes"), std::to_string(value)));
            value = 0;
            AMDSMI_CALL(amdsmi_get_gpu_memory_total(ph, AMDSMI_MEM_TYPE_VIS_VRAM, &value));
            fields.insert(std::pair(std::string("Total Visible VRAM Bytes"), std::to_string(value)));
            value = 0;
            AMDSMI_CALL(amdsmi_get_gpu_memory_usage(ph, AMDSMI_MEM_TYPE_VIS_VRAM, &value));
            fields.insert(std::pair(std::string("Used Visible VRAM Bytes"), std::to_string(value)));
            value = 0;
            AMDSMI_CALL(amdsmi_get_gpu_memory_total(ph, AMDSMI_MEM_TYPE_GTT, &value));
            fields.insert(std::pair(std::string("Total GTT Bytes"), std::to_string(value)));
            value = 0;
            AMDSMI_CALL(amdsmi_get_gpu_memory_usage(ph, AMDSMI_MEM_TYPE_GTT, &value));
            fields.insert(std::pair(std::string("Used GTT Bytes"), std::to_string(value)));

            /* utilization */
            uint32_t percent{0};
            amdsmi_engine_usage_t activity;
            memset(&activity, 0, sizeof(activity));
            AMDSMI_CALL(amdsmi_get_gpu_activity(ph, &activity));
            percent = activity.umc_activity;
            fields.insert(std::pair(std::string("Memory Busy %"), std::to_string(percent)));
            percent = 0;
            AMDSMI_CALL(amdsmi_get_gpu_busy_percent(ph, &percent));
            fields.insert(std::pair(std::string("Device Busy %"), std::to_string(percent)));
            percent = 0;
            amdsmi_utilization_counter_t utilization_counters[2];
            utilization_counters[0].type = AMDSMI_COARSE_GRAIN_GFX_ACTIVITY;
            utilization_counters[1].type = AMDSMI_COARSE_GRAIN_MEM_ACTIVITY;
            AMDSMI_CALL(amdsmi_get_utilization_count(ph, utilization_counters, 2, &timestamp));
            fields.insert(std::pair(std::string("GFX Activity %"), std::to_string(utilization_counters[0].value)));
            fields.insert(std::pair(std::string("Memory Activity %"), std::to_string(utilization_counters[1].value)));

            /* Metrics */
            fields.insert(std::pair(std::string("Clock Frequency, GLX (MHz)"), std::to_string(pgpu_metrics.current_gfxclk)));
            fields.insert(std::pair(std::string("Clock Frequency, SOC (MHz)"), std::to_string(pgpu_metrics.current_socclk)));
            fields.insert(std::pair(std::string("GFX Activity"), std::to_string(pgpu_metrics.average_gfx_activity)));
            fields.insert(std::pair(std::string("Memory Controller Activity"), std::to_string(pgpu_metrics.average_umc_activity)));
            fields.insert(std::pair(std::string("UVD|VCN Activity"), std::to_string(pgpu_metrics.average_mm_activity)));
            fields.insert(std::pair(std::string("Throttle Status"), std::to_string(pgpu_metrics.throttle_status)));
            allfields.push_back(fields);
        }
        computeNode.updateGPU(allfields, step);
        return 0;
    }
}
