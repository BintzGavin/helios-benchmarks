"""Preserve every original coded NAL payload; replace only the declared SPS signaling.
FFmpeg's direct h264_metadata route shortened VCL tails in the excluded control attempt.
Use its one-frame parameter template, then mux the ORIGINAL sample payloads explicitly.
"""
import hashlib,json,pathlib,subprocess,time
ffmpeg='/opt/homebrew/bin/ffmpeg';ffprobe='/opt/homebrew/bin/ffprobe'
def probe(path,packets=False):
    cmd=[ffprobe,'-v','error','-select_streams','v:0']
    cmd+=['-show_packets','-show_entries','packet=pos,size,pts,duration'] if packets else ['-show_streams','-show_data','-show_entries','stream=extradata,nal_length_size,is_avc']
    cmd+=['-of','json',str(path)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=600);assert p.returncode==0 and not p.stderr
    return json.loads(p.stdout),cmd
def parameters(path):
    doc,cmd=probe(path);s=doc['streams'][0];assert s['nal_length_size']=='4' and s['is_avc']=='true'
    data=bytearray()
    for line in s['extradata'].splitlines():
        if ':' in line:data.extend(bytes.fromhex(line.split(':',1)[1].strip().split('  ',1)[0]))
    assert data[0]==1 and data[4]&3==3;offset=6;sps=[];pps=[]
    for _ in range(data[5]&31):
        size=int.from_bytes(data[offset:offset+2],'big');offset+=2;sps.append(bytes(data[offset:offset+size]));offset+=size
    count=data[offset];offset+=1
    for _ in range(count):
        size=int.from_bytes(data[offset:offset+2],'big');offset+=2;pps.append(bytes(data[offset:offset+size]));offset+=size
    assert len(sps)==1 and all(nal[0]&31==7 for nal in sps) and all(nal[0]&31==8 for nal in pps)
    return sps,pps,cmd
def vcl(path):
    doc,cmd=probe(path,True);payloads=[]
    with path.open('rb') as f:
        for packet in doc['packets']:
            f.seek(int(packet['pos']));data=f.read(int(packet['size']));offset=0
            while offset<len(data):
                assert offset+4<=len(data);size=int.from_bytes(data[offset:offset+4],'big');offset+=4
                assert 0<size<=len(data)-offset;nal=data[offset:offset+size];offset+=size
                if 1<=nal[0]&31<=5:payloads.append({'nalType':nal[0]&31,'bytes':len(nal),'sha256':hashlib.sha256(nal).hexdigest()})
            assert offset==len(data)
    assert payloads;return payloads,cmd
def conform(original,destination):
    template=destination.parent/'center-parameter-template.mp4';assert not template.exists() and not destination.exists()
    argv=[ffmpeg,'-v','error','-xerror','-i',str(original),'-map','0:v:0','-an','-frames:v','1','-c:v','copy',
          '-bsf:v','h264_metadata=chroma_sample_loc_type=1',str(template)]
    t=time.time();p=subprocess.run(argv,capture_output=True,text=True,timeout=600)
    (destination.parent/'parameter-template.stderr.log').write_text(p.stderr);assert p.returncode==0 and not p.stderr
    old_sps,old_pps,old_params_cmd=parameters(original);new_sps,new_pps,new_params_cmd=parameters(template)
    assert old_pps==new_pps
    packets,packets_cmd=probe(original,True)
    mux=[ffmpeg,'-v','error','-xerror','-f','h264','-r','30','-i','pipe:0','-map','0:v:0','-an','-c:v','copy',
         '-movflags','+faststart',str(destination)]
    with (destination.parent/'conformance-mux.stderr.log').open('w') as err:
        child=subprocess.Popen(mux,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=err)
        try:
            prefix=b'\0\0\0\1'
            for nal in new_sps+old_pps:child.stdin.write(prefix+nal)
            with original.open('rb') as f:
                for packet in packets['packets']:
                    f.seek(int(packet['pos']));data=f.read(int(packet['size']));offset=0
                    while offset<len(data):
                        assert offset+4<=len(data);size=int.from_bytes(data[offset:offset+4],'big');offset+=4
                        assert 0<size<=len(data)-offset;nal=data[offset:offset+size];offset+=size
                        if nal[0]&31==7:
                            assert nal in old_sps,'unhandled dynamic SPS';nal=new_sps[old_sps.index(nal)]
                        child.stdin.write(prefix+nal)
                    assert offset==len(data)
            child.stdin.close();rc=child.wait(timeout=600)
        except BaseException:child.kill();child.wait();raise
    assert rc==0
    before,bc=vcl(original);after,ac=vcl(destination);assert before==after,'every coded VCL payload must remain byte exact'
    return {'templateCommand':argv,'templateReturncode':p.returncode,'muxCommand':mux,'muxReturncode':rc,
            'sourceParameterCommand':old_params_cmd,'templateParameterCommand':new_params_cmd,'sourcePacketCommand':packets_cmd,
            'originalPacketCommand':bc,'normalizedPacketCommand':ac,'allVCLPayloadsExactlyEqual':True,'vclPayloads':before,
            'oldSPShex':[s.hex() for s in old_sps],'newSPShex':[s.hex() for s in new_sps],
            'PPSbytesUnchanged':True,'mandatoryExportConformanceStage':True,'benchmarkTiming':False,'startedUnix':t,'finishedUnix':time.time()}
