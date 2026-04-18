from .constants import VERSION
from .ata import (
    _open_drive, _close_drive, _read_storage_descriptor, _read_length,
    _detect_usb_bridge, _smart_identify, _smart_read_data, _smart_read_thresholds,
    _ata_identify_device, _sat_ata_identify_device, _win_smart_identify,
    _scsi_get_info, _scsi_get_serial_vpd_80,
    _miniport_smart_identify, _miniport_smart_read_data
)
from .wmi import _get_scsi_port_and_target
from .identify import _decode_identify, _extract_flash_id_from_identify, _decode_string, _decode_string_plain_ascii
from .smart import (
    _parse_smart_attributes, _parse_smart_thresholds,
    _evaluate_health, _print_smart_table,
)
from .profiles import _detect_smart_profile
from .controllers import _get_controller_candidates, _get_nand_info_by_fid

def show_controller_detect(disk_number: int):
    h = _open_drive(disk_number)
    if not h:
        print(f"ERROR: Cannot open PhysicalDrive{disk_number}")
        return
    try:
        desc = _read_storage_descriptor(h) or {}
        bus_type = int(desc.get("bus_type", 0))
        bridge_name, bridge_type = None, None
        if bus_type in (7, 0, 1):
            bridge_name, bridge_type = _detect_usb_bridge(h, disk_number=disk_number)

        identify = _smart_identify(h, bridge_type=bridge_type, disk_number=disk_number)
        if not identify:
            print("IDENTIFY not read")
            return

        info = _decode_identify(identify)
        vendor_text = info.get("vendor_text", "")
        model = info.get("model") or desc.get("model") or "?"
        fid, manu = _extract_flash_id_from_identify(identify)
        vendor_area = info.get("vendor_area", b"")

        print(f"ssdmp v{VERSION}")
        print(f"Controller Detect: PhysicalDrive{disk_number}")
        if bridge_name:
            print(f"  USB Bridge: {bridge_name}")
        print()
        print(f"  Model:    {model}")
        print(f"  Flash ID: {' '.join(f'{b:02X}' for b in fid[:6]) + f' ({manu})' if fid else '?'}")
        print(f"  Vendor:  {vendor_text}")

        ctrl_candidates = _get_controller_candidates(model, vendor_text, vendor_area)

        print()
        print("  Possible controllers:")
        if ctrl_candidates:
            for name, conf in ctrl_candidates:
                bar = "#" * conf + "-" * (7 - conf)
                print(f"    [{bar}] {name}")
        else:
            print("    Not detected")

        # NAND detection
        if fid:
            nand_info = _get_nand_info_by_fid(fid, manu)
            if nand_info:
                print()
                print("  NAND:")
                for n in nand_info:
                    print(f"    - {n}")

        print()
        print()
        print("  Vendor area (hex, first 128 bytes):")
        va_len = min(128, len(vendor_area))
        for i in range(0, va_len, 32):
            hex_part = " ".join(f"{b:02X}" for b in vendor_area[i : i + 32])
            ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in vendor_area[i : i + 32])
            print(f"    {i:04x}: {hex_part}  {ascii_part}")
    finally:
        _close_drive(h)

def show_smart(disk_number: int, debug: bool = False):
    h = _open_drive(disk_number)
    if not h:
        print(f"ERROR: Cannot open PhysicalDrive{disk_number}")
        return
    try:
        desc = _read_storage_descriptor(h) or {}
        model = desc.get("model", "?")
        bus_type = int(desc.get("bus_type", 0))
        bridge_name, bridge_type = None, None
        if bus_type == 7: # USB
            bridge_name, bridge_type = _detect_usb_bridge(h, disk_number=disk_number)
        elif bus_type == 0:
            bridge_name, bridge_type = _detect_usb_bridge(h, disk_number=disk_number)

        print(f"ssdmp v{VERSION}")
        print(f"SMART: PhysicalDrive{disk_number}")
        print(f"  Model: {model}")
        if bridge_name:
            print(f"  USB Bridge: {bridge_name}")

        identify = _smart_identify(h, bridge_type=bridge_type, debug=debug, disk_number=disk_number)
        profile = None
        if identify:
            info = _decode_identify(identify)
            vendor_text = info.get("vendor_text", "")
            vendor_area = info.get("vendor_area", b"")
            model = info.get("model", model or "")
            profile = _detect_smart_profile(model, vendor_text, vendor_area)
            if profile:
                print(f"  Profile: {profile}")

        smart_data = _smart_read_data(h, bridge_type=bridge_type, debug=debug, disk_number=disk_number)
        if not smart_data:
            print("SMART data not available")
            return

        attrs = _parse_smart_attributes(smart_data)

        thr_data = _smart_read_thresholds(h, bridge_type=bridge_type)
        thresholds = _parse_smart_thresholds(thr_data) if thr_data else {}

        health_status, reasons = _evaluate_health(attrs, thresholds, profile=profile)
        print()
        print(f"Health Status: {health_status}")
        for r in reasons:
            print(f"  - {r}")
        print()
        _print_smart_table(attrs, thresholds, profile)
    finally:
        _close_drive(h)

