from typing import Dict, List, Optional, Tuple

from .constants import SMART_ATTRIBUTES, SMART_PROFILES


def _parse_smart_thresholds(data: bytes) -> Dict[int, int]:
    if not data or len(data) < 362:
        return {}
    thresholds = {}
    for i in range(30):
        offset = 2 + i * 12
        attr_id = data[offset]
        if attr_id == 0:
            continue
        thresholds[attr_id] = data[offset + 1]
    return thresholds


def _parse_smart_attributes(data: bytes) -> List[dict]:
    if not data or len(data) < 362:
        return []
    attrs = []
    for i in range(30):
        offset = 2 + i * 12
        attr_id = data[offset]
        if attr_id == 0:
            continue
        flags = int.from_bytes(data[offset + 1 : offset + 3], "little")
        current = data[offset + 3]
        worst = data[offset + 4]
        raw = int.from_bytes(data[offset + 5 : offset + 11], "little")
        attrs.append({
            "id": attr_id,
            "flags": flags,
            "current": current,
            "worst": worst,
            "raw": raw,
            "pre_fail": bool(flags & 0x01),
        })
    return attrs


def _get_smart_raw(attrs: List[dict], attr_id: int) -> Optional[int]:
    for a in attrs:
        if a["id"] == attr_id:
            return a["raw"]
    return None


def _evaluate_health(attrs: List[dict], thresholds: Optional[Dict[int, int]] = None,
                     profile: Optional[str] = None) -> Tuple[str, List[str]]:
    if not attrs:
        return "Unknown", ["SMART data not available"]

    status = "Good"
    reasons = []

    if thresholds:
        for a in attrs:
            thr = thresholds.get(a["id"], 0)
            if thr == 0:
                continue
            name, _ = SMART_ATTRIBUTES.get(a["id"], (f"Attr {a['id']}", "raw"))
            if a["current"] > 0 and a["current"] <= thr:
                status = "Bad"
                reasons.append(f"{name}: current={a['current']} <= threshold={thr} — FAILED")
            elif a["worst"] > 0 and a["worst"] <= thr:
                if status == "Good":
                    status = "Caution"
                reasons.append(f"{name}: worst={a['worst']} <= threshold={thr} — was below threshold")

    reallocated = _get_smart_raw(attrs, 5)
    pending = _get_smart_raw(attrs, 197)
    uncorrectable = _get_smart_raw(attrs, 198)
    life_left = _get_smart_raw(attrs, 231)
    crc_errors = _get_smart_raw(attrs, 199)
    temp_raw = _get_smart_raw(attrs, 194) or _get_smart_raw(attrs, 190)

    # Attr 169: "Remaining Life %" on most controllers, but "Bad Block Count" on Phison
    if profile != "phison":
        life_left_169 = _get_smart_raw(attrs, 169)
    else:
        life_left_169 = None

    # Attr 232: Available Reserve Space (Phison, Realtek)
    reserve_space = _get_smart_raw(attrs, 232)

    if reallocated is not None and reallocated > 0:
        if reallocated > 100:
            status = "Bad"
            reasons.append(f"Reallocated Sectors: {reallocated} (Critical)")
        else:
            if status == "Good": status = "Caution"
            reasons.append(f"Reallocated Sectors: {reallocated}")

    if pending is not None and pending > 0:
        if status != "Bad": status = "Caution"
        reasons.append(f"Pending Sectors: {pending}")

    if uncorrectable is not None and uncorrectable > 0:
        if status != "Bad": status = "Caution"
        reasons.append(f"Uncorrectable Sectors: {uncorrectable}")

    if crc_errors is not None and crc_errors > 50:
        if status == "Good": status = "Caution"
        reasons.append(f"UDMA CRC Errors: {crc_errors} (Check cable/connection)")

    if temp_raw is not None:
        temp = temp_raw & 0xFF
        if temp > 70:
            status = "Bad"
            reasons.append(f"Temperature: {temp}C (Critical Overheating)")
        elif temp > 60:
            if status == "Good": status = "Caution"
            reasons.append(f"Temperature: {temp}C (High)")

    life = life_left if life_left is not None else life_left_169
    if life is not None:
        if life == 0:
            status = "Bad"
            reasons.append("SSD Life Left: 0% (Wear out)")
        elif life <= 10:
            if status == "Good": status = "Caution"
            reasons.append(f"SSD Life Left: {life}%")

    if reserve_space is not None and profile in ("phison", "realtek"):
        if reserve_space == 0:
            status = "Bad"
            reasons.append("Available Reserve Space: 0%")
        elif reserve_space <= 10:
            if status == "Good":
                status = "Caution"
            reasons.append(f"Available Reserve Space: {reserve_space}%")

    if not thresholds:
        for a in attrs:
            if a["pre_fail"] and a["current"] <= 1 and a["current"] > 0:
                status = "Bad"
                reasons.append(f"Attr {a['id']} pre-fail threshold reached (current={a['current']})")

    if not reasons:
        reasons.append("All attributes within normal range")

    return status, reasons


