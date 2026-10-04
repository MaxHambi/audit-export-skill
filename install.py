#!/usr/bin/env python3
"""install.py — Universeller Installer für die Audit/Workflow-Skills.

Erfasst zu Beginn, welche Agenten/Model-CLIs installiert sind, schlägt daraus die
passenden Installationsorte vor (plus freie Projekt-/Eigenordner-Wahl) und installiert
die Skills nach Mehrfachauswahl (Leertaste = wählen, Enter = installieren).

Nur Python-Stdlib (3.9+). Läuft auf Linux, macOS, Windows.

Flags:
  --help            Hilfe (zweisprachig)
  --doctor          Diagnose: Tools, Skill-Integrität, Python-Module, Schreibrechte
  --dry-run         alles anzeigen, nichts schreiben
  --update          alle früher installierten Ziele aktualisieren (via Manifest)
  --debug           ausführliche Logs
  --lang de|en      Sprache (Default: automatisch aus Locale)
  --all             alle vorgeschlagenen Ziele ohne Rückfrage
  --non-interactive keine TUI; Ziele per --targets Liste angeben
  --ci              CI-Modus: --non-interactive --dry-run, exit 1 bei Defekt
  --version         Version anzeigen

Beispiele:
  python3 install.py
  python3 install.py --doctor
  python3 install.py --dry-run --all
  python3 install.py --non-interactive --targets claude-code,opencode-project,/pfad/zum/repo
  python3 install.py --update
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile

VERSION = "0.9.0"
MANIFEST = ".audit-skills-install.json"
HERE = os.path.dirname(os.path.abspath(__file__))
DEBUG = False


def resolve_skills_dir():
    """skills/ finden — funktioniert aus dem Repo, per Symlink und aus site-packages."""
    cands = [os.path.join(HERE, "skills"),
             os.path.join(HERE, "audit_export_skill", "skills"),
             os.path.join(os.path.dirname(HERE), "skills")]
    for c in cands:
        if os.path.isdir(c) and any(
                os.path.isfile(os.path.join(c, n, "SKILL.md"))
                for n in os.listdir(c) if os.path.isdir(os.path.join(c, n))):
            return os.path.realpath(c)
    return cands[0]


SKILLS_DIR = resolve_skills_dir()

# ─────────────────────────────────────────────────────────────────────────────
# Sprachauswahl
# ─────────────────────────────────────────────────────────────────────────────
L = {
    "de": {
        "title": "Audit-/Workflow-Skills Installer",
        "detecting": "Erfasse installierte Agenten, Modell-CLIs und Projektordner …",
        "no_tui": "Kein interaktives Terminal erkannt → nummerierte Auswahl.",
        "select_title": "Installationsziele auswählen",
        "select_hint": "Leertaste = Ziel wählen/abwählen · Enter = installieren · "
                       "a = alle · n = keine · q = abbrechen",
        "numbered_hint": "Nummern mit Leerzeichen/Komma getrennt eingeben "
                         "(z. B. '1 3 5'), 'all' für alle, 'none' zum Abbrechen:",
        "custom_dir": "Eigener Projekt-/Zielordner hinzufügen",
        "custom_prompt": "Pfad zum Zielordner (leer = überspringen): ",
        "custom_bad": "Ordner existiert nicht und konnte nicht angelegt werden: {}",
        "custom_exists": "Ziel ist bereits in der Liste: {}",
        "ci_integration": "CI-/Hook-Integration (audit-gate) in Git-Projekte installieren",
        "plan": "Installationsplan",
        "dry_hint": "DRY-RUN — es wird nichts geschrieben.",
        "install_to": "→ {}",
        "skills": "   Skills: {}",
        "ci_yes": "   + .github/workflows/audit-gate.yml",
        "hook_yes": "   + .git/hooks/pre-push (nur bei vorhandenem .git, warn-only)",
        "confirm": "Ausführen? [J/n] ",
        "aborted": "Abgebrochen. Es wurde nichts geschrieben.",
        "done": "Fertig. {} Ziel(e) installiert.",
        "manifest_written": "   Manifest: {}",
        "copied": "   kopiert: {}",
        "skipped_exists": "   übersprungen (existiert, --update zum Aktualisieren): {}",
        "updated": "Aktualisiert: {} Ziel(e).",
        "no_targets": "Keine Ziele ausgewählt.",
        "no_manifest": "Keine früheren Installationen gefunden (kein {} in bekannten Zielen).",
        "doctor_title": "Diagnose",
        "doctor_env": "1) Umgebung",
        "doctor_skills": "2) Skill-Integrität (Quelle: {})",
        "doctor_targets": "3) Installationsziele & Schreibrechte",
        "doctor_modules": "4) Optionale Python-Module",
        "doctor_summary": "Ergebnis",
        "detected": "erkannt",
        "not_detected": "nicht erkannt",
        "writable": "beschreibbar",
        "not_writable": "NICHT beschreibbar",
        "installed": "installiert (Manifest {})",
        "not_installed": "nicht installiert",
        "help_extra": "Universeller Installer: erfasst installierte Agenten/CLIs, "
                      "bietet passende Ziele + eigene Projektordner zur Mehrfachauswahl "
                      "an und kopiert die Skills samt CI-/Hook-Vorlagen.",
    },
    "en": {
        "title": "Audit/Workflow skills installer",
        "detecting": "Detecting installed agents, model CLIs and project folders …",
        "no_tui": "No interactive terminal detected → numbered selection.",
        "select_title": "Select installation targets",
        "select_hint": "Space = toggle target · Enter = install · a = all · n = none · q = quit",
        "numbered_hint": "Enter numbers separated by space/comma (e.g. '1 3 5'), "
                         "'all' for all, 'none' to cancel:",
        "custom_dir": "Add a custom project/target folder",
        "custom_prompt": "Path to target folder (empty = skip): ",
        "custom_bad": "Folder does not exist and could not be created: {}",
        "custom_exists": "Target already in list: {}",
        "ci_integration": "Install CI/hook integration (audit-gate) into Git projects",
        "plan": "Installation plan",
        "dry_hint": "DRY-RUN — nothing will be written.",
        "install_to": "→ {}",
        "skills": "   skills: {}",
        "ci_yes": "   + .github/workflows/audit-gate.yml",
        "hook_yes": "   + .git/hooks/pre-push (only if .git exists, warn-only)",
        "confirm": "Proceed? [Y/n] ",
        "aborted": "Aborted. Nothing was written.",
        "done": "Done. Installed to {} target(s).",
        "manifest_written": "   manifest: {}",
        "copied": "   copied: {}",
        "skipped_exists": "   skipped (exists, use --update): {}",
        "updated": "Updated {} target(s).",
        "no_targets": "No targets selected.",
        "no_manifest": "No previous installations found (no {} in known targets).",
        "doctor_title": "Diagnosis",
        "doctor_env": "1) Environment",
        "doctor_skills": "2) Skill integrity (source: {})",
        "doctor_targets": "3) Targets & write permissions",
        "doctor_modules": "4) Optional Python modules",
        "doctor_summary": "Result",
        "detected": "detected",
        "not_detected": "not detected",
        "writable": "writable",
        "not_writable": "NOT writable",
        "installed": "installed (manifest {})",
        "not_installed": "not installed",
        "help_extra": "Universal installer: detects installed agents/CLIs, offers matching "
                      "targets plus custom project folders as a multi-select, and copies the "
                      "skills including CI/hook templates.",
    },
}
LANG = "de"


def t(key, *a):
    s = L[LANG].get(key) or L["en"].get(key) or key
    return s.format(*a) if a else s


def detect_lang():
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var) or ""
        if v:
            return "de" if v.lower().startswith("de") else "en"
    return "en"


def log(*a):
    if DEBUG:
        print("[debug]", *a, file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# Ziel-Definitionen
# ─────────────────────────────────────────────────────────────────────────────
def home():
    """$HOME — überschreibbar für Tests/Sandboxes (z. B. --set-home)."""
    return os.environ.get("AUDIT_SKILLS_HOME") or os.path.expanduser("~")


def xdg_config():
    v = os.environ.get("XDG_CONFIG_HOME")
    return v if v else os.path.join(home(), ".config")


def project_root(start=None):
    """Nächstgelegenes Git-/Projekt-Root aufwärts suchen (max. 6 Ebenen)."""
    d = os.path.abspath(start or os.getcwd())
    for _ in range(6):
        if os.path.isdir(os.path.join(d, ".git")) or os.path.isdir(os.path.join(d, "docs")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None


def has(cmd):
    return shutil.which(cmd) is not None


def dir_exists(p):
    return bool(p) and os.path.isdir(p)


def skill_subdir(base_rel):
    """base_rel z. B. '.claude/skills' → Skills landen in <home>/<base_rel>/<skill>."""
    def build(_ctx):
        return os.path.join(home(), *base_rel.split("/"))
    return build


# id, label, detect(), skills_dir(ctx), supports_ci, note_key
TARGETS = [
    {
        "id": "claude-code",
        "label": "Claude Code / Claude Desktop (user-global)",
        "detect": lambda: dir_exists(os.path.join(home(), ".claude")) or has("claude"),
        "dir": skill_subdir(".claude/skills"),
        "ci": False,
    },
    {
        "id": "opencode-project",
        "label": "opencode — Projekt (./.opencode/skills)",
        "detect": lambda: bool(project_root()) and (
            dir_exists(os.path.join(project_root(), ".opencode")) or has("opencode")),
        "dir": lambda ctx: os.path.join(project_root(), ".opencode", "skills"),
        "ci": True,
    },
    {
        "id": "opencode-global",
        "label": "opencode — user-global (~/.config/opencode/skills)",
        "detect": lambda: has("opencode") or dir_exists(os.path.join(xdg_config(), "opencode")),
        "dir": lambda ctx: os.path.join(xdg_config(), "opencode", "skills"),
        "ci": False,
    },
    {
        "id": "hermes",
        "label": "Hermes Agent (Nous Research) — ~/.hermes/skills",
        "detect": lambda: dir_exists(os.path.join(home(), ".hermes")) or has("hermes"),
        "dir": skill_subdir(".hermes/skills"),
        "ci": False,
    },
    {
        "id": "codex",
        "label": "OpenAI Codex CLI — ~/.codex/skills",
        "detect": lambda: has("codex") or dir_exists(os.path.join(home(), ".codex")),
        "dir": skill_subdir(".codex/skills"),
        "ci": False,
    },
    {
        "id": "goose",
        "label": "goose — ~/.config/goose/skills",
        "detect": lambda: has("goose") or dir_exists(os.path.join(xdg_config(), "goose")),
        "dir": lambda ctx: os.path.join(xdg_config(), "goose", "skills"),
        "ci": False,
    },
    {
        "id": "zcode",
        "label": "ZCode (z.ai) — Projekt (./.zcode/skills)",
        "detect": lambda: bool(project_root()) and (
            dir_exists(os.path.join(project_root(), ".zcode")) or has("zcode")),
        "dir": lambda ctx: os.path.join(project_root(), ".zcode", "skills"),
        "ci": True,
    },
    {
        "id": "agentskills-generic",
        "label": "Generisch: ./skills (jeder Agent, der skills/ im Projekt liest)",
        "detect": lambda: bool(project_root()),
        "dir": lambda ctx: os.path.join(project_root(), "skills"),
        "ci": True,
    },
    {
        "id": "repo-vendor",
        "label": "Repo-Vendor: <dieses Paket>/skills (für CI im eigenen Repo)",
        "detect": lambda: os.path.isdir(SKILLS_DIR),
        "dir": lambda ctx: SKILLS_DIR,
        "ci": False,
        "readonly_hint": True,
    },
]


def list_skills():
    d = SKILLS_DIR
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        if os.path.isfile(os.path.join(d, name, "SKILL.md")):
            out.append(name)
    return out


def skill_meta(skill_dir):
    p = os.path.join(skill_dir, "SKILL.md")
    try:
        s = open(p, encoding="utf-8").read()
    except OSError:
        return {}
    m = re.match(r"^---\n(.*?)\n---\n", s, re.S)
    meta = {"raw_ok": bool(m)}
    if m:
        fm = m.group(1)
        for key in ("name", "description", "license", "compatibility"):
            mm = re.search(rf"^{key}:\s*(.*)$", fm, re.M)
            meta[key] = mm.group(1).strip() if mm else None
        mv = re.search(r'^\s*version:\s*"?([\w\.\-]+)"?', fm, re.M)
        meta["version"] = mv.group(1) if mv else "?"
    return meta


def referenced_files_ok(skill_dir):
    """Alle in SKILL.md referenzierten scripts/references/assets müssen existieren."""
    p = os.path.join(skill_dir, "SKILL.md")
    s = open(p, encoding="utf-8").read()
    refs = set(re.findall(r"`((?:references|scripts|assets)/[\w\.\-]+)`", s))
    missing = [r for r in sorted(refs) if not os.path.isfile(os.path.join(skill_dir, r))]
    return sorted(refs), missing


# ─────────────────────────────────────────────────────────────────────────────
# Auswahl-UI
# ─────────────────────────────────────────────────────────────────────────────
def build_choices(detected_only=False):
    pr = project_root()
    ctx = {"project_root": pr}
    items = []
    for tg in TARGETS:
        try:
            det = bool(tg["detect"]())
        except Exception as exc:
            log("detect-Fehler", tg["id"], exc)
            det = False
        try:
            d = tg["dir"](ctx)
        except Exception as exc:
            log("dir-Fehler", tg["id"], exc)
            d = None
        items.append({"id": tg["id"], "label": tg["label"], "detected": det, "dir": d,
                      "ci": tg.get("ci", False), "readonly": tg.get("readonly_hint", False)})
    if not detected_only:
        items.append({"id": "__custom__", "label": t("custom_dir"), "detected": True,
                      "dir": None, "ci": True, "custom": True})
        items.append({"id": "__ci__", "label": t("ci_integration"), "detected": True,
                      "dir": None, "ci": True, "toggle": True})
    return items


def numbered_select(items, preselect):
    print()
    print(t("select_title"))
    for i, it in enumerate(items, 1):
        if it.get("custom") or it.get("toggle"):
            mark = "[x]" if preselect.get(it["id"]) else "[ ]"
            print(f"  {i:2}. {mark} {it['label']}")
            continue
        tag = []
        tag.append(t("detected") if it["detected"] else t("not_detected"))
        if it["dir"]:
            tag.append(it["dir"])
        mark = "*" if it["id"] in preselect else " "
        print(f"  {i:2}. [{mark}] {it['label']}  ({', '.join(tag)})")
    print()
    try:
        raw = input(t("numbered_hint") + " ")
    except EOFError:
        return None
    raw = raw.strip().lower()
    if raw in {"none", "q", "quit", "abbruch", "abbrechen", ""}:
        return None
    if raw in {"all", "a", "alle"}:
        return {it["id"] for it in items if not it.get("toggle")} | ({"__ci__"} if any(
            it.get("ci") and it.get("dir") for it in items) else set())
    chosen = set()
    for tok in re.split(r"[\s,;]+", raw):
        if tok.isdigit() and 1 <= int(tok) <= len(items):
            chosen.add(items[int(tok) - 1]["id"])
    return chosen


def curses_select(items, preselect):
    import curses

    def run(stdscr):
        curses.use_default_colors()
        curses.curs_set(0)
        stdscr.clear()
        sel = set(preselect)
        cur = 0
        customs = []
        while True:
            h, w = stdscr.getmaxyx()
            stdscr.erase()
            title = t("select_title")
            stdscr.addnstr(0, 0, title, w - 1, curses.A_BOLD)
            stdscr.addnstr(1, 0, t("select_hint"), w - 1, curses.A_DIM)
            for idx, it in enumerate(items):
                y = 3 + idx
                if y >= h - 2:
                    break
                if it.get("custom") or it.get("toggle"):
                    box = "[x]" if sel.get(it["id"]) else "[ ]"
                else:
                    box = "[X]" if it["id"] in sel else "[ ]"
                det = "" if (it.get("custom") or it.get("toggle")) else (
                    "  · " + (t("detected") if it["detected"] else t("not_detected")))
                path = "" if not it.get("dir") else "  · " + it["dir"]
                line = f"{idx + 1:2}. {box} {it['label']}{det}"
                if path and len(line) + len(path) < w:
                    line += path
                attr = curses.A_REVERSE if idx == cur else curses.A_NORMAL
                stdscr.addnstr(y, 0, line, w - 1, attr)
            stdscr.addnstr(h - 1, 0, f"Enter = installieren · {len(sel)} gewählt", w - 1,
                           curses.A_DIM)
            stdscr.refresh()
            ch = stdscr.getch()
            if ch in (curses.KEY_UP, ord("k")):
                cur = max(0, cur - 1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                cur = min(len(items) - 1, cur + 1)
            elif ch == ord(" "):
                it = items[cur]
                if it.get("custom"):
                    curses.echo()
                    curses.curs_set(1)
                    stdscr.addnstr(h - 1, 0, t("custom_prompt"), w - 1)
                    stdscr.clrtoeol()
                    stdscr.refresh()
                    try:
                        path = stdscr.getstr(60).decode("utf-8", "replace").strip()
                    except KeyboardInterrupt:
                        path = ""
                    curses.noecho()
                    curses.curs_set(0)
                    if path:
                        path = os.path.abspath(os.path.expanduser(path))
                        cid = "custom:" + path
                        if any(c["id"] == cid for c in customs):
                            pass
                        else:
                            customs.append({"id": cid, "label": f"Custom: {path}",
                                            "detected": True, "dir": path, "ci": True,
                                            "custom_path": path})
                            items.insert(len(items) - 2, customs[-1])
                            sel.add(cid)
                elif it.get("toggle"):
                    sel[it["id"]] = not sel.get(it["id"])
                else:
                    if it["id"] in sel:
                        sel.discard(it["id"])
                    else:
                        sel.add(it["id"])
            elif ch in (ord("a"),):
                for it in items:
                    if not it.get("toggle"):
                        sel.add(it["id"])
                sel["__ci__"] = True
            elif ch in (ord("n"),):
                sel.clear()
            elif ch in (ord("q"), 27):
                return None
            elif ch in (10, 13, curses.KEY_ENTER):
                return sel, customs

    try:
        return curses.wrapper(run)
    except Exception as exc:
        log("curses-Fehler → Fallback", exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Installation
# ─────────────────────────────────────────────────────────────────────────────
def copy_skill(src, dst_dir, dry, force=False):
    os.makedirs(dst_dir, exist_ok=True) if not dry else None
    n = 0
    if os.path.exists(dst_dir) and not force:
        existing = os.listdir(dst_dir)
        if existing:
            log("Ziel existiert, überschreibe (update-Modus):", dst_dir)
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        rel = os.path.relpath(root, src)
        tgt_root = dst_dir if rel == "." else os.path.join(dst_dir, rel)
        if not dry:
            os.makedirs(tgt_root, exist_ok=True)
        for f in files:
            if f.endswith(".pyc"):
                continue
            s = os.path.join(root, f)
            d = os.path.join(tgt_root, f)
            if not dry:
                shutil.copy2(s, d)
                if f == "pre-push" or os.path.basename(root) == "hooks":
                    try:
                        os.chmod(d, 0o755)
                    except OSError:
                        pass
            n += 1
    return n


def install_ci(project_dir, dry):
    """audit-gate Workflow + pre-push Hook-Vorlage in ein Git-Projekt legen."""
    done = []
    wf_dir = os.path.join(project_dir, ".github", "workflows")
    wf = os.path.join(wf_dir, "audit-gate.yml")
    src_wf = os.path.join(SKILLS_DIR, "session-audit", "assets", "audit-gate.workflow.yml")
    if os.path.isfile(src_wf):
        if not dry:
            os.makedirs(wf_dir, exist_ok=True)
            shutil.copy2(src_wf, wf)
        done.append(os.path.relpath(wf, project_dir))
    hook_src = os.path.join(SKILLS_DIR, "session-audit", "assets", "hooks", "pre-push")
    git_dir = os.path.join(project_dir, ".git")
    if os.path.isfile(hook_src) and os.path.isdir(git_dir):
        hook = os.path.join(git_dir, "hooks", "pre-push")
        if not os.path.exists(hook):
            if not dry:
                os.makedirs(os.path.dirname(hook), exist_ok=True)
                shutil.copy2(hook_src, hook)
                try:
                    os.chmod(hook, 0o755)
                except OSError:
                    pass
            done.append(".git/hooks/pre-push (warn-only; scharf: git config hooks.auditGate true)")
        else:
            done.append(".git/hooks/pre-push existiert bereits → unverändert")
    audit_dir = os.path.join(project_dir, "docs", "audit")
    reg_src = os.path.join(SKILLS_DIR, "session-audit", "assets", "register-template.md")
    reg_dst = os.path.join(audit_dir, "register.md")
    if os.path.isfile(reg_src) and not os.path.exists(reg_dst):
        if not dry:
            os.makedirs(audit_dir, exist_ok=True)
            shutil.copy2(reg_src, reg_dst)
        done.append("docs/audit/register.md (Template)")
    return done


def write_manifest(dst_root, skills, dry):
    doc = {
        "installer_version": VERSION,
        "installed_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": HERE,
        "skills": {s: (skill_meta(os.path.join(SKILLS_DIR, s)).get("version", "?"))
                   for s in skills},
        "host": {"os": platform.system(), "python": sys.version.split()[0]},
    }
    p = os.path.join(dst_root, MANIFEST)
    if not dry:
        os.makedirs(dst_root, exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    return p


def do_install(targets, skills, with_ci, dry):
    count = 0
    print()
    for tg in targets:
        d = tg["dir"]
        if not d:
            continue
        print(t("install_to", d))
        print(t("skills", ", ".join(skills)))
        for s in skills:
            src = os.path.join(SKILLS_DIR, s)
            dst = os.path.join(d, s)
            if os.path.exists(dst) and not dry:
                n = copy_skill(src, dst, dry, force=True)
                print(t("copied", f"{s}/ ({n} Dateien, aktualisiert)"))
            else:
                n = copy_skill(src, dst, dry)
                print(t("copied", f"{s}/ ({n} Dateien)"))
        if with_ci and tg.get("ci") and not tg.get("readonly"):
            base = d
            for _ in range(4):
                if os.path.isdir(os.path.join(base, ".git")) or \
                   os.path.isdir(os.path.join(base, ".github")):
                    break
                nb = os.path.dirname(base)
                if nb == base:
                    break
                base = nb
            if os.path.isdir(os.path.join(base, ".git")) or base == project_root():
                for x in install_ci(base, dry):
                    print(t("ci_yes") if x.endswith("audit-gate.yml") else "   + " + x)
        mp = write_manifest(d, skills, dry)
        print(t("manifest_written", mp))
        count += 1
    print()
    print(t("done", count))
    if dry:
        print(t("dry_hint"))
    return count


def find_previous_installs():
    found = []
    cands = []
    for tg in TARGETS:
        try:
            d = tg["dir"]({"project_root": project_root()})
        except Exception as exc:
            log("find_previous_installs: Ziel unlesbar", tg.get("id"), exc)
            continue
        if d:
            cands.append(d)
    pr = project_root()
    cwd = os.getcwd()
    for base in dict.fromkeys([pr, cwd, project_root(cwd)]):
        if base:
            cands += [base, os.path.join(base, "skills"),
                      os.path.join(base, ".opencode", "skills")]
    for d in dict.fromkeys(cands):
        mp = os.path.join(d, MANIFEST)
        if os.path.isfile(mp):
            try:
                found.append((d, json.load(open(mp, encoding="utf-8"))))
            except Exception as exc:
                log("Manifest unreadable", mp, exc)
    return found


# ─────────────────────────────────────────────────────────────────────────────
# Doctor
# ─────────────────────────────────────────────────────────────────────────────
def doctor():
    ok = True
    print(f"\n{t('doctor_title')} — {t('title')} v{VERSION}\n")
    print(t("doctor_env"))
    print(f"  Python      : {sys.version.split()[0]} "
          f"({'OK' if sys.version_info >= (3, 9) else 'ZU ALT (>=3.9 nötig)'})")
    if sys.version_info < (3, 9):
        ok = False
    print(f"  OS          : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"  Quelle      : {SKILLS_DIR}")
    print(f"  Installer   : {os.path.abspath(__file__)}")
    print(f"  Sprache     : {LANG}")
    try:
        import curses  # noqa: F401
        print("  curses      : verfügbar (interaktive Mehrfachauswahl)")
    except ImportError:
        print("  curses      : nicht verfügbar → nummerierte Auswahl (voll funktional)")
    print(f"  Terminal    : {'interaktiv' if sys.stdin.isatty() else 'nicht interaktiv'}")

    print()
    print(t("doctor_skills", SKILLS_DIR))
    skills = list_skills()
    if not skills:
        print("  ✗ keine Skills gefunden — Paket unvollständig")
        ok = False
    for s in skills:
        d = os.path.join(SKILLS_DIR, s)
        meta = skill_meta(d)
        refs, missing = referenced_files_ok(d)
        prob = []
        if not meta.get("raw_ok"):
            prob.append("Frontmatter fehlt/unparsbar")
        else:
            nm = meta.get("name")
            if nm != s:
                prob.append(f"name '{nm}' ≠ Verzeichnis '{s}'")
            if not nm or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", nm or ""):
                prob.append("name ungültig (a-z, 0-9, Bindestrich)")
            desc = meta.get("description") or ""
            if not (1 <= len(desc) <= 1024):
                prob.append(f"description-Länge {len(desc)} (1–1024)")
            comp = meta.get("compatibility") or ""
            if len(comp) > 500:
                prob.append(f"compatibility {len(comp)} > 500")
        body_lines = 0
        try:
            txt = open(os.path.join(d, "SKILL.md"), encoding="utf-8").read()
            body_lines = txt.split("---\n", 2)[-1].count("\n") + 1
        except OSError:
            prob.append("SKILL.md nicht lesbar")
        if body_lines > 500:
            prob.append(f"Body {body_lines} > 500 Zeilen")
        if missing:
            prob.append(f"referenzierte Dateien fehlen: {missing}")
        status = "✓" if not prob else "✗"
        if prob:
            ok = False
        print(f"  {status} {s:18} v{meta.get('version', '?'):8} refs={len(refs)} "
              f"body={body_lines}Z" + (f"  → {'; '.join(prob)}" if prob else ""))

    print()
    print(t("doctor_targets"))
    items = build_choices(detected_only=True)
    any_writable = False
    for it in items:
        d = it["dir"]
        if not d:
            continue
        exists = os.path.isdir(d)
        testdir = d
        for _ in range(4):
            if os.path.isdir(testdir):
                break
            testdir = os.path.dirname(testdir)
        w = os.access(testdir or home(), os.W_OK)
        mp = os.path.join(d, MANIFEST)
        inst = t("installed", "vorhanden") if os.path.isfile(mp) else t("not_installed")
        mark = "✓" if (exists or w) else "✗"
        if exists or w:
            any_writable = True
        print(f"  {mark} {it['label']}")
        print(f"      {d} · {t('detected') if it['detected'] else t('not_detected')} · "
              f"{t('writable') if w else t('not_writable')} · {inst}")
    if not any_writable:
        ok = False

    print()
    print(t("doctor_modules"))
    for mod, why in (("yaml", "YAML-Parsing in validate_audit.py (sonst Fallback-Parser)"),
                     ("jsonschema", "Schema-Validierung der session.json-Sidecars")):
        try:
            __import__(mod)
            print(f"  ✓ {mod:12} verfügbar — {why}")
        except ImportError:
            print(f"  ⚠ {mod:12} fehlt — {why}")
    print("  Hinweis: beide optional; Installation: pip install pyyaml jsonschema")

    print()
    prev = find_previous_installs()
    if prev:
        print("Frühere Installationen:")
        for d, mf in prev:
            print(f"  · {d} (v{mf.get('installer_version', '?')}, "
                  f"{mf.get('installed_at', '?')}, Skills: {list(mf.get('skills', {}))})")
    print()
    print(f"{t('doctor_summary')}: {'ALLES OK' if ok else 'PROBLEME gefunden (siehe ✗)'}")
    return 0 if ok else 1


# ─────────────────────────────────────────────────────────────────────────────
# Update
# ─────────────────────────────────────────────────────────────────────────────
def do_update(dry):
    prev = find_previous_installs()
    if not prev:
        print(t("no_manifest", MANIFEST))
        return 1
    skills = list_skills()
    n = 0
    for d, mf in prev:
        old = set(mf.get("skills", {}))
        want = old | set(skills)
        print(t("install_to", d))
        for s in sorted(want):
            src = os.path.join(SKILLS_DIR, s)
            if not os.path.isdir(src):
                print(f"   ⚠ {s} in Quelle nicht mehr vorhanden → übersprungen")
                continue
            copy_skill(src, os.path.join(d, s), dry, force=True)
            print(t("copied", f"{s}/ (aktualisiert)"))
        mp = write_manifest(d, sorted(want), dry)
        print(t("manifest_written", mp))
        n += 1
    print()
    print(t("updated", n))
    if dry:
        print(t("dry_hint"))
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="install.py",
        description=(L["de"]["help_extra"] + "\n\n" + L["en"]["help_extra"]),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doctor", action="store_true", help="Diagnose ausführen / run diagnosis")
    ap.add_argument("--dry-run", action="store_true", help="nur anzeigen / preview only")
    ap.add_argument("--update", action="store_true",
                    help="frühere Installationen aktualisieren / update previous installs")
    ap.add_argument("--debug", action="store_true", help="ausführliche Logs / verbose logs")
    ap.add_argument("--lang", choices=["de", "en"], help="Sprache / language")
    ap.add_argument("--all", action="store_true",
                    help="alle erkannten Ziele ohne Rückfrage / all detected targets")
    ap.add_argument("--non-interactive", action="store_true",
                    help="keine TUI, nur --targets / no TUI, use --targets")
    ap.add_argument("--targets", help="Kommagetrennte Ziel-IDs oder Pfade / comma separated ids or paths")
    ap.add_argument("--no-ci", action="store_true", help="CI-/Hook-Integration überspringen")
    ap.add_argument("--version", action="store_true", help="Version ausgeben / print version")
    ap.add_argument("--set-home", metavar="PFAD",
                    help="Ziel-Home-Verzeichnis überschreiben (Test/Sandbox) / override home")
    a = ap.parse_args(argv)

    global DEBUG, LANG
    DEBUG = a.debug
    LANG = a.lang or detect_lang()
    if a.set_home:
        os.environ["AUDIT_SKILLS_HOME"] = os.path.abspath(os.path.expanduser(a.set_home))
    if a.version:
        print(VERSION)
        return 0
    log("Argumente:", vars(a))
    print(f"{t('title')} v{VERSION} — {SKILLS_DIR}")
    if a.doctor:
        return doctor()
    if a.update:
        return do_update(a.dry_run)

    skills = list_skills()
    if not skills:
        print("FEHLER: keine Skills unter skills/ gefunden — Paket unvollständig.",
              file=sys.stderr)
        return 1
    print(t("detecting"))
    items = build_choices()
    detected = [it for it in items if it.get("detected") and it.get("dir")
                and not it.get("readonly") and not it.get("custom") and not it.get("toggle")]
    log("erkannt:", [it["id"] for it in detected])

    if a.targets:
        ids = [x.strip() for x in a.targets.split(",") if x.strip()]
        resolved = []
        for tid in ids:
            if tid.startswith("/") or tid.startswith("./") or tid.startswith("~") or \
               (len(tid) > 1 and tid[1] == ":"):
                p = os.path.abspath(os.path.expanduser(tid))
                resolved.append({"id": "custom:" + p, "label": f"Custom: {p}", "dir": p,
                                 "ci": True})
            else:
                m = [it for it in items if it["id"] == tid]
                if not m:
                    print(f"Unbekanntes Ziel: {tid}", file=sys.stderr)
                    print("Verfügbar: " + ", ".join(
                        [it["id"] for it in items if it.get("dir") or it.get("custom")]),
                        file=sys.stderr)
                    return 1
                resolved.append(m[0])
        targets = [r for r in resolved if r.get("dir")]
        with_ci = not a.no_ci
        show_plan(targets, skills, with_ci)
        if not a.dry_run and not assume_yes(a):
            return 0
        do_install(targets, skills, with_ci, a.dry_run)
        return 0

    if a.all:
        targets = detected
        with_ci = not a.no_ci
        show_plan(targets, skills, with_ci)
        if not a.dry_run and not assume_yes(a):
            return 0
        do_install(targets, skills, with_ci, a.dry_run)
        return 0

    preselect = {it["id"] for it in detected}
    result = None
    interactive = sys.stdin.isatty() and sys.stdout.isatty() and not a.non_interactive
    if interactive:
        try:
            import curses  # noqa: F401
            result = curses_select(list(items), dict.fromkeys(preselect, True))
        except ImportError:
            result = False
        if result is False:
            print(t("no_tui"))
            result = None
    if result is None:
        if interactive:
            print(t("no_tui"))
        sel = numbered_select(items, dict.fromkeys(preselect, True))
        if sel is None:
            print(t("aborted"))
            return 0
        result = (sel, [])

    sel, customs = result
    if customs:
        items = items + [c for c in customs if c not in items]
    chosen = [it for it in items if it["id"] in sel and it.get("dir")]
    # Custom-Pfade ohne dir (nummerierte Auswahl) erfragen
    if "__custom__" in sel:
        try:
            p = input(t("custom_prompt"))
        except EOFError:
            p = ""
        if p.strip():
            p = os.path.abspath(os.path.expanduser(p.strip()))
            try:
                if not a.dry_run:
                    os.makedirs(p, exist_ok=True)
            except OSError:
                print(t("custom_bad", p), file=sys.stderr)
                return 1
            chosen.append({"id": "custom:" + p, "label": f"Custom: {p}", "dir": p, "ci": True})
    with_ci = bool(sel.get("__ci__")) and not a.no_ci
    chosen = [c for c in chosen if not c.get("readonly")]
    if not chosen:
        print(t("no_targets"))
        return 0
    show_plan(chosen, skills, with_ci)
    if not a.dry_run and interactive and not assume_yes(a):
        return 0
    do_install(chosen, skills, with_ci, a.dry_run)
    return 0


def show_plan(targets, skills, with_ci):
    print()
    print(t("plan") + ":")
    for tg in targets:
        print(t("install_to", tg["dir"]))
        print(t("skills", ", ".join(skills)))
        if with_ci and tg.get("ci"):
            print(t("ci_yes"))
            print(t("hook_yes"))


def assume_yes(a):
    if getattr(a, "non_interactive", False) or not sys.stdin.isatty():
        return True
    try:
        r = input(t("confirm")).strip().lower()
    except EOFError:
        return False
    return r in {"", "j", "y", "ja", "yes"}


if __name__ == "__main__":
    sys.exit(main())
