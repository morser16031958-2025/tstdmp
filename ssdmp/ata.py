import ctypes
from typing import Optional, Tuple

from .constants import (
    IOCTL_STORAGE_QUERY_PROPERTY, IOCTL_DISK_GET_LENGTH_INFO,
    IOCTL_ATA_PASS_THROUGH, IOCTL_SCSI_PASS_THROUGH_DIRECT,
    IOCTL_SCSI_MINIPORT, IOCTL_SCSI_GET_INQUIRY_DATA,
    IOCTL_SCSI_MINIPORT_IDENTIFY, IOCTL_SCSI_MINIPORT_READ_SMART_ATTRIBS,
    SCSI_DATA_IN,
    ATA_FLAGS_DATA_IN, ATA_IDENTIFY_CMD, ATA_SMART_CMD,
    SMART_READ_DATA, SMART_READ_THRESHOLDS, SMART_LBA_MID, SMART_LBA_HI,
    IOCTL_SMART_GET_VERSION, IOCTL_SMART_RCV_DRIVE_DATA, IOCTL_SMART_SEND_DRIVE_COMMAND,
    SMART_CMD_IDENTIFY, SMART_CMD_READ_DATA, SMART_CMD_READ_THR,
    SMART_CMD_ATA, SMART_CYL_LOW, SMART_CYL_HI,
)
from .winapi import (
    _open_drive, _close_drive, _ioctl, _last_win_error, kernel32,
    STORAGE_PROPERTY_QUERY, GET_LENGTH_INFORMATION,
    ATA_PASS_THROUGH_EX, SCSI_PASS_THROUGH_DIRECT, SRB_IO_CONTROL, _SPTD_WITH_SENSE,
    SENDCMDINPARAMS, _SENDCMDOUT512,
    GENERIC_READ, GENERIC_WRITE, FILE_SHARE_READ, FILE_SHARE_WRITE, OPEN_EXISTING, INVALID_HANDLE_VALUE
)
from .wmi import (
    _get_interface_type_from_wmi, _get_pnp_device_id_from_wmi, _get_usb_vid_pid_from_wmi,
    _get_scsi_port_and_target
)

USB_BRIDGE_TABLE = {
    (0x0BDA, 0x9210): "realtek_rtl9210",
    (0x0BDA, 0x9220): "realtek_rtl9220",
    (0x0BDA, 0x0153): "realtek_rts5735",
    (0x152D, 0x0578): "jmicron",
    (0x152D, 0x0562): "jmicron",
    (0x152D, 0x1337): "jmicron",
    (0x174C, 0x55AA): "asmedia",
    (0x174C, 0x225C): "asmedia",
    (0x174C, 0x1153): "asmedia", # ASM1153E
    (0x174C, 0x5106): "asmedia",
    (0x067B, 0x3507): "prolific",
    (0x04FC, 0x0C25): "sunplus",
}

