import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENGINE_DIR = BASE_DIR / "Prometheus-WeAre-Devs-Dumper-main"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR = BASE_DIR / "cache"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Load from .env if present
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_ROLE_BOT_TOKEN = os.environ.get("DISCORD_ROLE_BOT_TOKEN", "")
DISCORD_AI_BOT_TOKEN = os.environ.get("DISCORD_AI_BOT_TOKEN", "")

# Discord Client Credentials & OAuth2 Settings
DISCORD_ROLE_BOT_CLIENT_ID = os.environ.get("DISCORD_ROLE_BOT_CLIENT_ID", os.environ.get("DISCORD_CLIENT_ID", "1548921066833838080"))
DISCORD_ROLE_BOT_CLIENT_SECRET = os.environ.get("DISCORD_ROLE_BOT_CLIENT_SECRET", os.environ.get("DISCORD_CLIENT_SECRET", os.environ.get("CLIENT_SECRET", "c4ktSWk44t-8JPDOb9YH-pEk-p5qfOOw")))
DISCORD_CLIENT_ID = DISCORD_ROLE_BOT_CLIENT_ID
DISCORD_CLIENT_SECRET = DISCORD_ROLE_BOT_CLIENT_SECRET
CLIENT_ID = DISCORD_ROLE_BOT_CLIENT_ID
CLIENT_SECRET = DISCORD_ROLE_BOT_CLIENT_SECRET

def get_bot_invite_url(client_id: str = None, permissions: int = 8) -> str:
    """Generate Discord bot invite URL using Client ID"""
    cid = client_id or CLIENT_ID
    return f"https://discord.com/oauth2/authorize?client_id={cid}&permissions={permissions}&scope=bot%20applications.commands"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
raw_keys = os.environ.get("GEMINI_API_KEYS", "")
if raw_keys:
    GEMINI_API_KEYS = [k.strip() for k in raw_keys.split(",") if k.strip()]
else:
    GEMINI_API_KEYS = [GEMINI_API_KEY] if GEMINI_API_KEY else []

for i in range(2, 40):
    k = os.environ.get(f"GEMINI_API_KEY_{i}")
    if k and k.strip() and k.strip() not in GEMINI_API_KEYS:
        GEMINI_API_KEYS.append(k.strip())

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

# DeepSeek Official API (Disabled per dj - non-free API)
# All tasks route 100% via Free Tier providers (Gemini, Bluezy, OpenRouter Free, ThaiLLM)
DEEPSEEK_BASE_URL = ""
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_REASONER_MODEL = "deepseek-reasoner"
DEEPSEEK_OFFICIAL_KEYS = []

# OpenRouter DeepSeek (Free Tier Pool - 50 Req/Day per Key Fallback)
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")
OPENROUTER_API_KEYS = []
raw_or_keys = os.environ.get("OPENROUTER_API_KEYS", "")
if raw_or_keys:
    OPENROUTER_API_KEYS = [k.strip() for k in raw_or_keys.split(",") if k.strip()]

for i in range(1, 40):
    k = os.environ.get(f"OPENROUTER_API_KEY_{i}")
    if k and k.strip() and k.strip() not in OPENROUTER_API_KEYS:
        OPENROUTER_API_KEYS.append(k.strip())

# Combined DeepSeek Key Pool (OpenRouter Free Tier only)
DEEPSEEK_API_KEYS = []
for k in OPENROUTER_API_KEYS:
    if k not in DEEPSEEK_API_KEYS:
        DEEPSEEK_API_KEYS.append(k)
raw_ds_keys = os.environ.get("DEEPSEEK_API_KEYS", "")
if raw_ds_keys:
    for k in raw_ds_keys.split(","):
        k = k.strip()
        if k and k.startswith("sk-or-") and k not in DEEPSEEK_API_KEYS:
            DEEPSEEK_API_KEYS.append(k)

# BluezyGPT Workers (Deep Deobfuscation & Reverse Engineering - Multi-Key Pool)
BLUEZY_BASE_URL = os.environ.get("BLUEZY_BASE_URL", "https://bluezygpt.space/api/v1")
BLUEZY_MODEL = "bluezygpt-free"
BLUEZY_API_KEYS = []
raw_bz = os.environ.get("BLUEZY_API_KEYS", "")
if raw_bz:
    BLUEZY_API_KEYS = [k.strip() for k in raw_bz.split(",") if k.strip()]
for _i in range(1, 40):
    _k = os.environ.get(f"BLUEZY_API_KEY_{_i}")
    if _k and _k.strip() and _k.strip() not in BLUEZY_API_KEYS:
        BLUEZY_API_KEYS.append(_k.strip())
BLUEZY_API_KEY = BLUEZY_API_KEYS[0] if BLUEZY_API_KEYS else ""