def show_full_diag(disk_number: int, debug: bool = False):
    h = _open_drive(disk_number)
    if not h:
        print(f"ERROR: Cannot open PhysicalDrive{disk_number}")
        return
    try:
        desc = _read_storage_descriptor(h) or {}
        size_bytes = _read_length(h) or 0
        bus_type = int(desc.get("bus_type", 0))
        bridge_name, bridge_type = None, None
        if bus_type in (7, 0, 1): # USB, UAS or SCSI
            bridge_name, bridge_type = _detect_usb_bridge(h, disk_number=disk_number)

        identify = _smart_identify(h, bridge_type=bridge_type, debug=debug, disk_number=disk_number)
        
        # Base info from descriptor/WMI (fallback)
        from .wmi import _get_interface_type_from_wmi, _get_pnp_device_id_from_wmi
        import re
        
        bus_name = _get_interface_type_from_wmi(disk_number) or "Unknown"
        model = desc.get("model") or "?"
        serial = desc.get("serial") or "?"
        firmware = desc.get("firmware") or "?"
        vendor_text = ""
        vendor_area = b""
        fid = None
        manu = None
        
        if identify:
            info = _decode_identify(identify)
            model = info.get("model") or model
            serial = info.get("serial") or serial
            firmware = info.get("firmware") or firmware
            vendor_text = info.get("vendor_text", "")
            vendor_area = info.get("vendor_area", b"")
            fid = info.get("flash_id")
            manu = info.get("nand_manufacturer")
        else:
            # If IDENTIFY failed, try SCSI Inquiry as second fallback
            scsi = _scsi_get_info(h)
            if scsi:
                model = scsi.get("model") or model
                firmware = scsi.get("firmware") or firmware
            
            # Try VPD 0x80 for serial
            vpd_sn = _scsi_get_serial_vpd_80(h)
            if vpd_sn and len(vpd_sn) > 4:
                serial = vpd_sn

        # PNP ID Fallback for Serial
        if not serial or serial == "?" or len(serial) <= 4:
            pnp_id = _get_pnp_device_id_from_wmi(disk_number)
            if pnp_id and "\\" in pnp_id:
                sn_part = pnp_id.split("\\")[-1]
                segments = sn_part.split("&")
                best_seg = max(segments, key=len) if segments else ""
                if len(best_seg) > 5:
                    serial = best_seg

        # Cleanup Model/FW
        if firmware and any(x in firmware.upper() for x in ["GB", "TB", "SSD"]):
            if firmware.upper() not in model.upper():
                model = f"{model} {firmware}".strip()
            firmware = "?"
        
        if model:
            model = re.sub(r"\s+", " ", model).strip()
            model = re.sub(r"(\d+)\s+(\d+GB)", r"\1\2", model)
        
        size_gb = f"{size_bytes // (1024**3)} GB" if size_bytes else "?"
        profile = _detect_smart_profile(model, vendor_text, vendor_area)

        print(f"ssdmp v{VERSION} — Full Diagnostic Report: PhysicalDrive{disk_number}")
        print("=" * 70)
        print(f"  Model:      {model}")
        print(f"  Serial:     {serial}")
        print(f"  Firmware:   {firmware}")
        print(f"  Capacity:   {size_gb} ({size_bytes:,} bytes)")
        print(f"  Interface:  {bus_name}")
        if bridge_name:
            print(f"  USB Bridge: {bridge_name}")
        print("-" * 70)

        ctrl_candidates = _get_controller_candidates(model, vendor_text, vendor_area)
        if ctrl_candidates:
            best_ctrl, _ = ctrl_candidates[0]
            print(f"  Controller: {best_ctrl}")
        
        if fid:
            fid_str = " ".join(f"{b:02X}" for b in fid[:6])
            print(f"  Flash ID:   {fid_str} ({manu or 'Unknown'})")
        
        nand_info = _get_nand_info_by_fid(fid, manu)
        if nand_info:
            print(f"  NAND Type:  {', '.join(nand_info)}")

        # SMART & Health
        smart_data = _smart_read_data(h, bridge_type=bridge_type, debug=debug, disk_number=disk_number)
        if smart_data:
            attrs = _parse_smart_attributes(smart_data)
            thr_data = _smart_read_thresholds(h, bridge_type=bridge_type)
            thresholds = _parse_smart_thresholds(thr_data) if thr_data else {}
            
            health_status, reasons = _evaluate_health(attrs, thresholds, profile=profile)
            
            print("-" * 70)
            print(f"  HEALTH STATUS: {health_status}")
            for r in reasons:
                print(f"    - {r}")
            print("-" * 70)
            print()
            _print_smart_table(attrs, thresholds, profile)
        else:
            print("-" * 70)
            print("  SMART data not available (Blocked by driver or controller)")
    finally:
        _close_drive(h)

