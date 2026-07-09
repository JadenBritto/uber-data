"""
fix_unicode.py — patches all scripts/*.py to:
1. Replace non-cp1252-safe unicode chars with ASCII equivalents
2. Inject sys.stdout.reconfigure(encoding='utf-8') where missing
"""
import os, glob

SCRIPTS = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "scripts", "*.py")))

# Map of unicode chars to ASCII replacements (applied everywhere in file)
REPLACEMENTS = [
    ("\u2192", "->"),      # →
    ("\u2190", "<-"),      # ←
    ("\u2026", "..."),     # …
    ("\u2713", "[OK]"),    # ✓
    ("\u2705", "[DONE]"),  # ✅
    ("\u26a0", "[WARN]"),  # ⚠
    ("\u27a4", ">>"),      # ➤
    ("\u25cf", "o"),       # ●
    ("\u25b6", ">"),       # ▶
    ("\u2500", "-"),       # ─  (box-drawing)
    ("\u254c", "-"),       # ╌
    ("\u2014", "--"),      # —
    ("\u2015", "--"),      # ―
    ("\u2764", "<3"),      # ❤
    ("\u2bc8", ">"),       # ⯈
    ("\u2bc1", "<"),       # ⯁
    ("\u2b24", "o"),       # ⬤
    ("\u23f0", "[CLOCK]"), # ⏰
    ("\u23f3", "[TIME]"),  # ⏳
    ("\u1f6d1", "[STOP]"), # 🛑
    ("\u1f680", "[ROCKET]"), # 🚀
    ("\u1f4ca", "[CHART]"), # 📊
    ("\u1f5fa", "[MAP]"),  # 🗺
    ("\u1f916", "[BOT]"),  # 🤖
    ("\u1f697", "[CAR]"),  # 🚗
]

RECONFIGURE_SNIPPET = (
    "import sys\n"
    "if hasattr(sys.stdout, 'reconfigure'):\n"
    "    sys.stdout.reconfigure(encoding='utf-8')\n"
    "\n"
)

for path in SCRIPTS:
    with open(path, "r", encoding="utf-8") as f:
        original = f.read()

    patched = original

    # Apply all replacements
    for uni, asc in REPLACEMENTS:
        patched = patched.replace(uni, asc)

    # Inject reconfigure if missing
    if "sys.stdout.reconfigure" not in patched:
        # Insert right after the top-level warnings.filterwarnings line
        marker = 'warnings.filterwarnings("ignore")'
        if marker in patched:
            patched = patched.replace(
                marker,
                RECONFIGURE_SNIPPET + marker,
                1
            )
        else:
            # Fallback: insert after first import block (find first blank line after imports)
            lines = patched.splitlines(keepends=True)
            insert_at = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_at = i + 1
            lines.insert(insert_at, "\n" + RECONFIGURE_SNIPPET)
            patched = "".join(lines)

    if patched != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(patched)
        print(f"  Patched: {os.path.basename(path)}")
    else:
        print(f"  Clean:   {os.path.basename(path)}")

print("\nDone — all scripts are cp1252-safe.")