def _open_scsi_port(port_number: int):
    path = f"\\\\.\\Scsi{port_number}:"
    h = kernel32.CreateFileW(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if h == INVALID_HANDLE_VALUE:
        return None
    return h

def _miniport_smart_identify(scsi_port: int, scsi_target_id: int, debug: bool = False) -> Optional[bytes]:
    h = _open_scsi_port(scsi_port)
    if not h: return None
    try:
        # Buffer: SRB_IO_CONTROL + SENDCMDINPARAMS + 512 bytes
        header_size = ctypes.sizeof(SRB_IO_CONTROL)
        params_size = ctypes.sizeof(SENDCMDINPARAMS)
        total_size = header_size + params_size + 512
        buf = ctypes.create_string_buffer(total_size)
        
        srb = SRB_IO_CONTROL.from_buffer(buf)
        srb.HeaderLength = header_size
        ctypes.memmove(srb.Signature, b"SCSIDISK", 8)
        srb.Timeout = 2
        srb.ControlCode = IOCTL_SCSI_MINIPORT_IDENTIFY
        srb.Length = params_size + 512
        
        params = SENDCMDINPARAMS.from_buffer(buf, header_size)
        params.cBufferSize = 512
        params.irDriveRegs.bCommandReg = ATA_IDENTIFY_CMD
        params.bDriveNumber = scsi_target_id
        
        ok, br = _ioctl(h, IOCTL_SCSI_MINIPORT, buf, total_size, buf, total_size)
        if not ok:
            if debug:
                err_code, err_msg = _last_win_error()
                print(f"  [DEBUG] Miniport IDENTIFY FAILED: Scsi{scsi_port} Target{scsi_target_id} WinError {err_code} ({err_msg})")
            return None
        
        # Data is at offset header_size + 16 (+16 = 4 cBufferSize + 12 DRIVERSTATUS)
        data_offset = header_size + 16
        return bytes(buf[data_offset : data_offset + 512])
    finally:
        _close_drive(h)

def _miniport_smart_read_data(scsi_port: int, scsi_target_id: int, debug: bool = False) -> Optional[bytes]:
    h = _open_scsi_port(scsi_port)
    if not h: return None
    try:
        header_size = ctypes.sizeof(SRB_IO_CONTROL)
        params_size = ctypes.sizeof(SENDCMDINPARAMS)
        total_size = header_size + params_size + 512
        buf = ctypes.create_string_buffer(total_size)
        
        srb = SRB_IO_CONTROL.from_buffer(buf)
        srb.HeaderLength = header_size
        ctypes.memmove(srb.Signature, b"SCSIDISK", 8)
        srb.Timeout = 2
        srb.ControlCode = IOCTL_SCSI_MINIPORT_READ_SMART_ATTRIBS
        srb.Length = params_size + 512
        
        params = SENDCMDINPARAMS.from_buffer(buf, header_size)
        params.cBufferSize = 512
        params.irDriveRegs.bFeaturesReg = SMART_READ_DATA
        params.irDriveRegs.bCylLowReg = SMART_LBA_MID
        params.irDriveRegs.bCylHighReg = SMART_LBA_HI
        params.irDriveRegs.bCommandReg = ATA_SMART_CMD
        params.bDriveNumber = scsi_target_id
        
        ok, br = _ioctl(h, IOCTL_SCSI_MINIPORT, buf, total_size, buf, total_size)
        if not ok:
            if debug:
                err_code, err_msg = _last_win_error()
                print(f"  [DEBUG] Miniport SMART FAILED: Scsi{scsi_port} Target{scsi_target_id} WinError {err_code} ({err_msg})")
            return None
        
        data_offset = header_size + 16
        return bytes(buf[data_offset : data_offset + 512])
    finally:
        _close_drive(h)

def _read_length(h) -> Optional[int]:
    gli = GET_LENGTH_INFORMATION()
    ok, br = _ioctl(h, IOCTL_DISK_GET_LENGTH_INFO, None, 0, ctypes.byref(gli), ctypes.sizeof(gli))
    if not ok:
        return None
    return gli.Length

def _read_storage_descriptor(h) -> Optional[dict]:
    query = STORAGE_PROPERTY_QUERY()
    query.PropertyId = 0
    query.QueryType = 0
    buf = ctypes.create_string_buffer(1024)
    ok, br = _ioctl(h, IOCTL_STORAGE_QUERY_PROPERTY, ctypes.byref(query), ctypes.sizeof(query), buf, len(buf))
    if not ok or br < 36:
        return None
    raw = bytes(buf[:br])
    
    # STORAGE_DEVICE_DESCRIPTOR offsets:
    # 0: Version (4), 4: Size (4), 8: DeviceType (1), 9: DeviceTypeModifier (1)
    # 10: RemovableMedia (1), 11: CommandQueueing (1)
    # 12: VendorIdOffset (4), 16: ProductIdOffset (4), 20: ProductRevisionOffset (4)
    # 24: SerialNumberOffset (4), 28: BusType (4)
    
    def get_str(off):
        if off <= 0 or off >= br: return ""
        s = []
        for b in raw[off:]:
            if b == 0: break
            s.append(chr(b))
        return "".join(s).strip()

    return {
        "vendor": get_str(int.from_bytes(raw[12:16], "little")),
        "model": get_str(int.from_bytes(raw[16:20], "little")),
        "firmware": get_str(int.from_bytes(raw[20:24], "little")),
        "serial": get_str(int.from_bytes(raw[24:28], "little")),
        "bus_type": int.from_bytes(raw[28:32], "little"),
    }

def _detect_usb_bridge(h, disk_number: Optional[int] = None) -> Tuple[Optional[str], Optional[str]]:
    desc = _read_storage_descriptor(h)
    if not desc: return None, None
    if desc["bus_type"] not in (7, 0, 1): 
        return None, None
    
    # Try VID/PID from WMI
    if disk_number is not None:
        vid_pid = _get_usb_vid_pid_from_wmi(disk_number)
        if vid_pid in USB_BRIDGE_TABLE:
            bridge_type = USB_BRIDGE_TABLE[vid_pid]
            return f"{bridge_type} ({vid_pid[0]:04X}:{vid_pid[1]:04X})", bridge_type
        elif vid_pid:
            # Check model string if VID/PID is unknown but present
            model = (desc.get("model") or "").upper()
            if "ASM" in model or "ASMEDIA" in model:
                return f"asmedia ({vid_pid[0]:04X}:{vid_pid[1]:04X})", "asmedia"
            if "JMS" in model or "JMICRON" in model:
                return f"jmicron ({vid_pid[0]:04X}:{vid_pid[1]:04X})", "jmicron"
            if "REALTEK" in model or "RTL" in model:
                return f"realtek ({vid_pid[0]:04X}:{vid_pid[1]:04X})", "realtek"
                
            return f"unknown_usb ({vid_pid[0]:04X}:{vid_pid[1]:04X})", "unknown_usb"

    # Fallback to model string detection if disk_number is missing or WMI failed
    model = (desc.get("model") or "").upper()
    if "ASM" in model or "ASMEDIA" in model:
        return f"asmedia (string)", "asmedia"
    if "JMS" in model or "JMICRON" in model:
        return f"jmicron (string)", "jmicron"
    if "REALTEK" in model or "RTL" in model:
        return f"realtek (string)", "realtek"
            
    return "unknown_usb", "unknown_usb"

def _ata_identify_device(h) -> Optional[bytes]:
    apt = ATA_PASS_THROUGH_EX()
    apt.Length = ctypes.sizeof(apt)
    apt.AtaFlags = ATA_FLAGS_DATA_IN
    apt.DataTransferLength = 512
    apt.TimeOutValue = 2
    apt.DataBufferOffset = ctypes.sizeof(apt)
    apt.CurrentTaskFile[6] = ATA_IDENTIFY_CMD
    
    buf = ctypes.create_string_buffer(ctypes.sizeof(apt) + 512)
    ctypes.memmove(buf, ctypes.byref(apt), ctypes.sizeof(apt))
    
    ok, br = _ioctl(h, IOCTL_ATA_PASS_THROUGH, buf, len(buf), buf, len(buf))
    if not ok: return None
    return bytes(buf[ctypes.sizeof(apt):])

def _sat12_ata_identify_device(h, debug: bool = False) -> Optional[bytes]:
    # CDB 12 bytes: [0xA1, 0x08, 0x0E, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, ATA_IDENTIFY_CMD]
    cdb = (ctypes.c_uint8 * 16)(0xA1, 0x08, 0x0E, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, ATA_IDENTIFY_CMD, 0, 0, 0, 0)
    data = ctypes.create_string_buffer(512)
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 12
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = 512
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(data)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 12)
    
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0:
        if debug:
            _log_scsi_error("SAT12 IDENTIFY", ok, sws)
        return None
    return bytes(data[:512])

