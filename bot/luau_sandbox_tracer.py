#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ DYNAMIC LUAU HOOK SANDBOX & OBFUSCATION BREAKER V1.0
====================================================================
Headless Metamethod Trap & Decryption Sandbox:
  - Spawns local luau.exe binary in an isolated runtime
  - Mocks the entire Roblox C-API, Services, Metamethods, and Environment
  - Forces obfuscated scripts (Luraph, MoonSec, IronBrew, PSU, Xen)
    to self-decrypt their strings in memory when invoking Roblox remotes
  - Intercepts all FireServer, InvokeServer, and Workspace paths in <0.2s
====================================================================
"""

import os
import re
import sys
import tempfile
import subprocess
from typing import Dict, Any, List, Set, Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LUAU_BIN = BASE_DIR / "Prometheus-WeAre-Devs-Dumper-main" / "lua_bin" / "luau" / "luau.exe"

SANDBOX_PREAMBLE = """
-- [[ PAYOMBØYZ HEADLESS LUAU METAMETHOD TRAP ]]
local function serialize(val)
    local t = type(val)
    if t == "string" then return string.format("%q", val)
    elseif t == "number" or t == "boolean" then return tostring(val)
    elseif t == "table" then return "{...}"
    else return "<" .. t .. ">" end
end

local function formatArgs(...)
    local parts = {}
    for i = 1, select("#", ...) do
        table.insert(parts, serialize(select(i, ...)))
    end
    return table.concat(parts, ", ")
end

local function makeProxy(path)
    local proxy = {}
    local meta = {
        __index = function(self, key)
            local k_str = tostring(key)
            if k_str == "FireServer" or k_str == "InvokeServer" or k_str == "Fire" or k_str == "Invoke" then
                return function(inst, ...)
                    print("[TRAP_REMOTE] " .. path .. " -> " .. k_str .. "(" .. formatArgs(...) .. ")")
                end
            end
            if k_str == "WaitForChild" or k_str == "FindFirstChild" or k_str == "GetService" then
                return function(inst, name)
                    return makeProxy(path .. "." .. tostring(name))
                end
            end
            if k_str == "Connect" then
                return function(inst, fn) return { Disconnect = function() end } end
            end
            return makeProxy(path .. "." .. k_str)
        end,
        __namecall = function(self, ...)
            print("[TRAP_NAMECALL] " .. path .. "(" .. formatArgs(...) .. ")")
            return makeProxy(path .. ".Result")
        end,
        __tostring = function() return path end
    }
    return setmetatable(proxy, meta)
end

-- Global Roblox environment mocks
getfenv().game = makeProxy("game")
getfenv().workspace = makeProxy("workspace")
getfenv().Workspace = getfenv().workspace
getfenv().script = makeProxy("script")
getfenv().tick = function() return os.clock() end
getfenv().time = function() return os.clock() end
getfenv().cloneref = function(x) return x end
getfenv().checkcaller = function() return true end
getfenv().newcclosure = function(f) return f end
getfenv().hookmetamethod = function(obj, meta, fn) return fn end
getfenv().hookfunction = function(orig, newfn) return newfn end
getfenv().loadstring = function(s) return function() end end
getfenv().identifyexecutor = function() return "PayomboyZ", "v4.0" end
getfenv().getgenv = function() return getfenv() end
getfenv().getrenv = function() return getfenv() end
getfenv().task = {
    wait = function() return 0 end,
    spawn = function(f, ...) pcall(f, ...) end,
    defer = function(f, ...) pcall(f, ...) end,
    delay = function(t, f, ...) pcall(f, ...) end
}

-- Native / Custom signal wrappers (e.g. Slayer 2)
getfenv().Native = {
    SignalFunction = {
        ToServer = function(name, ...)
            print("[TRAP_SIGNAL_FUNC] " .. tostring(name) .. "(" .. formatArgs(...) .. ")")
            return true
        end
    },
    SignalEvent = {
        ToServer = function(name, ...)
            print("[TRAP_SIGNAL_EVENT] " .. tostring(name) .. "(" .. formatArgs(...) .. ")")
            return true
        end
    }
}
"""

class LuauSandboxTracer:
    """
    Executes heavily obfuscated scripts inside an emulated Luau environment
    to capture live remotes and arguments at the boundary.
    """

    @classmethod
    def trace_obfuscated_script(cls, code: str, timeout_sec: int = 4) -> Dict[str, Any]:
        """
        Runs the code against the Metamethod Trap and extracts intercepted events.
        """
        if not LUAU_BIN.exists():
            print(f"[-] Luau binary not found at {LUAU_BIN}", flush=True)
            return {"remotes": [], "remote_calls": []}

        # Wrap with safe pcall around target execution
        wrapped_script = f"""{SANDBOX_PREAMBLE}

pcall(function()
{code}
end)
"""
        remotes_found: Set[str] = set()
        remote_calls: List[Dict[str, Any]] = []

        with tempfile.NamedTemporaryFile(suffix=".luau", mode="w", encoding="utf-8", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(wrapped_script)

        try:
            res = subprocess.run(
                [str(LUAU_BIN), tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            stdout = res.stdout or ""

            # Parse TRAP_REMOTE lines
            # [TRAP_REMOTE] game.ReplicatedStorage.Remotes.CombatEvent -> FireServer("LightAttack", 45, true)
            remote_regex = re.compile(r'\[TRAP_REMOTE\]\s+([a-zA-Z0-9_\.:]+)\s*->\s*([a-zA-Z0-9_]+)\((.*?)\)')
            for m in remote_regex.finditer(stdout):
                path, method, args = m.groups()
                remotes_found.add(path)
                remote_calls.append({
                    "remote": path,
                    "method": method,
                    "args": args
                })

            # Parse TRAP_SIGNAL lines (Custom signal wrappers)
            signal_regex = re.compile(r'\[TRAP_SIGNAL_[A-Z]+\]\s+([a-zA-Z0-9_\.]+)\((.*?)\)')
            for m in signal_regex.finditer(stdout):
                name, args = m.groups()
                remotes_found.add(f"Signal:{name}")
                remote_calls.append({
                    "remote": f"Signal:{name}",
                    "method": "ToServer",
                    "args": args
                })

        except subprocess.TimeoutExpired:
            print("[SANDBOX] Execution timed out (infinite loop safely stopped).", flush=True)
        except Exception as e:
            print(f"[SANDBOX] Error during execution: {e}", flush=True)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        return {
            "remotes": sorted(list(remotes_found)),
            "remote_calls": remote_calls
        }

SANDBOX_TRACER = LuauSandboxTracer()
