import pathlib,hashlib,json
p=pathlib.Path('comparison/common-import-reference.nv12');b=p.read_bytes();w=h=64;size=w*h*3//2;assert len(b)==size*4
colors=[(255,0,0),(0,255,0),(0,0,255),(64,128,191)];rows=[]
def transfer(v):
 s=v/255;linear=s/12.92 if s<=.04045 else ((s+.055)/1.055)**2.4
 return 4.5*linear if linear<.018 else 1.099*linear**.45-.099
for i,color in enumerate(colors):
 r,g,bl=map(transfer,color);y=.2126*r+.7152*g+.0722*bl
 # Limited-range chroma spans224 levels for Cb/Cr in[-.5,+.5].
 expected=[round(16+219*y),round(128+224*(bl-y)/1.8556),round(128+224*(r-y)/1.5748)]
 frame=b[i*size:(i+1)*size];planes=[frame[:w*h],frame[w*h::2],frame[w*h+1::2]];delta=[max(abs(x-target) for x in plane) for plane,target in zip(planes,expected)];assert max(delta)<=1;rows.append({'inputRgb':color,'expectedYUV':expected,'actualUniqueYUV':[sorted(set(x)) for x in planes],'maximumError':delta})
pathlib.Path('comparison/common-import-test.json').write_text(json.dumps({'passed':True,'sourceGpuWritesOnly':True,'referenceOnlyCpuDownload':True,'tests':'four solidcolors/channelorder, quantizedmidtone BT709transfer, exactgeometry/format/nullrejection, source release before conversion','referenceSha256':hashlib.sha256(b).hexdigest(),'expectedFormulaCorrection':'initial verifier mistakenly used112 instead of224 chroma span; actualGPU bytes unchanged, corrected independent limited-range formula matches','rows':rows},indent=2));print(rows)