def _jmicron_ata_identify_device(h, debug: bool = False) -> Optional[bytes]:
    # JMicron Vendor Command (0xDF)
    cdb = (ctypes.c_uint8 * 16)(0xDF, 0x10, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
    data = ctypes.create_string_buffer(512)
    data[0] = 0x01 # Master
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 16
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = 512
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(data)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 16)
    
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0:
        if debug:
            _log_scsi_error("JMicron IDENTIFY", ok, sws)
        return None
    return bytes(data[:512])

def _log_scsi_error(label: str, ok: bool, sws: _SPTD_WITH_SENSE):
    if not ok:
        err_code, err_msg = _last_win_error()
        print(f"  [DEBUG] {label} FAILED: WinError {err_code} ({err_msg})")
    else:
        status = sws.sptd.ScsiStatus
        sense = bytes(sws.sense)
        resp_code = sense[0]
        sense_key = sense[2] & 0x0F
        asc = sense[12]
        ascq = sense[13]
        print(f"  [DEBUG] {label} SCSI ERROR: Status=0x{status:02X} Resp=0x{resp_code:02X} Key=0x{sense_key:02X} ASC=0x{asc:02X} ASCQ=0x{ascq:02X}")

def _sat_ata_identify_device(h, debug: bool = False) -> Optional[bytes]:
    # ATA16 (SAT) command
    cdb = (ctypes.c_uint8 * 16)(0x85, 0x08, 0x0e, 0, 0, 0, 0x01, 0, 0, 0, 0, 0, 0, 0, ATA_IDENTIFY_CMD, 0)
    data = ctypes.create_string_buffer(512)
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 16
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = 512
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(data)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 16)
    
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0:
        if debug:
            _log_scsi_error("SAT16 IDENTIFY", ok, sws)
        return None
    return bytes(data[:512])

