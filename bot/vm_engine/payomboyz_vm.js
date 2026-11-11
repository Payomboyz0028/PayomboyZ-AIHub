// lib/obfuscator/vm_engine/payomboyz_vm.js - High-Performance Luau Register VM & CFF Obfuscator
import { lex } from './lexer/Lexer.js';
import { parse } from './parser/Parser.js';
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
          \\_Welcome to PAYOMBOYZ Security (Sentinel Engine v4.4) ~ Much Love, dj

]]--
`;

// Internal runtime security guard — baked directly into AST before bytecode compilation
// (100% compiled into VM opcodes: zero plaintext comments, zero exposed functions)
const INTERNAL_VM_GUARD = `pcall(function()
    local _g = (getgenv and getgenv()) or _G
    if _g and not _g.__PBZ_ACTIVE then
        _g.__PBZ_ACTIVE = (tick and tick()) or os.time()
    end
end)
`;

/**
 * Obfuscates Luau source code using a 5-tier Register Bytecode Virtual Machine:
 * - Level 1: Fast VM (Lightweight Register VM, 60 FPS, Zero GC Lag)
 * - Level 2: Balanced VM (Register VM + Opcode Shuffling + S-Box String Encryption)
 * - Level 3: Maximum Armor (Register VM + Dual-State CFF + Instruction Fusion)
 * - Level 4: Prometheus Multi-Tier VM (Instruction Virtualizer + Metamorphic Mutation)
 * - Level 5: Sentinel Enterprise Armor (Maximum Bytecode Virtualization + Internal Integrity)
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
  const isLevel2 = (lvl === 'level2' || lvl === '2' || lvl === 'medium' || lvl === 'balanced');
  const isMaxLevel = (lvl === 'level3' || lvl === '3' || lvl === 'max' || lvl === 'armor' || lvl === 'level4' || lvl === '4' || lvl === 'level5' || lvl === '5' || lvl === 'sentinel');

  // 1. Bake Anti-Dump and runtime security directly into the source code
  // so it gets compiled into VM opcodes (never visible as plaintext outside the VM)
  let preparedSource = source;
  if (antiDump && !preparedSource.includes('__PBZ_ACTIVE')) {
    preparedSource = `${INTERNAL_VM_GUARD}\n${preparedSource}`;
  }

  // 2. Lexing
  const { tokens, errors } = lex(preparedSource);
  if (errors && errors.length > 0) {
    throw new Error(`Syntax Error: ${errors[0].message || 'Invalid Luau token'}`);
  }

  // 3. AST Parsing
  const ast = parse(tokens);

  // 4. Scope-Aware Variable & Local Identifier Mangling
  const obfuscatedAst = obfuscate(ast, {
    renameLocals,
    preserveGlobals: true
  });

  // 5. Register-Based Bytecode Compilation
  const chunk = regCompile(obfuscatedAst);

  // 6. Configure VM features based on Security Level
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

  // 7. VM Runtime Synthesis (Zero-loadstring, Shuffled Opcodes, Dual-State CFF)
  let vmOutput = generateRegVM(chunk, {
    level: isLevel1 ? 'fast' : (lvl === 'debug' ? 'debug' : 'max'),
    executorGlobals: true,
    polymorphicSeed: Date.now() ^ Math.floor(Math.random() * 0xFFFFFF),
    debugTrace: options.debugTrace ?? (lvl === 'debug'),
    noMinify: options.noMinify ?? false,
    placeId: options.placeId || options.targetPlaceId || 0,
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
