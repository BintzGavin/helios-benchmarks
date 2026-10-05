#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <CoreVideo/CoreVideo.h>
#include <cstdio>
#include <cassert>
#include <string>
extern "C" void* helios_create(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,const char*,bool,const char*,const char*);
extern "C" void* helios_device(void*);
extern "C" void* helios_queue(void*);
extern "C" bool comparison_import_bgra(void*,CVPixelBufferRef,uint32_t);
extern "C" bool helios_reference(void*,uint32_t);
extern "C" bool helios_encode(void*,uint32_t);
extern "C" bool helios_finish(void*,uint32_t);
extern "C" bool helios_close(void*);
static CVPixelBufferRef pixel(uint32_t width,OSType format) {
 NSDictionary* attrs=@{(id)kCVPixelBufferMetalCompatibilityKey:@YES,(id)kCVPixelBufferIOSurfacePropertiesKey:@{},(id)kCVMetalTextureUsage:@(MTLTextureUsageShaderRead|MTLTextureUsageShaderWrite)};
 CVPixelBufferRef p=nullptr;assert(!CVPixelBufferCreate(nullptr,width,64,format,(__bridge CFDictionaryRef)attrs,&p));return p;
}
int main(int argc,char**argv) {
 @autoreleasepool {
  assert(argc==3);bool reference=std::string(argv[1])=="reference";
  void* state=helios_create(64,64,30,1,1000000,30,3,reference?"":argv[2],true,"","");assert(state);
  assert(!comparison_import_bgra(state,nullptr,0));
  auto wrongSize=pixel(66,kCVPixelFormatType_32BGRA);assert(!comparison_import_bgra(state,wrongSize,0));CVPixelBufferRelease(wrongSize);
  auto wrongFormat=pixel(64,kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange);assert(!comparison_import_bgra(state,wrongFormat,0));CVPixelBufferRelease(wrongFormat);
  id<MTLDevice> device=(__bridge id<MTLDevice>)helios_device(state);id<MTLCommandQueue> queue=(__bridge id<MTLCommandQueue>)helios_queue(state);
  CVMetalTextureCacheRef cache=nullptr;assert(!CVMetalTextureCacheCreate(nullptr,nullptr,device,nullptr,&cache));
  NSString* shader=@"#include <metal_stdlib>\nusing namespace metal; kernel void solid(texture2d<float,access::write> image [[texture(0)]], constant float4& color [[buffer(0)]],uint2 p [[thread_position_in_grid]]) { if(p.x<image.get_width()&&p.y<image.get_height())image.write(color,p); }";
  NSError* error=nil;auto library=[device newLibraryWithSource:shader options:nil error:&error];assert(library);auto pipeline=[device newComputePipelineStateWithFunction:[library newFunctionWithName:@"solid"] error:&error];assert(pipeline);
  const float colors[4][4]={{1,0,0,1},{0,1,0,1},{0,0,1,1},{64.f/255,128.f/255,191.f/255,1}};
  for(uint32_t i=0;i<4;i++) {
   auto input=pixel(64,kCVPixelFormatType_32BGRA);CVMetalTextureRef cvTexture=nullptr;assert(!CVMetalTextureCacheCreateTextureFromImage(nullptr,cache,input,nullptr,MTLPixelFormatBGRA8Unorm,64,64,0,&cvTexture));
   auto command=[queue commandBuffer];auto compute=[command computeCommandEncoder];[compute setComputePipelineState:pipeline];[compute setTexture:CVMetalTextureGetTexture(cvTexture) atIndex:0];[compute setBytes:colors[i] length:sizeof(colors[i]) atIndex:0];[compute dispatchThreads:MTLSizeMake(64,64,1) threadsPerThreadgroup:MTLSizeMake(8,8,1)];[compute endEncoding];[command commit];[command waitUntilCompleted];assert(command.status==MTLCommandBufferStatusCompleted);
   assert(comparison_import_bgra(state,input,i));CFRelease(cvTexture);CVPixelBufferRelease(input);
   // Release the source before conversion/encode to test import completion and
   // lifetime isolation. Reference-only mode intentionally downloads NV12 bytes.
   assert(reference?helios_reference(state,i):helios_encode(state,i));
  }
  if(!reference)assert(helios_finish(state,4));CFRelease(cache);assert(helios_close(state));fprintf(stderr,"source lifetime, BGRA channel order, dimensions/formats, four imports and finaldrain passed\n");
 }
}
