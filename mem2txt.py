"""Convert a Hioki LR8400 binary memory file (MEMDATA.MEM) to the CSV-style
text export produced by the logger (memdata.txt).

Usage:  python mem2txt.py [MEMDATA.MEM] [output.txt]

File layout (as observed):
  * A series of 0x200-byte header blocks, each starting with an ASCII tag
    ("HW", "HWC1", "HS", "HE-LR8400", ...). Fields are NUL-padded ASCII
    strings at fixed offsets within each block.
  * One "HWC1" block per channel holding channel number, conversion factor,
    offset, unit, mode and range.
  * After the header, sample data: big-endian signed 16-bit integers,
    one per channel per sample, interleaved by sample.
"""
import sys
import numpy as np

BLOCK = 0x200

MODE_NAMES = {
    "VOLT": "Voltage",
    "TEMP": "Temperature",
    "HUMID": "Humidity",
    "RESIST": "Resistance",
}


def field(block, offset, length=12):
    return block[offset:offset + length].split(b"\0", 1)[0].decode("ascii", "replace")


def parse_interval(text):
    """'100ms' -> 0.1, '1s' -> 1.0, '1min' -> 60.0"""
    for suffix, scale in (("ms", 1e-3), ("min", 60.0), ("h", 3600.0), ("s", 1.0)):
        if text.endswith(suffix):
            return float(text[: -len(suffix)]) * scale
    raise ValueError(f"Unknown sampling interval {text!r}")


def read_mem(path):
    data = open(path, "rb").read()

    hw = data[0:BLOCK]
    info = {
        "version": field(hw, 0x24),
        "samples": int(field(hw, 0x48)),
        "date": field(hw, 0x54),
        "time": field(hw, 0x60),
        "interval": parse_interval(field(hw, 0x90)),
        "title": field(hw, 0x15C, 0x50),
    }

    # Walk the header blocks until the first one without a tag starting 'H'.
    channels = []
    offset = 0
    while data[offset:offset + 1] == b"H":
        block = data[offset:offset + BLOCK]
        if field(block, 0) == "HWC1":
            unit, ch = field(block, 0x3C).split("-")
            scaling = field(block, 0xD8)
            raw_factor = float(field(block, 0x90, 0x18))
            raw_offset = float(field(block, 0xA8, 0x18))
            factor = float(field(block, 0xE4, 0x18))
            offs = float(field(block, 0xFC, 0x18))
            channels.append({
                "unit": int(unit),
                "ch": int(ch),
                "mode": field(block, 0x120),
                "range": field(block, 0x12C),
                "eng_unit": field(block, 0x114),
                "scaling": scaling,
                "factor": factor,
                "offset": offs,
                "ratio": factor / raw_factor if scaling == "ON" else 1.0,
                "ratio_offset": offs - raw_offset if scaling == "ON" else 0.0,
            })
        offset += BLOCK
    data_start = offset

    n_ch = len(channels)
    n = info["samples"]
    raw = np.frombuffer(data, dtype=">i2", count=n * n_ch, offset=data_start)
    raw = raw.reshape(n, n_ch).astype(np.float64)
    factors = np.array([c["factor"] for c in channels])
    offsets = np.array([c["offset"] for c in channels])
    values = raw * factors + offsets

    return info, channels, values


def write_txt(path, info, channels, values):
    def row(label, items, fmt='"{}"'):
        return ",".join([f'"{label}"'] + [fmt.format(i) for i in items]) + ",\r\n"

    labels = [f"A{c['unit']:2d}-{c['ch']:2d}" for c in channels]
    lines = [
        f'"File name","MEMDATA.CSV","{info["version"]}"\r\n',
        f'"Title comment","{info["title"]}"\r\n',
        f'"Trigger Time","\'{info["date"]} {info["time"]}"\r\n',
        row("Ch", labels),
        row("Mode", [MODE_NAMES.get(c["mode"], c["mode"]) for c in channels]),
        row("Range", [c["range"] for c in channels]),
        row("Comment", ["" for _ in channels]),
        row("Scaling", [c["scaling"].capitalize() for c in channels]),
        row("Ratio", [f"{c['ratio']: .5E}" for c in channels]),
        row("Offset", [f"{c['ratio_offset']: .5E}" for c in channels]),
        row("Time", [f"{c['unit']}-{c['ch']}[{c['eng_unit']}]" for c in channels] + ["Event"]),
    ]

    n = len(values)
    times = np.arange(n) * info["interval"]
    table = np.column_stack([times, values, np.zeros(n)])
    fmt = "% .9E," + "% .5E," * len(channels) + "%d,"

    with open(path, "w", newline="") as f:
        f.writelines(lines)
        np.savetxt(f, table, fmt=fmt, delimiter="", newline="\r\n")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "MEMDATA.MEM"
    dst = sys.argv[2] if len(sys.argv) > 2 else "memdata_converted.txt"
    info, channels, values = read_mem(src)
    write_txt(dst, info, channels, values)
    print(f"Wrote {len(values)} samples x {len(channels)} channels to {dst}")


if __name__ == "__main__":
    main()
