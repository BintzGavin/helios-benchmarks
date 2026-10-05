import pathlib,json,hashlib,subprocess,zipfile,shutil,re,time,os
root=pathlib.Path(__file__).resolve().parent.parent;r=root/'comparison/fframes-concurrent-nv12-20261004';deliver=root/'deliverables'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
build=json.loads((r/'BUILD-READY.json').read_text())
for x in build['source']:assert sha(pathlib.Path(build['sourceDirectory'])/x['path'])==x['sha256']
for x in build['helpers']:
 for key in ['path','immutableCopy']:assert sha(pathlib.Path(x[key]))==x['sha256']
with zipfile.ZipFile(r/'source.zip') as z:assert z.testzip() is None
assert sha(r/'source.zip')==build['sourceZipSha256']
# Verify retained original-product failure/clock/reference files and prior scope pins, never modify them.
oldroot=root/'comparison/fframes-original-handoff-20261004';oldmanifest=json.loads((oldroot/'RECEIPT-MANIFEST.json').read_text())
for x in oldmanifest['files']:assert (oldroot/x['path']).stat().st_size==x['bytes'] and sha(oldroot/x['path'])==x['sha256']
prior=json.loads((deliver/'FFRAMES-COLOR-CONTRACT-INVESTIGATION-20261004.json').read_text())['readSet']
for x in prior:assert pathlib.Path(x['path']).stat().st_size==x['bytes'] and sha(pathlib.Path(x['path']))==x['sha256']
write(r/'PRIOR-EVIDENCE-UNCHANGED.json',{'passed':True,'oldManifest':pin(oldroot/'RECEIPT-MANIFEST.json'),'oldFilesVerified':len(oldmanifest['files']),'priorReadSet':prior,'noPreviousClocksOrSourceModified':True})
# Record exact linked runtime and host receipts. Shared-cache libraries are reported as unavailable bytes.
runtime=[]
for h in build['helpers']:
 p=pathlib.Path(h['path']);cmd=['/usr/bin/otool','-L',str(p)];s=subprocess.run(cmd,capture_output=True,text=True);assert s.returncode==0
 libs=[]
 for line in s.stdout.splitlines()[1:]:
  name=line.strip().split(' (',1)[0];path=pathlib.Path(name);path=path if path.is_absolute() else root/path
  libs.append({'installName':name,'resolvedPath':str(path),'sha256':sha(path) if path.is_file() else None,'readableBytes':path.is_file(),'sharedCacheBytesNotMaterialized':not path.is_file()})
 runtime.append({'helper':pin(p),'command':cmd,'returncode':s.returncode,'stdout':s.stdout,'stderr':s.stderr,'libraries':libs})
commands=[['/usr/bin/sw_vers'],['/usr/sbin/system_profiler','SPHardwareDataType','SPDisplaysDataType','-json'],['/opt/homebrew/bin/ffmpeg','-version'],['/opt/homebrew/bin/ffprobe','-version'],['/usr/bin/clang++','--version']]
host=[]
for cmd in commands:
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=30);assert p.returncode==0;host.append({'command':cmd,'returncode':0,'stdout':p.stdout,'stderr':p.stderr})
write(r/'EXACT-RUNTIME-PINS.json',{'workingDirectory':str(root),'relativeConverterInstallName':'sources/fframes-concurrent-nv12/nv12-converter.dylib','runtime':runtime,'host':host,'validationTools':[pin(pathlib.Path('/opt/homebrew/bin/ffmpeg').resolve()),pin(pathlib.Path('/opt/homebrew/bin/ffprobe').resolve())],'noProcessEnvironmentInspected':True})
# Archive/pin Cargo workspace source reached through executor symlinks, including local svgr override source.
paths=[];source=pathlib.Path(build['sourceDirectory']);excluded={'.git','target','node_modules','.next','dist'}
for link in source.iterdir():
 if not link.is_symlink() or link.name in {'landing','fframes-editor','skills','.vscode','.github','scripts'}:continue
 for base,dirs,files in os.walk(link):
  dirs[:]=[d for d in dirs if d not in excluded]
  for f in files:
   p=pathlib.Path(base)/f
   if p.suffix in {'.rs','.toml','.lock','.wgsl','.h','.hpp','.cpp','.mm'} and p.is_file():paths.append((p,'workspace/'+str(p.relative_to(source))))
