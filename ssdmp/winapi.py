import ctypes
import ctypes.wintypes as W
from typing import Tuple

from .constants import (
    GENERIC_READ, GENERIC_WRITE, FILE_SHARE_READ, FILE_SHARE_WRITE,
    OPEN_EXISTING, INVALID_HANDLE_VALUE
)

kernel32 = ctypes.windll.kernel32

class STORAGE_PROPERTY_QUERY(ctypes.Structure):
    _fields_ = [
        ("PropertyId", W.DWORD),
        ("QueryType", W.DWORD),
        ("AdditionalParameters", ctypes.c_byte * 1),
    ]

class GET_LENGTH_INFORMATION(ctypes.Structure):
    _fields_ = [("Length", ctypes.c_longlong)]

class ATA_PASS_THROUGH_EX(ctypes.Structure):
    _fields_ = [
        ("Length", ctypes.c_ushort),
        ("AtaFlags", ctypes.c_ushort),
        ("PathId", ctypes.c_ubyte),
        ("TargetId", ctypes.c_ubyte),
        ("Lun", ctypes.c_ubyte),
        ("ReservedAsUchar", ctypes.c_ubyte),
        ("DataTransferLength", ctypes.c_ulong),
        ("TimeOutValue", ctypes.c_ulong),
        ("ReservedAsUlong", ctypes.c_ulong),
        ("DataBufferOffset", ctypes.c_void_p),
        ("PreviousTaskFile", ctypes.c_ubyte * 8),
        ("CurrentTaskFile", ctypes.c_ubyte * 8),
    ]

class SCSI_PASS_THROUGH_DIRECT(ctypes.Structure):
    _fields_ = [
        ("Length", ctypes.c_uint16),
        ("ScsiStatus", ctypes.c_uint8),
        ("PathId", ctypes.c_uint8),
        ("TargetId", ctypes.c_uint8),
        ("Lun", ctypes.c_uint8),
        ("CdbLength", ctypes.c_uint8),
        ("SenseInfoLength", ctypes.c_uint8),
        ("DataIn", ctypes.c_uint8),
        ("_pad1", ctypes.c_uint8 * 3),
        ("DataTransferLength", ctypes.c_uint32),
        ("TimeOutValue", ctypes.c_uint32),
        ("_pad2", ctypes.c_uint8 * 4),
        ("DataBuffer", ctypes.c_void_p),
        ("SenseInfoOffset", ctypes.c_uint32),
        ("_pad3", ctypes.c_uint8 * 4),
        ("Cdb", ctypes.c_uint8 * 16),
    ]

class SRB_IO_CONTROL(ctypes.Structure):
    _fields_ = [
        ("HeaderLength", ctypes.c_uint32),
        ("Signature",    ctypes.c_uint8 * 8),
        ("Timeout",      ctypes.c_uint32),
        ("ControlCode",  ctypes.c_uint32),
        ("ReturnCode",   ctypes.c_uint32),
        ("Length",       ctypes.c_uint32),
    ]

class _SPTD_WITH_SENSE(ctypes.Structure):
    _fields_ = [("sptd", SCSI_PASS_THROUGH_DIRECT), ("sense", ctypes.c_uint8 * 32)]

class IDEREGS(ctypes.Structure):
    _fields_ = [
        ("bFeaturesReg",    ctypes.c_uint8),
        ("bSectorCountReg", ctypes.c_uint8),
        ("bSectorNumberReg",ctypes.c_uint8),
        ("bCylLowReg",      ctypes.c_uint8),
        ("bCylHighReg",     ctypes.c_uint8),
        ("bDriveHeadReg",   ctypes.c_uint8),
        ("bCommandReg",     ctypes.c_uint8),
        ("bReserved",       ctypes.c_uint8),
    ]

class SENDCMDINPARAMS(ctypes.Structure):
    _fields_ = [
        ("cBufferSize",  ctypes.c_uint32),
        ("irDriveRegs",  IDEREGS),
        ("bDriveNumber", ctypes.c_uint8),
        ("bReserved",    ctypes.c_uint8 * 3),
        ("dwReserved",   ctypes.c_uint32 * 4),
        ("bBuffer",      ctypes.c_uint8 * 1),
    ]

class DRIVERSTATUS(ctypes.Structure):
    _fields_ = [
        ("bDriverError", ctypes.c_uint8),
        ("bIDEError",    ctypes.c_uint8),
        ("bReserved",    ctypes.c_uint8 * 2),
        ("dwReserved",   ctypes.c_uint32 * 2),
    ]

class _SENDCMDOUT512(ctypes.Structure):
    _fields_ = [
        ("cBufferSize",   ctypes.c_uint32),
        ("DriverStatus",  DRIVERSTATUS),
        ("bBuffer",       ctypes.c_uint8 * 512),
    ]

def _open_drive(number: int):
    path = f"\\\\.\\PhysicalDrive{number}"
    h = kernel32.CreateFileW(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if h == INVALID_HANDLE_VALUE:
        h = kernel32.CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if h == INVALID_HANDLE_VALUE:
        return None
    return h

def _close_drive(h):
    if h and h != INVALID_HANDLE_VALUE:
        kernel32.CloseHandle(h)

def _ioctl(h, code, inbuf, insize, outbuf, outsize) -> Tuple[bool, int]:
    returned = W.DWORD(0)
    ok = kernel32.DeviceIoControl(
        h,
        code,
        inbuf,
        insize,
        outbuf,
        outsize,
        ctypes.byref(returned),
        None,
    )
    return bool(ok), int(returned.value)

def _last_win_error() -> Tuple[int, str]:
    code = int(kernel32.GetLastError())
    try:
        msg = ctypes.FormatError(code).strip()
    except Exception:
        msg = ""
    return code, msg
