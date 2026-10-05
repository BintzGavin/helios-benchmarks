#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <CoreVideo/CoreVideo.h>
#import <IOSurface/IOSurface.h>
#include <atomic>
#include <cstdio>
#include <mutex>
#include <unordered_map>
#include <memory>

// Task-only explicit conversion. Encoding/muxing stays in the production fframes pipeline.
static std::mutex logMutex;
static FILE* logFile = nullptr;
static std::atomic<uint64_t> contexts{0};
static uint64_t sequence=0;
static bool captureStarted=false;
struct Owner { uint64_t context; uint32_t index; uint32_t surface; };
static std::unordered_map<void*,Owner> owners;
static std::unordered_map<void*,Owner> sourceOwners;
template<typename... Args> static void trace(const char* fields,Args... args) {
    std::lock_guard<std::mutex> lock(logMutex);
    if(logFile){fprintf(logFile,"{\"seq\":%llu,",(unsigned long long)++sequence);fprintf(logFile,fields,args...);fputs("}\n",logFile);fflush(logFile);}
}
struct Converter {
    id<MTLDevice> device;
    id<MTLCommandQueue> queue;
    id<MTLComputePipelineState> kernel;
    CVMetalTextureCacheRef cache=nullptr;
    CVPixelBufferPoolRef pool=nullptr;
    uint32_t width,height;
    uint64_t id;
    ~Converter(){if(cache)CFRelease(cache);if(pool)CFRelease(pool);}
};
static const char* shader=R"metal(
#include <metal_stdlib>
using namespace metal;
float3 transfer(float3 s) {
    float3 linear = select(pow((s + 0.055f) / 1.055f, float3(2.4f)), s / 12.92f, s <= 0.04045f);
    return select(1.099f * pow(linear, float3(0.45f)) - 0.099f, 4.5f * linear, linear < 0.018f);
}
kernel void convert(texture2d<float, access::read> bgra [[texture(0)]],
                    texture2d<float, access::write> y [[texture(1)]],
                    texture2d<float, access::write> uv [[texture(2)]], uint2 p [[thread_position_in_grid]]) {
    if (p.x >= uv.get_width() || p.y >= uv.get_height()) return;
    float2 chroma = 0;
    for (uint dy = 0; dy < 2; ++dy) for (uint dx = 0; dx < 2; ++dx) {
        uint2 q = 2 * p + uint2(dx, dy);
        float3 rgb = transfer(clamp(bgra.read(q).rgb, 0.0f, 1.0f));
        float luma = dot(rgb, float3(0.2126f, 0.7152f, 0.0722f));
        y.write(float4((16.0f + 219.0f * luma) / 255.0f), q);
        chroma += float2((rgb.b - luma) / 1.8556f, (rgb.r - luma) / 1.5748f);
    }
    uv.write(float4((128.0f + 56.0f * chroma) / 255.0f, 0, 1), p);
}
)metal";