# ThaiLLM National API (National Thai AI - Multi-Key Pool & Models)
THAILLM_BASE_URL = os.environ.get("THAILLM_BASE_URL", "http://thaillm.or.th/api/v1")
THAILLM_MODEL = os.environ.get("THAILLM_MODEL", "qwen3.6-35b-a3b")
THAILLM_API_KEY = os.environ.get("THAILLM_API_KEY", "I3QmH3w8WQ6rF4mj5ZJbYvagrdy0FD5B")
THAILLM_PATHUMMA_URL = os.environ.get("THAILLM_PATHUMMA_URL", "http://thaillm.or.th/api/pathumma/v1")

THAILLM_API_KEYS = []
raw_thai_keys = os.environ.get("THAILLM_API_KEYS", "")
if raw_thai_keys:
    THAILLM_API_KEYS = [k.strip() for k in raw_thai_keys.split(",") if k.strip()]
else:
    THAILLM_API_KEYS = [THAILLM_API_KEY] if THAILLM_API_KEY else []

for i in range(1, 10):
    k = os.environ.get(f"THAILLM_API_KEY_{i}")
    if k and k.strip() and k.strip() not in THAILLM_API_KEYS:
        THAILLM_API_KEYS.append(k.strip())

BRIDGE_PORT = int(os.environ.get("BRIDGE_PORT", 49281))
COMMAND_PREFIX = os.environ.get("COMMAND_PREFIX", "!")
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", 100))
DEOBFUSCATION_TIMEOUT = int(os.environ.get("DEOBFUSCATION_TIMEOUT", 600))
ROLE_ID = int(os.environ.get("ROLE_ID", "1549785782330593330"))

# ScriptCenter / Shop Key Verification API
SC_API_BASE = os.environ.get("SC_API_BASE", "https://payomboyz-hub.scriptcenter.online/api/discord")
SC_API_KEY = os.environ.get("SC_API_KEY", "")

# ==============================================================================
# GROUP 5 & GROUP 3: LOCAL POW SOLVER & FREE OPENAI-COMPATIBLE PROVIDERS
# ==============================================================================
# 1. Local DeepSeek PoW WASM Server (Deepseek-API-main)
DEEPSEEK_POW_BASE_URL = os.environ.get("DEEPSEEK_POW_BASE_URL", "http://127.0.0.1:8000/v1")
DEEPSEEK_POW_MODEL = os.environ.get("DEEPSEEK_POW_MODEL", "deepseek-chat")

# 2. Groq (Free Tier: 30 RPM, 14,400 RPD)
GROQ_BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEYS = []
raw_groq = os.environ.get("GROQ_API_KEYS", os.environ.get("GROQ_API_KEY", ""))
if raw_groq:
    GROQ_API_KEYS = [k.strip() for k in raw_groq.split(",") if k.strip()]
for i in range(1, 10):
    k = os.environ.get(f"GROQ_API_KEY_{i}")
    if k and k.strip() and k.strip() not in GROQ_API_KEYS:
        GROQ_API_KEYS.append(k.strip())

# 3. Cerebras (Free Tier: 5 RPM)
CEREBRAS_BASE_URL = os.environ.get("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")
CEREBRAS_MODEL = os.environ.get("CEREBRAS_MODEL", "llama3.1-70b")
CEREBRAS_API_KEYS = []
raw_cerebras = os.environ.get("CEREBRAS_API_KEYS", os.environ.get("CEREBRAS_API_KEY", ""))
if raw_cerebras:
    CEREBRAS_API_KEYS = [k.strip() for k in raw_cerebras.split(",") if k.strip()]

# 4. SambaNova (Free Tier: 20 RPM)
SAMBANOVA_BASE_URL = os.environ.get("SAMBANOVA_BASE_URL", "https://api.sambanova.ai/v1")
SAMBANOVA_MODEL = os.environ.get("SAMBANOVA_MODEL", "Meta-Llama-3.1-70B-Instruct")
SAMBANOVA_API_KEYS = []
raw_sambanova = os.environ.get("SAMBANOVA_API_KEYS", os.environ.get("SAMBANOVA_API_KEY", ""))
if raw_sambanova:
    SAMBANOVA_API_KEYS = [k.strip() for k in raw_sambanova.split(",") if k.strip()]

# 5. Hugging Face Router & LLM7 Free Endpoints
HUGGINGFACE_BASE_URL = os.environ.get("HUGGINGFACE_BASE_URL", "https://router.huggingface.co/v1")
HUGGINGFACE_MODEL = os.environ.get("HUGGINGFACE_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct")
HUGGINGFACE_API_KEYS = [k.strip() for k in os.environ.get("HUGGINGFACE_API_KEY", "").split(",") if k.strip()]

LLM7_BASE_URL = os.environ.get("LLM7_BASE_URL", "https://api.llm7.io/v1")
LLM7_MODEL = os.environ.get("LLM7_MODEL", "llama-3.3-70b")
LLM7_API_KEYS = [k.strip() for k in os.environ.get("LLM7_API_KEY", "").split(",") if k.strip()]

# 6. gpt4free (g4f) Infinite Zero-Key Fallback Engine
ENABLE_G4F_FALLBACK = os.environ.get("ENABLE_G4F_FALLBACK", "true").lower() in ("1", "true", "yes")



