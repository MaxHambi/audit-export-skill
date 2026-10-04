#!/usr/bin/env python3
"""_common.py — Geteilte Helfer für die session-audit/meta-audit Skripte.

Keine Pflicht-Abhängigkeiten; PyYAML wird genutzt wenn verfügbar, sonst greift
ein minimalistischer Fallback-Parser für das Sitzungs-Pass-Subset.
"""
from __future__ import annotations

import io
import os
import re
import sys

# Bereich aus Bindestrich (maskiert) + Gedankenstrich-Varianten U+2010..U+2015 + U+2212
DASH_CLASS = r"[\-\u2010-\u2015\u2212]"

SECRET_PATTERNS = [
    (r"sk-[A-Za-z0-9_\-]{12,}", "OpenAI/kompatible-Keys"),
    (r"ghp_[A-Za-z0-9]{20,}", "GitHub Personal Access Token"),
    (r"github_pat_[A-Za-z0-9_]{20,}", "GitHub Fine-grained PAT"),
    (r"AKIA[0-9A-Z]{12,}", "AWS Access Key"),
    (r"xai-[A-Za-z0-9_\-]{12,}", "xAI-Key"),
    (r"AIza[0-9A-Za-z_\-]{20,}", "Google API-Key"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "Private-Key-Block"),
    (r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}", "JWT"),
]

AGENT_CATEGORIES_DE = {
    "recherche", "coding", "dokumentation", "planung_architektur",
    "verifikation_testing", "kommunikation_orga", "sonstiges",
}
AGENT_CATEGORIES_EN = {
    "research", "coding", "documentation", "planning_architecture",
    "verification_testing", "communication_org", "other",
}
PASSPORT_ALIASES = {
    "dokument": "document", "sitzung_id": "session_id", "sitzung_datum": "session_date",
    "thema": "topic", "beteiligte": "participants", "id_bereiche": "id_ranges",
    "agent_nutzung": "agent_usage", "quellen_mix": "source_mix",
    "ergebnis": "verdict", "befunde": "findings", "hinweis": "note",
    "modell": "model", "schaetzgrundlage": "estimation_basis",
}
PASSPORT_REQUIRED = [
    "schema", "document", "session_id", "session_date", "topic",
    "participants", "version", "status", "gate", "id_ranges", "agent_usage",
]


def read_text(path: str) -> str:
    with io.open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def normalize_keys(d):
    """Alias-Normalisierung (DE→EN) rekursiv; Werte bleiben unverändert."""
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            key = PASSPORT_ALIASES.get(str(k), str(k))
            out[key] = normalize_keys(v)
        return out
    if isinstance(d, list):
        return [normalize_keys(x) for x in d]
    return d


def _minimal_yaml(text: str):
    """Fallback-Parser für das Pass-Subset: flache Keys, Inline-Maps {a: b},
    eine Verschachtungsebene, >- Block-Skalare, #-Kommentare."""
    root: dict = {}
    stack = [(0, root)]  # (indent, container)
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.split(" #", 1)[0].rstrip() if " #" in raw else raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        while stack and indent < stack[-1][0]:
            stack.pop()
        container = stack[-1][1] if stack else root
        m = re.match(r"^([A-Za-z_][\w_\-]*):\s*(.*)$", line.strip())
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == ">-" or val == ">":
            block = []
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                block.append(nxt.strip())
                i += 1
            container[key] = " ".join(x for x in block if x)
            continue
        if val == "":
            child: dict = {}
            container[key] = child
            stack.append((indent + 1, child))
            i += 1
            continue
        if val.startswith("{") and val.endswith("}"):
            inner = {}
            for part in val[1:-1].split(","):
                if ":" in part:
                    k2, v2 = part.split(":", 1)
                    inner[k2.strip()] = _coerce(v2.strip())
            container[key] = inner
            i += 1
            continue
        container[key] = _coerce(val)
        i += 1
    return root


def _coerce(val: str):
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    if re.fullmatch(r"-?\d+", val):
        return int(val)
    if re.fullmatch(r"-?\d+\.\d+", val):
        return float(val)
    return val


def parse_yaml(text: str):
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text), "pyyaml"
    except Exception:
        return _minimal_yaml(text), "fallback"


