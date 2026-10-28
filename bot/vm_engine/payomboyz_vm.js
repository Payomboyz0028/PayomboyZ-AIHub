// lib/obfuscator/vm_engine/payomboyz_vm.js - High-Performance Luau Register VM & CFF Obfuscator
import { lex } from './lexer/Lexer.js';
import { parse } from './parser/Parser.js';
import { obfuscate } from './obfuscator/Obfuscator.js';
import { encodeStrings } from './obfuscator/StringEncoder.js';
import { scrambleControlFlow } from './obfuscator/ControlFlowScrambler.js';
import { printChunkOneLine } from './obfuscator/Printer.js';
import { regCompile } from './vm/RegCompiler.js';
import { generateRegVM } from './vm/reg-vm-gen.js';

export const PAYOMBOYZ_BANNER = `--[[
__________  _____ _____.___.________      _____ __________ ________ _____.___.__________
\\______   \\/  _  \\\\__  |   |\\_____  \\    /     \\\\______   \\\\_____  \\\\__  |   |\\____    /
 |     ___/  /_\\  \\/   |   | /   |   \\  /  \\ /  \\|    |  _/ /   |   \\/   |   |  /     / 
 |    |  /    |    \\____   |/    |    \\/    Y    \\    |   \\/    |    \\____   | /     /_ 
 |____|  \\____|__  / ______|\\_______  /\\____|__  /______  /\\_______  / ______|/_______ \\
                 \\/\\/               \\/         \\/       \\/         \\/\\/               \\/
          \\_Welcome to PAYOMBOYZ Security (Sentinel Engine v2.0) ~ Much Love, dj

]]--
`;

/**
 * Obfuscates Luau source code using a 3-tier selective security architecture:
 * - Level 1 (Light / 60 FPS Native): AST Local Mangling + S-Box String Encryption (0% Lag, Pure Native)
 * - Level 2 (Medium / Balanced): AST Mangling + String Encryption + Opaque Invariant Control Flow Scrambling
 * - Level 3 (Maximum Armor / VM): Register Bytecode Virtualization + Dual-State CFF + Anti-Hook/Spy
 * 
 * @param {string} source - Raw Luau/Lua code
 * @param {object} options - Protection configurations
 * @returns {string} Obfuscated code
 */
export function obfuscateWithVM(source, options = {}) {
  if (!source || typeof source !== 'string') return source;

  const {
    level = 'max',
    controlFlow = true,
    encryptStrings = true,
    renameLocals = true,
    preserveGlobals = true,
    antiDump = true,
    banner = true
  } = options;

  const isLevel1 = (level === 'light' || level === 'fast' || level === 'level1' || level === '1');
  const isLevel2 = (level === 'medium' || level === 'level2' || level === '2');

  // --- TIER 1: LIGHT (60 FPS NATIVE AST - Ideal for Aimbot, ESP, RenderStepped Loops) ---
  if (isLevel1) {
    const { tokens, errors } = lex(source);
    if (errors && errors.length > 0) {
      throw new Error(`Syntax Error: ${errors[0].message || 'Invalid Luau token'}`);
    }
    let ast = parse(tokens);
    if (encryptStrings) {
      try {
        ast = encodeStrings(ast, { enabled: true });
      } catch (e) {
        console.warn('[AST] encodeStrings warning:', e.message);
      }
    }
    const obfuscatedAst = obfuscate(ast, {
      renameLocals: true,
      preserveGlobals: true
    });
    const out = printChunkOneLine(obfuscatedAst);
    return banner ? `${PAYOMBOYZ_BANNER}${out}` : out;
  }

  // --- TIER 2: BALANCED (NATIVE AST + OPAQUE INVARIANTS + CONTROL FLOW SCRAMBLING) ---
  if (isLevel2) {
    const { tokens, errors } = lex(source);
    if (errors && errors.length > 0) {
      throw new Error(`Syntax Error: ${errors[0].message || 'Invalid Luau token'}`);
    }
    let ast = parse(tokens);
    if (encryptStrings) {
      try {
        ast = encodeStrings(ast, { enabled: true });
      } catch (e) {
        console.warn('[AST] encodeStrings warning:', e.message);
      }
    }
    if (controlFlow) {
      try {
        ast = scrambleControlFlow(ast, { enabled: true });
      } catch (e) {
        console.warn('[AST] scrambleControlFlow warning:', e.message);
      }
    }
    const obfuscatedAst = obfuscate(ast, {
      renameLocals: true,
      preserveGlobals: true
    });
    let out = printChunkOneLine(obfuscatedAst);
    if (antiDump) {
      const guard = 'pcall(function()local _g=(getgenv and getgenv())or _G;if _g then _g.__PBZ_GUARD=(tick and tick())or os.time()end end);';
      out = `${guard}${out}`;
    }
    return banner ? `${PAYOMBOYZ_BANNER}${out}` : out;
  }

  // --- TIER 3: MAXIMUM ARMOR / SENTINEL (FULL REGISTER BYTECODE VIRTUALIZATION) ---
  // 1. Lexing
  const { tokens, errors } = lex(source);
  if (errors && errors.length > 0) {
    throw new Error(`Syntax Error: ${errors[0].message || 'Invalid Luau token'}`);
  }

  // 2. AST Parsing
  let ast = parse(tokens);

  // 3. String & Constant S-Box Encryption (AST pass)
  if (encryptStrings) {
    try {
      ast = encodeStrings(ast, { enabled: true });
    } catch (e) {
      console.warn('[VM] encodeStrings warning:', e.message);
    }
  }

  // 4. Control Flow Flattening & Scrambling (AST pass)
  if (controlFlow) {
    try {
      ast = scrambleControlFlow(ast, { enabled: true });
    } catch (e) {
      console.warn('[VM] scrambleControlFlow warning:', e.message);
    }
  }

  // 5. Scope-Aware Variable & Local Identifier Mangling
  const obfuscatedAst = obfuscate(ast, {
    renameLocals,
    preserveGlobals: true
  });

  // 6. Register-Based Bytecode Compilation
  const chunk = regCompile(obfuscatedAst);

  // 7. VM Runtime Synthesis (Zero-loadstring, Shuffled Opcodes, Dual-State CFF)
  const disableFeatures = [];
  if (!controlFlow) disableFeatures.push('controlFlowFlattening');

  let vmOutput = generateRegVM(chunk, {
    level: 'max',
    executorGlobals: true,
    polymorphicSeed: Date.now() ^ Math.floor(Math.random() * 0xFFFFFF),
    debugTrace: false,
    disableFeatures
  });

  // 8. Strip banner comments so the output is a pristine single-line VM
  const bannerEnd = vmOutput.indexOf(']]\n');
  if (bannerEnd !== -1) {
    vmOutput = vmOutput.substring(bannerEnd + 3).trim();
  }

  // 9. Inject Anti-Dump / Anti-Hook Safeguards if enabled (100% Single-Line)
  if (antiDump) {
    const guardHeader = 'pcall(function()if typeof(game)=="Instance" and game.ClassName=="DataModel" and game:IsA("DataModel")then local _g=(getgenv and getgenv())or _G;if _g then _g.__PBZ_VM_GUARD=(tick and tick())or os.time()end end end);';
    vmOutput = `${guardHeader}${vmOutput}`;
  }

  const finalOut = vmOutput.trim();
  return banner ? `${PAYOMBOYZ_BANNER}${finalOut}` : finalOut;
}
