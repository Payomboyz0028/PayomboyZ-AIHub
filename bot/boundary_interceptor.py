# -*- coding: utf-8 -*-
"""
=============================================================================
  🌪️ PAYOMBØYZ HEADLESS DYNAMIC BOUNDARY INTERCEPTOR (GAP #1 & STEP #2)
  Sandboxed Runtime Boundary Hook & Memory Dumper for Protected Scripts
  Handles:
    - Luarmor V4 / Superflow (Intercepts multi-closure module tables at setmetatable)
    - Luraph / IronBrew Loaders (Intercepts self-extracting loadstring payloads)
    - Key Systems / Remote Asset Handshakes (Mocks HttpGet/request to force payload drop)
    - Anti-Tamper Evasion (Suppresses debugger detection, kicks, and integrity traps)
=============================================================================
"""

from __future__ import annotations
import os
import sys
import re
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
PROMETHEUS_DIR = BASE_DIR / "Prometheus-WeAre-Devs-Dumper-main"
LUAU_EXE = PROMETHEUS_DIR / "lua_bin" / "luau" / "luau.exe"
LUA51_EXE = PROMETHEUS_DIR / "lua_bin" / "lua5.1.exe"


HEADLESS_MOCK_HARNESS = r"""-- [PAYOMBØYZ HEADLESS LUAU SANDBOX HARNESS]
local __INTERCEPTED_DUMPS = {}
local __DUMP_COUNTER = 0

-- Mock Roblox Globals & Datatypes
local function makeMockInstance(className)
    local inst = { ClassName = className or "Instance", Name = className or "Instance" }
    inst.Parent = nil
    function inst:FindFirstChild(n) return nil end
    function inst:WaitForChild(n, t) return nil end
    function inst:GetChildren() return {} end
    function inst:GetDescendants() return {} end
    function inst:Destroy() end
    function inst:Clone() return makeMockInstance(className) end
    function inst:Connect(fn) return { Disconnect = function() end } end
    return inst
end

local mockServices = {}
function getMockService(sName)
    if not mockServices[sName] then
        local s = makeMockInstance(sName)
        if sName == "Players" then
            s.LocalPlayer = makeMockInstance("Player")
            s.LocalPlayer.Character = makeMockInstance("Model")
            s.LocalPlayer.Character.Humanoid = makeMockInstance("Humanoid")
            s.LocalPlayer.Character.HumanoidRootPart = makeMockInstance("Part")
            s.LocalPlayer.PlayerGui = makeMockInstance("PlayerGui")
        elseif sName == "HttpService" then
            function s:JSONDecode(str) return {} end
            function s:JSONEncode(t) return "{}" end
            function s:GenerateGUID() return "0000-0000" end
        end
        mockServices[sName] = s
    end
    return mockServices[sName]
end

game = {
    GetService = function(self, s) return getMockService(s) end,
    FindFirstChild = function(self, s) return getMockService(s) end,
    WaitForChild = function(self, s, t) return getMockService(s) end,
    Loaded = { Connect = function() end, Wait = function() end },
    HttpGet = function(self, url)
        -- Log & return stub payload to satisfy handshake
        return "return function(...) return true end"
    end
}
workspace = getMockService("Workspace")
Workspace = workspace

Vector3 = {
    new = function(x, y, z) return { X = x or 0, Y = y or 0, Z = z or 0 } end,
    zero = { X = 0, Y = 0, Z = 0 }
}
CFrame = {
    new = function(...) return { LookVector = {X=0,Y=0,Z=1}, RightVector = {X=1,Y=0,Z=0} } end
}
UDim2 = {
    new = function(a, b, c, d) return { X = {Scale=a, Offset=b}, Y = {Scale=c, Offset=d} } end
}
UDim = {
    new = function(a, b) return { Scale = a, Offset = b } end
}
Color3 = {
    new = function(r, g, b) return { R = r, G = g, B = b } end,
    fromRGB = function(r, g, b) return { R = r, G = g, B = b } end,
    fromHex = function(hex) return { Hex = hex } end
}
Enum = setmetatable({}, {
    __index = function(t, k)
        return setmetatable({}, {
            __index = function(_, subk) return { Name = subk, Value = 1 } end
        })
    end
})
Instance = {
    new = function(className, parent)
        local inst = makeMockInstance(className)
        inst.Parent = parent
        return inst
    end
}

task = {
    wait = function(t) return t or 0 end,
    spawn = function(f, ...)
        if type(f) == "function" then
            pcall(f, ...)
        end
    end,
    delay = function(t, f, ...)
        if type(f) == "function" then
            pcall(f, ...)
        end
    end
}

-- ─────────────────────────────────────────────────────────────────────────────
-- EXECUTOR BOUNDARY HOOKS
-- ─────────────────────────────────────────────────────────────────────────────
local _real_setmetatable = setmetatable
local _real_loadstring = loadstring or load

-- Hook 1: Metatable Interception (Captures Luarmor Multi-Closure Module Tables)
setmetatable = function(tbl, meta)
    if type(tbl) == "table" then
        local closure_count = 0
        for k, v in pairs(tbl) do
            if (type(k) == "number" or type(k) == "string") and type(v) == "function" then
                closure_count = closure_count + 1
            end
        end
        -- Luarmor module table signature (typically 20-150+ functions)
        if closure_count >= 15 then
            __DUMP_COUNTER = __DUMP_COUNTER + 1
            print("[PAYOMBOYZ_INTERCEPT:METATABLE:" .. tostring(closure_count) .. "]")
            local lines = { "return setmetatable({" }
            for k, v in pairs(tbl) do
                local k_repr = type(k) == "number" and ("[" .. tostring(k) .. "]") or ("['" .. tostring(k) .. "']")
                table.insert(lines, "  " .. k_repr .. " = " .. tostring(v) .. ",")
            end
            table.insert(lines, "}, {})")
            local payload = table.concat(lines, "\n")
            __INTERCEPTED_DUMPS[#__INTERCEPTED_DUMPS + 1] = payload
        end
    end
    return _real_setmetatable(tbl, meta)
end

-- Hook 2: Loadstring Interception (Captures Decrypted Inner Scripts in Memory)
loadstring = function(code, chunkname)
    if type(code) == "string" and #code > 60 then
        print("[PAYOMBOYZ_INTERCEPT:LOADSTRING:" .. tostring(#code) .. "]")
        __INTERCEPTED_DUMPS[#__INTERCEPTED_DUMPS + 1] = code
        -- Return dummy function so loader doesn't execute harmful payloads or crash
        return function(...) return true end
    end
    if _real_loadstring then
        return _real_loadstring(code, chunkname)
    end
    return function() end
end
load = loadstring

-- Hook 3: Executor Globals
getgenv = function() return _G end
getrenv = function() return _G end
getrawmetatable = function(t) return debug and debug.getmetatable and debug.getmetatable(t) or {} end
setrawmetatable = function(t, m) return setmetatable(t, m) end
hookmetamethod = function(obj, meth, fn) return fn end
hookfunction = function(old, new) return old end
cloneref = function(inst) return inst end
request = function(options)
    local url = type(options) == "table" and options.Url or ""
    print("[PAYOMBOYZ_INTERCEPT:HTTP:" .. tostring(url) .. "]")
    return { StatusCode = 200, Body = "return true", Success = true }
end
http_request = request

writefile = function(filename, content)
    print("[PAYOMBOYZ_INTERCEPT:WRITEFILE:" .. tostring(filename) .. "]")
    __INTERCEPTED_DUMPS[#__INTERCEPTED_DUMPS + 1] = content
end
readfile = function(filename) return "" end
isfile = function(filename) return true end

-- Target script execution wrapped in pcall
"""


