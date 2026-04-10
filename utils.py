import string

BASE62_CHARS = string.ascii_lowercase + string.ascii_uppercase + string.digits

def encode_base62(n: int) -> str:
    if n == 0: return BASE62_CHARS[0]
    result = []
    while n > 0:
        n, remainder = divmod(n, 62)
        result.append(BASE62_CHARS[remainder])
    return "".join(reversed(result))