def _format_smart_raw(attr_id: int, raw: int, fmt_override: Optional[str] = None) -> str:
    _, fmt = SMART_ATTRIBUTES.get(attr_id, (f"Unknown ({attr_id})", "raw"))
    if fmt_override:
        fmt = fmt_override
    if fmt == "temp":
        return f"{raw & 0xFF} C"
    if fmt == "temp_minmax":
        b = raw.to_bytes(6, "little")
        cur = b[0]
        mn = b[2] if b[2] != 0 and b[2] < 100 else None
        mx = b[4] if b[4] != 0 and b[4] < 100 else None
        s = f"{cur} C"
        if mn is not None and mx is not None:
            s += f" (Min={mn}, Max={mx})"
        return s
    if fmt == "percent":
        return f"{raw}%"
    if fmt == "percent_inv":
        return f"{100 - raw}% used" if raw <= 100 else f"{raw}"
    if fmt == "lba":
        gb = raw * 512 / (1024**3)
        if gb > 1:
            return f"{gb:.1f} GB"
        return f"{raw:,}"
    if fmt == "lba_32mb":
        gb = raw * 32 / 1024
        if gb > 1:
            return f"{gb:.1f} GB"
        return f"{raw:,} x32MB"
    if fmt == "gib":
        return f"{raw:,} GB"
    return f"{raw:,}"


def _print_smart_table(attrs: List[dict], thresholds: Optional[Dict[int, int]] = None, profile: Optional[str] = None):
    prof = SMART_PROFILES.get(profile, {}) if profile else {}
    thr_hdr = "Thr" if thresholds else ""
    print(f"  {'ID':>3}  {'Name':<35} {'Cur':>4} {'Wst':>4} {thr_hdr:>4}  {'Raw':>16}  {'Flags'}")
    print(f"  {'---':>3}  {'-'*35} {'---':>4} {'---':>4} {'-'*4:>4}  {'-'*16}  {'-----'}")
    for a in attrs:
        if a["id"] in prof:
            name, fmt = prof[a["id"]]
        else:
            name, fmt = SMART_ATTRIBUTES.get(a["id"], (f"Vendor ({a['id']})", "raw"))
        raw_str = _format_smart_raw(a["id"], a["raw"], fmt_override=fmt)
        pf = "PF" if a["pre_fail"] else "OL"
        thr_val = ""
        if thresholds:
            t = thresholds.get(a["id"], 0)
            thr_val = f"{t:>4}" if t > 0 else "   -"
        status = ""
        if thresholds and a["id"] in thresholds:
            t = thresholds[a["id"]]
            if t > 0 and a["current"] > 0 and a["current"] <= t:
                status = " !!FAIL"
        print(f"  {a['id']:>3}  {name:<35} {a['current']:>4} {a['worst']:>4} {thr_val:>4}  {raw_str:>16}  {pf}{status}")