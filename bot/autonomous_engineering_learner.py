# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
KNOWLEDGE_FILE = DATA_DIR / 'autonomous_engineering_knowledge.json'

_DEFAULT_ARCHS = {
    'LURAPH': {'versions_detected': ['v14.0','v14.7','v15.0'], 'known_opcodes': ['Jt','vt','GQ','fQ'], 'samples_processed': 0, 'success_rate': 1.0, 'failure_patterns': [], 'avg_recovery_lines': 480, 'r1_required': False},
    'MOONSEC': {'versions_detected': ['v2','v3','v5'], 'unicode_stego': True, 'samples_processed': 0, 'success_rate': 0.95, 'failure_patterns': [], 'avg_recovery_lines': 320, 'r1_required': False},
    'CLYDE_VM': {'two_tier': True, 'cff_flattened': True, 'samples_processed': 0, 'success_rate': 1.0, 'failure_patterns': ['nested_upvalue_closure'], 'avg_recovery_lines': 650, 'r1_required': True},
}

class AutonomousEngineeringLearner:
    def __init__(self):
        self.knowledge_path = KNOWLEDGE_FILE
        self._knowledge = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.knowledge_path.exists():
            default_data = {'version': '2.0.0', 'total_learned_samples': 0, 'last_updated': time.time(), 'vm_architectures': _DEFAULT_ARCHS.copy(), 'cff_state_patterns': [{'name': 'state_machine_switch', 'signature': 'while true do if state == ', 'reduction': 'AST_SSA_INLINE', 'frequency': 1}], 'anticheat_traps_bypassed': [{'trap': 'solara_xeno_env_check', 'signature': 'getgenv().debug', 'mitigation': 'MOCK_ENVIRONMENT'}], 'autonomous_idle_missions': [], 'cross_session_insights': [], 'gap_analysis_results': [], 'prompt_performance_log': []}
            self._save(default_data)
            return default_data
        try:
            with open(self.knowledge_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if str(data.get('version', '1.0.0')) < '2.0.0':
                data['version'] = '2.0.0'
                data.setdefault('cross_session_insights', [])
                data.setdefault('gap_analysis_results', [])
                data.setdefault('prompt_performance_log', [])
                for ad in data.get('vm_architectures', {}).values():
                    ad.setdefault('failure_patterns', [])
                    ad.setdefault('avg_recovery_lines', 0)
                    ad.setdefault('r1_required', False)
                    ad.setdefault('samples_processed', 0)
            return data
        except Exception:
            return {}

    def _save(self, data=None):
        target = data or self._knowledge
        target['last_updated'] = time.time()
        try:
            with open(self.knowledge_path, 'w', encoding='utf-8') as f:
                json.dump(target, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f'[-] Failed to save engineering knowledge: {e}', flush=True)

    def record_decompilation_success(self, architecture, source_hash, recovered_lines, confidence, discovered_patterns=None, notes=''):
        arch_key = architecture.upper()
        self._knowledge.setdefault('vm_architectures', {})
        if arch_key not in self._knowledge['vm_architectures']:
            self._knowledge['vm_architectures'][arch_key] = {'first_seen': time.time(), 'samples_processed': 0, 'patterns': [], 'success_rate': 1.0, 'failure_patterns': [], 'avg_recovery_lines': 0, 'r1_required': False}
        ae = self._knowledge['vm_architectures'][arch_key]
        n = ae.get('samples_processed', 0)
        ae['samples_processed'] = n + 1
        ae['last_seen'] = time.time()
        ae['avg_recovery_lines'] = int((ae.get('avg_recovery_lines', 0) * n + recovered_lines) / (n + 1))
        if discovered_patterns:
            ex = set(ae.get('patterns', []))
            ex.update(discovered_patterns)
            ae['patterns'] = list(ex)
        if 'r1_pass_4.5' in notes:
            ae['r1_required'] = True
        self._knowledge.setdefault('prompt_performance_log', []).append({'arch': arch_key, 'hash': source_hash[:16], 'lines': recovered_lines, 'confidence': round(confidence, 3), 'notes': notes, 'ts': time.time()})
        if len(self._knowledge['prompt_performance_log']) > 200:
            self._knowledge['prompt_performance_log'] = self._knowledge['prompt_performance_log'][-200:]
        self._knowledge['total_learned_samples'] = self._knowledge.get('total_learned_samples', 0) + 1
        self._save()

    def record_failure_pattern(self, architecture, error_msg, fallback_used=''):
        arch_key = architecture.upper()
        ae = self._knowledge.setdefault('vm_architectures', {}).setdefault(arch_key, {'samples_processed': 0, 'success_rate': 1.0, 'failure_patterns': [], 'r1_required': False})
        fail_entry = (error_msg[:80]) + ' | fallback=' + fallback_used
        existing_fails = ae.setdefault('failure_patterns', [])
        if fail_entry not in existing_fails:
            existing_fails.append(fail_entry)
            if len(existing_fails) > 20:
                ae['failure_patterns'] = existing_fails[-20:]
        if 'r1' in fallback_used.lower():
            ae['r1_required'] = True
        self._save()

    def get_architecture_confidence(self, arch_name) -> float:
        return float(self._knowledge.get('vm_architectures', {}).get(arch_name.upper(), {}).get('success_rate', 0.85))

    def get_ranked_patterns(self, limit=10) -> list:
        all_patterns: Dict[str, int] = {}
        for entry in self._knowledge.get('cff_state_patterns', []):
            sig = entry.get('signature', '')
            if sig:
                all_patterns[sig] = all_patterns.get(sig, 0) + entry.get('frequency', 1)
        for ad in self._knowledge.get('vm_architectures', {}).values():
            for p in ad.get('patterns', []):
                all_patterns[p] = all_patterns.get(p, 0) + 1
        ranked = sorted(all_patterns.items(), key=lambda x: x[1], reverse=True)
        return [sig for sig, _ in ranked[:limit]]

    def cross_session_merge(self, external_json_path):
        try:
            with open(external_json_path, 'r', encoding='utf-8') as f:
                ext = json.load(f)
            insights = self._knowledge.setdefault('cross_session_insights', [])
            new_items = ext.get('cross_session_insights', []) + ext.get('prompt_performance_log', [])
            for item in new_items:
                if item not in insights:
                    insights.append(item)
            insights.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            self._knowledge['cross_session_insights'] = insights[:500]
            for arch_key, arch_data in ext.get('vm_architectures', {}).items():
                if arch_key not in self._knowledge.get('vm_architectures', {}):
                    self._knowledge.setdefault('vm_architectures', {})[arch_key] = arch_data
                else:
                    existing = self._knowledge['vm_architectures'][arch_key]
                    n_ext = arch_data.get('samples_processed', 0)
                    n_cur = existing.get('samples_processed', 0)
                    if n_ext + n_cur > 0:
                        existing['success_rate'] = (existing.get('success_rate', 1.0) * n_cur + arch_data.get('success_rate', 1.0) * n_ext) / (n_ext + n_cur)
                    existing['samples_processed'] = n_cur + n_ext
            self._save()
            print(f'[+] cross_session_merge: absorbed {len(new_items)} insights', flush=True)
        except Exception as e:
            print(f'[-] cross_session_merge failed: {e}', flush=True)

    def record_idle_mission(self, mission_data):
        missions = self._knowledge.setdefault('autonomous_idle_missions', [])
        missions.append(mission_data)
        if len(missions) > 50:
            self._knowledge['autonomous_idle_missions'] = missions[-50:]
        self._save()

    def get_todays_mission_count(self) -> int:
        today_start = time.time() - (time.time() % 86400)
        return sum(1 for m in self._knowledge.get('autonomous_idle_missions', []) if m.get('timestamp', 0) >= today_start and m.get('success', False))

    def get_engineering_prompt_context(self) -> str:
        archs = self._knowledge.get('vm_architectures', {})
        total = self._knowledge.get('total_learned_samples', 0)
        cff = len(self._knowledge.get('cff_state_patterns', []))
        traps = len(self._knowledge.get('anticheat_traps_bypassed', []))
        r1_archs = [k for k, v in archs.items() if v.get('r1_required')]
        lines = [
            f'PAYOMBZ ENGINEERING BRAIN v2.0 — Samples Learned: {total}',
            f'Mastered: {", ".join(archs.keys()) or "None"}',
            f'CFF patterns: {cff} | Traps mitigated: {traps}',
        ]
        if r1_archs:
            lines.append(f'R1 Required: {", ".join(r1_archs)}')
        return '\n'.join(lines)


AUTONOMOUS_LEARNER = AutonomousEngineeringLearner()
