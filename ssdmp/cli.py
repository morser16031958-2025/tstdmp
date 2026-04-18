import argparse

from .constants import VERSION
from .reports import show_smart, show_controller_detect, show_full_diag, show_raw_identify


def main():
    ap = argparse.ArgumentParser(prog="ssdmp", description="SSD SMART analyzer")
    ap.add_argument("--list", action="store_true", help="List PhysicalDrives")
    ap.add_argument("--max-disk", type=int, default=32, help="Max PhysicalDrive number")
    ap.add_argument("--flash-id", type=int, metavar="N", help="Read Flash ID from ATA IDENTIFY")
    ap.add_argument("--identify", type=int, metavar="N", help="Show ATA IDENTIFY")
    ap.add_argument("--smart", type=int, metavar="N", help="Show SMART attributes")
    ap.add_argument("--controller-detect", type=int, metavar="N", help="Detect controller type")
    ap.add_argument("--full-diag", type=int, metavar="N", help="Full diagnostic report for disk N")
    ap.add_argument("--raw-identify", type=int, metavar="N", help="Dump raw IDENTIFY bytes + decode debug for disk N")
    ap.add_argument("--debug", action="store_true", help="Enable verbose debug output")
    ap.add_argument("--config", metavar="PATH", help="config_6643.ini path")
    ap.add_argument("--nand-list", metavar="PATH", help="nand_support_list_*.ini path")
    args = ap.parse_args()

    if args.list:
        from dataclasses import dataclass
        from .ata import (
            _open_drive, _close_drive, _read_storage_descriptor, _read_length, 
            _detect_usb_bridge, _smart_identify
        )
        from .reports import _scsi_get_info, _scsi_get_serial_vpd_80
        from .wmi import _get_interface_type_from_wmi, _get_pnp_device_id_from_wmi, _init_wmi_cache
        _init_wmi_cache()
        from .identify import _decode_identify

        @dataclass
        class PhysicalDriveInfo:
            number: int
            model: str = ""
            serial: str = ""
            firmware: str = ""
            bus_name: str = "Unknown"
            bridge: str = ""
            size_bytes: int = 0

        drives = []
        for n in range(args.max_disk + 1):
            h = _open_drive(n)
            if not h:
                continue
            try:
                desc = _read_storage_descriptor(h) or {}
                size = _read_length(h) or 0
                bus_type = int(desc.get("bus_type", 0))
                bus_name = str(desc.get("bus_name", "Unknown"))
                if bus_name == "Unknown":
                    wmi_type = _get_interface_type_from_wmi(n)
                    if wmi_type:
                        bus_name = wmi_type
                
                model = desc.get("model") or ""
                serial = desc.get("serial") or ""
                firmware = desc.get("firmware") or ""

                if not model and not size:
                    continue

                bridge_name = ""
                bridge_type = None
                if bus_type in (7, 0, 1):
                    bridge_name, bridge_type = _detect_usb_bridge(h, disk_number=n)

                ata_model = ""
                ata_serial = ""
                ata_fw = ""
                data_src = "StorageDescriptor"

                ident = _smart_identify(h, bridge_type=bridge_type)
                if ident and sum(1 for b in ident if b != 0) > 10:
                    info = _decode_identify(ident)
                    ata_model = info.get("model") or ""
                    ata_serial = info.get("serial") or ""
                    ata_fw = info.get("firmware") or ""
                    data_src = "ATA IDENTIFY"
                elif bus_type == 0 or bridge_type is not None or bus_name == "SCSI":
                    scsi_info = _scsi_get_info(h)
                    if scsi_info:
                        ata_model = scsi_info.get("model") or ""
                        # SCSI Standard Inquiry does NOT contain Serial, so we keep ata_serial empty
                        ata_fw = scsi_info.get("firmware") or ""
                        if ata_model:
                            data_src = "SCSI INQUIRY"
                    
                    # Try to get Serial from VPD Page 0x80 (most reliable for SCSI)
                    vpd_sn = _scsi_get_serial_vpd_80(h)
                    if vpd_sn and len(vpd_sn) > 3:
                        ata_serial = vpd_sn
                        data_src += " + VPD 0x80"

                if data_src.startswith("ATA IDENTIFY") or data_src.startswith("SCSI INQUIRY"):
                    if ata_model: model = ata_model
                    if ata_serial: serial = ata_serial
                    if ata_fw: firmware = ata_fw

                # Cleanup serial: remove non-printable characters and extra spaces
                if serial:
                    serial = "".join(c for c in serial if c.isprintable()).strip()
                    if not serial or all(c in " 0\x00" for c in serial):
                        serial = "?"

                # Fallback to PNPDeviceID if serial is still unknown or too short (often junk on budget SSDs)
                if not serial or serial == "?" or len(serial) <= 4:
                    pnp_id = _get_pnp_device_id_from_wmi(n)
                    if pnp_id:
                        # PNP ID often ends with serial after the last backslash
                        if "\\" in pnp_id:
                            sn_part = pnp_id.split("\\")[-1]
                            # For budget SSDs, the "real" unique ID is often the longest segment
                            # e.g. 7&136FCE66&0&000000 -> 136FCE66
                            segments = sn_part.split("&")
                            best_seg = max(segments, key=len) if segments else ""
                            
                            if len(best_seg) > 5:
                                serial = best_seg
                            elif sn_part and "&" not in sn_part and len(sn_part) > 5:
                                serial = sn_part

                # Smart cleanup for Model and FW (for budget SSDs where fields are swapped)
                import re
                if firmware and any(x in firmware.upper() for x in ["GB", "TB", "DISK", "SSD"]):
                    # If firmware looks like capacity or model part, move it to model
                    if firmware.upper() not in model.upper():
                        model = f"{model} {firmware}".strip()
                    firmware = "?"
                
                # Final model cleanup: remove extra spaces and common junk
                if model:
                    model = re.sub(r"\s+", " ", model).strip()
                    # Fix "WALRAM 1 28GB" -> "WALRAM 128GB" if the '1' is just a split digit
                    model = re.sub(r"(\d+)\s+(\d+GB)", r"\1\2", model)

                if serial == "?" and firmware and ata_fw:
                    if firmware.startswith(ata_fw) and len(firmware) > len(ata_fw):
                        serial = firmware[len(ata_fw):]
                        firmware = ata_fw

                drives.append(PhysicalDriveInfo(
                    number=n,
                    model=model,
                    serial=serial,
                    firmware=firmware,
                    bus_name=bus_name,
                    bridge=bridge_name or "",
                    size_bytes=size,
                ))
            finally:
                _close_drive(h)

        print(f"ssdmp v{VERSION}")
        print()
        print("=== PhysicalDrive list ===")
        if not drives:
            print("Ничего не найдено. Запусти от имени администратора.")
        else:
            for d in drives:
                size_gb = f"{d.size_bytes // (1024**3)}GB" if d.size_bytes else "?"
                model = d.model or "?"
                serial = d.serial or "?"
                fw = d.firmware or "?"
                bus = d.bus_name
                if d.bridge:
                    bus = f"{d.bus_name} ({d.bridge})"
                print(f"- PhysicalDrive{d.number}: {model} | SN={serial} | FW={fw} | BUS={bus} | SIZE={size_gb}")
        return

    if args.flash_id is not None or args.identify is not None:
        # Re-using show_full_diag logic for identify as it's more comprehensive
        show_full_diag(args.flash_id if args.flash_id is not None else args.identify, debug=args.debug)
        return

    if args.smart is not None:
        show_smart(args.smart, debug=args.debug)
        return

    if args.controller_detect is not None:
        show_controller_detect(args.controller_detect)
        return

    if args.full_diag is not None:
        show_full_diag(args.full_diag, debug=args.debug)
        return

    if args.raw_identify is not None:
        show_raw_identify(args.raw_identify, debug=args.debug)
        return

    ap.print_help()
