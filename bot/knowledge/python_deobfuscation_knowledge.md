# PAYOMBØYZ Python Deobfuscation & Reverse Engineering Knowledge Base

## 1. Overview
The PAYOMBØYZ Python Deobfuscator Engine (`bot/python_deobfuscator.py`) provides automated reverse-engineering for Python scripts protected with multi-layer wrappers, Marshal code objects, PyArmor (v7/v8/v9), and Control Flow Flattening (CFF).

## 2. Core Deobfuscation Passes
### Pass 1: Recursive Multi-Layer Wrapper Peeler
- Detects nested wrappers such as:
  `exec(__import__('zlib').decompress(__import__('base64').b64decode(...)))`
  `exec(bytes.fromhex(...))`
  `exec(bytes([108, 111, ...]))`
  `exec("..."[::-1])`
- Recursively peels up to 200 nested layers within milliseconds using streaming decompression.

### Pass 2: Marshal Deserialization & Bytecode Disassembly
- Extracts `marshal.loads(b'...')` code objects.
- Uses Python `dis` instruction inspection to trace `LOAD_CONST`, `STORE_FAST`, `CALL_FUNCTION`, string pools, and argument signatures.
- Recurses into child code objects (nested closures and functions).

### Pass 3: Python Control Flow Flattening (CFF) Unwinder
- Identifies state machines:
  ```python
  state = 1
  while True:
      if state == 1:
          do_step()
          state = 2
      elif state == 2:
          break
  ```
- Traverses state transitions deterministically, eliminates opaque predicates, and reconstructs clean linear statements.

### Pass 4: PyArmor Boundary Inspection
- Recognizes PyArmor v7, v8, and v9 headers (`__pyarmor__`, `pytransform`, `pyarmor_runtime`).
- Extracts armored bytecode payloads and reconstructs unarmored Python code.

### Pass 5: 17-Agent AI Council Semantic Lifter
- Employs DeepSeek, ThaiLLM (Qwen 3.6 35B), BluezyGPT, and Gemini under O.Z.L.S.R Protocol.
- Restores PEP 8 clean structure, variables, functions, and authentic logic with zero hallucination.
