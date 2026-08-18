#!/usr/bin/env python3
"""Etherscan V2 contract fetcher/parser for audit repo assembly."""
import json, os, sys, urllib.parse, urllib.request, time

KEY = os.environ.get("ETHERSCAN_KEY", "")
BASE = "https://api.etherscan.io/v2/api"

def api(params, retries=4):
    params = dict(params); params["apikey"] = KEY
    url = BASE + "?" + urllib.parse.urlencode(params)
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e; time.sleep(2*(i+1))
    raise last

def getsource(address, chainid=1):
    return api({"chainid": chainid, "module": "contract", "action": "getsourcecode", "address": address})

def parse_sources(result_entry):
    """Return dict {relpath: content} from a getsourcecode result[0]."""
    src = result_entry.get("SourceCode", "")
    name = result_entry.get("ContractName", "Contract")
    files = {}
    if src.startswith("{{") and src.endswith("}}"):
        obj = json.loads(src[1:-1])
        for path, meta in obj.get("sources", {}).items():
            files[path] = meta.get("content", "")
    elif src.startswith("{") and src.endswith("}"):
        try:
            obj = json.loads(src)
            # could be {sources:{...}} or {path:{content:...}}
            if "sources" in obj and isinstance(obj["sources"], dict):
                for path, meta in obj["sources"].items():
                    files[path] = meta.get("content", "")
            else:
                for path, meta in obj.items():
                    if isinstance(meta, dict) and "content" in meta:
                        files[path] = meta["content"]
                    else:
                        files[f"{name}.sol"] = src
        except json.JSONDecodeError:
            files[f"{name}.sol"] = src
    else:
        files[f"{name}.sol"] = src
    return files

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "meta":
        addr = sys.argv[2]; chain = int(sys.argv[3]) if len(sys.argv)>3 else 1
        r = getsource(addr, chain)
        e = r["result"][0]
        print(json.dumps({k: e.get(k) for k in ["ContractName","CompilerVersion","Proxy","Implementation","OptimizationUsed","Runs","EVMVersion","ConstructorArguments","LicenseType"]}, indent=2))
    elif cmd == "dump":
        # dump sources to a dir: dump <addr> <outdir> [chain]
        addr = sys.argv[2]; outdir = sys.argv[3]; chain = int(sys.argv[4]) if len(sys.argv)>4 else 1
        r = getsource(addr, chain)
        e = r["result"][0]
        files = parse_sources(e)
        os.makedirs(outdir, exist_ok=True)
        for path, content in files.items():
            safe = path.replace("..","_")
            full = os.path.join(outdir, safe)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w") as f: f.write(content)
        # write meta + abi + constructor args
        with open(os.path.join(outdir, "_metadata.json"), "w") as f:
            json.dump({k: e.get(k) for k in ["ContractName","CompilerVersion","Proxy","Implementation","OptimizationUsed","Runs","EVMVersion","ConstructorArguments","LicenseType","SwarmSource"]}, f, indent=2)
        with open(os.path.join(outdir, "_abi.json"), "w") as f:
            f.write(e.get("ABI",""))
        print(f"Wrote {len(files)} files to {outdir}")
        for p in files: print("  ", p)
