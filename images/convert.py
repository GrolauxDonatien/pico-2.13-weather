import math

with open('50.pbm', 'rb') as f:
    f.readline()  # Magic number
    f.readline()  # Creator comment
#    f.readline()  # Creator comment
    data = bytearray(f.read())

s = str(data)
bits = []
for i in range(0, len(s)):
    if s[i] == "0":
        bits.append(1)
    elif s[i] == "1":
        bits.append(0)

width = 56  # 50
height = 50
bytes = []


def setbit(x, y):
    idx = (y * 56 + x) // 8
    offset = (y * 56 + x) % 8
    v = 1 << (7-offset)
    bytes[idx] = bytes[idx] | v


for i in range(0, width * height):
    bytes.append(0)

for h in range(0, 50):
    for w in range(0, 50):
        if w + h * 50 < len(bits) and bits[w + h * 50] == 1:
            setbit(w, h)

print(bytearray(bytes))