def _win_smart_identify(h) -> Optional[bytes]:
    params = SENDCMDINPARAMS()
    params.cBufferSize = 512
    params.irDriveRegs.bCommandReg = SMART_CMD_IDENTIFY
    out = _SENDCMDOUT512()
    out.cBufferSize = 512
    ok, br = _ioctl(h, IOCTL_SMART_RCV_DRIVE_DATA, ctypes.byref(params), ctypes.sizeof(params), ctypes.byref(out), ctypes.sizeof(out))
    if not ok: return None
    return bytes(out.bBuffer)

def _try_vsc_smi_identify(h) -> Optional[bytes]:
    """
    SMI (Silicon Motion) Vendor Specific Identify.
    Tries to knock with SMI signature to get real passport.
    """
    # SMI Knock: Feature=0x01, LBA Mid=0x22, LBA High=0x55, Command=0xF1
    cdb = (ctypes.c_uint8 * 16)(0x85, 0x08, 0x0e, 0x01, 0, 0, 0x01, 0, 0x22, 0x55, 0, 0, 0, 0, 0xF1, 0)
    data = ctypes.create_string_buffer(512)
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 16
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = 512
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(data)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 16)
    
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0: return None
    return bytes(data[:512])

def _asmedia_ata_identify_device(h, debug: bool = False) -> Optional[bytes]:
    """
    ASMedia Vendor Specific Command (0xEE) to bypass UASPStor blocks.
    CDB: EE 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    Data buffer starts with 0x01 (identify command).
    """
    cdb = (ctypes.c_uint8 * 16)(0xEE, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    data = ctypes.create_string_buffer(512)
    # ASMedia protocol: 0x01 in first byte often means IDENTIFY
    data[0] = 0x01 
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 16
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = 512
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(data)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 16)
    
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0:
        if debug:
            _log_scsi_error("ASMedia IDENTIFY (0xEE)", ok, sws)
        return None
    return bytes(data[:512])

def _smart_identify(h, bridge_type: Optional[str] = None, debug: bool = False, disk_number: Optional[int] = None) -> Optional[bytes]:
    if bridge_type == "jmicron":
        data = _jmicron_ata_identify_device(h, debug=debug)
        if data: return data
    
    if bridge_type == "asmedia":
        # 1. Try Vendor Specific (0xEE) - CDI often uses this
        data = _asmedia_ata_identify_device(h, debug=debug)
        if data: return data
        
        # 2. Try Miniport
        if disk_number is not None:
            scsi_port, scsi_target = _get_scsi_port_and_target(disk_number)
            if scsi_port is not None and scsi_target is not None:
                data = _miniport_smart_identify(scsi_port, scsi_target, debug=debug)
                if data: return data
                
        # 3. Fallback to SAT
        data = _sat_ata_identify_device(h, debug=debug)
        if data: return data
        data = _sat12_ata_identify_device(h, debug=debug)
        if data: return data

    if bridge_type and bridge_type != "unknown_usb" and bridge_type != "asmedia":
        # For other known USB bridges, try SAT16 then SAT12
        data = _sat_ata_identify_device(h, debug=debug)
        if data: return data
        data = _sat12_ata_identify_device(h, debug=debug)
        if data: return data
    
    if bridge_type == "unknown_usb":
        # MINI-PORT PATH (Bypassing UASPStor) - Try first
        if disk_number is not None:
            scsi_port, scsi_target = _get_scsi_port_and_target(disk_number)
            if scsi_port is not None and scsi_target is not None:
                data = _miniport_smart_identify(scsi_port, scsi_target, debug=debug)
                if data: return data

        # For unknown USB, try all SAT methods as fallback
        data = _sat_ata_identify_device(h, debug=debug)
        if data: return data
        data = _sat12_ata_identify_device(h, debug=debug)
        if data: return data
    
    if bridge_type is None:
        # Priority for SATA: 1. Win SMART API, 2. ATA PT
        data = _win_smart_identify(h)
        if data: return data
        data = _ata_identify_device(h)
        if data: return data
        
    # Final fallback for any type
    return _try_vsc_smi_identify(h)

