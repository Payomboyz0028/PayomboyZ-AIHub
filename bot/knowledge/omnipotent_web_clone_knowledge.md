# PAYOMBØYZ Omnipotent Web Clone & Reconnaissance Knowledge Base

## 1. Overview
The PAYOMBØYZ Web Clone Engine (`bot/web_clone_engine.py`) is an industrial cyber reconnaissance and web mirror framework powered by `curl_cffi` (Chrome 124 TLS/JA3/JA4 impersonation), multi-threaded asset downloading, and deep SPA crawling.

## 2. Operational Modes
1. **🔍 เจาะลึกโครงสร้าง (Deep Recon)**:
   - Mirrored HTML, CSS, JS, fonts, and images.
   - Secret scan for Google API keys, Telegram tokens, Discord webhooks, and private endpoints.
2. **🌐 ทะลวงไฟร์วอลล์ (Bypass WAF/CF)**:
   - Deep mode + Subdomain enumeration + Cloudflare/Akamai bypass.
3. **💀 ชำแหละเต็มสูบ (Full Apocalypse)**:
   - Bypass + Sensitive path discovery (`.git/HEAD`, `.env`, `swagger.json`, `robots.txt`).
   - OWASP Top 10 surface reconnaissance + Security header audit.
4. **⚙️ สกัด API เมทริกซ์ (API Matrix)**:
   - Full + Deep JS Bundle chunk AST extraction + REST/GraphQL endpoint mapping.
5. **🍪 ทะลวงเซสชัน (Cookie Pass)**:
   - API Full + Cookie injection + Automated JWT token header & payload decoder without secret.
6. **👻 เงาล่องหน (Phantom Spider)**:
   - Deep + Spider form harvester + Email and contact harvesting.
7. **⚡ ปีศาจกลืนกินโลก (Omnipotent Godmode)**:
   - Combines all 6 modes simultaneously with 16 concurrent worker threads.
   - **Source Map Harvester**: Checks `.js.map` and `.css.map`, reconstructing original uncompiled TypeScript, TSX, React, and Vue source code into `reconstructed_sources/`.
   - **Next.js & Vite Chunks**: Scrapes `_buildManifest.js`, `_ssgManifest.js`, and dynamic route bundles.
   - **1-Click Local Server**: Includes `serve.py` in the `.zip` archive for immediate local preview.
