import hashlib, json, pathlib, zipfile
from fractions import Fraction
root=pathlib.Path(__file__).resolve().parent.parent
evidence=root/'comparison/fframes-original-handoff-20261004'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
preserved=[]
old=json.loads((root/'deliverables/FFRAMES-COLOR-CONTRACT-INVESTIGATION-20261004.json').read_text())
for row in old['readSet']:
    p=pathlib.Path(row['path']);assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
    preserved.append({**row,'unchanged':True})
pins=json.loads((evidence/'BUILD-PINS.json').read_text())
for item in pins['source']:
    assert sha(pathlib.Path(pins['sourceDirectory'])/item['path'])==item['sha256']
for item in pins['helpers']:assert sha(pathlib.Path(item['path']))==item['sha256']
with zipfile.ZipFile(evidence/'source.zip') as z:assert z.testzip() is None
lanes=[]
for name in ['controls','circles300']:
    d=evidence/name;q=json.loads((d/'quality.json').read_text());binding=json.loads((d/'capture/independent-handoff-audit.json').read_text())
    reference=json.loads((d/'reference-binding.json').read_text());frames=json.loads((d/'decoded-frames.json').read_text())
    stream=frames['streams'][0];n=q['expected']['frames'];timebase=Fraction(stream['time_base'])
    assert len(frames['frames'])==n
    indexed=[]
    for index,f in enumerate(frames['frames']):
        assert Fraction(f['pts'])*timebase==Fraction(index,30)
        assert Fraction(f['duration'])*timebase==Fraction(1,30)
        assert f['color_range']=='tv' and f['color_space']=='smpte170m' and f['chroma_location']=='left'
        indexed.append({'index':index,'pts':f['pts'],'ptsSecondsExact':str(Fraction(f['pts'])*timebase),
                        'duration':f['duration'],'colorRange':f['color_range'],'colorSpace':f['color_space'],
                        'chromaLocation':f['chroma_location'],'keyFrame':f['key_frame']})
    keys=[i for i,f in enumerate(frames['frames']) if f['key_frame']]
    spacing=[b-a for a,b in zip(keys,keys[1:])]
    assert keys[0]==0 and all(s<=30 for s in spacing) and n-keys[-1]<=30
    gate={'passed':True,'frames':n,'fps':'30/1','decodedPTSAndDurationExact':True,'expectedColorMetadata':'BT601 limited, left chroma',
          'transferAndPrimariesUnspecified':stream.get('color_transfer') is None and stream.get('color_primaries') is None,
          'keyFrameIndexes':keys,'maximumGopSpacing':max(spacing,default=0),'framesIndexed':indexed,
          'candidateSha256':sha(d/'video.mp4'),'decodedFrameReceiptSha256':sha(d/'decoded-frames.json')}
    (d/'cadence-color-gop-audit.json').write_text(json.dumps(gate,indent=2)+'\n')
    assert q['candidate']['sha256']==sha(d/'video.mp4') and q['reference']['sha256']==sha(d/'reference-same-stream-bt601-proxy.mkv')
    assert binding['passed'] and len(binding['frames'])==n and reference['allProxyReferenceFramesExactlyBound']
    metrics=q['quality'];assert metrics['ssim']['frame_count']==metrics['psnr']['frame_count']==n
    assert metrics['ssim']['thresholds']=={'Y':.995} and metrics['psnr']['thresholds']=={'psnr_y':40.,'psnr_u':35.,'psnr_v':35.}
    minimum={**metrics['ssim']['minimum'],**metrics['psnr']['minimum']}
    failures={k:sum(f[k]<v for f in metrics['psnr']['frames']) for k,v in metrics['psnr']['thresholds'].items()}
    lanes.append({'lane':name,'frames':n,'sameStreamHandoffAuditPassed':True,'losslessProxyDirectBindingPassed':True,
        'cadenceColorMetadataGopPassed':True,'structureDecodePassed':q['structure_decode_passed'],
        'qualityPassed':q['quality_passed'],'minimum':minimum,'belowFloorFrameCounts':failures,
        'candidateSha256':sha(d/'video.mp4'),'qualitySha256':sha(d/'quality.json'),
        'captureAuditSha256':sha(d/'capture/independent-handoff-audit.json'),
        'referenceBindingSha256':sha(d/'reference-binding.json'),'benchmarkTiming':False})