def _ata_smart_read_data(h) -> Optional[bytes]:
    apt = ATA_PASS_THROUGH_EX()
    apt.Length = ctypes.sizeof(apt)
    apt.AtaFlags = ATA_FLAGS_DATA_IN
    apt.DataTransferLength = 512
    apt.TimeOutValue = 2
    apt.DataBufferOffset = ctypes.sizeof(apt)
    apt.CurrentTaskFile[0] = SMART_READ_DATA
    apt.CurrentTaskFile[3] = SMART_LBA_MID
    apt.CurrentTaskFile[4] = SMART_LBA_HI
    apt.CurrentTaskFile[6] = ATA_SMART_CMD
    buf = ctypes.create_string_buffer(ctypes.sizeof(apt) + 512)
    ctypes.memmove(buf, ctypes.byref(apt), ctypes.sizeof(apt))
    ok, br = _ioctl(h, IOCTL_ATA_PASS_THROUGH, buf, len(buf), buf, len(buf))
    if not ok: return None
    return bytes(buf[ctypes.sizeof(apt):])

def _sat12_smart_read_data(h, debug: bool = False) -> Optional[bytes]:
    # CDB 12 bytes: [0xA1, 0x08, 0x0E, SMART_READ_DATA, 0x01, 0x00, SMART_LBA_MID, SMART_LBA_HI, 0x00, ATA_SMART_CMD, 0x00, 0x00]
    cdb = (ctypes.c_uint8 * 16)(0xA1, 0x08, 0x0E, SMART_READ_DATA, 0x01, 0x00, SMART_LBA_MID, SMART_LBA_HI, 0x00, ATA_SMART_CMD, 0x00, 0x00, 0, 0, 0, 0)
    data = ctypes.create_string_buffer(512)
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 12
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = 512
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(data)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 12)
    
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0:
        if debug:
            _log_scsi_error("SAT12 SMART", ok, sws)
        return None
    return bytes(data[:512])

def _jmicron_smart_read_data(h, debug: bool = False) -> Optional[bytes]:
    # JMicron Vendor Command (0xDF) for SMART
    # CDB: DF 10 00 02 00 00 00 00 00 00 00 00 00 00 00 00
    # Data buffer: 0x01 (master), SMART_READ_DATA, 0x00, 0x00, SMART_LBA_MID, SMART_LBA_HI, ATA_SMART_CMD, ...
    cdb = (ctypes.c_uint8 * 16)(0xDF, 0x10, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
    data = ctypes.create_string_buffer(512)
    data[0] = 0x01 # Master
    data[1] = SMART_READ_DATA
    data[4] = SMART_LBA_MID
    data[5] = SMART_LBA_HI
    data[6] = ATA_SMART_CMD
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 16
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = 512
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(data)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 16)
    
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0:
        if debug:
            _log_scsi_error("JMicron SMART", ok, sws)
        return None
    return bytes(data[:512])

def _asmedia_smart_read_data(h, debug: bool = False) -> Optional[bytes]:
    """
    ASMedia Vendor Specific Command (0xEE) for SMART.
    Data buffer starts with 0x02 (smart read command).
    """
    cdb = (ctypes.c_uint8 * 16)(0xEE, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    data = ctypes.create_string_buffer(512)
    # ASMedia protocol: 0x02 often means SMART READ DATA
    data[0] = 0x02 
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 16
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = 512
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(data)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 16)
    
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0:
        if debug:
            _log_scsi_error("ASMedia SMART (0xEE)", ok, sws)
        return None
    return bytes(data[:512])

