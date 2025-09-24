/* Copyright (c) 2025 Advanced Micro Devices, Inc.

 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 THE SOFTWARE. */

#include <hip/amd_detail/hip_storage.h>

#include <hip/hip_runtime.h>
#include "hip_internal.hpp"

hipError_t hipFileRead(hipFileHandle_t handle, void* devicePtr, uint64_t size, int64_t file_offset,
                       uint64_t* size_copied, int32_t* status) {
  if (size == 0) {
    // Skip if nothing needs reading.
    return hipSuccess;
  }
  amd::Device* device = hip::getCurrentDevice()->devices()[0];
  if (device == nullptr) {
    LogError("Failed to get current device");
    return hipErrorInvalidDevice;
  }
#if defined(_WIN32)
  void* opaque = handle.handle;
#else
  void* opaque = reinterpret_cast<void*>(static_cast<intptr_t>(handle.fd));
#endif
  if (!device->fileRead(opaque, devicePtr, size, file_offset, size_copied, status)) {
    LogError("Failed to perform file read operation");
    return hipErrorInvalidValue;
  }
  return hipSuccess;
}

hipError_t hipFileWrite(hipFileHandle_t handle, void* devicePtr, uint64_t size, int64_t file_offset,
                       uint64_t* size_copied, int32_t* status) {
  if (size == 0) {
    // Skip if nothing needs writing.
    return hipSuccess;
  }
  amd::Device* device = hip::getCurrentDevice()->devices()[0];
  if (device == nullptr) {
    LogError("Failed to get current device");
    return hipErrorInvalidDevice;
  }
#if defined(_WIN32)
  void* opaque = handle.handle;
#else
  void* opaque = reinterpret_cast<void*>(static_cast<intptr_t>(handle.fd));
#endif
  if (!device->fileWrite(opaque, devicePtr, size, file_offset, size_copied, status)) {
    LogError("Failed to perform file write operation");
    return hipErrorInvalidValue;
  }
  return hipSuccess;
}