controls=json.loads((evidence/'controls/independent-color-chroma-analysis.json').read_text())
report={'status':'bounded_same_stream_original_hardware_capture_complete; original_quality_gate_failed',
        'broaderObjectiveComplete':False,'owner':'comparison harness','timingWindowOpen':False,'newBenchmarkTimingAttempts':0,
        'fullyEnabledOriginalLaneQualified':False,'productionWinnerClaimAllowed':False,'publishedM5ClaimBeaten':False,
        'sourceLibraryId':'libfile_19c903c1d7508191ac4881f0e96e4229','historicalCheckpointLibraryId':'libfile_cd84375e4648819195364136245484c6',
        'newLibraryDeliverableIds':[],'libraryBlocker':'required Library helper prepare_uploads unavailable; no alternate container used',
        'protocolSha256':sha(evidence/'DIAGNOSTIC-PROTOCOL.json'),'buildPinsSha256':sha(evidence/'BUILD-PINS.json'),
        'sourceArchiveSha256':sha(evidence/'source.zip'),'sourceArchiveCRCpassed':True,
        'helpers':pins['helpers'],'lanes':lanes,
        'controls':{'all36RawBGRAFramesExactlyMatchIndependentOracle':True,'nominalBT601LimitedSolidInteriorsPassed':controls['solidInteriorsPassed'],
                    'maximumSolidInteriorCodeValueError':max(max(s['maximumErrorYUV']) for s in controls['solids']),
                    'fineChromaPatternsDisagreeWithFixedProxy':True,'analysisSha256':sha(evidence/'controls/independent-color-chroma-analysis.json')},
        'tests':{'rustCaptureUnitTests':3,'independentAuditTests':11,'auditMutantsDetected':10,'actualInitRefusals':2,
                 'releaseBuildPassed':True,'clippyCompletedWithWarnings':True,'strictWarningsFreeLintClaim':False},
        'unchangedPriorReadSet':preserved,
        'conclusions':['Exact candidate source stream removes independent-raster reference ambiguity for this diagnostic.',
            'Original 4K chroma floors still fail against unchanged BT601 FFmpeg proxy; 296 U and 300 V frames fail.',
            'Exact source and nominal solid controls place the remaining difference downstream of rasterization: reference subsampling versus opaque VideoToolbox conversion and encoding.',
            'This does not distinguish conversion-kernel choices from compression distortion and does not prove the original product encoder is incorrect.',
            'Same-stream BGRA capture is not an actual VideoToolbox pre-compression NV12 oracle.',
            'All capture clocks/readbacks/resource use are excluded; no balanced timing window opened.'],
        'actualEncoderNV12OracleProved':False,'opaqueEncoderOwnershipKnown':False,'zeroCopyProved':False,
        'remainingGate':{'originalLane':'Independently specified/validated original encoder conversion and chroma oracle remains unavailable; no public pre-compression VideoToolbox NV12 exposure identified.',
            'modifiedPipelineOption':'Separately freeze explicit GPU NV12 conversion with production contexts/concurrency and proper lifetime/fences; qualify all300 before timing. Must be labeled modified pipeline, not original product.',
            'noFurtherOptimizationSelected':True,'full4KHEVCVulkanPerformanceQualificationPending':True,
            'vulkanPublication':'Native-thread auto-review push destination approval still pending; no push or workaround here.'},
        'harnessPins':[]}
for name in ['run-fframes-handoff.py','audit-fframes-handoff.py','qualify-fframes-handoff.py','test_fframes_handoff.py','analyze-handoff-controls.py','finalize-fframes-handoff.py']:
    p=root/'checkpoint'/name;report['harnessPins'].append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
(evidence/'FINAL-REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
(root/'checkpoint/FFRAMES-HANDOFF-CAPTURE-20261004.json').write_text(json.dumps({'status':report['status'],'report':str(evidence/'FINAL-REPORT.json'),'reportSha256':sha(evidence/'FINAL-REPORT.json'),'timingWindowOpen':False,'broaderObjectiveComplete':False},indent=2)+'\n')
print(json.dumps({'status':report['status'],'lanes':lanes,'preservedReadSet':len(preserved),'timingWindowOpen':False}))
