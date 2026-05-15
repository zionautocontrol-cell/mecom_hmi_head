import argparse
import shutil
import struct
import zlib
from pathlib import Path

SITES_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = SITES_DIR / "template"


def _fast_gradient_png(path: Path, w: int, h: int, label: str):
    bg_r, bg_g, bg_b = 30, 40, 60
    stripe_h = max(1, h // 10)

    raw = bytearray()
    for y in range(h):
        raw.append(0)
        t = y / h
        r = min(255, int(bg_r + 30 * (1 - t)))
        g = min(255, int(bg_g + 20 * t))
        b = min(255, int(bg_b + 30 * (1 - t)))
        if y % stripe_h < 2:
            g = min(255, g + 15)
            b = min(255, b + 15)
        raw.extend(struct.pack("BBB", r, g, b) * w)

    def _chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), level=1))
    png += _chunk(b"IEND", b"")
    path.write_bytes(png)


def create_site(site_id: str, name: str = ""):
    site_dir = SITES_DIR / site_id
    if site_dir.exists():
        print(f"Error: Site directory already exists: {site_dir}")
        return False

    site_dir.mkdir(parents=True, exist_ok=True)

    if TEMPLATE_DIR.exists():
        for item in TEMPLATE_DIR.iterdir():
            if item.is_file():
                dest = site_dir / item.name
                shutil.copy2(item, dest)
                print(f"  Copied: {item.name}")

    bg = site_dir / "background.png"
    if not bg.exists():
        _fast_gradient_png(bg, 1920, 1080, name or site_id)
        print(f"  Created background: {bg.name} (1920x1080)")

    print(f"\nSite '{site_id}' created at: {site_dir}")
    print(f"Next steps:")
    print(f"  1. Replace {bg} with actual site image")
    print(f"  2. Set SITE_ID='{site_id}' via env MECOM_SITE_ID")
    return True


def main():
    parser = argparse.ArgumentParser(description="Create a new site directory")
    parser.add_argument("site_id", help="Site identifier (e.g. site_a)")
    parser.add_argument("--name", default="", help="Human-readable name")
    args = parser.parse_args()
    create_site(args.site_id, args.name)


if __name__ == "__main__":
    main()
