import subprocess
import json
from typing import Optional, Tuple, Dict

# Global cache for WMI DiskDrive information
_wmi_disk_cache: Dict[int, dict] = {}

def _init_wmi_cache():
    """
    Fetch all Win32_DiskDrive information once via a single PowerShell call.
    This significantly speeds up disk enumeration.
    """
    global _wmi_disk_cache
    _wmi_disk_cache = {}
    try:
        # Get essential properties for all disks in one go
        cmd = "Get-CimInstance Win32_DiskDrive | Select-Object Index, InterfaceType, PNPDeviceID, SCSIPort, SCSITargetId | ConvertTo-Json"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=10
        )
        if not result.stdout.strip():
            return

        data = json.loads(result.stdout)
        
        # PowerShell returns a single dict if only one disk is found, otherwise a list of dicts
        if isinstance(data, dict):
            items = [data]
        elif isinstance(data, list):
            items = data
        else:
            return

        for item in items:
            idx = item.get("Index")
            if idx is not None:
                _wmi_disk_cache[int(idx)] = item
    except Exception:
        pass

def _get_interface_type_from_wmi(disk_number: int) -> Optional[str]:
    item = _wmi_disk_cache.get(disk_number)
    if item:
        itype = str(item.get("InterfaceType", "")).upper()
        if "IDE" in itype: return "SATA"
        if "SCSI" in itype: return "SCSI"
        if "USB" in itype: return "USB"
        return itype
    return None

def _get_pnp_device_id_from_wmi(disk_number: int) -> Optional[str]:
    item = _wmi_disk_cache.get(disk_number)
    if item:
        return item.get("PNPDeviceID")
    return None

def _get_usb_vid_pid_from_wmi(disk_number: int) -> Optional[Tuple[int, int]]:
    pnp_id = _get_pnp_device_id_from_wmi(disk_number)
    if not pnp_id or "USB\\VID_" not in pnp_id.upper():
        return None
    
    try:
        import re
        m = re.search(r"VID_([0-9A-F]{4})&PID_([0-9A-F]{4})", pnp_id.upper())
        if m:
            vid = int(m.group(1), 16)
            pid = int(m.group(2), 16)
            return vid, pid
    except Exception:
        pass
    return None

def _get_scsi_port_and_target(disk_number: int) -> Tuple[Optional[int], Optional[int]]:
    item = _wmi_disk_cache.get(disk_number)
    if item:
        port = item.get("SCSIPort")
        target = item.get("SCSITargetId")
        return (int(port) if port is not None else None, 
                int(target) if target is not None else None)
    return None, None
