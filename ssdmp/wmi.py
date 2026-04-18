import subprocess
from typing import Optional

def _get_interface_type_from_wmi(disk_number: int) -> Optional[str]:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-CimInstance Win32_DiskDrive | Where-Object {{$_.Index -eq {disk_number}}} | Select-Object -ExpandProperty InterfaceType"],
            capture_output=True, text=True, timeout=5
        )
        itype = result.stdout.strip().upper()
        if not itype: return None
        if "IDE" in itype: return "SATA"
        if "SCSI" in itype: return "SCSI"
        if "USB" in itype: return "USB"
        return itype
    except Exception:
        pass
    return None

def _get_pnp_device_id_from_wmi(disk_number: int) -> Optional[str]:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-CimInstance Win32_DiskDrive | Where-Object {{$_.Index -eq {disk_number}}} | Select-Object -ExpandProperty PNPDeviceID"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception:
        pass
    return None

def _get_usb_vid_pid_from_wmi(disk_number: int) -> Optional[Tuple[int, int]]:
    pnp_id = _get_pnp_device_id_from_wmi(disk_number)
    if not pnp_id or "USB\\VID_" not in pnp_id.upper():
        return None
    
    try:
        # Example: USB\VID_0BDA&PID_9210\...
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
    try:
        # Get SCSIPort and SCSITargetId from Win32_DiskDrive
        cmd = f"Get-CimInstance Win32_DiskDrive | Where-Object {{$_.Index -eq {disk_number}}} | Select-Object SCSIPort, SCSITargetId"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=5
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        # PowerShell output for Select-Object often has headers or is in list format
        # More reliable: output as CSV or JSON
        cmd = f"Get-CimInstance Win32_DiskDrive | Where-Object {{$_.Index -eq {disk_number}}} | Select-Object SCSIPort, SCSITargetId | ConvertTo-Json"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=5
        )
        import json
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            port = data.get("SCSIPort")
            target = data.get("SCSITargetId")
            return (int(port) if port is not None else None, 
                    int(target) if target is not None else None)
    except Exception:
        pass
    return None, None