extern "C" void* fframes_nv12_create(void* device,uint32_t width,uint32_t height) {
    @autoreleasepool {
        if(!width||!height||width>3840||height>2160||width%2||height%2)return nullptr;
        auto c=std::make_unique<Converter>();c->device=(__bridge id<MTLDevice>)device;c->width=width;c->height=height;c->id=++contexts;
        if(!c->device)return nullptr;
        const char* fault=getenv("FFRAMES_NV12_FAULT");if(fault && !strcmp(fault,"device"))return nullptr;
        {std::lock_guard<std::mutex> lock(logMutex);const char* file=getenv("FFRAMES_NV12_TRACE");if(!logFile && file && file[0]){logFile=fopen(file,"wx");if(!logFile)return nullptr;}}
        c->queue=[c->device newCommandQueue];NSError* error=nil;
        auto library=[c->device newLibraryWithSource:[NSString stringWithUTF8String:shader] options:nil error:&error];
        if(!library){fprintf(stderr,"NV12_SHADER_FAILED %s\n",error.description.UTF8String);return nullptr;}
        c->kernel=[c->device newComputePipelineStateWithFunction:[library newFunctionWithName:@"convert"] error:&error];
        NSDictionary* attributes=@{(id)kCVPixelBufferPixelFormatTypeKey:@(kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange),
            (id)kCVPixelBufferWidthKey:@(width),(id)kCVPixelBufferHeightKey:@(height),
            (id)kCVPixelBufferMetalCompatibilityKey:@YES,(id)kCVPixelBufferIOSurfacePropertiesKey:@{}};
        NSDictionary* usage=@{(id)kCVMetalTextureUsage:@(MTLTextureUsageShaderRead|MTLTextureUsageShaderWrite)};
        if(!c->queue||!c->kernel||CVPixelBufferPoolCreate(nullptr,nullptr,(__bridge CFDictionaryRef)attributes,&c->pool)||
           CVMetalTextureCacheCreate(nullptr,nullptr,c->device,(__bridge CFDictionaryRef)usage,&c->cache))return nullptr;
        const char* cap=getenv("FFRAMES_NV12_METAL_CAPTURE");
        if(cap && cap[0]){std::lock_guard<std::mutex> lock(logMutex);if(!captureStarted){
            auto manager=[MTLCaptureManager sharedCaptureManager];auto descriptor=[MTLCaptureDescriptor new];descriptor.captureObject=c->device;
            descriptor.destination=MTLCaptureDestinationGPUTraceDocument;descriptor.outputURL=[NSURL fileURLWithPath:[NSString stringWithUTF8String:cap]];
            if(![manager supportsDestination:descriptor.destination]||![manager startCaptureWithDescriptor:descriptor error:&error])return nullptr;
            captureStarted=true;
        }}
        trace("\"event\":\"converter-create\",\"context\":%llu,\"deviceRegistryId\":%llu,\"width\":%u,\"height\":%u,\"poolThreshold\":64,\"extraGpuCopy\":false,\"colorContract\":\"sRGB to BT709 limited; centered 2x2 box\"",c->id,c->device.registryID,width,height);
        return c.release();
    }
}
extern "C" void* fframes_nv12_convert(Converter* c,void* sourcePixel,void* sourceTexture,uint32_t index) {
    @autoreleasepool {
        const char* fault=getenv("FFRAMES_NV12_FAULT");if(fault && !strcmp(fault,"convert"))return nullptr;
        auto src=(CVPixelBufferRef)sourcePixel;id<MTLTexture> texture=(__bridge id<MTLTexture>)sourceTexture;
        auto sourceSurface=CVPixelBufferGetIOSurface(src);
        if(!texture||texture.pixelFormat!=MTLPixelFormatBGRA8Unorm||texture.width!=c->width||texture.height!=c->height||
           texture.device.registryID!=c->device.registryID||!sourceSurface||texture.iosurface!=sourceSurface||texture.iosurfacePlane!=0||
           (fault && !strcmp(fault,"identity")))return nullptr;
        {std::lock_guard<std::mutex> lock(logMutex);if(sourceOwners.find(src)!=sourceOwners.end())return nullptr;sourceOwners[src]=Owner{c->id,index,IOSurfaceGetID(sourceSurface)};}
        CVPixelBufferRef dest=nullptr;
        NSDictionary* threshold=@{(id)kCVPixelBufferPoolAllocationThresholdKey:@64};
        auto status=CVPixelBufferPoolCreatePixelBufferWithAuxAttributes(nullptr,c->pool,(__bridge CFDictionaryRef)threshold,&dest);
        if(status||!dest||(fault && !strcmp(fault,"pool"))){if(dest)CVPixelBufferRelease(dest);trace("\"event\":\"pool-allocation-failed\",\"context\":%llu,\"status\":%d",c->id,(int)status);return nullptr;}
        CVMetalTextureRef yy=nullptr,uvv=nullptr;
        if(CVMetalTextureCacheCreateTextureFromImage(nullptr,c->cache,dest,nullptr,MTLPixelFormatR8Unorm,c->width,c->height,0,&yy)||
           CVMetalTextureCacheCreateTextureFromImage(nullptr,c->cache,dest,nullptr,MTLPixelFormatRG8Unorm,c->width/2,c->height/2,1,&uvv)){
            if(yy)CFRelease(yy);if(uvv)CFRelease(uvv);CVPixelBufferRelease(dest);return nullptr;}
        auto y=CVMetalTextureGetTexture(yy),uv=CVMetalTextureGetTexture(uvv);auto surface=CVPixelBufferGetIOSurface(dest);
        if(!surface||y.iosurface!=surface||uv.iosurface!=surface||y.iosurfacePlane!=0||uv.iosurfacePlane!=1){CFRelease(yy);CFRelease(uvv);CVPixelBufferRelease(dest);return nullptr;}
        trace("\"event\":\"conversion-begin\",\"context\":%llu,\"index\":%u,\"sourcePixelBuffer\":%llu,\"sourceTexture\":%llu,\"sourceSurfaceId\":%u,\"pixelBuffer\":%llu,\"surfaceId\":%u,\"sourceFenceAlreadyCompleted\":true",c->id,index,(uint64_t)src,(uint64_t)(__bridge void*)texture,IOSurfaceGetID(sourceSurface),(uint64_t)dest,IOSurfaceGetID(surface));
        auto command=[c->queue commandBuffer];command.label=@"fframes modified explicit sRGB BT709 NV12";
        auto compute=[command computeCommandEncoder];[compute setComputePipelineState:c->kernel];[compute setTexture:texture atIndex:0];[compute setTexture:y atIndex:1];[compute setTexture:uv atIndex:2];
        [compute dispatchThreads:MTLSizeMake(c->width/2,c->height/2,1) threadsPerThreadgroup:MTLSizeMake(8,8,1)];[compute endEncoding];[command commit];[command waitUntilCompleted];
        const bool completed=command.status==MTLCommandBufferStatusCompleted;
        trace("\"event\":\"conversion-complete\",\"context\":%llu,\"index\":%u,\"pixelBuffer\":%llu,\"surfaceId\":%u,\"completed\":%s,\"sameSourceTextureIOSurface\":true,\"sameDestinationIOSurfacePlanes\":true,\"gpuStartSeconds\":%.9f,\"gpuEndSeconds\":%.9f",c->id,index,(uint64_t)dest,IOSurfaceGetID(surface),completed?"true":"false",command.GPUStartTime,command.GPUEndTime);
        CFRelease(yy);CFRelease(uvv);if(!completed){CVPixelBufferRelease(dest);return nullptr;}
        CVBufferSetAttachment(dest,kCVImageBufferColorPrimariesKey,kCVImageBufferColorPrimaries_ITU_R_709_2,kCVAttachmentMode_ShouldPropagate);
        CVBufferSetAttachment(dest,kCVImageBufferTransferFunctionKey,kCVImageBufferTransferFunction_ITU_R_709_2,kCVAttachmentMode_ShouldPropagate);
        CVBufferSetAttachment(dest,kCVImageBufferYCbCrMatrixKey,kCVImageBufferYCbCrMatrix_ITU_R_709_2,kCVAttachmentMode_ShouldPropagate);
        CVBufferSetAttachment(dest,kCVImageBufferChromaLocationTopFieldKey,kCVImageBufferChromaLocation_Center,kCVAttachmentMode_ShouldPropagate);
        {std::lock_guard<std::mutex> lock(logMutex);if(owners.find(dest)!=owners.end()){CVPixelBufferRelease(dest);return nullptr;}owners[dest]=Owner{c->id,index,IOSurfaceGetID(surface)};}
        const char* positive=getenv("FFRAMES_NV12_POSITIVE_RGBA");
        if(positive && index!=UINT32_MAX){
            auto buffer=[c->device newBufferWithLength:c->width*c->height*4 options:MTLResourceStorageModeShared];
            auto download=[c->queue commandBuffer];auto blit=[download blitCommandEncoder];
            [blit copyFromTexture:texture sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0,0,0) sourceSize:MTLSizeMake(c->width,c->height,1)
                toBuffer:buffer destinationOffset:0 destinationBytesPerRow:c->width*4 destinationBytesPerImage:c->width*c->height*4];
            [blit endEncoding];[download commit];[download waitUntilCompleted];
            volatile uint8_t observed=((const uint8_t*)buffer.contents)[0];(void)observed;
            trace("\"event\":\"positive-rgba-download\",\"index\":%u,\"bytes\":%llu",index,(uint64_t)c->width*c->height*4);
        }
        return dest; // +1 reference transferred to AVBuffer callback. CoreVideo alone decides reuse.
    }
}
extern "C" void fframes_nv12_owner_release(void* pixel){
    Owner o{};bool found=false;{std::lock_guard<std::mutex> lock(logMutex);auto i=owners.find(pixel);if(i!=owners.end()){o=i->second;owners.erase(i);found=true;}}
    if(!found){std::lock_guard<std::mutex> lock(logMutex);auto i=sourceOwners.find(pixel);if(i!=sourceOwners.end()){o=i->second;sourceOwners.erase(i);found=true;
        if(logFile){fprintf(logFile,"{\"seq\":%llu,\"event\":\"source-avbuffer-owner-release\",\"context\":%llu,\"index\":%u,\"sourcePixelBuffer\":%llu,\"sourceSurfaceId\":%u}\n",(unsigned long long)++sequence,o.context,o.index,(uint64_t)pixel,o.surface);fflush(logFile);}return;
    }}
    if(found)trace("\"event\":\"avbuffer-owner-release\",\"context\":%llu,\"index\":%u,\"pixelBuffer\":%llu,\"surfaceId\":%u,\"opaqueEncoderOwnershipKnown\":false",o.context,o.index,(uint64_t)pixel,o.surface);
}
extern "C" void fframes_nv12_destroy(Converter* c){trace("\"event\":\"converter-destroy\",\"context\":%llu",c->id);delete c;}
extern "C" void fframes_nv12_profile_finish(){std::lock_guard<std::mutex> lock(logMutex);if(captureStarted){[[MTLCaptureManager sharedCaptureManager] stopCapture];captureStarted=false;}if(logFile){fflush(logFile);}}

