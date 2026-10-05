#!/usr/bin/env python3
"""Read-only host inventory plus tiny real encode probes; no software fallback qualifies."""
import argparse, datetime, glob, json, os, pathlib, platform, re, shutil, subprocess, tempfile

SOFTWARE = re.compile(r"swiftshader|llvmpipe|lavapipe|software raster|microsoft basic render", re.I)

def capture(argv, timeout=25):
    try:
        p = subprocess.run(argv, text=True, capture_output=True, timeout=timeout)
        return {"argv": argv, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"argv": argv, "returncode": None, "error": str(e)}

def inventory(ffmpeg):
    system = platform.system()
    records = {"uname": capture(["uname", "-a"]), "ffmpeg": capture([ffmpeg, "-version"]),
               "encoders": capture([ffmpeg, "-hide_banner", "-encoders"])}
    devices = glob.glob("/dev/dri/renderD*") + glob.glob("/dev/nvidia[0-9]*")
    real_gpu = False
    if system == "Darwin":
        records["displays"] = capture(["system_profiler", "SPDisplaysDataType", "-json"])
        try:
            displays = json.loads(records["displays"]["stdout"])["SPDisplaysDataType"]
            real_gpu = any(d.get("sppci_model") and not SOFTWARE.search(d["sppci_model"]) for d in displays)
        except (ValueError, KeyError, TypeError):
            pass
    else:
        if shutil.which("nvidia-smi"):
            records["nvidia"] = capture(["nvidia-smi", "--query-gpu=name,driver_version,uuid", "--format=csv,noheader"])
            real_gpu = bool(devices and records["nvidia"]["returncode"] == 0 and records["nvidia"].get("stdout", "").strip())
        if shutil.which("vulkaninfo"):
            records["vulkan"] = capture(["vulkaninfo", "--summary"])
            names = re.findall(r"deviceName\s*=\s*(.+)", records["vulkan"].get("stdout", ""))
            real_gpu |= bool(devices and any(not SOFTWARE.search(n) for n in names))
    return system, devices, bool(real_gpu), records

def run(ffmpeg="ffmpeg"):
    system, devices, real_gpu, records = inventory(ffmpeg)
    encoder_listing = records["encoders"].get("stdout", "")
    codecs = ["h264_videotoolbox", "hevc_videotoolbox"] if system == "Darwin" else ["h264_nvenc", "hevc_nvenc", "h264_vulkan", "hevc_vulkan"]
    probes = []
    with tempfile.TemporaryDirectory(prefix="helios-gpu-probe-") as folder:
        for codec in codecs:
            if codec not in encoder_listing:
                probes.append({"codec": codec, "status": "unavailable_in_ffmpeg_build"})
                continue
            destination = str(pathlib.Path(folder) / (codec + ".mp4"))
            argv = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
            if codec.endswith("vulkan"):
                argv += ["-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk"]
            argv += ["-f", "lavfi", "-i", "testsrc2=size=128x128:rate=30", "-frames:v", "2"]
            if codec.endswith("vulkan"):
                argv += ["-vf", "format=nv12,hwupload"]
            argv += ["-c:v", codec]
            if codec.endswith("videotoolbox"):
                argv += ["-allow_sw", "0"]
            argv += [destination]
            result = capture(argv)
            successful = result["returncode"] == 0 and pathlib.Path(destination).is_file() and pathlib.Path(destination).stat().st_size > 0
            probes.append({"codec": codec, "encode_succeeded": successful,
                           "hardware_qualified": bool(successful and real_gpu), "process": result})
    return {"schema": 1, "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "system": system, "devices": devices, "physical_gpu_observed": real_gpu,
            "inventory": records, "encoder_probes": probes,
            "hardware_encoder_available": any(p.get("hardware_qualified") for p in probes),
            "browser_gpu_attested": False,
            "notes": ["Encoder registration is not hardware availability.",
                      "Browser renderer GPU use requires separate browser/scene attestation.",
                      "An encode probe validates a backend, not benchmark speed, fidelity, or another engine's use of that backend.",
                      "No software rasterizer or software encoder fallback counts as a GPU result."]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--output", default="evidence/preflight.json")
    args = parser.parse_args()
    result = run(args.ffmpeg)
    target = pathlib.Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"output": str(target), "physical_gpu_observed": result["physical_gpu_observed"], "hardware_encoder_available": result["hardware_encoder_available"]}))
    return 0 if result["physical_gpu_observed"] and result["hardware_encoder_available"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
