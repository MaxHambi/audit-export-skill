#!/usr/bin/env python3
"""register_update.py — Schritt 9: Zentral-Register aus dem SAD aktualisieren.

Liest den Sitzungs-Pass eines Audits, hängt eine Ledger-Zeile an und aktualisiert
die „Next"-Schnellzugriffstabelle (nächste freie IDs/Bereiche, kollisionsfrei).

Nutzung:
  python3 register_update.py --sad Audit-Thema-2026-10-04.md [--register docs/audit/register.md]
                             [--handoff Handoff-Thema-2026-10-04.md] [--dry-run] [--force]
Exit: 0 ok · 1 Fehler (z. B. Kollision ohne --force)
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (  # noqa: E402

    extract_passport, find_register, normalize_keys, parse_range,
    parse_register_ranges, read_text,
)

BLOCK = {"E": 25, "A": 25, "R": 25, "Q": 200}


# Windows-Konsolen (cp1252/etc.) koennen Symbole wie ✓⚠✗ nicht kodieren:
# Ausgabe einheitlich auf UTF-8 erzwingen (Agenten- und CI-tauglich).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def fmt_range(prefix, lo, hi):
    width = 3 if prefix == "Q" else 2
    return f"{lo:0{width}d}–{hi:0{width}d}"


def build_row(p, sad_path, handoff_path):
    sid = str(p.get("session_id", "")).strip()
    if not re.fullmatch(r"S\d+", sid):
        raise SystemExit(f"session_id '{sid}' hat nicht das Format S<nn>")
    date = str(p.get("session_date", ""))
    topic = str(p.get("topic", "")).replace("|", "/")[:60]
    part = p.get("participants") or {}
    model = str(part.get("model", "?")).replace("|", "/")
    ranges = p.get("id_ranges") or {}
    cells = [sid, date, topic, model]
    for pre in ("E", "A", "R", "Q"):
        r = parse_range(ranges.get(pre))
        cells.append(fmt_range(pre, *r) if r else "—")
    cells.append(os.path.basename(sad_path))
    cells.append(os.path.basename(handoff_path) if handoff_path else "—")
    gate = (p.get("gate") or {}).get("verdict", "?")
    cells.append(str(gate))
    cells.append(str(p.get("status", "?")))
    return "| " + " | ".join(cells) + " |"


def next_ids(entries):
    """Nächste freie ID + nächster Block je Präfix aus allen Ledger-Bereichen.

    Blöcke schließen direkt an die verbrauchten Bereiche an (E/A/R: 25er-Blöcke,
    Q: 200er-Blöcke) — dadurch kollisionsfrei ohne Ausrichtungslogik.
    Returns {prefix: (next_free_int, block_str, next_free_str)}.
    """
    maxima = {pre: 0 for pre in BLOCK}
    for _sid, pre, _lo, hi in entries:
        if pre in maxima:
            maxima[pre] = max(maxima[pre], hi)
    out = {}
    for pre, mx in maxima.items():
        nf = mx + 1
        start, end = nf, nf + BLOCK[pre] - 1   # Block schließt direkt an (kollisionsfrei)
        out[pre] = (nf, fmt_range(pre, start, end), fmt_id(pre, nf))
    return out


def fmt_id(prefix, n):
    return f"{prefix}-{n:0{3 if prefix == 'Q' else 2}d}"


def next_session_id(text):
    ids = [int(m) for m in re.findall(r"^\|\s*S(\d+)\s*\|", text, re.M)]
    return f"S{max(ids) + 1:02d}" if ids else "S02"


def main():
    ap = argparse.ArgumentParser(
        description="Zentral-Register aus SAD aktualisieren (Ledger + Next-Tabelle)",
        epilog="Exit-Codes: 0 = aktualisiert · 1 = Kollision oder Sitzung bereits vorhanden\n"
               "(dann ID-Bereiche neu ziehen bzw. --force zum Ersetzen).\n"
               "Beispiel: python3 register_update.py --sad docs/audit/Audit-X.md --dry-run",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sad", required=True)
    ap.add_argument("--register")
    ap.add_argument("--handoff")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="bestehende Zeile derselben Sitzung ersetzen")
    a = ap.parse_args()

    if not os.path.isfile(a.sad):
        raise SystemExit(f"SAD nicht gefunden: {a.sad}")
    reg_path = find_register(a.register)
    if not reg_path:
        raise SystemExit("Register nicht gefunden (--register setzen; erwartete Namen: "
                         "docs/audit/register.md, Audit-Register-Zentral.md)")
    reg = read_text(reg_path)
    data, _body, _parser = extract_passport(read_text(a.sad))
    if not data:
        raise SystemExit(f"{a.sad}: kein Sitzungs-Pass gefunden")
    p = normalize_keys(data)

    handoff = a.handoff
    if not handoff:
        guess = re.sub(r"^Audit-", "Handoff-", os.path.basename(a.sad))
        guess_p = os.path.join(os.path.dirname(a.sad) or ".", guess)
        handoff = guess_p if os.path.isfile(guess_p) else None

    entries = parse_register_ranges(reg)
    sid = str(p.get("session_id", ""))
    existing = [e for e in entries if e[0] == sid]
    row = build_row(p, a.sad, handoff)

    # Kollisionsprüfung gegen ALLE anderen Sitzungen
    ranges = {pre: parse_range(v) for pre, v in (p.get("id_ranges") or {}).items()}
    clashes = []
    for osid, opre, olo, ohi in entries:
        if osid == sid:
            continue
        r = ranges.get(opre)
        if r and r[0] <= ohi and olo <= r[1]:
            clashes.append(f"{opre}: {sid}({r[0]}-{r[1]}) vs {osid}({olo}-{ohi})")
    if clashes and not a.force:
        print("KOLLISION(EN) — kein Update:", file=sys.stderr)
        for c in clashes:
            print("  " + c, file=sys.stderr)
        return 1
    if existing and not a.force:
        print(f"{sid} steht bereits im Ledger → --force zum Ersetzen", file=sys.stderr)
        return 1

    lines = reg.splitlines()
    # 1) Ledger-Zeile einfügen/ersetzen
    ledger_idx = [i for i, l in enumerate(lines) if re.match(r"^\|\s*S\d+\s*\|", l)]
    if existing and a.force and ledger_idx:
        for i in ledger_idx:
            if lines[i].split("|")[1].strip() == sid:
                lines[i] = row
                break
        action = f"ersetzt {sid}"
    elif ledger_idx:
        lines.insert(ledger_idx[-1] + 1, row)
        action = f"angehängt {sid}"
    else:
        raise SystemExit("Keine Ledger-Tabelle im Register gefunden (Zeilen '| Sxx | …').")

    # 2) „Next"-Tabelle aktualisieren
    new_text = "\n".join(lines)
    new_entries = parse_register_ranges(new_text)
    nxt = next_ids(new_entries)
    nsid = next_session_id(new_text)
    mapping = {"Sitzung": (nsid, nsid)}
    for pre in ("E", "A", "R", "Q"):
        _nf, block, idstr = nxt[pre]
        mapping[pre] = (idstr, block)

    def fix_next(m):
        label = m.group(1).strip()
        if label in mapping:
            nf, block = mapping[label]
            return f"| {label} | {nf} | {block} |"
        return m.group(0)

    new_text = re.sub(r"^\|\s*(Sitzung|E|A|R|Q)\s*\|.*$", fix_next, new_text, flags=re.M)
    if not new_text.endswith("\n"):
        new_text += "\n"

    if a.dry_run:
        print("DRY-RUN — neue Ledger-Zeile:")
        print("  " + row)
        print("DRY-RUN — neue Next-Werte:")
        for k, v in mapping.items():
            print(f"  {k}: {v}")
        return 0
    with open(reg_path, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    print(f"Register {reg_path}: {action}; Next aktualisiert "
          f"(E:{nxt['E'][2]} A:{nxt['A'][2]} R:{nxt['R'][2]} Q:{nxt['Q'][2]})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