def show_raw_identify(disk_number: int, debug: bool = False):
    h = _open_drive(disk_number)
    if not h:
        print(f"ERROR: Cannot open PhysicalDrive{disk_number}")
        return
    try:
        desc = _read_storage_descriptor(h) or {}
        bus_type = int(desc.get("bus_type", 0))
        bridge_name, bridge_type = None, None
        if bus_type in (7, 0, 1):
            bridge_name, bridge_type = _detect_usb_bridge(h, disk_number=disk_number)

        print(f"ssdmp v{VERSION} — RAW IDENTIFY DUMP: PhysicalDrive{disk_number}")
        print(f"  StorageDescriptor: model={desc.get('model')!r} serial={desc.get('serial')!r} "
              f"fw={desc.get('firmware')!r} bus_type={bus_type} bridge={bridge_type!r}")
        print()

        from .ata import _sat12_ata_identify_device, _jmicron_ata_identify_device
        
        data_win     = _win_smart_identify(h)
        data_ata     = _ata_identify_device(h)
        data_sat16   = _sat_ata_identify_device(h, debug=debug)
        data_sat12   = _sat12_ata_identify_device(h, debug=debug)
        data_jmicron = _jmicron_ata_identify_device(h, debug=debug) if bridge_type == "jmicron" else None
        
        # Miniport test
        scsi_port, scsi_target = _get_scsi_port_and_target(disk_number)
        data_miniport = None
        if scsi_port is not None and scsi_target is not None:
            data_miniport = _miniport_smart_identify(scsi_port, scsi_target, debug=debug)

        def _method_report(label, data):
            if data is None:
                print(f"  {label:<35}: FAILED (None)")
            else:
                nonzero = sum(1 for b in data if b != 0)
                print(f"  {label:<35}: OK  non-zero={nonzero}/512")

        _method_report("_win_smart_identify (SMART API)", data_win)
        _method_report("_ata_identify_device (ATA PT)",  data_ata)
        _method_report("_sat_ata_identify_device (SAT16)", data_sat16)
        _method_report("_sat12_ata_identify_device (SAT12)", data_sat12)
        if bridge_type == "jmicron":
            _method_report("_jmicron_ata_identify_device (0xDF)", data_jmicron)
        _method_report("_miniport_smart_identify (ScsiPort)", data_miniport)

        # Final choice using the smart waterfall logic
        data = _smart_identify(h, bridge_type=bridge_type, debug=debug, disk_number=disk_number)
        
        if not data:
            print()
            print("  ERROR: All IDENTIFY methods failed — no data to dump")
            return

        print()
        print(f"  Final selection data source: {'VSC/SAT/WinAPI'}")
        print()

        print("-- IDENTIFY_DEVICE (raw bytes) " + "-" * 45)
        print(f"       {'  '.join(f'{i:3d}' for i in range(10))}")
        for row in range(0, 256, 10):
            words = []
            for col in range(10):
                idx = (row + col) * 2
                if idx + 1 < len(data):
                    w = int.from_bytes(data[idx:idx+2], "little")
                    words.append(f"{w:04X}")
                else:
                    words.append("    ")
            print(f"  {row:03d}: {' '.join(words)}")

        print()
        print("-- FIELD DECODE COMPARISON " + "-" * 50)
        def field(label: str, raw_bytes: bytes):
            ata  = _decode_string(raw_bytes)
            plain = _decode_string_plain_ascii(raw_bytes)
            hex_preview = " ".join(f"{b:02X}" for b in raw_bytes[:12])
            print(f"  {label:<12} hex: {hex_preview}")
            print(f"  {'':<12} ATA-swap : {ata!r}")
            print(f"  {'':<12} plain    : {plain!r}")
            print()

        field("serial",   data[20:40])
        field("firmware", data[46:54])
        field("model",    data[54:94])

        info = _decode_identify(data)
        print("-- _decode_identify result " + "-" * 50)
        for k in ("model", "serial", "firmware", "nand_manufacturer"):
            print(f"  {k}: {info.get(k)!r}")
        fid, manu = _extract_flash_id_from_identify(data)
        if fid:
            fid_str = " ".join(f"{b:02X}" for b in fid[:6])
            print(f"  flash_id: {fid_str} ({manu})")
        else:
            print(f"  flash_id: None")

        print()
        print("-- VENDOR AREA (bytes 256-319) " + "-" * 45)
        va = data[256:320]
        for i in range(0, 64, 16):
            hex_part = " ".join(f"{b:02X}" for b in va[i:i+16])
            asc_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in va[i:i+16])
            print(f"  {i:04x}: {hex_part}  {asc_part}")
    finally:
        _close_drive(h)