# Match exact path override directories, no guessed downloads.
toml=(source/'Cargo.toml').read_text()
for path in set(re.findall(r'path\s*=\s*"([^\"]+)"',toml)):
 p=pathlib.Path(path)
 if not p.is_absolute() or not p.exists():continue
 for base,dirs,files in os.walk(p):
  dirs[:]=[d for d in dirs if d not in excluded]
  for f in files:
   q=pathlib.Path(base)/f
   if q.suffix in {'.rs','.toml','.lock'}:paths.append((q,'path-overrides/'+p.name+'/'+str(q.relative_to(p))))
seen=set();dep=[]
with zipfile.ZipFile(r/'dependency-source-overlay.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
 for p,name in sorted(paths,key=lambda x:x[1]):
  if name in seen:continue
  seen.add(name);z.write(p,name);dep.append({**pin(p),'archiveName':name})
with zipfile.ZipFile(r/'dependency-source-overlay.zip') as z:assert z.testzip() is None
write(r/'DEPENDENCY-SOURCE-PINS.json',{'files':dep,'entries':len(dep),'archive':pin(r/'dependency-source-overlay.zip'),'fullCheckoutRequired':True,'baseCommit':build['sourceBaseline'],'optimizedSvgr':build['optimizedUsvgr']})
harness=[root/'checkpoint'/x for x in ['run-concurrent-nv12.py','audit-concurrent-nv12.py','audit-concurrent-gpu.py','audit-concurrent-4k-profile.py','conform-nv12-chroma.py','audit-nv12-conformance.py','qualify-concurrent-nv12.py','requalify-concurrent-nv12-reference.py','test-concurrent-nv12-acceptance.py','nv12-transfer-interposer.mm','build-fframes-concurrent-nv12-01.py','build-fframes-concurrent-nv12-controls-01.py','recover-failed-reference-storage.py','finalize-concurrent-nv12.py']]
q=json.loads((r/'circles300/quality.json').read_text());controls=json.loads((r/'controls36/quality.json').read_text());profile=json.loads((r/'FULL-4K-TRANSFER-PROFILE.json').read_text());binding=json.loads((r/'circles300/DIRECT-NV12-REFERENCE-BINDING.json').read_text());sps=json.loads((r/'circles300/SPS-FIELD-CADENCE-AUDIT.json').read_text());tests=json.loads((r/'ACCEPTANCE-TESTS.json').read_text())
assert all(x['passed'] for x in [q,controls,profile,binding,sps,tests]);assert binding['frames']==300
report={'status':'modified production-concurrent NV12 functional/4K quality/full-workload transfer profile qualified; performance not measured','broaderObjectiveComplete':False,'owner':'root comparison harness','timingWindowOpen':False,'benchmarkTiming':False,'newBalancedTimingAttempts':0,'originalProduct':False,'publishedM5Reproduction':False,'publishedM5ClaimBeaten':False,'zeroCopyProved':False,'helpers':build['helpers'],'sourceArchive':pin(r/'source.zip'),'dependencySourcePins':pin(r/'DEPENDENCY-SOURCE-PINS.json'),'runtimePins':pin(r/'EXACT-RUNTIME-PINS.json'),'harnessPins':[pin(p) for p in harness],
 'workload':{'scene':'99000circles+1000digits','width':3840,'height':2160,'frames':300,'fps':'30/1','sourceFrames':'3..302','nonuniformScale':'1000x1000 ->3840x2160','painterOrder':'circles before text','audio':False,'font':pin(root/'comparison/font/DM Sans.ttf') if (root/'comparison/font/DM Sans.ttf').exists() else [pin(p) for p in (root/'comparison/font').iterdir() if p.is_file()]},
 'contract':{'gpuContexts':3,'generators':5,'encoderWorkers':5,'queueSize':10,'segments':5,'framesPerSegment':60,'nv12PoolAllocationThresholdPerContext':64,'nativeComparisonPoolThreshold':3,'poolExhaustion':'fail closed','encoder':'required VideoToolbox H264, allow_sw0','bitrateRequested':300000000,'gopRequested':30,'conversion':'direct Skia Metal BGRA texture ->GPU sRGB EOTF/BT709 OETF/limited NV12; centered2x2 chroma box','sourceCompletion':'flush_submit_and_sync_cpu','conversionCompletion':'Metal waitUntilCompleted successful before send/source release','destinationLifetime':'CoreVideo pool and AVBuffer owner, opaque VT retention unknown','mandatorySPSConformance':'independent full SPS parser confirms only chroma location fields; all VCL payload and decoded bytes unchanged; parameter-template/copy mux included in future export/delivery clocks','matchedNativeContractIdentical':False},
 'qualification':{'reference':pin(r/'circles300/reference-direct-nv12-02.mkv'),'candidate':pin(r/'circles300/video-center.mp4'),'originalCandidate':pin(r/'circles300/video.mp4'),'directByteBinding':pin(r/'circles300/DIRECT-NV12-REFERENCE-BINDING.json'),'frames':300,'zeroBindingMismatches':True,'noReferenceColorArithmetic':True,'ssimYMinimum':q['quality']['ssim']['minimum'],'psnrMinimum':q['quality']['psnr']['minimum'],'floorsUnchanged':{'ssimY':.995,'psnrY':40,'psnrU':35,'psnrV':35},'allFramesPassed':True,'margin':'luma PSNR40.23 narrowly exceeds40; every future timed candidate requires its own all-frame gate','controls36':{'ssim':controls['quality']['ssim']['minimum'],'psnr':controls['quality']['psnr']['minimum'],'independentOracleWithinOneCode':True},'cadenceColorGopAudit':pin(r/'circles300/SPS-FIELD-CADENCE-AUDIT.json')},
 'GPU':{'full300TransferProfile':pin(r/'FULL-4K-TRANSFER-PROFILE.json'),'captureReadbackOff':True,'hookedRawDownloadsObserved':0,'three4KPositiveControlsDetected':True,'full300ConversionsAndLifetimesPassed':True,'additionalGpuCopy':False,'opaqueUnhookedCopiesUnknown':True,'zeroCopyProved':False,'actualMetalCapture':'bounded256x128 capture3 succeeds; separate4K capture attempt failed ENOSPC/excluded','profilingAndControlClocksExcluded':True},
 'tests':{'receiptMutationsRejected':tests['mutationsRejected'],'actualFaultRefusals':4,'actualPoolThresholdRetainedSecondOwnerAndReuseTestPassed':True,'newReleaseBinariesBuiltAndExecuted':True,'newCargoFullSuiteClippyNotRun':'compiler cache/disk constraint; no upstream general-product CI claim'},
 'excluded':['all reference-capture/control/profile clocks','initial DYLD-through-time profiler attempt','direct h264_metadata attempt shortening VCL tails','failed initial ENOSPC FFV1 reference','failed initial4K positive attempt','failed4K Metal capture; partial500MB retained','no clock reconstructed as benchmark'],
 'sourceLibraryId':'libfile_19c903c1d7508191ac4881f0e96e4229','historicalCheckpointLibraryId':'libfile_cd84375e4648819195364136245484c6','newLibraryDeliverableIds':[],'libraryBlocker':'supported Library helper prepare_uploads unavailable; no substitute upload route','remaining':['balanced matched Helios/modified concurrent fframes exports with mandatory conformance included','full4K nativeHEVC/Vulkan qualification and matched performance','original-product chroma quality still fails unchanged floors; no product win','publishedM5 benchmark not beaten','Library publication helper blocked','native Vulkan PR push destination approval remains with native thread'], 'storage':{'freeBytes':shutil.disk_usage(root).free,'remainingBalancedMediaEstimate':'several GiB; insufficient free disk for retained balanced outputs/references','taskOwnedCompilerArchivesOnlyReclaimed':True,'failedReferenceRetainedByteExactlyViaAPFSClone':True},'noOptimizationSelected':True}
write(r/'FINAL-REPORT.json',report)
(r/'REPRODUCE.md').write_text('''This is a modified production-concurrent fframes GPU NV12 lane, not the original product or published M5 reproduction. All current clocks are excluded diagnostics.

Obtain full fframes checkout f89cbd572524b70a709ba3569fa23b0bbc8a0d9c and svgr1c2a088217eb3365e965fd8dbd62acf265a07d33. Overlay source.zip. Restore dependency-source-overlay.zip workspace/ paths into that checkout; path-overrides/ files bind local svgr/usvgr contents. Exact live source/runtime/Cargo path bindings are in BUILD-READY and DEPENDENCY-SOURCE-PINS. Absolute Cargo paths and the relative converter install name require this executor's CWD or explicit new path/source/build pins. A path substitution invalidates the original hashes; rebuild and requalify.

Frozen converter uses relative installname sources/fframes-concurrent-nv12/nv12-converter.dylib. Run from the declared task root. C build argv and successful logs are retained; Cargo rustc release locked build commands are in checkpoint build scripts and process receipts. Official Skia0.153.3 and original FFmpeg9.0.0 remain; no native Helios ABI substitution. The copied static compiler caches were reclaimed after all jobs terminated; source/dependency pins and retained executables remain.

Use fresh directories. run-concurrent-nv12.py records commands/settings without dumping the process environment. controls36 runs the predetermined oracle; circles300 captures the exact encoder-input NV12 frames. qualification and SPS-only conformance scripts require actual indexed reference and decoded-byte/VCL equality before all-frame quality. Full qualification already completed; do not rerun it to reconstruct clocks. reference-direct-nv12-02.mkv is the valid reference; the first partial reference is explicitly invalid/excluded and byte-exactly retained.

For a future timed runner: disable raw capture (FFRAMES_CAPTURE_NO_DOWNLOAD=1), remove profiling/interposition/capture, preserve3contexts/5generator/5encoderworkers/queue10 and64poolthreshold/context, pin helper/converter/font/settings, and include startup/render/encode/segment mux plus the mandatory parameter-template and SPS-only copy mux in export clocks. Stop the export clock before excluded decode/reference/quality checks, then separately report API-delivered validation. Preserve raw clocks, ordered balanced rounds, no concurrent engines. Every timed video must pass its own unchanged .995/40/35/35 per-frame floors, all300cadence/color/GOP checks, and exact SPS/VCL/decode conformance. Native pool3 differs from fframes64/context; disclose this in comparison conclusions.

Full300 uncaptured4K external profile and separate3same4K raw-download positive controls passed, with0 observed hooked raw downloads. Pointer intent, unhooked and opaque driver/encoder transfers remain unknown: zeroCopyProved=false. 256x128 actual Metal capture succeeded; a distinct4K capture failed ENOSPC and is retained/excluded. Profiling, raw reference capture, copy diagnostics and every existing clock are excluded from speed claims.

The review ZIP contains source overlays, runtime/harness pins, protocol, tests, raw ledgers, logs and small outputs. Large candidate/reference files and frozen binaries remain in the local SHA-bound manifest. Full raw receipt file access is required for independent replay; review ZIP is not a complete media archive. Library prepare_uploads remains unavailable, so there is no new Library result ID.
''')
write(r/'HARNESS-PINS.json',{'files':[pin(p) for p in harness]})
# Freeze final root manifest; exclude itself only. Opaque capture metadata remains uninspected.
files=[]
for p in sorted(r.rglob('*')):
 if p.is_file() and p.name!='RECEIPT-MANIFEST.json':files.append({'path':str(p.relative_to(r)),'bytes':p.stat().st_size,'sha256':sha(p)})
write(r/'RECEIPT-MANIFEST.json',{'files':files,'entries':len(files),'bytes':sum(x['bytes'] for x in files),'allFilesReadable':True,'manifestExcludesItself':True,'captureMetadataNotInterpreted':True,'benchmarkTiming':False,'timingWindowOpen':False})
md='''The modified concurrent fframes GPU lane passes the full 4K quality gate. All300 exact NV12 encoder-input frames bind to the lossless reference without color arithmetic. Every decoded frame meets the unchanged .995 SSIM-Y and40/35/35 PSNR-Y/U/V floors; observed minima are .995261 and40.23/40.54/40.48. The luma margin is narrow, so every timed repeat must qualify independently.

Production scheduling stays3GPUcontexts,5generatorworkers,5encoderworkers,queue10 and5ordered60frame segments. A separate64allocation threshold per CoreVideo converter context is configured; native Helios uses pool3. The new directGPU converter and mandatory SPS-only chroma signaling/copy mux make this a modified pipeline. Full SPS semantic parsing permits only chroma-location changes; all VCL payloads and decoded frame bytes are identical before/after conformance. Future clocks must include that stage.

The full300-frame uncaptured4K profile observes no hooked raw download; same4K NV12/RGBA positive controls detect deliberate downloads. All300GPU conversions, source fences and AVBuffer ownership orders pass. Opaque driver/encoder transfers and pointer intent remain unknown; total zero-copy is unproved. 16acceptance mutations,4actual fault refusals and the64buffer retained-owner/reuse control pass. The separate4K Metal capture and initial FFV1 reference hit ENOSPC; failed artifacts remain excluded and byte-preserved. The reference retry passes. No balanced performance round has run in this lane.

Review/source package and all raw receipts are SHA-bound below. Previous original-product failures, references and clocks were verified unchanged. The broader comparison, full4K nativeHEVC/Vulkan qualification and publishedM5 target remain unfinished. Free disk is insufficient for retained balanced outputs; supported Library prepare_uploads is unavailable, so no new Library IDs exist.
'''
(deliver/'FFRAMES-CONCURRENT-NV12-20261004.md').write_text(md)
package=deliver/'fframes-concurrent-nv12-review-20261004.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
 for p in sorted(r.rglob('*')):
  if not p.is_file() or 'metal.gputrace' in str(p) or p.suffix in {'.mp4','.mkv','.zlib','.dylib'} or p.name.startswith('frozen-'):continue
  # Source archive nested compressed bytes are stored as-is.
  z.write(p,'evidence/'+str(p.relative_to(r)),compress_type=zipfile.ZIP_STORED if p.suffix=='.zip' else zipfile.ZIP_DEFLATED)
 for p in harness:z.write(p,'checkpoint/'+p.name)
 for p in [root/'checkpoint/concurrent-nv12-compiler-cache-reclamation.json',root/'checkpoint/concurrent-nv12-static-cache-reclamation.json',root/'checkpoint/concurrent-nv12-final-static-cache-reclamation.json']:z.write(p,'checkpoint/'+p.name)
 # Validator consumed in this executor is directly copied, never recreated.
 candidates=list((root/'preparation').rglob('validate_video.py')) if (root/'preparation').exists() else []
 if not candidates:
  candidates=[p for p in root.glob('**/validate_video.py') if 'node_modules' not in p.parts and 'sources' not in p.parts]
 assert candidates,'required prep validator missing'
 z.write(candidates[0],'preparation/validate_video.py')
 z.write(deliver/'FFRAMES-CONCURRENT-NV12-20261004.md','REPORT.md')
with zipfile.ZipFile(package) as z:assert z.testzip() is None;members=len(z.infolist())
# Recheck manifest after packaging, not rewriting qualified files.
for x in files:assert (r/x['path']).stat().st_size==x['bytes'] and sha(r/x['path'])==x['sha256']
delivery={'status':report['status'],'report':pin(r/'FINAL-REPORT.json'),'manifest':pin(r/'RECEIPT-MANIFEST.json'),'reviewPackage':{**pin(package),'members':members,'CRCpassed':True},'sourceArchive':pin(r/'source.zip'),'allManifestPinsRechecked':True,'broaderObjectiveComplete':False,'timingWindowOpen':False,'newLibraryIds':[],'remaining':report['remaining'],'freeBytesAfter':shutil.disk_usage(root).free}
write(deliver/'FFRAMES-CONCURRENT-NV12-DELIVERY-20261004.json',delivery);write(root/'checkpoint/FFRAMES-CONCURRENT-NV12-20261004.json',delivery)
print(json.dumps(delivery))