def extract_passport(md_text: str):
    """Extrahiert den YAML-Pass (--- … ---) am Dateianfang.

    Erlaubtoptionale Titelzeilen/Kommentare VOR dem Pass (Template-Kompatibilität):
    gesucht wird das erste Paar --- Zeilen im ersten Block der Datei.
    Returns (raw_yaml|None, body_text, parser_name).
    """
    lines = md_text.splitlines()
    starts = [i for i, l in enumerate(lines[:80]) if l.strip() == "---"]
    if len(starts) < 2:
        return None, md_text, "none"
    raw = "\n".join(lines[starts[0] + 1:starts[1]])
    body = "\n".join(lines[starts[1] + 1:])
    data, parser = parse_yaml(raw)
    return data, body, parser


def parse_range(val):
    """'01-06' | '1–25' | [1,25] → (lo, hi) als int oder None."""
    if val is None:
        return None
    if isinstance(val, (list, tuple)) and len(val) == 2:
        try:
            return int(val[0]), int(val[1])
        except (TypeError, ValueError):
            return None
    if isinstance(val, int):
        return val, val
    s = str(val).strip().strip('"\'')
    if s.startswith("[") and s.endswith("]"):  # PyYAML liest "01-02" als int 1 → ggf. Liste
        try:
            parts = [int(x) for x in re.findall(r"-?\d+", s)]
            if len(parts) == 2:
                return parts[0], parts[1]
        except ValueError:
            return None
    m = re.match(r"^(\d+)\s*" + DASH_CLASS + r"\s*(\d+)$", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    m2 = re.fullmatch(r"\d+", s)
    if m2:
        return int(s), int(s)
    return None


def collect_ids(body: str, prefix: str) -> set:
    return {int(m) for m in re.findall(r"\b" + prefix + r"-(\d+)\b", body)}


def find_register(explicit: str | None = None, base: str = ".") -> str | None:
    candidates = []
    if explicit:
        candidates.append(explicit)
    candidates += [
        os.path.join(base, "docs", "audit", "register.md"),
        os.path.join(base, "Audit-Register-Zentral.md"),
        os.path.join(base, "register.md"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def parse_register_ranges(reg_text: str):
    """Liefert [(session_id, prefix, lo, hi)] aus Ledger-Zeilen '| Sxx | … |'.

    Spaltenlayout (SAD-Konvention): Sitzungs-ID | Datum | Thema | Modell |
    E-Bereich | A-Bereich | R-Bereich | Q-Bereich | SAD | Handoff | Gate | Status
    """
    entries = []
    for line in reg_text.splitlines():
        ls = line.strip()
        if not ls.startswith("|"):
            continue
        cells = [c.strip() for c in ls.strip("|").split("|")]
        if len(cells) < 12 or not re.fullmatch(r"S\d+", cells[0]):
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[1]):
            continue  # Kopf-/Hinweiszeile, kein Ledger-Eintrag
        for prefix, idx in (("E", 4), ("A", 5), ("R", 6), ("Q", 7)):
            cell = cells[idx]
            if not re.fullmatch(r"\d{1,4}\s*[\-\u2010-\u2015\u2212]\s*\d{1,4}", cell.strip()):
                continue  # "—" oder Freitext (z. B. Legacy-Hinweis) → kein Bereich
            rng = parse_range(cell)
            if rng:
                entries.append((cells[0], prefix, rng[0], rng[1]))
    return entries


def secret_scan(text: str):
    """Findet unmaskierte Secrets; maskierte (*** / …) werden übersprungen."""
    findings = []
    for pat, label in SECRET_PATTERNS:
        for m in re.finditer(pat, text):
            snippet = m.group(0)
            ctx = text[max(0, m.start() - 5):m.end() + 5]
            if "***" in snippet or "***" in ctx or "…" in snippet:
                continue
            findings.append((label, snippet[:10] + "…(maskiert im Report)"))
    return findings


def usage_shares(agent_usage: dict):
    """Extrahiert die Prozent-Werte (ohne provenance/source/schaetzgrundlage)."""
    skip = {"provenance", "source", "schaetzgrundlage", "estimation_basis", "quelle"}
    return {k: v for k, v in (agent_usage or {}).items()
            if k not in skip and isinstance(v, (int, float)) and not isinstance(v, bool)}


def section_lines(body: str, heading_patterns):
    """Zeilen eines Markdown-Abschnitts (bis zur nächsten ##-Überschrift)."""
    lines = body.splitlines()
    out, active = [], False
    for l in lines:
        if re.match(r"^#{1,3}\s", l):
            active = any(re.search(p, l, re.I) for p in heading_patterns)
            continue
        if active:
            out.append(l)
    return out


def eprint(*a):
    print(*a, file=sys.stderr)
