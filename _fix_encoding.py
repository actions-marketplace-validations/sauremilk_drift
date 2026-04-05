# fmt: off
"""Fix ALL mojibake throughout drift_community_flywheel.py."""
import pathlib

fp = pathlib.Path("examples/agent-framework/drift_community_flywheel.py")
data = fp.read_bytes()

# Remove BOM if present
if data.startswith(b"\xef\xbb\xbf"):
    data = data[3:]
    print("Removed BOM")

text = data.decode("utf-8")

# Text-level mojibake fixes (order: longer sequences first)
text_fixes = [
    # Multi-char mojibake from double/triple encoding
    # Em-dash: U+2014 -> UTF-8 E2 80 94 -> CP1252 -> â€" (but " = U+0022)
    ("\u00e2\u20ac\u0022", "--"),     # em dash mojibake: â€"
    # Down arrow: -> â†"
    ("\u00e2\u2020\u0022", "->"),     # down arrow mojibake: â†"
    # Ellipsis: U+2026 -> â€¦ (U+00E2 U+20AC U+00A6)
    ("\u00e2\u20ac\u00a6", "..."),    # ellipsis mojibake
    # Sharp-s: U+00DF -> CP1252 garbled
    ("\u00c3\u0178", "ss"),           # ß double-encoded (MaÃŸnahmen)
    # Checkmark: U+2713 -> â + œ (U+0153) + next char
    ("\u00e2\u0153", "[OK]"),         # checkmark mojibake
    # Cross mark: U+274C -> â + U+009D + Œ (U+0152)
    ("\u00e2\u009d\u0152", "[X]"),    # cross mark mojibake
    # Play button: U+25B6 -> â (already partially fixed to â--¶)
    # Will handle â--¶ as text below
    # German chars (single UTF-8)
    ("\u00e4", "ae"),
    ("\u00f6", "oe"),
    ("\u00fc", "ue"),
    ("\u00c4", "Ae"),
    ("\u00d6", "Oe"),
    ("\u00dc", "Ue"),
    ("\u00df", "ss"),
    # Other unicode
    ("\u2013", "--"),
    ("\u2014", "--"),
    ("\u2018", "'"),
    ("\u2019", "'"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u2022", " * "),
    ("\u2026", "..."),
    ("\u2192", "->"),
    ("\u2193", "->"),
    ("\u2265", ">="),
    ("\u2264", "<="),
    ("\u2713", "[OK]"),
    ("\u25b6", ">"),
    ("\u00b6", ""),               # pilcrow sign (orphan from play button)
    ("\ufeff", ""),
    # Checkmarks/crosses
    ("\u00e2\u0153\u0093", "[OK] "),
    ("\u00e2\u0153\u0085", "[OK] "),
    ("\u00e2\u0152\u0178", "[X] "),
    # Single German chars (valid UTF-8 but convert to ASCII)
    ("\u00e4", "ae"),
    ("\u00f6", "oe"),
    ("\u00fc", "ue"),
    ("\u00c4", "Ae"),
    ("\u00d6", "Oe"),
    ("\u00dc", "Ue"),
    ("\u00df", "ss"),
    # Unicode special chars
    ("\u2013", "--"),
    ("\u2014", "--"),
    ("\u2018", "'"),
    ("\u2019", "'"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u2022", " * "),
    ("\u2026", "..."),
    ("\u2192", "->"),
    ("\u2193", "->"),
    ("\u2191", "->"),
    ("\u2265", ">="),
    ("\u2264", "<="),
    ("\u2713", "[OK]"),
    ("\u2714", "[OK]"),
    ("\u2717", "[X]"),
    ("\u2718", "[X]"),
    ("\u25b6", ">"),
    ("\ufeff", ""),
]

for old, new in text_fixes:
    if old in text:
        count = text.count(old)
        text = text.replace(old, new)
        print(f"  Fixed {count}x: U+{ord(old[0]):04X}... -> {new!r}")

# Fix specific broken words
word_fixes = [
    ("fuuer", "fuer"),
    # Right arrow mojibake: â (U+00E2) + † (U+2020) + ' -> becomes "-> "
    ("\u00e2\u2020'", "-> "),
    # Play button remnant: â-- (after previous pilcrow/dash fixes)
    ("\u00e2--", ">"),
]
for old, new in word_fixes:
    if old in text:
        text = text.replace(old, new)
        print(f"  Fixed word: {old!r} -> {new!r}")

# Final check
non_ascii = []
for i, c in enumerate(text):
    if ord(c) > 127:
        non_ascii.append((i, c))

if non_ascii:
    print(f"\n  WARNING: {len(non_ascii)} remaining non-ASCII chars:")
    for idx, c in non_ascii[:20]:
        linenum = text[:idx].count("\n") + 1
        line_start = text.rfind("\n", 0, idx) + 1
        line_end = text.find("\n", idx)
        if line_end == -1:
            line_end = len(text)
        context_line = text[line_start:line_end].strip()[:100]
        print(f"    L{linenum} U+{ord(c):04X}: {context_line}")
else:
    print("\n  All non-ASCII chars fixed!")

fp.write_text(text, encoding="utf-8", newline="")
print(f"\nDone. File size: {len(text)} chars")