// Actual bounded CoreVideo-pool ownership test: a second counted owner must prevent reuse.
extern "C" bool fframes_nv12_pool_test(void* device){
    @autoreleasepool {
        auto* c=(Converter*)fframes_nv12_create(device,256,128);if(!c)return false;
        CVPixelBufferRef held[64]={};NSDictionary* threshold=@{(id)kCVPixelBufferPoolAllocationThresholdKey:@64};bool ok=true;
        for(auto& b:held)if(CVPixelBufferPoolCreatePixelBufferWithAuxAttributes(nullptr,c->pool,(__bridge CFDictionaryRef)threshold,&b))ok=false;
        CVPixelBufferRef extra=nullptr;auto full=CVPixelBufferPoolCreatePixelBufferWithAuxAttributes(nullptr,c->pool,(__bridge CFDictionaryRef)threshold,&extra);
        if(extra)CVPixelBufferRelease(extra);ok=ok&&full==kCVReturnWouldExceedAllocationThreshold;
        if(held[0]){
            auto retained=held[0];CVPixelBufferRetain(retained);CVPixelBufferRelease(held[0]);held[0]=nullptr;extra=nullptr;
            auto still=CVPixelBufferPoolCreatePixelBufferWithAuxAttributes(nullptr,c->pool,(__bridge CFDictionaryRef)threshold,&extra);
            if(extra)CVPixelBufferRelease(extra);ok=ok&&still==kCVReturnWouldExceedAllocationThreshold;
            auto id=IOSurfaceGetID(CVPixelBufferGetIOSurface(retained));CVPixelBufferRelease(retained);extra=nullptr;
            auto recycled=CVPixelBufferPoolCreatePixelBufferWithAuxAttributes(nullptr,c->pool,(__bridge CFDictionaryRef)threshold,&extra);
            ok=ok&&recycled==0&&extra&&IOSurfaceGetID(CVPixelBufferGetIOSurface(extra))==id;
            if(extra)CVPixelBufferRelease(extra);
        }
        for(auto b:held)if(b)CVPixelBufferRelease(b);
        trace("\"event\":\"pool-lifetime-control\",\"passed\":%s,\"threshold\":64,\"blockedWhileSecondOwnerHeld\":%s,\"sameSurfaceReusedAfterFinalRelease\":%s",ok?"true":"false",ok?"true":"false",ok?"true":"false");
        delete c;return ok;
    }
}