def _sat_smart_read_data(h, debug: bool = False) -> Optional[bytes]:
    cdb = (ctypes.c_uint8 * 16)(0x85, 0x08, 0x0e, SMART_READ_DATA, 0, 0, 0x01, 0, 0, 0, SMART_LBA_MID, SMART_LBA_HI, 0, 0, ATA_SMART_CMD, 0)
    data = ctypes.create_string_buffer(512)
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 16
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = 512
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(data)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 16)
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0:
        if debug:
            _log_scsi_error("SAT16 SMART", ok, sws)
        return None
    return bytes(data[:512])

def _win_smart_read_data(h) -> Optional[bytes]:
    params = SENDCMDINPARAMS()
    params.cBufferSize = 512
    params.irDriveRegs.bFeaturesReg = SMART_READ_DATA
    params.irDriveRegs.bCylLowReg = SMART_CYL_LOW
    params.irDriveRegs.bCylHighReg = SMART_CYL_HI
    params.irDriveRegs.bCommandReg = SMART_CMD_ATA
    out = _SENDCMDOUT512()
    out.cBufferSize = 512
    ok, br = _ioctl(h, IOCTL_SMART_RCV_DRIVE_DATA, ctypes.byref(params), ctypes.sizeof(params), ctypes.byref(out), ctypes.sizeof(out))
    if not ok: return None
    return bytes(out.bBuffer)

def _scsi_log_sense_smart(h) -> Optional[bytes]:
    """
    Try to read SMART data via SCSI LOG SENSE command (Page 0x2F or 0x30).
    Some SCSI/USB bridges expose SMART this way.
    """
    # LOG SENSE, PC=1 (Cumulative), PageCode=0x2F, AllocationLength=512
    cdb = (ctypes.c_uint8 * 16)(0x4D, 0, 0x40 | 0x2F, 0, 0, 0, 0, 0x02, 0x00, 0)
    buf = ctypes.create_string_buffer(512)
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 10
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = 512
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(buf)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 10)
    
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0 or br < 4:
        return None
    
    # Return raw data if it looks like SMART (starts with page 0x2F)
    raw = bytes(buf[:br])
    if raw[0] & 0x3F == 0x2F:
        return raw
    return None

def _smart_read_data(h, bridge_type: Optional[str] = None, debug: bool = False, disk_number: Optional[int] = None) -> Optional[bytes]:
    if bridge_type == "jmicron":
        data = _jmicron_smart_read_data(h, debug=debug)
        if data: return data
        
    if bridge_type == "asmedia":
        # 1. Vendor Specific
        data = _asmedia_smart_read_data(h, debug=debug)
        if data: return data
        # 2. Miniport
        if disk_number is not None:
            scsi_port, scsi_target = _get_scsi_port_and_target(disk_number)
            if scsi_port is not None and scsi_target is not None:
                data = _miniport_smart_read_data(scsi_port, scsi_target, debug=debug)
                if data: return data
        # 3. SAT fallback
        data = _sat_smart_read_data(h, debug=debug)
        if data: return data
        data = _sat12_smart_read_data(h, debug=debug)
        if data: return data
        
    if bridge_type and bridge_type != "unknown_usb" and bridge_type != "asmedia":
        # MINI-PORT PATH (Bypassing UASPStor) - Try first
        if disk_number is not None:
            scsi_port, scsi_target = _get_scsi_port_and_target(disk_number)
            if scsi_port is not None and scsi_target is not None:
                data = _miniport_smart_read_data(scsi_port, scsi_target, debug=debug)
                if data: return data

        # Fallback to SAT
        data = _sat_smart_read_data(h, debug=debug)
        if data: return data
        data = _sat12_smart_read_data(h, debug=debug)
        if data: return data
        
    if bridge_type is None:
        data = _win_smart_read_data(h)
        if data: return data
        data = _ata_smart_read_data(h)
        if data: return data
        
    # Last resort fallbacks
    data = _scsi_log_sense_smart(h)
    return data

