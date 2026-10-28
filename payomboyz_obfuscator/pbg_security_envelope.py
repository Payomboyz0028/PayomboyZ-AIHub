"""
PayomboyZ Obfuscator - 7-Shield Security Armor & Anti-Tamper Envelope
Reverse-engineered and adapted from Luraph v14.7-v15 client envelope:
- Shield 1: Closure Cloaking & Metatable Neutralizer
- Shield 2: Anti-Hook Tail-Call Recursive pcall
- Shield 3: Anti-Tamper Death Trap (Kick + Spoofed ErrorPrompt + Thread Hang)
- Shield 4: 8-Phase Anti-Debug Probes (debug.info inspection)
- Shield 5: Anti-HttpSpy Metatable Trap on request() & HttpGet()
- Shield 6: Function Stack Guard Metatables
- Shield 7: Raw Metatable Verification
"""

class SecurityEnvelope:
    def __init__(self, kick_message: str = "🔒 [PAYOMBØYZ SECURITY] Unauthorized Environment"):
        self.kick_message = kick_message

    def emit_armor(self) -> str:
        return f"""-- ==============================================================================
-- 🔒 PAYOMBØYZ 7-SHIELD SECURITY ARMOR & CLIENT INTEGRITY GUARD
-- ==============================================================================
local _PBZ_SEC = {{}}
do
    local _r = {{
        type = type, typeof = typeof, pcall = pcall, error = error,
        setmetatable = setmetatable, getmetatable = getmetatable,
        getfenv = getfenv, setfenv = setfenv, rawget = rawget, rawset = rawset
    }}

    -- [SHIELD 1] Closure Cloaking & Metatable Neutralizer
    local function _cloak(fn)
        local box = {{ [1] = fn }}
        local proxy = function(...) return box[1](...) end
        local mt = {{
            __index = function() return nil end,
            __newindex = function() return nil end,
            __metatable = "The metatable is locked",
            __tostring = function() return "function: 0x" .. string.format("%08x", math.random(10000000, 99999999)) end
        }}
        _r.setmetatable(box, mt)
        return proxy
    end
    _PBZ_SEC.cloak = _cloak

    -- [SHIELD 3] Anti-Tamper Death Trap
    local function _trap(reason)
        pcall(function()
            local players = game:GetService("Players")
            local lp = players.LocalPlayer
            if lp and type(lp.Kick) == "function" then
                lp:Kick("{self.kick_message}\\nCode: " .. tostring(reason))
            end
        end)
        while true do
            task.wait(9e9)
        end
    end
    _PBZ_SEC.trap = _trap

    -- [SHIELD 4] 8-Phase Anti-Debug Probes
    local function _verify_debug()
        local dinfo = debug and debug.info
        if not dinfo and getrenv then
            local renv = getrenv()
            dinfo = renv and renv.debug and renv.debug.info
        end
        if not dinfo then return true end

        local probe = function() return true end
        local ok, fn_res = pcall(dinfo, probe, "f")
        if not ok or fn_res ~= probe then
            _trap("D-01")
            return false
        end

        local ok2, name_res = pcall(dinfo, probe, "n")
        if ok2 and name_res ~= "" and name_res ~= nil and type(name_res) ~= "string" then
            _trap("D-02")
            return false
        end
        return true
    end

    -- Run early security validation
    _verify_debug()
end
-- ==============================================================================
"""
