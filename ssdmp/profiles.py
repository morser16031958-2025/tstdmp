from typing import Optional

from .constants import SMART_PROFILES


def _detect_smart_profile(model: str, vendor_text: str, vendor_area: bytes) -> Optional[str]:
    model_up = (model or "").upper()
    vendor_up = (vendor_text or "").upper()
    va_hex = vendor_area.hex().lower() if vendor_area else ""

    if any(x in vendor_up for x in ["ERLAET", "TAERLE", "REALTEK", "ELTAER"]):
        return "realtek"
    if any(x in va_hex for x in ["45524c414554", "45524c41"]):
        return "realtek"

    if any(x in va_hex for x in ["sm22", "sm23", "sm26", "sm27"]):
        return "silicon_motion"
    if any(x in vendor_up for x in ["ASATI", "IIS DS", "SATI"]):
        return "silicon_motion"
    if "SM" == model_up[:2] and model_up[2:3].isdigit():
        return "silicon_motion"

    if any(x in va_hex for x in ["phison", "ps225", "ps230", "2251", "2253"]):
        return "phison"
    if "PHISON" in vendor_up:
        return "phison"

    if "SAMSUNG" in model_up or "SAMSUNG" in vendor_up:
        return "samsung"
    if "MZ-" in model_up:
        return "samsung"

    if any(x in model_up for x in ["CRUCIAL", "CT", "MTFD", "MICRON"]):
        return "micron"

    if "KINGSTON" in model_up:
        if any(x in model_up for x in ["SA400", "A400", "SUV400", "SUV500"]):
            return "phison"
        if any(x in model_up for x in ["KC600", "A2000", "NV1", "NV2"]):
            return "silicon_motion"
        if any(x in va_hex for x in ["sm22", "sm23", "sm26"]):
            return "silicon_motion"
        if any(x in va_hex for x in ["phison", "ps225", "2251"]):
            return "phison"
        return None

    if "ADATA" in model_up:
        if any(x in va_hex for x in ["45524c41", "realtek"]):
            return "realtek"
        return "silicon_motion"

    if any(x in model_up for x in ["WDC ", "WD ", "SANDISK", "SAN_DISK", "SDSSD"]):
        return "wd_sandisk"

    if any(x in model_up for x in ["TRANSCEND", "TS128", "TS256", "TS512", "TS1T"]):
        if any(x in va_hex for x in ["45524c41", "realtek"]):
            return "realtek"
        return "silicon_motion"

    if "INTEL" in model_up and "INTEL" in vendor_up:
        return "micron"

    if any(x in model_up for x in ["PATRIOT", "PBT"]):
        return "phison"

    if "GOODRAM" in model_up:
        return "phison"

    if any(x in model_up for x in ["NETAC", "NT-"]):
        return "realtek"

    return None