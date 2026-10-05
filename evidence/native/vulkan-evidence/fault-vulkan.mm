#define VK_USE_PLATFORM_METAL_EXT
#include <vulkan/vulkan.h>
#include <dlfcn.h>
#include <cstring>

extern "C" void properties(VkPhysicalDevice device, VkPhysicalDeviceProperties* out) {
  vkGetPhysicalDeviceProperties(device, out); out->deviceType = VK_PHYSICAL_DEVICE_TYPE_CPU;
}
extern "C" VkResult createImage(VkDevice, const VkImageCreateInfo*, const VkAllocationCallbacks*, VkImage*) { return VK_ERROR_OUT_OF_DEVICE_MEMORY; }
extern "C" VkResult waitFence(VkDevice, uint32_t, const VkFence*, VkBool32, uint64_t) { return VK_TIMEOUT; }
extern "C" VkResult extensions(VkPhysicalDevice device, const char* layer, uint32_t* count, VkExtensionProperties* out) {
  auto result = vkEnumerateDeviceExtensionProperties(device, layer, count, out);
  if (out) for (uint32_t i=0; i<*count; i++) if (!strcmp(out[i].extensionName, "VK_EXT_metal_objects")) out[i].extensionName[0] = '\0';
  return result;
}
#define INTERPOSE(replacement, original) __attribute__((used)) static struct { const void* replacement; const void* original; } pair __attribute__((section("__DATA,__interpose"))) = {(const void*)&replacement, (const void*)&original}
#if defined(FAIL_CPU)
INTERPOSE(properties, vkGetPhysicalDeviceProperties);
#elif defined(FAIL_IMAGE)
INTERPOSE(createImage, vkCreateImage);
#elif defined(FAIL_FENCE)
INTERPOSE(waitFence, vkWaitForFences);
#elif defined(FAIL_EXTENSION)
INTERPOSE(extensions, vkEnumerateDeviceExtensionProperties);
#endif
