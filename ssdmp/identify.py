from typing import Optional, Tuple

from .constants import NAND_MANUFACTURER_IDS


def _extract_flash_id_from_identify(identify_data: bytes) -> Tuple[Optional[Tuple[int, ...]], Optional[str]]:
    if not identify_data or len(identify_data) < 512:
        return None, None
    vendor_area = identify_data[256:512]
    known_ids = set(NAND_MANUFACTURER_IDS.keys())
    for i in range(len(vendor_area) - 8):
        b = vendor_area[i]
        if b not in known_ids:
            continue
        candidate = vendor_area[i : i + 8]
        nonzero = sum(1 for x in candidate[:6] if x != 0)
        if nonzero < 4:
            continue
        before_printable = (i > 0 and 0x20 <= vendor_area[i - 1] <= 0x7E)
        first4_printable = sum(1 for x in candidate[:4] if 0x20 <= x <= 0x7E)
        if before_printable and first4_printable >= 3:
            continue
        return tuple(candidate), NAND_MANUFACTURER_IDS[b]
    return None, None


def _decode_string(data: bytes) -> str:
    result = bytearray()
    for i in range(0, len(data) - 1, 2):
        for b in (data[i + 1], data[i]):
            if 32 <= b <= 126:
                result.append(b)
    return bytes(result).decode("ascii", errors="replace").strip()


def _decode_string_plain_ascii(data: bytes) -> str:
    cleaned = bytearray(b for b in data if b != 0)
    result = bytearray()
    for b in cleaned:
        if 0x20 <= b <= 126:
            result.append(b)
        else:
            break
    return bytes(result).decode("ascii", errors="replace").strip()


def _decode_identify(identify_data: bytes) -> dict:
    if not identify_data or len(identify_data) < 512:
        return {}
    d = identify_data

    def w(word_offset: int, word_count: int = 1) -> int:
        byte_off = word_offset * 2
        if word_count == 1:
            return int.from_bytes(d[byte_off : byte_off + 2], "little")
        return int.from_bytes(d[byte_off : byte_off + word_count * 2], "little")

    cylinders = w(1)
    heads = w(3)
    sectors_per_track = w(6)
    chs_size = cylinders * heads * sectors_per_track * 512

    result = {
        "model": _decode_string(d[27*2:47*2]),
        "serial": _decode_string(d[10*2:20*2]),
        "firmware": _decode_string(d[23*2:27*2]),
        "config": w(0),
        "cylinders": cylinders,
        "heads": heads,
        "sectors_per_track": sectors_per_track,
        "total_sectors_lba28": w(60, 2),
        "total_sectors_lba48": w(100, 4),
        "capabilities": w(49),
        "capabilities_ext": w(83),
        "optimum_transfer_size": w(88),
        "mult_sector_count": w(47) & 0xFF,
        "dma_modes": w(62),
        "pio_modes": w(63),
        "ata_version_major": w(80),
        "ata_version_minor": w(81),
        "smart_support": (w(82) >> 0) & 1,
        "smart_enabled": (w(85) >> 0) & 1,
        "vendor_text": _decode_string(d[256:512]),
        "vendor_area": d[256:512],
        "flash_id": None,
        "nand_manufacturer": None,
    }

    fid, manu = _extract_flash_id_from_identify(identify_data)
    result["flash_id"] = fid
    result["nand_manufacturer"] = manu

    return result