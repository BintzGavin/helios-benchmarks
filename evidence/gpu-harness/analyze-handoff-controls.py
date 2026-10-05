"""Independent nominal BT601 limited-range solid-control contract, no fitting.
Solid interior tolerance3 code values accommodates rounding and encoder quantization;
fine chroma bands are characterized separately, not used to choose a reference scaler.
"""
import hashlib, json, math, pathlib, subprocess
root=pathlib.Path(__file__).resolve().parent.parent
out=root/'comparison/fframes-original-handoff-20261004/controls'
width,height,count=256,128,36
def decode(path):
    cmd=['/opt/homebrew/bin/ffmpeg','-v','error','-xerror','-i',str(path),'-map','0:v:0','-threads','1','-c:v','rawvideo','-pix_fmt','yuv420p','-f','rawvideo','-']
    p=subprocess.run(cmd,capture_output=True,timeout=60)
    assert p.returncode==0 and not p.stderr and len(p.stdout)==width*height*3//2*count
    return p.stdout,cmd
candidate,command=decode(out/'video.mp4')
reference,reference_command=decode(out/'reference-same-stream-bt601-proxy.mkv')
colors=[(0,0,0),(255,255,255),(255,0,0),(0,255,0),(0,0,255),(0,255,255),(255,0,255),(255,255,0)]
nominal=[]
for r,g,b in colors:
    nominal.append([round(16+219*(.299*r+.587*g+.114*b)/255),
                    round(128+224*(-.168736*r-.331264*g+.5*b)/255),
                    round(128+224*(.5*r-.418688*g-.081312*b)/255)])
size=width*height*3//2
solid=[];bands=[]
for frame in range(count):
    a=candidate[frame*size:(frame+1)*size];b=reference[frame*size:(frame+1)*size]
    for bar,expected in enumerate(nominal):
        errors=[]
        for plane in range(3):
            pw,ph=(width,height) if plane==0 else (width//2,height//2)
            offset=0 if plane==0 else width*height+(plane-1)*width*height//4
            # Exclude transitions by8 source pixels, fixed before inspecting any values.
            xs=range(bar*32+8,bar*32+24) if plane==0 else range(bar*16+4,bar*16+12)
            ys=range(8,24) if plane==0 else range(4,12)
            values=[a[offset+y*pw+x] for y in ys for x in xs]
            errors.append(max(abs(v-expected[plane]) for v in values))
        solid.append({'frame':frame,'bar':bar,'nominalBT601Limited':expected,'maximumErrorYUV':errors,'passed':max(errors)<=3})
    for band in range(4):
        stats={}
        for plane,label in enumerate('YUV'):
            pw=width if plane==0 else width//2
            offset=0 if plane==0 else width*height+(plane-1)*width*height//4
            start,end=(band*32,(band+1)*32) if plane==0 else (band*16,(band+1)*16)
            sums=0;maximum=0;n=0
            for y in range(start,end):
                for x in range(pw):
                    delta=a[offset+y*pw+x]-b[offset+y*pw+x]
                    sums+=delta*delta;maximum=max(maximum,abs(delta));n+=1
            stats[label]={'maximumDelta':maximum,'mse':sums/n,'psnrDb':None if sums==0 else 10*math.log10(255*255/(sums/n))}
        bands.append({'frame':frame,'sourceIndex':frame+3,'band':band,'metricsVersusFixedProxy':stats})
report={'benchmarkTiming':False,'noReferenceScalerSelected':True,'nominalMatrix':'BT601 limited','solidTolerance':3,
        'solidInteriorsPassed':all(row['passed'] for row in solid),'solids':solid,'bands':bands,
        'decodedCandidateSha256':hashlib.sha256(candidate).hexdigest(),'decodedProxySha256':hashlib.sha256(reference).hexdigest(),
        'decodeCommand':command,'referenceDecodeCommand':reference_command,'opaqueEncoderNV12OracleProved':False}
(out/'independent-color-chroma-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'solidInteriorsPassed':report['solidInteriorsPassed'],'maximumSolidError':max(max(s['maximumErrorYUV']) for s in solid),
                  'bandWorstPSNR':{str(band):{c:min((x['metricsVersusFixedProxy'][c]['psnrDb'] for x in bands if x['band']==band and x['metricsVersusFixedProxy'][c]['psnrDb'] is not None), default=None) for c in 'YUV'} for band in range(4)}}))
