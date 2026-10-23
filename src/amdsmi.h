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

#pragma once

#include "zerosum.h"
#include "amd_smi/amdsmi.h"

#define AMDSMI_CALL(call)                                                    \
try {                                                                         \
    static bool seen{false};                                                  \
    amdsmi_status_t _status = call;                                           \
    if (_status != AMDSMI_STATUS_SUCCESS && !seen) {                          \
        const char *errstr;                                                   \
        if (amdsmi_status_code_to_string(_status, &errstr) == AMDSMI_STATUS_SUCCESS) {   \
        fprintf(stderr, "%s:%d: error: device %d function %s failed with error %d: %s.\n", \
                __FILE__, __LINE__, d, #call, _status, errstr);              \
        fprintf(stderr, "\nError: AMD SMI call failed\n");                   \
        /*exit(0);*/                                                          \
        seen = true;                                                          \
        }                                                                     \
    }                                                                         \
} catch (const std::system_error& ex) {                                       \
    std::cout << "Caught system_error with code "                             \
                     "[" << ex.code() << "] meaning "                         \
                     "[" << ex.what() << "]\n";                               \
} catch (const std::exception& ex) {                                          \
    std::cerr << ex.what() << std::endl;                                      \
};

namespace zerosum {

std::vector<uint32_t> initialize_amd_smi(void);
void finalize_amd_smi(void);

class ScopedAMDSMI {
private:
public:
    std::vector<uint32_t> devices;
    ScopedAMDSMI(void) {
        devices = initialize_amd_smi();
    }
    ~ScopedAMDSMI(void) {
        finalize_amd_smi();
    }
};

}
