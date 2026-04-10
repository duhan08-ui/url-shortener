import string

# Base62 변환 (0-9, a-z, A-Z)
CHARS = string.digits + string.ascii_letters

def encode_base62(num: int) -> str:
    if num == 0:
        return CHARS[0]
    arr = []
    base = len(CHARS)
    while num:
        num, rem = divmod(num, base)
        arr.append(CHARS[rem])
    arr.reverse()
    return ''.join(arr)
