# -*- coding: utf-8 -*-
"""
Polsec / Fulcrum Automated Loader Spy & Deobfuscator
Handles:
1. Dynamic Headless Luau Boundary Interception
2. Automated local Zstandard enclib delivery
3. Live fetcher relay (X-Polsec-Key, nonce, user-agent)
4. JSON extraction of Luraph V15 payload ('S' + 'consts')
5. Direct pipeline routing to Luraph CFG Dominator Devirtualizer
"""
import os
import sys
import json
import time
import urllib.request
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
PROMETHEUS_DIR = BASE_DIR / "Prometheus-WeAre-Devs-Dumper-main"
LUAU_BIN = PROMETHEUS_DIR / "lua_bin" / "luau" / "luau.exe"
ENCLIB_PATH = BASE_DIR / "scratch" / "enclib.lua"

if str(PROMETHEUS_DIR) not in sys.path:
    sys.path.insert(0, str(PROMETHEUS_DIR))

import luraph_engine


def fetch_url(url: str, headers: Optional[Dict[str, str]] = None) -> bytes:
    hdrs = {'User-Agent': 'Roblox/WinInet'}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def ensure_enclib() -> str:
    if ENCLIB_PATH.exists():
        return ENCLIB_PATH.read_text(encoding="utf-8")
    data = fetch_url("https://api.polsec.net/enclib")
    ENCLIB_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENCLIB_PATH.write_bytes(data)
    return data.decode("utf-8")


