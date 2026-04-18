from typing import List, Tuple, Optional

def _get_controller_candidates(model: str, vendor_text: str, vendor_area: bytes) -> List[Tuple[str, int]]:
    """Helper for controller detection logic"""
    model_lower = model.lower()
    vendor_lower = (vendor_text or "").lower()
    va_hex = vendor_area.hex().lower() if vendor_area else ""
    va_decoded = vendor_area.decode("ascii", errors="replace").strip().lower() if vendor_area else ""
    
    ctrl_candidates = []
    
    # Realtek exact models
    if "rtl5735" in va_hex or "rts5735" in model_lower or "rtl5735" in model_lower:
        ctrl_candidates.append(("Realtek RTS5735", 10))
    if "rtl9210" in va_hex or "rtl9210" in model_lower:
        ctrl_candidates.append(("Realtek RTL9210", 9))
    if "rtl9220" in va_hex or "rtl9220" in model_lower:
        ctrl_candidates.append(("Realtek RTL9220", 9))
    if "rtl930" in va_hex or "rtl930" in model_lower:
        ctrl_candidates.append(("Realtek RTL930", 8))
    if "rtl9120" in va_hex or "rtl9120" in model_lower:
        ctrl_candidates.append(("Realtek RTL9120", 8))
    if "erlaet" in va_decoded or "45524c414554" in va_hex:
        ctrl_candidates.append(("Realtek RTL66xx (reversed)", 8))
    if "45524c41" in va_hex:
        ctrl_candidates.append(("Realtek RTL66xx", 7))
    if "rtl" in model_lower or "realtek" in vendor_lower or "rts" in vendor_lower:
        ctrl_candidates.append(("Realtek", 3))

    # Silicon Motion exact models
    if "sm2258" in va_hex or "sm2258" in model_lower:
        ctrl_candidates.append(("Silicon Motion SM2258", 9))
    if "sm2259" in va_hex or "sm2259" in model_lower:
        ctrl_candidates.append(("Silicon Motion SM2259", 9))
    if "sm2257" in va_hex or "sm2257" in model_lower:
        ctrl_candidates.append(("Silicon Motion SM2257", 9))
    if "sm2256" in va_hex or "sm2256" in model_lower:
        ctrl_candidates.append(("Silicon Motion SM2256", 9))
    if "sm2263" in va_hex or "sm2263" in model_lower:
        ctrl_candidates.append(("Silicon Motion SM2263", 9))
    if "sm27" in va_hex:
        ctrl_candidates.append(("Silicon Motion SM27xx", 8))
    if "sm26" in va_hex:
        ctrl_candidates.append(("Silicon Motion SM26xx", 8))
    if "sm23" in va_hex:
        ctrl_candidates.append(("Silicon Motion SM23xx", 7))
    if "sm22" in va_hex:
        ctrl_candidates.append(("Silicon Motion SM22xx", 6))
    if "asati" in va_decoded or "4153415449" in va_hex:
        ctrl_candidates.append(("Silicon Motion SM2xxx (ASATI)", 7))

    # Phison exact models
    if "ps2251" in va_hex or "ps2251" in model_lower:
        ctrl_candidates.append(("Phison PS2251-xx (U17)", 9))
    if "ps2253" in va_hex or "ps2253" in model_lower:
        ctrl_candidates.append(("Phison PS2253-xx (U18)", 9))
    if "ps2257" in va_hex or "ps2257" in model_lower:
        ctrl_candidates.append(("Phison PS2257-xx", 9))
    if "ps2303" in va_hex or "ps2303" in model_lower:
        ctrl_candidates.append(("Phison PS2303 (S11)", 9))
    if "ps3110" in va_hex or "ps3110" in model_lower:
        ctrl_candidates.append(("Phison PS3110-S10", 9))
    if "ps3111" in va_hex or "ps3111" in model_lower:
        ctrl_candidates.append(("Phison PS3111-S11", 9))
    if "phison" in vendor_lower:
        ctrl_candidates.append(("Phison", 4))

    # Marvell
    if "88ss" in model_lower or "88ss" in va_hex:
        ctrl_candidates.append(("Marvell 88SSxxx", 7))
    if "marvell" in vendor_lower:
        ctrl_candidates.append(("Marvell", 4))

    # Samsung
    if "samsung" in vendor_lower or "sec" in vendor_lower:
        ctrl_candidates.append(("Samsung", 4))
    if "mz-" in model_lower:
        ctrl_candidates.append(("Samsung (MZ-xxx)", 5))

    # WD/SanDisk
    if "wd" in vendor_lower or "sandisk" in vendor_lower or "san_disk" in vendor_lower:
        ctrl_candidates.append(("WD/SanDisk", 4))
    
    # Walram / Generic Budget SSDs
    if "walram" in model_lower or "walram" in vendor_lower:
        ctrl_candidates.append(("Walram (likely SMI or Maxio)", 5))
    if "28gb" in model_lower or "240gb" in model_lower or "120gb" in model_lower:
        if not ctrl_candidates:
            ctrl_candidates.append(("Generic Budget SSD", 2))

    # Intel
    if "intel" in vendor_lower:
        ctrl_candidates.append(("Intel (innostor/isilon)", 4))
    if "innostor" in va_hex or "isilon" in va_hex:
        ctrl_candidates.append(("Innostor/Isilon", 5))

    # Kingston
    if "kingston" in vendor_lower:
        ctrl_candidates.append(("Kingston", 3))

    # Maxio
    if "maxio" in va_hex or "mai" in va_hex[:10]:
        ctrl_candidates.append(("Maxio (MAS160x)", 4))

    ctrl_candidates.sort(key=lambda x: x[1], reverse=True)
    return ctrl_candidates

def _get_nand_info_by_fid(fid: Optional[Tuple[int, ...]], manu: Optional[str]) -> List[str]:
    """Helper for NAND detection logic"""
    if not fid or not manu:
        return []
    
    nand_info = []
    # SanDisk/WD
    if manu == "SanDisk/WD":
        if fid[1] >= 0x3e:
            nand_info.append("SanDisk BiCS5 TLC 16k")
        elif fid[1] >= 0x2c:
            nand_info.append("SanDisk BiCS4 TLC")
    # Intel
    elif manu == "Intel":
        if fid[1] >= 0xaa:
            nand_info.append("Intel 96L 3D NAND")
        elif fid[1] >= 0x2:
            nand_info.append("Intel 64L 3D NAND")
    # Micron
    elif manu == "Micron":
        if fid[1] >= 0x32:
            nand_info.append("Micron 176L 3D NAND")
        elif fid[1] >= 0x26:
            nand_info.append("Micron 96L 3D NAND")
    # Samsung
    elif manu == "Samsung":
        if fid[1] >= 0x3c:
            nand_info.append("Samsung 136L V-NAND")
        elif fid[1] >= 0x32:
            nand_info.append("Samsung 92L V-NAND")
    # Hynix
    elif manu == "Hynix":
        if fid[1] >= 0x32:
            nand_info.append("Hynix 176L 3D NAND")
        elif fid[1] >= 0x26:
            nand_info.append("Hynix 96L 3D NAND")
    # Toshiba/Kioxia
    elif manu == "Toshiba/Kioxia":
        if fid[1] >= 0x76:
            nand_info.append("Toshiba BiCS5 112L")
        elif fid[1] >= 0x32:
            nand_info.append("Toshiba BiCS4 96L")
    
    return nand_info
