# PAYOMBØYZ REA (Reverse Engineer Anything) Engine Knowledge Base

## 1. Overview
REA is an MCP-driven universal reverse engineering platform supporting native binary decompilation, web bundle source recovery, .NET CIL assemblies, and Android APK/DEX decompilation.

## 2. Integrated Tooling & Workflows
### A. JavaScript / Web Application Recovery
- **Wakaru Integration**: High-fidelity unbundler for Webpack, Vite, Rollup, and Browserify bundles.
- **Source Map Inlining**: Restores exact source file paths and original formatting.
- **Application Graph**: Analyzes client-side routing, Electron IPC boundaries, and module dependencies.

### B. Native Binary Reversing (PE / ELF / Mach-O)
- **Ghidra & Hopper Bridges**: Generates headless control flow graphs, procedure listings, and decompiled pseudocode.
- **PE Resource & Export Inspection**: Inspects manifest files, imports, exports, and section layouts.

### C. Managed Code & Android
- **.NET CLR Assemblies**: Inspects metadata, types, methods, and P/Invoke native interop boundaries.
- **Android APK / DEX**: Inspects manifest permissions, activities, JEB decompilation, and classes.dex structures.
