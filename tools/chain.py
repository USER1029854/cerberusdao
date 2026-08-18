#!/usr/bin/env python3
"""On-chain reader via Etherscan V2 proxy (eth_call, eth_getCode, etc.)."""
import json, os, sys, urllib.parse, urllib.request, time, re
from Crypto.Hash import keccak
from eth_abi import decode as abi_decode, encode as abi_encode

KEY = os.environ.get("ETHERSCAN_KEY", "")
BASE = "https://api.etherscan.io/v2/api"
CHAIN = int(os.environ.get("CHAINID", "1"))

def json_str(x):
    try: return json.dumps(x)
    except Exception: return str(x)

def _k(s):
    h = keccak.new(digest_bits=256); h.update(s.encode()); return h.digest()

def selector(sig):
    return "0x" + _k(sig).hex()[:8]

def parse_sig(sig):
    # 'name(type1,type2)(rettype1,rettype2)' -> (name, [argtypes], [rettypes])
    m = re.match(r'^(\w+)\(([^)]*)\)(?:\(([^)]*)\))?$', sig.replace(" ", ""))
    name = m.group(1)
    args = [a for a in (m.group(2).split(",") if m.group(2) else []) if a]
    rets = [r for r in (m.group(3).split(",") if m.group(3) else []) if r]
    return name, args, rets

def api(params, retries=8):
    params = dict(params); params["apikey"] = KEY
    url = BASE + "?" + urllib.parse.urlencode(params)
    last=None
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                j = json.loads(r.read().decode())
            blob = json.dumps(j).lower()
            if ("rate limit" in blob) or ("max calls" in blob) or (j.get("message")=="NOTOK" and "rate" in blob):
                time.sleep(1.2*(i+1)); last=j; continue
            return j
        except Exception as e:
            last=e; time.sleep(1.5*(i+1))
    if isinstance(last, dict): return last
    raise last

_last_t=[0.0]
def _throttle():
    import time as _t
    dt=_t.time()-_last_t[0]
    if dt<0.22: _t.sleep(0.22-dt)
    _last_t[0]=_t.time()

def raw_call(to, data, tag="latest", retries=6):
    last=None
    for i in range(retries):
        _throttle()
        r = api({"chainid":CHAIN,"module":"proxy","action":"eth_call","to":to,"data":data,"tag":tag})
        res=r.get("result")
        if isinstance(res,str) and res.startswith("0x"):
            return res
        # error object or rate-limit message
        err = r.get("error") or res or r.get("message")
        emsg = (json_str(err)).lower()
        # definitive execution errors -> do not retry
        if any(k in emsg for k in ["revert","invalid opcode","out of gas","stack","0x"]) and "rate" not in emsg and "limit" not in emsg:
            return None
        last=err
        import time as _t; _t.sleep(1.0*(i+1))
    # return whatever we have; caller handles None
    if isinstance(last,str) and last.startswith("0x"): return last
    return None

def call(to, sig, *args, argtypes=None, rettypes=None):
    name, atypes, rtypes = parse_sig(sig)
    if argtypes is not None: atypes = argtypes
    if rettypes is not None: rtypes = rettypes
    fsig = f"{name}({','.join(atypes)})"
    data = selector(fsig)
    if args:
        data += abi_encode(atypes, list(args)).hex()
    res = raw_call(to, data)
    if res is None or res == "0x":
        return None
    b = bytes.fromhex(res[2:])
    if not rtypes:
        return res
    dec = abi_decode(rtypes, b)
    return dec[0] if len(dec)==1 else dec

def get_code(addr):
    r = api({"chainid":CHAIN,"module":"proxy","action":"eth_getCode","address":addr,"tag":"latest"})
    return r.get("result")

def get_balance(addr):
    # account/balance module is more reliable than proxy/eth_getBalance
    r = api({"chainid":CHAIN,"module":"account","action":"balance","address":addr,"tag":"latest"})
    res = r.get("result")
    try:
        return int(res)
    except Exception:
        try: return int(res,16)
        except Exception: return None

def get_storage(addr, slot):
    slot_hex = slot if isinstance(slot,str) else hex(slot)
    r = api({"chainid":CHAIN,"module":"proxy","action":"eth_getStorageAt","address":addr,"position":slot_hex,"tag":"latest"})
    return r.get("result")

def is_verified(addr):
    r = api({"chainid":CHAIN,"module":"contract","action":"getsourcecode","address":addr})
    try:
        e = r["result"][0]
        src = e.get("SourceCode","")
        return (bool(src), e.get("ContractName",""), e.get("Implementation",""), e.get("Proxy","0"))
    except Exception:
        return (False,"","","0")

def addr_of(x):
    if x is None: return None
    if isinstance(x,str) and x.startswith("0x") and len(x)==42: return x
    return x

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "call":
        to = sys.argv[2]; sig = sys.argv[3]; extra = sys.argv[4:]
        print(call(to, sig, *extra))
    elif cmd == "code":
        print(get_code(sys.argv[2]))
    elif cmd == "codelen":
        c = get_code(sys.argv[2]); print(len((c or "0x")[2:])//2, "bytes")
    elif cmd == "verified":
        print(is_verified(sys.argv[2]))
    elif cmd == "storage":
        print(get_storage(sys.argv[2], sys.argv[3]))
    elif cmd == "bal":
        print(get_balance(sys.argv[2]))
