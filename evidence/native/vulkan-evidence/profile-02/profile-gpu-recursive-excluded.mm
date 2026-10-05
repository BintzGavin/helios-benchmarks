// Task-owned DYLD interposer. Compile separately; never link into production.
// Positive-control reference runs must observe CPU maps/readback transfers.
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <CoreVideo/CoreVideo.h>
#import <IOSurface/IOSurface.h>
#import <objc/runtime.h>
#include <dlfcn.h>
#include <cstdio>
#include <mutex>
#include <time.h>
#ifdef HELIOS_PROFILE_VULKAN
#include <vulkan/vulkan.h>
#include <cstring>
#endif

#ifndef HELIOS_PROFILE_PATH
#error "Compile with an explicit task-owned HELIOS_PROFILE_PATH outside the repository"
#endif

static FILE* receipt;
static std::mutex mutex;
static void log(const char* event, unsigned long long bytes = 0) {
    std::lock_guard<std::mutex> lock(mutex);
    if (!receipt) receipt = fopen(HELIOS_PROFILE_PATH, "ab");
    struct timespec now; clock_gettime(CLOCK_MONOTONIC, &now);
    if (receipt) { fprintf(receipt, "{\"event\":\"%s\",\"resourceExtentBytes\":%llu,\"timeSeconds\":%.9f}\n", event, bytes, now.tv_sec + now.tv_nsec / 1e9); fflush(receipt); }
}
static CVReturn lockPixel(CVPixelBufferRef buffer, CVPixelBufferLockFlags flags) {
    log("CVPixelBufferLockBaseAddress", CVPixelBufferGetDataSize(buffer));
    return CVPixelBufferLockBaseAddress(buffer, flags);
}
static void* pixelBase(CVPixelBufferRef buffer) {
    log("CVPixelBufferGetBaseAddress", CVPixelBufferGetDataSize(buffer));
    return CVPixelBufferGetBaseAddress(buffer);
}
static void* pixelPlane(CVPixelBufferRef buffer, size_t plane) {
    log("CVPixelBufferGetBaseAddressOfPlane", CVPixelBufferGetBytesPerRowOfPlane(buffer, plane) * CVPixelBufferGetHeightOfPlane(buffer, plane));
    return CVPixelBufferGetBaseAddressOfPlane(buffer, plane);
}
static IOReturn lockSurface(IOSurfaceRef surface, IOSurfaceLockOptions flags, uint32_t* seed) {
    log("IOSurfaceLock", IOSurfaceGetAllocSize(surface));
    return IOSurfaceLock(surface, flags, seed);
}
static void* surfaceBase(IOSurfaceRef surface) {
    log("IOSurfaceGetBaseAddress", IOSurfaceGetAllocSize(surface));
    return IOSurfaceGetBaseAddress(surface);
}
static void* surfacePlane(IOSurfaceRef surface, size_t plane) {
    log("IOSurfaceGetBaseAddressOfPlane", IOSurfaceGetBytesPerRowOfPlane(surface, plane) * IOSurfaceGetHeightOfPlane(surface, plane));
    return IOSurfaceGetBaseAddressOfPlane(surface, plane);
}
#define INTERPOSE(replacement, replacee) \
__attribute__((used)) static struct { const void* replacement; const void* replacee; } ip_##replacee \
__attribute__((section("__DATA,__interpose"))) = { (const void*)&replacement, (const void*)&replacee }
INTERPOSE(lockPixel, CVPixelBufferLockBaseAddress);
INTERPOSE(pixelBase, CVPixelBufferGetBaseAddress);
INTERPOSE(pixelPlane, CVPixelBufferGetBaseAddressOfPlane);
INTERPOSE(lockSurface, IOSurfaceLock);
INTERPOSE(surfaceBase, IOSurfaceGetBaseAddress);
INTERPOSE(surfacePlane, IOSurfaceGetBaseAddressOfPlane);

