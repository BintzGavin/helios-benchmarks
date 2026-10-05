#import <Metal/Metal.h>
#import <CoreVideo/CoreVideo.h>
#import <IOSurface/IOSurface.h>
#import <objc/runtime.h>
#include <dlfcn.h>
#include <cstdio>
#include <mutex>

static FILE* output;
static std::mutex guard;
static thread_local bool inside=false;
static void log(const char* event,uint64_t bytes=0){if(inside||!output)return;inside=true;{std::lock_guard<std::mutex> lock(guard);fprintf(output,"{\"event\":\"%s\",\"bytes\":%llu}\n",event,(unsigned long long)bytes);fflush(output);}inside=false;}
#define INTERPOSE(replacement, original) __attribute__((used)) static struct {const void* replace;const void* original;} pair_##original __attribute__((section("__DATA,__interpose")))={(const void*)&replacement,(const void*)&original}
static CVReturn lock_cv(CVPixelBufferRef p,CVPixelBufferLockFlags flags){log("CVPixelBufferLockBaseAddress");return CVPixelBufferLockBaseAddress(p,flags);}INTERPOSE(lock_cv,CVPixelBufferLockBaseAddress);
static void* base_cv(CVPixelBufferRef p){log("CVPixelBufferGetBaseAddress");return CVPixelBufferGetBaseAddress(p);}INTERPOSE(base_cv,CVPixelBufferGetBaseAddress);
static void* plane_cv(CVPixelBufferRef p,size_t plane){log("CVPixelBufferGetBaseAddressOfPlane");return CVPixelBufferGetBaseAddressOfPlane(p,plane);}INTERPOSE(plane_cv,CVPixelBufferGetBaseAddressOfPlane);
static IOReturn lock_io(IOSurfaceRef p,IOSurfaceLockOptions opts,uint32_t* seed){log("IOSurfaceLock");return IOSurfaceLock(p,opts,seed);}INTERPOSE(lock_io,IOSurfaceLock);
static void* base_io(IOSurfaceRef p){log("IOSurfaceGetBaseAddress");return IOSurfaceGetBaseAddress(p);}INTERPOSE(base_io,IOSurfaceGetBaseAddress);
static void* plane_io(IOSurfaceRef p,size_t plane){log("IOSurfaceGetBaseAddressOfPlane");return IOSurfaceGetBaseAddressOfPlane(p,plane);}INTERPOSE(plane_io,IOSurfaceGetBaseAddressOfPlane);
static IMP getBytesOriginal=nullptr,copyOriginal=nullptr,contentsOriginal=nullptr;
static void get_bytes(id self,SEL selector,void* bytes,NSUInteger row,MTLRegion region,NSUInteger level){log("texture-getBytes",region.size.width*region.size.height*4);((void(*)(id,SEL,void*,NSUInteger,MTLRegion,NSUInteger))getBytesOriginal)(self,selector,bytes,row,region,level);}
static void copy_texture(id self,SEL selector,id<MTLTexture> texture,NSUInteger slice,NSUInteger level,MTLOrigin origin,MTLSize size,id<MTLBuffer> buffer,NSUInteger offset,NSUInteger row,NSUInteger image){log("texture-to-buffer",size.width*size.height*4);((void(*)(id,SEL,id,NSUInteger,NSUInteger,MTLOrigin,MTLSize,id,NSUInteger,NSUInteger,NSUInteger))copyOriginal)(self,selector,texture,slice,level,origin,size,buffer,offset,row,image);}
static void* contents(id self,SEL selector){log("buffer-contents-unknown-intent");return ((void*(*)(id,SEL))contentsOriginal)(self,selector);}
static bool install(id object,SEL selector,IMP replacement,IMP* original){
    Class cls=object_getClass(object);Method method=class_getInstanceMethod(cls,selector);if(!method)return false;
    *original=method_getImplementation(method);
    // Add a concrete-class override when inherited. Never mutate an inherited superclass twice.
    if(!class_addMethod(cls,selector,replacement,method_getTypeEncoding(method)))method_setImplementation(class_getInstanceMethod(cls,selector),replacement);
    return true;
}
__attribute__((constructor)) static void setup(){
    @autoreleasepool {
        const char* path=getenv("FFRAMES_EXTERNAL_TRANSFER_LOG");if(!path||!path[0])return;
        output=fopen(path,"wx");if(!output)return;
        auto device=MTLCreateSystemDefaultDevice();auto queue=[device newCommandQueue];auto command=[queue commandBuffer];auto blit=[command blitCommandEncoder];
        auto descriptor=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:256 height:128 mipmapped:NO];descriptor.storageMode=MTLStorageModeShared;
        auto texture=[device newTextureWithDescriptor:descriptor];auto buffer=[device newBufferWithLength:256*128*4 options:MTLResourceStorageModeShared];
        bool a=install(texture,@selector(getBytes:bytesPerRow:fromRegion:mipmapLevel:),(IMP)get_bytes,&getBytesOriginal);
        bool b=install(blit,@selector(copyFromTexture:sourceSlice:sourceLevel:sourceOrigin:sourceSize:toBuffer:destinationOffset:destinationBytesPerRow:destinationBytesPerImage:),(IMP)copy_texture,&copyOriginal);
        bool c=install(buffer,@selector(contents),(IMP)contents,&contentsOriginal);[blit endEncoding];
        log(a&&b&&c?"interposer-installed":"interposer-install-failed");
    }
}
