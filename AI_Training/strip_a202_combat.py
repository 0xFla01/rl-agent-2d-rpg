"""Sterge toate enemies + traps din A2/02.tscn, pastreaza levere + decoratii."""
import re, shutil, os

TSCN = r"C:\LICENTA FINALA\Fla18\Licenta\Levels\Area02\02.tscn"
BACKUP = TSCN + ".bak_pre_strip"

# Regex pentru node-urile care trebuie sterse
PATTERN = re.compile(r'^\[node name="(Enemy_|SpikeTrap|Saw\d|ArrowTrap|FireTrap)')

if not os.path.exists(BACKUP):
    shutil.copy(TSCN, BACKUP)
    print(f"Backup creat: {BACKUP}")

with open(TSCN, "r", encoding="utf-8") as f:
    lines = f.readlines()

out = []
skip = False
removed_count = 0
removed_names = []
i = 0
while i < len(lines):
    line = lines[i]
    if PATTERN.match(line):
        # Extrage numele pentru log
        m = re.search(r'name="([^"]+)"', line)
        if m:
            removed_names.append(m.group(1))
        removed_count += 1
        skip = True
        i += 1
        # Sare peste liniile de proprietate (nu incep cu [ si nu sunt goale)
        while i < len(lines):
            nxt = lines[i]
            if nxt.startswith('['):
                break
            if nxt.strip() == "":
                # Linie goala dupa proprietati — sarim si pe ea
                i += 1
                break
            i += 1
        skip = False
    else:
        out.append(line)
        i += 1

with open(TSCN, "w", encoding="utf-8") as f:
    f.writelines(out)

print(f"Sters {removed_count} entitati din A2/02:")
for n in removed_names[:10]:
    print(f"  - {n}")
if len(removed_names) > 10:
    print(f"  ... si inca {len(removed_names) - 10}")
print(f"\nFisier salvat. Restore: copy '{BACKUP}' peste '{TSCN}'")
