import re


def safe_name(s):
    s = s.strip().replace(" ", "_")
    s = re.sub(r"[^\w一-鿿\-]", "", s)
    return s[:40]