static IMP getBytesOriginal, copyToBufferOriginal, copyFromBufferOriginal, contentsOriginal;
static void getBytes(id object, SEL selector, void* bytes, NSUInteger row, MTLRegion region, NSUInteger level) {
    log("MTLTextureGetBytes", row * region.size.height * region.size.depth);
    reinterpret_cast<void(*)(id,SEL,void*,NSUInteger,MTLRegion,NSUInteger)>(getBytesOriginal)(object,selector,bytes,row,region,level);
}
static void copyToBuffer(id object, SEL selector, id texture, NSUInteger slice, NSUInteger level, MTLOrigin origin, MTLSize size, id buffer, NSUInteger offset, NSUInteger row, NSUInteger image) {
    log("MTLBlitTextureToBuffer", row * size.height * size.depth);
    reinterpret_cast<void(*)(id,SEL,id,NSUInteger,NSUInteger,MTLOrigin,MTLSize,id,NSUInteger,NSUInteger,NSUInteger)>(copyToBufferOriginal)(object,selector,texture,slice,level,origin,size,buffer,offset,row,image);
}
static void copyFromBuffer(id object, SEL selector, id buffer, NSUInteger offset, NSUInteger row, NSUInteger image, MTLSize size, id texture, NSUInteger slice, NSUInteger level, MTLOrigin origin) {
    log("MTLBlitBufferToTexture", row * size.height * size.depth);
    reinterpret_cast<void(*)(id,SEL,id,NSUInteger,NSUInteger,NSUInteger,MTLSize,id,NSUInteger,NSUInteger,MTLOrigin)>(copyFromBufferOriginal)(object,selector,buffer,offset,row,image,size,texture,slice,level,origin);
}
static void* contents(id object, SEL selector) {
    log("MTLBufferContentsAccessIntentUnknown", [(id<MTLBuffer>)object length]);
    return reinterpret_cast<void*(*)(id,SEL)>(contentsOriginal)(object,selector);
}
static IMP install(id object, SEL selector, IMP replacement) {
    Class cls = object_getClass(object);
    Method method = class_getInstanceMethod(cls, selector);
    if (!method) return nullptr;
    IMP original = method_getImplementation(method);
    // Add an override on the concrete class; do not mutate shared superclass behavior.
    if (!class_addMethod(cls, selector, replacement, method_getTypeEncoding(method))) method_setImplementation(method, replacement);
    return original;
}
__attribute__((constructor)) static void attach() {
    @autoreleasepool {
        auto device = MTLCreateSystemDefaultDevice();
        auto queue = [device newCommandQueue];
        auto command = [queue commandBuffer];
        auto encoder = [command blitCommandEncoder];
        auto texture = [device newTextureWithDescriptor:[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm width:64 height:64 mipmapped:NO]];
        auto buffer = [device newBufferWithLength:65536 options:MTLResourceStorageModeShared];
        getBytesOriginal = install(texture, @selector(getBytes:bytesPerRow:fromRegion:mipmapLevel:), (IMP)getBytes);
        copyToBufferOriginal = install(encoder, @selector(copyFromTexture:sourceSlice:sourceLevel:sourceOrigin:sourceSize:toBuffer:destinationOffset:destinationBytesPerRow:destinationBytesPerImage:), (IMP)copyToBuffer);
        copyFromBufferOriginal = install(encoder, @selector(copyFromBuffer:sourceOffset:sourceBytesPerRow:sourceBytesPerImage:sourceSize:toTexture:destinationSlice:destinationLevel:destinationOrigin:), (IMP)copyFromBuffer);
        contentsOriginal = install(buffer, @selector(contents), (IMP)contents);
        [encoder endEncoding];
        log(getBytesOriginal && copyToBufferOriginal && copyFromBufferOriginal && contentsOriginal ? "profiler-hooks-installed" : "profiler-hooks-incomplete");
    }
}