def spy_and_unpack_polsec(loader_code: str, custom_key: str = "POLSEC_TEST_KEY_DJ_1337") -> Dict[str, Any]:
    """
    Dynamically spies on Polsec loader, intercepts enclib, relays live fetcher request,
    and captures the decrypted Luraph payload.
    """
    start_time = time.time()
    enclib_content = ensure_enclib()
    
    # Check if target is a raw URL
    if loader_code.strip().startswith("http"):
        loader_code = fetch_url(loader_code.strip()).decode("utf-8", errors="replace")

    # Step 1: Pre-fetch payload by simulating or probing the endpoint if found in loader
    # Polsec loader has URL path like /fetcher/<id1>/<id2>/
    # But running Luau harness can discover it dynamically!
    
    # Build Luau Spy Harness
    scratch_dir = BASE_DIR / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    
    # First pass: find the fetcher URL by running loader with dummy response
    spy_harness_pass1 = """
local ENCLIB_BODY = [=====[""" + enclib_content + """]=====]

local logs = {}
local function log(cat, msg)
    print(string.format("[SPY][%s] %s", cat, tostring(msg)))
end

-- Deep Mock Proxy generator
local function create_mock(name)
    local t = {}
    local mt = {
        __index = function(self, k)
            if k == "IsLoaded" then
                return function(...) return true end
            elseif k == "HttpGet" or k == "HttpGetAsync" then
                return function(self, url, ...)
                    local u = tostring(url)
                    if string.find(u, "enclib") then
                        return ENCLIB_BODY
                    end
                    return "{}"
                end
            elseif k == "GetService" then
                return function(self, sname)
                    return create_mock("Service:" .. tostring(sname))
                end
            elseif k == "FindFirstChild" or k == "WaitForChild" then
                return function(self, cname, ...)
                    return create_mock(name .. "." .. tostring(cname))
                end
            elseif k == "Connect" or k == "connect" then
                return function(self, cb) return { Disconnect = function() end } end
            elseif k == "Wait" or k == "wait" then
                return function(self) return 0 end
            elseif k == "PlaceId" then return 123456789
            elseif k == "GameId" then return 987654321
            elseif k == "JobId" then return "mock-job-id"
            end
            return create_mock(name .. "." .. tostring(k))
        end,
        __call = function(self, ...) return create_mock(name .. "()") end,
        __tostring = function(self) return "MockInstance(" .. name .. ")" end
    }
    return setmetatable(t, mt)
end

getfenv().game = create_mock("game")
getfenv().workspace = create_mock("workspace")
getfenv().Workspace = getfenv().workspace
getfenv().script = create_mock("script")
getfenv().task = { wait = function() return 0 end, spawn = function(f, ...) return f(...) end }
getfenv().wait = getfenv().task.wait

local function mock_request(options)
    local u = tostring(options.Url or options.url)
    local hdrs = options.Headers or options.headers or {}
    local k = tostring(hdrs["X-Polsec-Key"] or hdrs["x-polsec-key"] or "")
    log("INTERCEPTED_URL", u)
    log("INTERCEPTED_KEY", k)
    if string.find(u, "enclib") then
        return { StatusCode = 200, Success = true, Body = ENCLIB_BODY, Headers = {} }
    end
    return { StatusCode = 200, Success = true, Body = "{}", Headers = {} }
end

getfenv().request = mock_request
getfenv().http_request = mock_request
getfenv().syn = { request = mock_request }
getfenv().http = { request = mock_request }
getfenv().identifyexecutor = function() return "Fluxus", "v2.1" end
getfenv().getexecutorname = function() return "Fluxus" end
getfenv().checkcaller = function() return true end
getfenv().cloneref = function(x) return x end
getfenv().getgenv = function() return getfenv() end
getfenv().getrenv = function() return getfenv() end
getfenv()._G = getfenv()
getfenv().shared = getfenv()
getfenv().script_key = \"""" + custom_key + """\"
"""
    
    probe_script = scratch_dir / "polsec_probe.luau"
    probe_script.write_text(spy_harness_pass1 + "\n" + loader_code, encoding="utf-8")
    
    proc1 = subprocess.run([str(LUAU_BIN), str(probe_script)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
    
    target_fetch_url = None
    target_key = custom_key
    for line in proc1.stdout.splitlines():
        if "[SPY][INTERCEPTED_URL]" in line:
            u = line.split("[SPY][INTERCEPTED_URL]", 1)[1].strip()
            if "fetcher" in u:
                target_fetch_url = u
        if "[SPY][INTERCEPTED_KEY]" in line:
            k = line.split("[SPY][INTERCEPTED_KEY]", 1)[1].strip()
            if k:
                target_key = k

    if not target_fetch_url:
        return {
            "success": False,
            "error": "Failed to intercept Polsec fetcher endpoint URL.",
            "elapsed": time.time() - start_time
        }
        
    print(f"[*] Intercepted Polsec endpoint: {target_fetch_url}")
    print(f"[*] Using key: {target_key}")
    
    # Step 2: Fetch real binary payload from Polsec server
    raw_payload_bytes = fetch_url(target_fetch_url, headers={"X-Polsec-Key": target_key})
    print(f"[*] Fetched live encrypted binary payload: {len(raw_payload_bytes):,} bytes")
    
    # Step 3: Second pass - inject real payload body into Luau loader and catch JSONDecode
    chunk_size = 4000
    chunks = []
    for i in range(0, len(raw_payload_bytes), chunk_size):
        chunk = raw_payload_bytes[i:i+chunk_size]
        escaped = "".join(f"\\{b:03d}" for b in chunk)
        chunks.append(f'"{escaped}"')
    payload_table = "{\n" + ",\n".join(chunks) + "\n}"
    
    spy_harness_pass2 = """
local ENCLIB_BODY = [=====[""" + enclib_content + """]=====]
local PAYLOAD_BODY = table.concat(""" + payload_table + """)

-- Deep Mock Proxy generator
local function create_mock(name)
    local t = {}
    local mt = {
        __index = function(self, k)
            if k == "IsLoaded" then
                return function(...) return true end
            elseif k == "HttpGet" or k == "HttpGetAsync" then
                return function(self, url, ...)
                    local u = tostring(url)
                    if string.find(u, "enclib") then
                        return ENCLIB_BODY
                    end
                    return "{}"
                end
            elseif k == "GetService" then
                return function(self, sname)
                    return create_mock("Service:" .. tostring(sname))
                end
            elseif k == "FindFirstChild" or k == "WaitForChild" then
                return function(self, cname, ...)
                    return create_mock(name .. "." .. tostring(cname))
                end
            elseif k == "Connect" or k == "connect" then
                return function(self, cb) return { Disconnect = function() end } end
            elseif k == "Wait" or k == "wait" then
                return function(self) return 0 end
            elseif k == "JSONDecode" then
                return function(self, json_str)
                    print("[SPY_JSON_START]")
                    print(json_str)
                    print("[SPY_JSON_END]")
                    return {}
                end
            elseif k == "PlaceId" then return 123456789
            elseif k == "GameId" then return 987654321
            elseif k == "JobId" then return "mock-job-id"
            end
            return create_mock(name .. "." .. tostring(k))
        end,
        __call = function(self, ...) return create_mock(name .. "()") end,
        __tostring = function(self) return "MockInstance(" .. name .. ")" end
    }
    return setmetatable(t, mt)
end

getfenv().game = create_mock("game")
getfenv().workspace = create_mock("workspace")
getfenv().Workspace = getfenv().workspace
getfenv().script = create_mock("script")
getfenv().task = { wait = function() return 0 end, spawn = function(f, ...) return f(...) end }
getfenv().wait = getfenv().task.wait

local function mock_request(options)
    local u = tostring(options.Url or options.url)
    if string.find(u, "enclib") then
        return { StatusCode = 200, Success = true, Body = ENCLIB_BODY, Headers = {} }
    end
    if string.find(u, "fetcher") then
        return { StatusCode = 200, Success = true, Body = PAYLOAD_BODY, Headers = {} }
    end
    return { StatusCode = 200, Success = true, Body = "{}", Headers = {} }
end

getfenv().request = mock_request
getfenv().http_request = mock_request
getfenv().syn = { request = mock_request }
getfenv().http = { request = mock_request }
getfenv().identifyexecutor = function() return "Fluxus", "v2.1" end
getfenv().getexecutorname = function() return "Fluxus" end
getfenv().checkcaller = function() return true end
getfenv().cloneref = function(x) return x end
getfenv().getgenv = function() return getfenv() end
getfenv().getrenv = function() return getfenv() end
getfenv()._G = getfenv()
getfenv().shared = getfenv()
getfenv().script_key = \"""" + target_key + """\"
"""
    run_script = scratch_dir / "polsec_full_run.luau"
    run_script.write_text(spy_harness_pass2 + "\n" + loader_code, encoding="utf-8")
    
    proc2 = subprocess.run([str(LUAU_BIN), str(run_script)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    
    stdout = proc2.stdout
    if "[SPY_JSON_START]" not in stdout or "[SPY_JSON_END]" not in stdout:
        return {
            "success": False,
            "error": "Failed to capture decrypted JSON from HttpService:JSONDecode.",
            "elapsed": time.time() - start_time
        }
        
    json_block = stdout.split("[SPY_JSON_START]")[1].split("[SPY_JSON_END]")[0].strip()
    data = json.loads(json_block)
    
    consts = data.get("consts", [])
    s = data.get("S", "")
    
    consts_lua = "local consts = {" + ", ".join(str(c) for c in consts) + "}\n"
    standalone_luraph = consts_lua + s
    
    luraph_file = scratch_dir / f"polsec_unpacked_luraph_{int(time.time())}.lua"
    luraph_file.write_text(standalone_luraph, encoding="utf-8")
    print(f"[*] Unpacked standalone Luraph V15 payload: {len(standalone_luraph):,} bytes")
    
    # Step 4: Run through Luraph V15 Node CFG Dominator Devirtualizer
    print("[*] Invoking Luraph V15 Node CFG Dominator Devirtualizer...")
    v15_res = luraph_engine.deobfuscate_luraph_v15_engine(str(luraph_file), timeout=90)
    
    elapsed = time.time() - start_time
    if v15_res and v15_res.get("success"):
        clean_code = v15_res.get("deobfuscated_code", "")
        return {
            "success": True,
            "engine": "Polsec Headless Boundary Spy + Luraph V15 CFG Dominator",
            "deobfuscated_code": clean_code,
            "lines": len(clean_code.splitlines()),
            "cache_id": data.get("cacheId"),
            "script_hash": data.get("scriptHash"),
            "elapsed": elapsed
        }
    else:
        return {
            "success": False,
            "error": v15_res.get("error", "Luraph Devirtualization failed"),
            "unpacked_luraph_source": standalone_luraph,
            "elapsed": elapsed
        }


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    test_url = "https://api.polsec.net/loader/96665bec3031741f/4e69080c13331f77"
    print(f"Testing Polsec Unpacker on {test_url}...")
    res = spy_and_unpack_polsec(test_url)
    print("Success:", res.get("success"))
    print("Lines:", res.get("lines"))
    print("Elapsed:", f"{res.get('elapsed', 0):.2f}s")
    if res.get("success"):
        print("\nDEOBFUSCATED CODE:\n" + res.get("deobfuscated_code"))
    else:
        print("Error:", res.get("error"))
