import os
import re
from typing import Dict, List, Optional

from .constants import NAND_MANUFACTURER_IDS


def _parse_ini(path: str) -> Dict[str, Dict[str, str]]:
    cur = None
    out: Dict[str, Dict[str, str]] = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(("#", ";")):
                continue
            if line.startswith("[") and line.endswith("]"):
                cur = line[1:-1].strip()
                out.setdefault(cur, {})
                continue
            if "=" in line and cur:
                k, v = line.split("=", 1)
                out[cur][k.strip()] = v.strip()
    return out


def _parse_int(s: Optional[str]) -> Optional[int]:
    if s is None:
        return None
    t = str(s).strip()
    if not t:
        return None
    try:
        if t.lower().startswith("0x"):
            return int(t, 16)
        return int(t)
    except ValueError:
        return None


def _find_nand_support_list(folder: str) -> Optional[str]:
    candidates = []
    for name in os.listdir(folder):
        if name.lower().startswith("nand_support_list") and name.lower().endswith(".ini"):
            candidates.append(os.path.join(folder, name))
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def _find_nand_by_vendor_num(nand_list_path: str, flash_vendor_num: int) -> List[str]:
    needle = f"0x{flash_vendor_num:08x}".lower()
    matches = []
    with open(nand_list_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith(("#", ";")):
                continue
            if "Flash" not in line or "=" not in line:
                continue
            if needle in line.lower():
                matches.append(line)
    return matches


def _score_nand_line(line: str, blocks: Optional[int], pages: Optional[int], cap_gb: Optional[int]) -> int:
    s = 0
    normalized = re.sub(r"\s+", "", line)
    if blocks is not None and f";{blocks};" in normalized:
        s += 2
    if pages is not None and f";{pages};" in normalized:
        s += 2
    if cap_gb is not None and f"{cap_gb}GB" in normalized:
        s += 1
    return s


def _extract_flash_ids_from_nand_line(line: str) -> List[tuple]:
    result = []
    parts = line.replace(" ", "").split(";")
    for part in parts:
        part = part.strip().replace(",", "")
        if len(part) >= 12 and all(c in "0123456789ABCDEFabcdef" for c in part):
            try:
                if len(part) == 12:
                    vals = tuple(int(part[i:i+2], 16) for i in (0, 2, 4, 6, 8, 10))
                elif len(part) == 14:
                    vals = tuple(int(part[i:i+2], 16) for i in (0, 2, 4, 6, 8, 10, 12))
                else:
                    continue
                if vals[0] in NAND_MANUFACTURER_IDS:
                    result.append(vals)
            except ValueError:
                continue
    return result