#ifdef HELIOS_PROFILE_VULKAN
// Hook function-pointer lookup as well as direct imports: Skia obtains Vulkan
// commands through vkGet*ProcAddr rather than ordinary linked function calls.
static VkResult profileSubmit(VkQueue queue, uint32_t count, const VkSubmitInfo* batches, VkFence fence) {
    log(count ? "VulkanQueueSubmitCommands" : "VulkanQueueSubmitFence");
    return reinterpret_cast<PFN_vkQueueSubmit>(dlsym(RTLD_NEXT, "vkQueueSubmit"))(queue, count, batches, fence);
}
static VkResult profileWait(VkDevice device, uint32_t count, const VkFence* fences, VkBool32 all, uint64_t timeout) {
    const auto result = reinterpret_cast<PFN_vkWaitForFences>(dlsym(RTLD_NEXT, "vkWaitForFences"))(device, count, fences, all, timeout);
    log(result == VK_SUCCESS ? "VulkanFenceWaitComplete" : "VulkanFenceWaitFailed");
    return result;
}
static void profileImageToBuffer(VkCommandBuffer command, VkImage image, VkImageLayout layout, VkBuffer buffer, uint32_t count, const VkBufferImageCopy* regions) {
    log("VulkanCopyImageToBuffer");
    reinterpret_cast<PFN_vkCmdCopyImageToBuffer>(dlsym(RTLD_NEXT, "vkCmdCopyImageToBuffer"))(command, image, layout, buffer, count, regions);
}
static void profileImageToBuffer2(VkCommandBuffer command, const VkCopyImageToBufferInfo2* info) {
    log("VulkanCopyImageToBuffer2");
    reinterpret_cast<PFN_vkCmdCopyImageToBuffer2>(dlsym(RTLD_NEXT, "vkCmdCopyImageToBuffer2"))(command, info);
}
static void profileImageToBuffer2KHR(VkCommandBuffer command, const VkCopyImageToBufferInfo2* info) {
    log("VulkanCopyImageToBuffer2KHR");
    reinterpret_cast<PFN_vkCmdCopyImageToBuffer2KHR>(dlsym(RTLD_NEXT, "vkCmdCopyImageToBuffer2KHR"))(command, info);
}
static VkResult profileMap(VkDevice device, VkDeviceMemory memory, VkDeviceSize offset, VkDeviceSize size, VkMemoryMapFlags flags, void** data) {
    log("VulkanMapMemoryAccessIntentUnknown");
    return reinterpret_cast<PFN_vkMapMemory>(dlsym(RTLD_NEXT, "vkMapMemory"))(device, memory, offset, size, flags, data);
}
static PFN_vkVoidFunction profileProc(const char* name, PFN_vkVoidFunction original) {
    if (!original) return original;
    if (!strcmp(name, "vkQueueSubmit")) return reinterpret_cast<PFN_vkVoidFunction>(profileSubmit);
    if (!strcmp(name, "vkWaitForFences")) return reinterpret_cast<PFN_vkVoidFunction>(profileWait);
    if (!strcmp(name, "vkCmdCopyImageToBuffer")) return reinterpret_cast<PFN_vkVoidFunction>(profileImageToBuffer);
    if (!strcmp(name, "vkCmdCopyImageToBuffer2")) return reinterpret_cast<PFN_vkVoidFunction>(profileImageToBuffer2);
    if (!strcmp(name, "vkCmdCopyImageToBuffer2KHR")) return reinterpret_cast<PFN_vkVoidFunction>(profileImageToBuffer2KHR);
    if (!strcmp(name, "vkMapMemory")) return reinterpret_cast<PFN_vkVoidFunction>(profileMap);
    return original;
}
static PFN_vkVoidFunction profileDeviceProc(VkDevice device, const char* name) {
    return profileProc(name, reinterpret_cast<PFN_vkGetDeviceProcAddr>(dlsym(RTLD_NEXT, "vkGetDeviceProcAddr"))(device, name));
}
static PFN_vkVoidFunction profileInstanceProc(VkInstance instance, const char* name) {
    return profileProc(name, reinterpret_cast<PFN_vkGetInstanceProcAddr>(dlsym(RTLD_NEXT, "vkGetInstanceProcAddr"))(instance, name));
}
INTERPOSE(profileDeviceProc, vkGetDeviceProcAddr);
INTERPOSE(profileInstanceProc, vkGetInstanceProcAddr);
INTERPOSE(profileSubmit, vkQueueSubmit);
INTERPOSE(profileWait, vkWaitForFences);
INTERPOSE(profileImageToBuffer, vkCmdCopyImageToBuffer);
INTERPOSE(profileMap, vkMapMemory);
__attribute__((constructor)) static void attachVulkan() {
    bool complete = true;
    for (auto name : {"vkGetDeviceProcAddr", "vkGetInstanceProcAddr", "vkQueueSubmit", "vkWaitForFences", "vkCmdCopyImageToBuffer", "vkMapMemory"}) complete &= dlsym(RTLD_NEXT, name) != nullptr;
    log(complete ? "vulkan-profiler-hooks-installed" : "vulkan-profiler-hooks-incomplete");
}
#endif
