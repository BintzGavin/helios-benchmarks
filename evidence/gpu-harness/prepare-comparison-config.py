import pathlib,json,hashlib
root=pathlib.Path(__file__).resolve().parent.parent
native=pathlib.Path('/private/tmp/helios-gpu-evidence').resolve()
helios=pathlib.Path('/Users/gavinbintz/.codex/worktrees/native-gpu-rendering/helios')
def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def binding(p):return {'path':str(p),'sha256':sha(p)}
node='/opt/homebrew/bin/node';tsx=str(helios/'node_modules/tsx/dist/cli.mjs')
common=[root/'checkpoint/export-comparison.mts',helios/'packages/portable/src/render.ts',helios/'packages/portable/src/gpu.ts',helios/'packages/portable/benchmarks/fframes-textgrid.mjs',root/'comparison/font/DMSans-Regular.ttf']
att={'engine':'fframes','sourcePin':'f89cbd572524b70a709ba3569fa23b0bbc8a0d9c','physicalDevice':'Apple M3 Pro','softwareActivePath':'SkiaMetalCtx::new_with_device -> GPU frame_renderer -> Previewer::render -> CPU RGBA readback','hardwareActivePath':'SkiaEncoderFrameRenderer HardwareFrames checked in every actual worker; required h264_videotoolbox allow_sw=0','profile':'fframes-profile.jsonl','zeroCopyProved':False,'timedPerFrameExternalProof':False}
attestation=root/'comparison/fframes-gpu-attestation.json'
if not attestation.exists():attestation.write_text(json.dumps(att,indent=2))
def engine(id,lane):
 mode='software' if lane=='software' else 'hardware'
 if id=='R':
  ref=root/'comparison/reference-r-software-02/reference.mkv';screen=root/'comparison/screen-r-software-01tab/quality.json';cmd=[node,tsx,str(root/'checkpoint/export-remotion.mts'),mode,'{output}'];gpu=root/'comparison/remotion-gpu-attestation.json';pin='Remotion4.0.529/Chromium154.0.8037.97';files=[root/'checkpoint/export-remotion.mts',helios/'packages/portable/src/render.ts',pathlib.Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')]
 else:
  ref=(native/('final-reference-software' if mode=='software' else 'final-reference-hardware-tagged')/'reference.mkv') if id=='H' else root/('comparison/reference-f-software/reference.mkv' if mode=='software' else 'comparison/reference-f-hardware-02/reference.mkv')
  screen=root/('comparison/screen-h-software/quality.json' if mode=='software' else 'comparison/screen-h-hardware-100/quality.json') if id=='H' else root/('comparison/screen-f-software-03/quality.json' if mode=='software' else 'comparison/screen-f-hardware-180/quality.json')
  cmd=[node,tsx,str(root/'checkpoint/export-comparison.mts'),id,mode,'{output}','300',str(100000000 if id=='H' else 180000000)]
  gpu=native/'full-profile.stdout.json' if id=='H' else root/'comparison/fframes-gpu-attestation.json';pin='478035260fb5c0ae5a391e9b66bacee19a7a9ffa' if id=='H' else 'f89cbd572524b70a709ba3569fa23b0bbc8a0d9c';files=common+[helios/'packages/portable/native/target/release/helios-gpu' if id=='H' else root/'build/fframes-current/release/textgrid-adapter']
 quality=json.loads(screen.read_text());assert quality['passed'] and quality['quality']['status']=='evaluated'
 return {'id':id,'command':cmd,'cwd':str(root),'source_pin':pin,'backend':'Metal/Skia' if id!='R' else 'Chromium ANGLE Metal','codec':'libx264 medium CRF11 threads2' if mode=='software' else 'required VideoToolbox H264','ready':True,'reference':str(ref),'reference_sha256':sha(ref),'gpu_evidence':str(gpu),'runtime_attestation_reviewed':True,'screen_quality':str(screen),'screen_quality_sha256':sha(screen),'screen_quality_passed':True,'file_bindings':[binding(p) for p in files+[gpu]]}
for lane,ids in [('software',['H','F','R']),('hardware',['H','F'])]:
 config={'scene':{'width':1920,'height':1080,'frames':300,'fps':30,'name':'TextGrid'},'lane':'gpu-raster-software-x264' if lane=='software' else 'hardware-product-pipeline','four_balanced_rounds':True,'quality_floors':{'ssimY':.995,'psnrY':40,'psnrU':35,'psnrV':35},'timingContract':'fresh adapter process startup, font/scene/raster/conversion/transport/encode/mux/write plus one supervisor full decode; quality excluded','engines':[engine(i,lane) for i in ids],'limitations':[] if lane=='software' else ['Product pipeline comparison: H100Mbps BT709 limited GPU conversion; F180Mbps BT601 attachments with opaque encoder conversion. Same own-reference floors, different color transforms and encoder bitrates. Not isolated GPU throughput.']}
 (root/f'comparison/{lane}-config.json').write_text(json.dumps(config,indent=2))
host=json.loads((root/'checkpoint/host-preflight-unsandboxed.json').read_text());host.pop('inventory',None)
(root/'comparison/preflight-sanitized.json').write_text(json.dumps(host,indent=2))