def _ata_smart_read_thresholds(h) -> Optional[bytes]:
    apt = ATA_PASS_THROUGH_EX()
    apt.Length = ctypes.sizeof(apt)
    apt.AtaFlags = ATA_FLAGS_DATA_IN
    apt.DataTransferLength = 512
    apt.TimeOutValue = 2
    apt.DataBufferOffset = ctypes.sizeof(apt)
    apt.CurrentTaskFile[0] = SMART_READ_THRESHOLDS
    apt.CurrentTaskFile[3] = SMART_LBA_MID
    apt.CurrentTaskFile[4] = SMART_LBA_HI
    apt.CurrentTaskFile[6] = ATA_SMART_CMD
    buf = ctypes.create_string_buffer(ctypes.sizeof(apt) + 512)
    ctypes.memmove(buf, ctypes.byref(apt), ctypes.sizeof(apt))
    ok, br = _ioctl(h, IOCTL_ATA_PASS_THROUGH, buf, len(buf), buf, len(buf))
    if not ok: return None
    return bytes(buf[ctypes.sizeof(apt):])

def _sat_smart_read_thresholds(h) -> Optional[bytes]:
    cdb = (ctypes.c_uint8 * 16)(0x85, 0x08, 0x0e, SMART_READ_THRESHOLDS, 0, 0, 0x01, 0, 0, 0, SMART_LBA_MID, SMART_LBA_HI, 0, 0, ATA_SMART_CMD, 0)
    data = ctypes.create_string_buffer(512)
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 16
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = 512
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(data)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 16)
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0: return None
    return bytes(data[:512])

def _smart_read_thresholds(h, bridge_type: Optional[str] = None) -> Optional[bytes]:
    data = _ata_smart_read_thresholds(h)
    if data: return data
    return _sat_smart_read_thresholds(h)

def _scsi_get_info(h) -> Optional[dict]:
    # SCSI INQUIRY, page 0 (Standard Inquiry Data)
    # CDB: 12 00 00 00 24 00 (Request 36 bytes for standard inquiry)
    cdb = (ctypes.c_uint8 * 16)(0x12, 0, 0, 0, 36, 0)
    buf = ctypes.create_string_buffer(64)
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 6
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = 36
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(buf)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 6)
    
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0 or br < 36:
        return None
        
    # Clean strings: only printable characters
    def clean(s: str) -> str:
        return "".join(c for c in s if c.isprintable()).strip()
        
    vendor = clean(raw[8:16].decode("ascii", errors="replace"))
    model = clean(raw[16:32].decode("ascii", errors="replace"))
    fw = clean(raw[32:36].decode("ascii", errors="replace"))
    
    # If model is truncated or weird, try to combine with vendor
    full_model = model
    if vendor and vendor.lower() not in model.lower():
        full_model = f"{vendor} {model}"
        
    # If FW looks like model part (GB, SSD), mark as unknown
    if any(x in fw.upper() for x in ["GB", "TB", "SSD"]):
        if fw.upper() not in full_model.upper():
            full_model = f"{full_model} {fw}".strip()
        fw = "?"
        
    return {
        "vendor": vendor,
        "model": full_model.strip(),
        "firmware": fw,
    }

def _scsi_get_serial_vpd_80(h) -> Optional[str]:
    cdb = (ctypes.c_uint8 * 16)(0x12, 0x01, 0x80, 0, 0xFF, 0)
    buf = ctypes.create_string_buffer(256)
    sws = _SPTD_WITH_SENSE()
    sws.sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.CdbLength = 6
    sws.sptd.DataIn = SCSI_DATA_IN
    sws.sptd.DataTransferLength = len(buf)
    sws.sptd.TimeOutValue = 2
    sws.sptd.DataBuffer = ctypes.addressof(buf)
    sws.sptd.SenseInfoOffset = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sws.sptd.SenseInfoLength = 32
    ctypes.memmove(sws.sptd.Cdb, cdb, 6)
    ok, br = _ioctl(h, IOCTL_SCSI_PASS_THROUGH_DIRECT, ctypes.byref(sws), ctypes.sizeof(sws), ctypes.byref(sws), ctypes.sizeof(sws))
    if not ok or sws.sptd.ScsiStatus != 0 or br < 4: return None
    raw = bytes(buf[:br])
    page_len = raw[3]
    if page_len > 0:
        return raw[4:4+page_len].decode("ascii", errors="replace").strip()
    return None
