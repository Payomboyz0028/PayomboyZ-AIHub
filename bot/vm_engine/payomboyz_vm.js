// lib/obfuscator/vm_engine/payomboyz_vm.js - High-Performance Luau Register VM & CFF Obfuscator
import { lex } from './lexer/Lexer.js';
import { parse } from './parser/Parser.js';
import { preprocessMacrosAndTiers } from './vm/v5-macros-native.js';
import { obfuscate } from './obfuscator/Obfuscator.js';
import { regCompile } from './vm/RegCompiler.js';
import { generateRegVM } from './vm/reg-vm-gen.js';

export const PAYOMBOYZ_BANNER = `--[[
__________  _____ _____.___.________      _____ __________ ________ _____.___.__________
\\______   \\/  _  \\\\__  |   |\\_____  \\    /     \\\\______   \\\\_____  \\\\__  |   |\\____    /
 |     ___/  /_\\  \\/   |   | /   |   \\  /  \\ /  \\|    |  _/ /   |   \\/   |   |  /     / 
 |    |  /    |    \\____   |/    |    \\/    Y    \\    |   \\/    |    \\____   | /     /_ 
 |____|  \\____|__  / ______|\\_______  /\\____|__  /______  /\\_______  / ______|/_______ \\
                 \\/\\/               \\/         \\/       \\/         \\/\\/               \\/
          \\_Welcome to PAYOMBOYZ Security (Sentinel Engine v5.3 APEX) ~ Much Love, dj

]]--
`;

/**
 * Obfuscates Luau source code using Sentinel Engine v5.3 APEX (ONYX / OPAL):
 * - Level 1: OPAL Fast (SoA Superoperators + 128-bit ARX Keys + Masked BST + Zero-Plaintext Env)
 * - Level 2: OPAL+ Balanced (Level 1 + Rolling-State Block Cipher + Merged/Split Ops + Shifted _rb/_kb + Reg Perm)
 * - Level 3: ONYX Maximum Armor (Dual-Mode Asymmetric Dispatcher + IR State Machine + Anti-SCCP Opaque + MBA + Strict Roblox)
 *
 * @param {string} source - Raw Luau/Lua code
 * @param {object} options - Protection configurations
 * @returns {string} Obfuscated code
 */
export function obfuscateWithVM(source, options = {}) {
  if (!source || typeof source !== 'string') return source;

  const {
    level = 'level3',
    controlFlow = true,
    encryptStrings = true,
    renameLocals = true,
    preserveGlobals = true,
    antiDump = true,
    banner = true
  } = options;

  const lvl = String(level).toLowerCase();
  const isLevel1 = (lvl === 'level1' || lvl === '1' || lvl === 'fast' || lvl === 'light');
  const isLevel2 = (lvl === 'level2' || lvl === '2' || lvl === 'medium' || lvl === 'balanced' || lvl === 'normal');
  const isDebug = (lvl === 'debug');
  const isMaxLevel = !isLevel1 && !isLevel2 && !isDebug;

  // 1. Lexing
  const { tokens, errors } = lex(source);
  if (errors && errors.length > 0) {
    throw new Error(`Syntax Error: ${errors[0].message || 'Invalid Luau token'}`);
  }

  // 3. AST Parsing
  const ast = parse(tokens);

  // 4. Macros, Execution Tiers & Hardened Native Extraction
  const { ast: preAst, nativeFuncs, strictRoblox: preStrictRoblox } = preprocessMacrosAndTiers(ast, {
    placeId: options.placeId || options.targetPlaceId || 0,
    target: options.target,
    disableNative: options.disableNative,
    native: options.native,
  });

  // 5. Scope-Aware Variable & Local Identifier Mangling
  const obfuscatedAst = obfuscate(preAst, {
    renameLocals,
    preserveGlobals: true
  });

  // 6. Register-Based Bytecode Compilation
  const chunk = regCompile(obfuscatedAst);

  // 7. Configure VM features based on Security Level
  const disableFeatures = [...(options.disableFeatures || [])];

  if (!encryptStrings && !disableFeatures.includes('stringEncoding')) {
    disableFeatures.push('stringEncoding');
  }

  if (isLevel1) {
    // Level 1: Fast VM - Disable heavy CFF for pure 60 FPS speed
    if (!disableFeatures.includes('controlFlowFlattening')) {
      disableFeatures.push('controlFlowFlattening');
    }
  } else if (!controlFlow && !disableFeatures.includes('controlFlowFlattening')) {
    disableFeatures.push('controlFlowFlattening');
  }

  // 8. VM Runtime Synthesis (Sentinel Engine v5.3 APEX)
  let vmOutput = generateRegVM(chunk, {
    level: isDebug ? 'debug' : (isLevel1 ? 'fast' : (isLevel2 ? 'normal' : 'max')),
    executorGlobals: true,
    polymorphicSeed: options.polymorphicSeed ?? (Date.now() ^ Math.floor(Math.random() * 0xFFFFFF)),
    debugTrace: options.debugTrace ?? isDebug,
    noMinify: options.noMinify ?? false,
    placeId: options.placeId || options.targetPlaceId || 0,
    robloxOnly: Boolean(options.robloxOnly || options.strictRoblox || preStrictRoblox),
    nativeFuncs,
    disableFeatures
  });

  // 8. Strip any internal generation header comments so output is pure single-line VM
  const bannerEnd = vmOutput.indexOf(']]\n');
  if (bannerEnd !== -1) {
    vmOutput = vmOutput.substring(bannerEnd + 3).trim();
  }

  const finalOut = vmOutput.trim();
  return banner ? `${PAYOMBOYZ_BANNER}${finalOut}` : finalOut;
}
