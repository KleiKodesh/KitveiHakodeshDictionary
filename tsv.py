"""Shared TSV codec for the source files.

One row per line, tab-separated, UTF-8, LF line ends, first line = header.
Escapes inside a field: backslash -> \\\\, tab -> \\t, newline -> \\n, CR -> \\r.
A SQL NULL is written as \\N (a literal backslash-N text becomes \\\\N, so it never clashes).
"""

_ENC = {"\\": "\\\\", "\t": "\\t", "\n": "\\n", "\r": "\\r"}
_DEC = {"\\": "\\", "t": "\t", "n": "\n", "r": "\r"}


def encode(value):
    if value is None:
        return "\\N"
    if isinstance(value, int):
        return str(value)
    return "".join(_ENC.get(ch, ch) for ch in str(value))


def decode(field):
    if field == "\\N":
        return None
    if "\\" not in field:
        return field
    out, i = [], 0
    while i < len(field):
        ch = field[i]
        if ch == "\\" and i + 1 < len(field):
            out.append(_DEC[field[i + 1]])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def write(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(header) + "\n")
        for row in rows:
            f.write("\t".join(encode(v) for v in row) + "\n")


def read(path):
    """Yields dicts keyed by the header."""
    with open(path, encoding="utf-8", newline="\n") as f:
        header = f.readline().rstrip("\n").split("\t")
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            yield dict(zip(header, (decode(x) for x in line.split("\t"))))
