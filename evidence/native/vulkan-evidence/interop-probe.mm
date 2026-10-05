#define VK_USE_PLATFORM_METAL_EXT
#include <vulkan/vulkan.h>
#import <Metal/Metal.h>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>

extern "C" void* helios_create(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,bool,const char*,bool,const char*,const char*);
extern "C" void* helios_texture(void*);
extern "C" bool helios_encode(void*,uint32_t);
extern "C" bool helios_finish(void*,uint32_t);
extern "C" bool helios_hardware(void*);
extern "C" bool helios_close(void*);
extern "C" void helios_raster_submitted(void*,uint32_t);

void require(VkResult result, const char* stage) { if (result != VK_SUCCESS) throw std::runtime_error(stage); }
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    VkInstance instance = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    VkImage image = VK_NULL_HANDLE;
    VkCommandPool pool = VK_NULL_HANDLE;
    VkFence fence = VK_NULL_HANDLE;
    void* native = nullptr;
    int exit = 1;
    try {
        // Direct MoltenVK linkage does not use the loader-only enumeration extension.
        const char* instExt[] = {VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME};
        VkExportMetalObjectCreateInfoEXT exportDevice{VK_STRUCTURE_TYPE_EXPORT_METAL_OBJECT_CREATE_INFO_EXT};
        exportDevice.exportObjectType = VK_EXPORT_METAL_OBJECT_TYPE_METAL_DEVICE_BIT_EXT;
        VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO}; app.pApplicationName="helios-vulkan-interop-probe"; app.apiVersion=VK_API_VERSION_1_1;
        VkInstanceCreateInfo ic{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO}; ic.pNext=&exportDevice; ic.pApplicationInfo=&app; ic.enabledExtensionCount=1; ic.ppEnabledExtensionNames=instExt;
        require(vkCreateInstance(&ic,nullptr,&instance),"instance");
        uint32_t count=0; require(vkEnumeratePhysicalDevices(instance,&count,nullptr),"devices");
        std::vector<VkPhysicalDevice> physicals(count); require(vkEnumeratePhysicalDevices(instance,&count,physicals.data()),"devices");
        VkPhysicalDevice physical=VK_NULL_HANDLE; VkPhysicalDeviceProperties properties{};
        for (auto p : physicals) { vkGetPhysicalDeviceProperties(p,&properties); if (properties.deviceType==VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU || properties.deviceType==VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU) {physical=p; break;} }
        if (!physical) throw std::runtime_error("hardware Vulkan GPU absent");
        require(vkEnumerateDeviceExtensionProperties(physical,nullptr,&count,nullptr),"extensions");
        std::vector<VkExtensionProperties> extensions(count); require(vkEnumerateDeviceExtensionProperties(physical,nullptr,&count,extensions.data()),"extensions");
        bool metal=false, portability=false;
        for (auto& e : extensions) {metal |= !strcmp(e.extensionName,VK_EXT_METAL_OBJECTS_EXTENSION_NAME); portability |= !strcmp(e.extensionName,"VK_KHR_portability_subset");}
        if (!metal || !portability) throw std::runtime_error("required Vulkan sharing extension absent");
        vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,nullptr);
        std::vector<VkQueueFamilyProperties> families(count); vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,families.data());
        uint32_t family=0; while (family<count && !(families[family].queueFlags&VK_QUEUE_GRAPHICS_BIT)) ++family;
        if (family==count) throw std::runtime_error("graphics queue absent");
        float priority=1; VkDeviceQueueCreateInfo qc{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO}; qc.queueFamilyIndex=family; qc.queueCount=1; qc.pQueuePriorities=&priority;
        const char* devExt[]={VK_EXT_METAL_OBJECTS_EXTENSION_NAME,"VK_KHR_portability_subset"};
        VkDeviceCreateInfo dc{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO}; dc.queueCreateInfoCount=1; dc.pQueueCreateInfos=&qc; dc.enabledExtensionCount=2; dc.ppEnabledExtensionNames=devExt;
        require(vkCreateDevice(physical,&dc,nullptr,&device),"device");
        VkQueue queue; vkGetDeviceQueue(device,family,0,&queue);
        native=helios_create(64,64,30,1,20000000,30,3,false,argv[1],true,argv[2],"");
        if (!native) throw std::runtime_error("required hardware encoder failed");
        id<MTLTexture> texture=(__bridge id<MTLTexture>)helios_texture(native);
        VkExportMetalObjectCreateInfoEXT exportTexture{VK_STRUCTURE_TYPE_EXPORT_METAL_OBJECT_CREATE_INFO_EXT}; exportTexture.exportObjectType=VK_EXPORT_METAL_OBJECT_TYPE_METAL_TEXTURE_BIT_EXT;
        VkImportMetalTextureInfoEXT import{VK_STRUCTURE_TYPE_IMPORT_METAL_TEXTURE_INFO_EXT}; import.pNext=&exportTexture; import.plane=VK_IMAGE_ASPECT_COLOR_BIT; import.mtlTexture=texture;
        VkImageCreateInfo img{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO}; img.pNext=&import; img.imageType=VK_IMAGE_TYPE_2D; img.format=VK_FORMAT_R8G8B8A8_UNORM; img.extent={64,64,1}; img.mipLevels=1; img.arrayLayers=1; img.samples=VK_SAMPLE_COUNT_1_BIT; img.tiling=VK_IMAGE_TILING_OPTIMAL; img.usage=VK_IMAGE_USAGE_TRANSFER_DST_BIT|VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_SAMPLED_BIT; img.sharingMode=VK_SHARING_MODE_EXCLUSIVE; img.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED;
        require(vkCreateImage(device,&img,nullptr,&image),"import private texture");
        auto exportObjects=(PFN_vkExportMetalObjectsEXT)vkGetDeviceProcAddr(device,"vkExportMetalObjectsEXT");
        if (!exportObjects) throw std::runtime_error("metal export function absent");
        VkExportMetalTextureInfoEXT exported{VK_STRUCTURE_TYPE_EXPORT_METAL_TEXTURE_INFO_EXT}; exported.image=image; exported.plane=VK_IMAGE_ASPECT_COLOR_BIT;
        VkExportMetalObjectsInfoEXT ei{VK_STRUCTURE_TYPE_EXPORT_METAL_OBJECTS_INFO_EXT}; ei.pNext=&exported; exportObjects(device,&ei);
        if (exported.mtlTexture != texture) throw std::runtime_error("texture identity mismatch");
        VkCommandPoolCreateInfo pc{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO}; pc.queueFamilyIndex=family; pc.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        require(vkCreateCommandPool(device,&pc,nullptr,&pool),"pool");
        VkCommandBufferAllocateInfo ca{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO}; ca.commandPool=pool; ca.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY; ca.commandBufferCount=1;
        VkCommandBuffer cmd; require(vkAllocateCommandBuffers(device,&ca,&cmd),"command");
        VkFenceCreateInfo fc{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO}; require(vkCreateFence(device,&fc,nullptr,&fence),"fence");
        for (uint32_t frame=0;frame<3;frame++) {
            require(vkResetCommandBuffer(cmd,0),"reset command");
            VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO}; begin.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT; require(vkBeginCommandBuffer(cmd,&begin),"begin");
            VkImageMemoryBarrier barrier{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER}; barrier.oldLayout=frame?VK_IMAGE_LAYOUT_GENERAL:VK_IMAGE_LAYOUT_UNDEFINED; barrier.newLayout=VK_IMAGE_LAYOUT_GENERAL; barrier.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED; barrier.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED; barrier.image=image; barrier.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}; barrier.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
            vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&barrier);
            VkClearColorValue color{}; color.float32[frame]=1; color.float32[3]=1;
            vkCmdClearColorImage(cmd,image,VK_IMAGE_LAYOUT_GENERAL,&color,1,&barrier.subresourceRange);
            require(vkEndCommandBuffer(cmd),"end");
            VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO}; submit.commandBufferCount=1; submit.pCommandBuffers=&cmd;
            require(vkQueueSubmit(queue,1,&submit,fence),"submit");
            require(vkWaitForFences(device,1,&fence,VK_TRUE,30000000000ULL),"fence completion");
            require(vkResetFences(device,1,&fence),"reset fence");
            helios_raster_submitted(native,frame);
            if (!helios_encode(native,frame)) throw std::runtime_error("encode");
        }
        if (!helios_finish(native,3) || !helios_hardware(native)) throw std::runtime_error("drain hardware");
        printf("{\"device\":\"%s\",\"deviceType\":%u,\"apiVersion\":%u,\"metalObjects\":true,\"sameImportedTexture\":true,\"hardwareUsed\":true,\"vulkanSubmissions\":3,\"completedFences\":3,\"encoderFrames\":3,\"zeroCopyProved\":false}\n",properties.deviceName,properties.deviceType,properties.apiVersion);
        exit=0;
    } catch (const std::exception& e) {fprintf(stderr,"VULKAN_SETUP_FAILED: %s\n",e.what());}
    if (device) {vkDeviceWaitIdle(device); if(fence)vkDestroyFence(device,fence,nullptr); if(pool)vkDestroyCommandPool(device,pool,nullptr); if(image)vkDestroyImage(device,image,nullptr); vkDestroyDevice(device,nullptr);}
    if (native) helios_close(native);
    if (instance) vkDestroyInstance(instance,nullptr);
    return exit;
}