class HeadlessBoundaryInterceptor:
    """
    Spawns sandboxed headless Luau execution to intercept decrypted payloads
    at runtime boundaries (metatable, loadstring, writefile).
    """

    def __init__(self):
        self.runner = LUAU_EXE if LUAU_EXE.exists() else (LUA51_EXE if LUA51_EXE.exists() else None)

    def intercept(self, script_path: str | Path, timeout: int = 8) -> Dict[str, Any]:
        """
        Executes target script inside the sandboxed mock harness.
        Returns: {
            "success": bool,
            "intercepted_payloads": List[str],
            "http_calls": List[str],
            "module_count": int,
            "elapsed": float
        }
        """
        start_time = time.time()
        path = Path(script_path).resolve()
        if not path.is_file():
            return {"success": False, "error": f"File not found: {script_path}", "elapsed": 0}

        if not self.runner:
            return {"success": False, "error": "No Luau runner binary found in lua_bin", "elapsed": 0}

        raw_script = path.read_text(encoding="utf-8", errors="replace")

        # Construct sandbox harness script
        # Add output dump printer at end of harness
        dump_collector = """
pcall(function()
-- TARGET_SCRIPT_INJECTION_POINT
end)

-- Emit intercepted dumps through tagged stdout
for i, d in ipairs(__INTERCEPTED_DUMPS) do
    print("===PAYOM_DUMP_START:" .. tostring(i) .. "===")
    print(d)
    print("===PAYOM_DUMP_END:" .. tostring(i) .. "===")
end
"""
        harness_code = HEADLESS_MOCK_HARNESS.replace(
            "-- Target script execution wrapped in pcall",
            f"pcall(function()\n{raw_script}\nend)"
        ) + "\n" + dump_collector

        with tempfile.NamedTemporaryFile(suffix=".luau", mode="w", encoding="utf-8", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(harness_code)

        try:
            proc = subprocess.run(
                [str(self.runner), str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            elapsed = time.time() - start_time

            # Extract tagged dumps
            dumps: List[str] = []
            dump_blocks = re.findall(r'===PAYOM_DUMP_START:\d+===\s*([\s\S]*?)\s*===PAYOM_DUMP_END:\d+===', stdout)
            for b in dump_blocks:
                cleaned = b.strip()
                if cleaned and len(cleaned) > 50:
                    dumps.append(cleaned)

            # Extract HTTP requests
            http_calls = re.findall(r'\[PAYOMBOYZ_INTERCEPT:HTTP:(.*?)\]', stdout)

            # Check if setmetatable was intercepted
            metatable_matches = re.findall(r'\[PAYOMBOYZ_INTERCEPT:METATABLE:(\d+)\]', stdout)
            module_count = int(metatable_matches[0]) if metatable_matches else 0

            return {
                "success": len(dumps) > 0,
                "intercepted_payloads": dumps,
                "http_calls": http_calls,
                "module_count": module_count,
                "output_lines": sum(len(d.splitlines()) for d in dumps),
                "elapsed": elapsed
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Execution timed out after {timeout}s", "elapsed": timeout}
        except Exception as e:
            return {"success": False, "error": f"Interceptor error: {e}", "elapsed": time.time() - start_time}
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass


# Global singleton instance
BOUNDARY_INTERCEPTOR = HeadlessBoundaryInterceptor()
