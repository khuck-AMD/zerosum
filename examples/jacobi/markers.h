/***************************************************************************
 Copyright (c) 2022, Advanced Micro Devices, Inc. All rights reserved.
***************************************************************************/

#ifndef MARKERS_H
#define MARKERS_H

#include <hip/hip_runtime.h>
#include <iostream>
#include <sstream>
#include <stdexcept>

#define CONCAT_(x, y) x##y
#define CONCAT(x, y) CONCAT_(x, y)

#include <roctracer_ext.h>
#include <roctx.h>

#define BEGIN_RANGE(name, group)                                               \
  do {                                                                         \
    std::stringstream ss;                                                      \
    ss << (name) << "::" << (group);                                           \
    std::string str = ss.str();                                                \
    const char *cstr = str.c_str();                                            \
    roctxRangePush(cstr);                                                      \
  } while (0) // must terminate with semi-colon

#define END_RANGE()                                                            \
  do {                                                                         \
    if (roctxRangePop() < 0) {                                                 \
      std::stringstream ss;                                                    \
      ss << "rocTX error popping range." << std::endl;                         \
      std::string str = ss.str();                                              \
      throw std::runtime_error(str);                                           \
    }                                                                          \
  } while (0)

// embed event recording in class to automatically pop when destroyed
class ScopedRange {
public:
  ScopedRange(const char *name, const char *group) {
    std::stringstream ss;
    ss << (name) << "::" << (group);
    std::string str = ss.str();
    const char *cstr = str.c_str();
    roctxRangePush(cstr);
  }
  ~ScopedRange() { roctxRangePop(); }
};

#define SCOPED_RANGE(name, group)                                              \
  ScopedRange CONCAT(range, __COUNTER__)((name), (group))

#define MARKER(name, group)                                                    \
  do {                                                                         \
    std::stringstream ss;                                                      \
    ss << (name) << "::" << (group);                                           \
    std::string str = ss.str();                                                \
    const char *cstr = str.c_str();                                            \
    roctxMark(cstr);                                                           \
  } while (0) // must terminate with semi-colon

static inline void initialize_logger() { roctracer_start(); }

static inline void finalize_logger() { roctracer_stop(); }

#endif // MARKERS_H
