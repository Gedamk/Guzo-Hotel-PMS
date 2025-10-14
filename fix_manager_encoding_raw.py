import os

path = "dashboard/pages/manager_center.py"
if not os.path.exists(path):
    print("‚ùå File not found:", path)
    raise SystemExit()

print(f"Ì∑π Cleaning raw bytes in {path} ...")

with open(path, "rb") as f:
    raw = f.read()

# remove any byte that cannot appear in valid UTF-8
clean_bytes = bytearray()
i = 0
while i < len(raw):
    b = raw[i]
    if b < 0x80:
        clean_bytes.append(b)
        i += 1
    elif 0xC2 <= b <= 0xF4:      # valid UTF-8 leading byte
        # try to copy continuation bytes safely
        seq_len = 2 if b < 0xE0 else 3 if b < 0xF0 else 4
        seg = raw[i:i+seq_len]
        if len(seg) == seq_len and all(0x80 <= x <= 0xBF for x in seg[1:]):
            clean_bytes.extend(seg)
            i += seq_len
        else:
            i += 1  # skip invalid lead
    else:
        i += 1      # skip invalid byte like 0xED

# write back clean file
with open(path, "wb") as f:
    f.write(clean_bytes)

print("‚úÖ All invalid bytes removed. Saved clean UTF-8 file.")
