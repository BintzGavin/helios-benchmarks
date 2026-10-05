import pathlib,json,hashlib,subprocess,importlib.util,shutil
root=pathlib.Path(__file__).resolve().parent.parent;r=root/'comparison/native-chroma-contract-20261004';r.mkdir(exist_ok=False)
def pin(p):
 with p.open('rb') as f:return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
base=pathlib.Path('/Users/gavinbintz/.codex/worktrees');metal=base/'gpu-binary-transport/helios/packages/portable/native/metal.mm';vulkan=base/'gpu-vulkan-interop/helios/packages/portable/native/metal.mm';helper=base/'gpu-binary-transport/helios/packages/portable/native/target/release/helios-gpu'
assert pin(helper)['sha256']=='1383da791a588731101f6dd22bea8e911d4bc97243b7f01541214981afc90ecc'
old=root/'comparison/circles-common-binary-screen-h-300';q=json.loads((old/'quality.json').read_text());adapter=json.loads((old/'adapter.json').read_text());assert adapter['executableSha256']==pin(helper)['sha256'] and q['passed']
shader=lambda p:p.read_text().split('R"metal(',1)[1].split(')metal"',1)[0]
# Locate actual common inline source rather than inferring from texture capability flags.
texts={str(p):p.read_text() for p in [metal,vulkan]}
for text in texts.values():
 assert 'for (uint dy = 0; dy < 2; ++dy) for (uint dx = 0; dx < 2; ++dx)' in text
 assert 'uint2 q = 2 * p + uint2(dx, dy);' in text
 assert '56.0f * chroma' in text and '1.8556f' in text and '1.5748f' in text
 assert 'kCVImageBufferChromaLocationTopFieldKey' not in text and 'kCVImageBufferChromaLocationBottomFieldKey' not in text
snippet=lambda t:t[t.index('kernel void'):t.index(')metal"')]
assert snippet(texts[str(metal)])==snippet(texts[str(vulkan)])
video=pathlib.Path(q['candidate']['path']);reference=pathlib.Path(q['reference']['path']);before=[pin(p) for p in [old/'quality.json',old/'adapter.json',video,reference,helper,metal,vulkan]]
cmd=['/opt/homebrew/bin/ffmpeg','-hide_banner','-loglevel','trace','-i',str(video),'-map','0:v:0','-frames:v','1','-c:v','copy','-bsf:v','trace_headers','-f','null','-'];p=subprocess.run(cmd,capture_output=True,text=True,timeout=60);assert p.returncode==0
(r/'native-first-packet-SPS-trace.stderr.log').write_text(p.stderr)
spec=importlib.util.spec_from_file_location('sps',root/'checkpoint/audit-nv12-conformance.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);fields=m.spsfields(p.stderr)
assert ['chroma_loc_info_present_flag',0] in fields and not any('chroma_sample_loc_type' in x[0] for x in fields)
assert q['candidate']['probe']['stream']['chroma_location']=='left' and q['reference']['probe']['stream'].get('chroma_location') is None
for x in before:assert pin(pathlib.Path(x['path']))==x
report={'status':'confirmed native physical centered2x2 versus absent/defaultleft SPS and unspecified reference metadata; new aligned lane correction required','readOnlyExistingEvidence':True,'newBuildExportDecodeOrTiming':False,'timingWindowOpen':False,'readSet':before,'savedNumericQualityPassed':True,'oldByteBindingsClocksVideosUnchanged':True,'source':{'nativeHelper':pin(helper),'oldMetal':pin(metal),'currentVulkanMetal':pin(vulkan),'conversionShaderBytesEqual':True,'predictedPhysicalCenter':'2x2 samples at offsets(0,0),(1,0),(0,1),(1,1), equalweights center(0.5,0.5)','chromaMath':'sum4 chroma *56 = mean *224','CoreVideoChromaLocationAttachmentsPresent':False},'SPS':{'command':cmd,'returncode':0,'fields':fields,'flagPresent':False,'decodedSavedMetadata':'left','inference':'absent explicit siting signals defaultleft despite centered equal2x2 physical samples'},'oldReferenceSavedMetadata':None,'modifiedFReferenceAndSPSMetadata':'center; independently qualified current lane','oldNumericQualityInvalidated':False,'matchedColorContractCurrentlyAligned':False,
 'nextBoundedNativeConformanceSlice':{'scope':'separate owner harness signaling/reference correction, no native helper rebuild/optimization','predeterminedControls':'use centered2x2 independent RGB controls and the unchanged sRGB->BT709 limited formula; no fitting to encoded pixels/floors','candidateCorrection':'new SPS-only conformed H264 outputs in fresh lane with full syntax/allremainingRBSP/PPS/everyVCL/allDecoded invariance; correct lossless reference siting tags with per-frame rawNV12 binding and decoded-byte equality','HEVCDistinct':'codec-specific SPS/VUI semantic and raw payload/decoded invariance validation required; H264 filter result not extrapolated','requiredFreshQualification':'all3004K reference binding and same quality/cadence/color/GOP gates; source/helper/adapter/reference pins; frozen old lane preserved','timedCost':'include mandatory signaling/template/copy mux in new export/delivery clocks; exclude independent decode and reference diagnostics','nativeConcurrency':'pool3 retained; comparison discloses F64/context and3contexts/5+5workers/queue10','resourceGate':'enoughspace before new output/reference/quality runs; no timingwindow now'},'zeroCopyProved':False,'noProductBugOrPerformanceClaim':True,'freeBytes':shutil.disk_usage(root).free}
(r/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['readSet','source','SPS','nextBoundedNativeConformanceSlice']}))
