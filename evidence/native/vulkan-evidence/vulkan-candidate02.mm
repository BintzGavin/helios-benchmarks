#define VK_USE_PLATFORM_METAL_EXT
#import <Metal/Metal.h>
#include <cstdio>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#include <vulkan/vulkan.h>

static void require(VkResult result, const char *stage) {
  if (result != VK_SUCCESS)
    throw std::runtime_error(stage);
}

extern "C" void *helios_texture(void *);

struct Vulkan {
  VkInstance instance = VK_NULL_HANDLE;
  VkPhysicalDevice physical = VK_NULL_HANDLE;
  VkDevice device = VK_NULL_HANDLE;
  VkQueue queue = VK_NULL_HANDLE;
  VkImage image = VK_NULL_HANDLE;
  uint32_t family = 0;
  VkFence fence = VK_NULL_HANDLE;
  FILE *trace = nullptr;
  bool capturing = false;
  ~Vulkan() {
    if (device) {
      vkDeviceWaitIdle(device);
      if (capturing)
        [[MTLCaptureManager sharedCaptureManager] stopCapture];
      if (fence)
        vkDestroyFence(device, fence, nullptr);
      if (image)
        vkDestroyImage(device, image, nullptr);
      vkDestroyDevice(device, nullptr);
    }
    if (instance)
      vkDestroyInstance(instance, nullptr);
    if (trace)
      fclose(trace);
  }
};
extern "C" void *helios_vk_create(void *native, const char *trace,
                                  const char *capture) {
  auto owner = std::make_unique<Vulkan>();
  auto &instance = owner->instance;
  auto &device = owner->device;
  auto &image = owner->image;
  auto &physical = owner->physical;
  auto &family = owner->family;
  auto &queue = owner->queue;
  try {
    const char *instExt[] = {
        VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME};
    VkExportMetalObjectCreateInfoEXT exportDevice{
        VK_STRUCTURE_TYPE_EXPORT_METAL_OBJECT_CREATE_INFO_EXT};
    exportDevice.exportObjectType =
        VK_EXPORT_METAL_OBJECT_TYPE_METAL_DEVICE_BIT_EXT;
    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
    app.pApplicationName = "helios-skia-vulkan";
    app.apiVersion = VK_API_VERSION_1_1;
    VkInstanceCreateInfo ic{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    ic.pNext = &exportDevice;
    ic.pApplicationInfo = &app;
    ic.enabledExtensionCount = 1;
    ic.ppEnabledExtensionNames = instExt;
    require(vkCreateInstance(&ic, nullptr, &instance), "instance");
    uint32_t count = 0;
    require(vkEnumeratePhysicalDevices(instance, &count, nullptr), "devices");
    std::vector<VkPhysicalDevice> physicals(count);
    require(vkEnumeratePhysicalDevices(instance, &count, physicals.data()),
            "devices");
    VkPhysicalDeviceProperties properties{};
    for (auto p : physicals) {
      vkGetPhysicalDeviceProperties(p, &properties);
      if (properties.deviceType == VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU ||
          properties.deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU) {
        physical = p;
        break;
      }
    }
    if (!physical)
      throw std::runtime_error("hardware Vulkan GPU absent");
    require(vkEnumerateDeviceExtensionProperties(physical, nullptr, &count,
                                                 nullptr),
            "extensions");
    std::vector<VkExtensionProperties> extensions(count);
    require(vkEnumerateDeviceExtensionProperties(physical, nullptr, &count,
                                                 extensions.data()),
            "extensions");
    bool metal = false, portability = false;
    for (auto &e : extensions) {
      metal |= !strcmp(e.extensionName, VK_EXT_METAL_OBJECTS_EXTENSION_NAME);
      portability |= !strcmp(e.extensionName, "VK_KHR_portability_subset");
    }
    if (!metal || !portability)
      throw std::runtime_error("required Vulkan sharing extension absent");
    vkGetPhysicalDeviceQueueFamilyProperties(physical, &count, nullptr);
    std::vector<VkQueueFamilyProperties> families(count);
    vkGetPhysicalDeviceQueueFamilyProperties(physical, &count, families.data());
    family = 0;
    while (family < count &&
           !(families[family].queueFlags & VK_QUEUE_GRAPHICS_BIT))
      ++family;
    if (family == count)
      throw std::runtime_error("graphics queue absent");
    float priority = 1;
    VkDeviceQueueCreateInfo qc{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
    qc.queueFamilyIndex = family;
    qc.queueCount = 1;
    qc.pQueuePriorities = &priority;
    const char *devExt[] = {VK_EXT_METAL_OBJECTS_EXTENSION_NAME,
                            "VK_KHR_portability_subset"};
    VkPhysicalDeviceFeatures features{};
    vkGetPhysicalDeviceFeatures(physical, &features);
    VkDeviceCreateInfo dc{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
    dc.pEnabledFeatures = &features;
    dc.queueCreateInfoCount = 1;
    dc.pQueueCreateInfos = &qc;
    dc.enabledExtensionCount = 2;
    dc.ppEnabledExtensionNames = devExt;
    require(vkCreateDevice(physical, &dc, nullptr, &device), "device");
    vkGetDeviceQueue(device, family, 0, &queue);

    id<MTLTexture> texture = (__bridge id<MTLTexture>)helios_texture(native);
    VkExportMetalObjectCreateInfoEXT exportTexture{
        VK_STRUCTURE_TYPE_EXPORT_METAL_OBJECT_CREATE_INFO_EXT};
    exportTexture.exportObjectType =
        VK_EXPORT_METAL_OBJECT_TYPE_METAL_TEXTURE_BIT_EXT;
    VkImportMetalTextureInfoEXT import{
        VK_STRUCTURE_TYPE_IMPORT_METAL_TEXTURE_INFO_EXT};
    import.pNext = &exportTexture;
    import.plane = VK_IMAGE_ASPECT_COLOR_BIT;
    import.mtlTexture = texture;
    VkImageCreateInfo img{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
    img.pNext = &import;
    img.imageType = VK_IMAGE_TYPE_2D;
    img.format = VK_FORMAT_R8G8B8A8_UNORM;
    img.extent = {uint32_t(texture.width), uint32_t(texture.height), 1};
    img.mipLevels = 1;
    img.arrayLayers = 1;
    img.samples = VK_SAMPLE_COUNT_1_BIT;
    img.tiling = VK_IMAGE_TILING_OPTIMAL;
    img.usage =
        VK_IMAGE_USAGE_TRANSFER_SRC_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT |
        VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_SAMPLED_BIT;
    img.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    img.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    require(vkCreateImage(device, &img, nullptr, &image),
            "import private texture");
    auto exportObjects = (PFN_vkExportMetalObjectsEXT)vkGetDeviceProcAddr(
        device, "vkExportMetalObjectsEXT");
    if (!exportObjects)
      throw std::runtime_error("metal export function absent");
    VkExportMetalTextureInfoEXT exported{
        VK_STRUCTURE_TYPE_EXPORT_METAL_TEXTURE_INFO_EXT};
    exported.image = image;
    exported.plane = VK_IMAGE_ASPECT_COLOR_BIT;
    VkExportMetalObjectsInfoEXT ei{
        VK_STRUCTURE_TYPE_EXPORT_METAL_OBJECTS_INFO_EXT};
    ei.pNext = &exported;
    exportObjects(device, &ei);
    if (exported.mtlTexture != texture)
      throw std::runtime_error("texture identity mismatch");

    VkExportMetalDeviceInfoEXT gpu{
        VK_STRUCTURE_TYPE_EXPORT_METAL_DEVICE_INFO_EXT};
    ei.pNext = &gpu;
    exportObjects(device, &ei);
    if (!gpu.mtlDevice || gpu.mtlDevice.registryID != texture.device.registryID)
      throw std::runtime_error("Vulkan/encoder GPU identity mismatch");
    if (capture[0]) {
      auto manager = [MTLCaptureManager sharedCaptureManager];
      if (![manager supportsDestination:MTLCaptureDestinationGPUTraceDocument])
        throw std::runtime_error("GPU capture unavailable");
      auto descriptor = [MTLCaptureDescriptor new];
      descriptor.captureObject = gpu.mtlDevice;
      descriptor.destination = MTLCaptureDestinationGPUTraceDocument;
      descriptor.outputURL =
          [NSURL fileURLWithPath:[NSString stringWithUTF8String:capture]];
      NSError *error = nil;
      if (![manager startCaptureWithDescriptor:descriptor error:&error])
        throw std::runtime_error("GPU capture failed");
      owner->capturing = true;
    }
    VkFenceCreateInfo fc{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
    require(vkCreateFence(device, &fc, nullptr, &owner->fence), "fence");
    if (trace[0]) {
      owner->trace =
          fopen((std::string(trace) + ".vulkan.jsonl").c_str(), "wb");
      if (!owner->trace)
        throw std::runtime_error("trace");
      fprintf(owner->trace,
              "{\"event\":\"vulkan-shared-texture\",\"deviceType\":%u,"
              "\"sameImportedTexture\":true,\"sameGpuRegistryId\":true,"
              "\"metalObjects\":true}\n",
              properties.deviceType);
      fflush(owner->trace);
    }
    return owner.release();
  } catch (const std::exception &e) {
    fprintf(stderr, "VULKAN_INIT_FAILED: %s\n", e.what());
    return nullptr;
  }
}
extern "C" void *helios_vk_instance(Vulkan *v) { return v->instance; }
extern "C" void *helios_vk_physical(Vulkan *v) { return v->physical; }
extern "C" void *helios_vk_device(Vulkan *v) { return v->device; }
extern "C" void *helios_vk_queue(Vulkan *v) { return v->queue; }
extern "C" uint32_t helios_vk_family(Vulkan *v) { return v->family; }
extern "C" uint64_t helios_vk_image(Vulkan *v) { return uint64_t(v->image); }
extern "C" void *helios_vk_proc(Vulkan *v, const char *name, bool device) {
  return (void *)(device ? vkGetDeviceProcAddr(v->device, name)
                         : vkGetInstanceProcAddr(v->instance, name));
}
extern "C" bool helios_vk_wait(Vulkan *v, uint32_t frame) {
  if (vkQueueSubmit(v->queue, 0, nullptr, v->fence) != VK_SUCCESS ||
      vkWaitForFences(v->device, 1, &v->fence, VK_TRUE, 30000000000ULL) !=
          VK_SUCCESS ||
      vkResetFences(v->device, 1, &v->fence) != VK_SUCCESS)
    return false;
  if (v->trace) {
    fprintf(v->trace, "{\"event\":\"vulkan-fence-complete\",\"frame\":%u}\n",
            frame);
    fflush(v->trace);
  }
  return true;
}
extern "C" void helios_vk_close(Vulkan *v) { delete v; }
