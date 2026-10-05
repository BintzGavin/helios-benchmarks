#import <Metal/Metal.h>
#import <VideoToolbox/VideoToolbox.h>
#import <CoreMedia/CoreMedia.h>
#define IP(replacement,replacee) __attribute__((used)) static struct {const void* a;const void* b;} ip_##replacee __attribute__((section("__DATA,__interpose")))={(const void*)&replacement,(const void*)&replacee}
#if defined(FAIL_DEVICE)
static id<MTLDevice> refuseDevice(){return nil;}
IP(refuseDevice,MTLCreateSystemDefaultDevice);
#elif defined(FAIL_ENCODER)
static OSStatus refuseEncoder(CFAllocatorRef,int32_t,int32_t,CMVideoCodecType,CFDictionaryRef,CFDictionaryRef,CFAllocatorRef,VTCompressionOutputCallback,void*,VTCompressionSessionRef*){return -12902;}
IP(refuseEncoder,VTCompressionSessionCreate);
#elif defined(FAIL_FORMAT)
static OSStatus refuseParameter(CMFormatDescriptionRef,size_t,const uint8_t**,size_t*,size_t*,int*){return -12712;}
IP(refuseParameter,CMVideoFormatDescriptionGetHEVCParameterSetAtIndex);
#else
#error explicit scoped fault required
#endif
