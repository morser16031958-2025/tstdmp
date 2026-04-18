VERSION = "0.50"

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = -1

IOCTL_STORAGE_QUERY_PROPERTY = 0x002D1400
IOCTL_DISK_GET_LENGTH_INFO = 0x0007405C
IOCTL_ATA_PASS_THROUGH = 0x0004D02C
IOCTL_SCSI_PASS_THROUGH_DIRECT = 0x0004D014
IOCTL_SCSI_MINIPORT = 0x0004D008
IOCTL_SCSI_GET_INQUIRY_DATA = 0x0004100C

# SCSI Miniport Control Codes for SMART
IOCTL_SCSI_MINIPORT_IDENTIFY = 0x0002001C
IOCTL_SCSI_MINIPORT_READ_SMART_ATTRIBS = 0x00020019

# Windows legacy SMART API (works where ATA_PASS_THROUGH fails)
IOCTL_SMART_GET_VERSION        = 0x00074080
IOCTL_SMART_RCV_DRIVE_DATA     = 0x0007C088
IOCTL_SMART_SEND_DRIVE_COMMAND = 0x0007C084

# SMART API command codes
SMART_CMD_IDENTIFY   = 0xEC  # IDENTIFY DEVICE
SMART_CMD_READ_DATA  = 0xD0  # SMART READ DATA (feature reg)
SMART_CMD_READ_THR   = 0xD1  # SMART READ THRESHOLDS (feature reg)
SMART_CMD_ATA        = 0xB0  # ATA SMART command
SMART_CYL_LOW        = 0x4F
SMART_CYL_HI         = 0xC2

SCSI_DATA_IN = 1

ATA_FLAGS_DATA_IN = 0x02
ATA_IDENTIFY_CMD = 0xEC
ATA_SMART_CMD = 0xB0
SMART_READ_DATA = 0xD0
SMART_READ_THRESHOLDS = 0xD1
SMART_LBA_MID = 0x4F
SMART_LBA_HI = 0xC2


BUS_TYPES = {
    0: "Unknown",
    1: "SCSI",
    2: "ATAPI",
    3: "ATA",
    4: "IEEE1394",
    6: "Fibre",
    7: "USB",
    8: "RAID",
    9: "iSCSI",
    10: "SAS",
    11: "SATA",
    12: "SD",
    0x11: "NVMe",
}


NAND_MANUFACTURER_IDS = {
    0x2C: "Micron",
    0xAD: "Hynix",
    0x45: "SanDisk/WD",
    0x98: "Toshiba/Kioxia",
    0xEC: "Samsung",
    0x89: "Intel",
    0x9B: "YMTC",
}


SMART_ATTRIBUTES = {
    1:   ("Read Error Rate", "raw"),
    2:   ("Throughput Performance", "raw"),
    3:   ("Spin-Up Time", "raw"),
    4:   ("Start/Stop Count", "raw"),
    5:   ("Reallocated Sectors Count", "raw"),
    7:   ("Seek Error Rate", "raw"),
    9:   ("Power-On Hours", "raw"),
    10:  ("Spin Retry Count", "raw"),
    12:  ("Power Cycle Count", "raw"),
    160: ("Uncorrectable Sector Count", "raw"),
    161: ("Valid Spare Block Count", "raw"),
    163: ("Initial Invalid Block Count", "raw"),
    164: ("Total Erase Count", "raw"),
    165: ("Max Erase Count", "raw"),
    166: ("Min Erase Count", "raw"),
    167: ("Average Erase Count", "raw"),
    168: ("Max Erase Count (NAND)", "raw"),
    169: ("Remaining Life Perc", "percent"),
    170: ("Bad Block Count", "raw"),
    171: ("Program Fail Count", "raw"),
    172: ("Erase Fail Count", "raw"),
    173: ("Wear Leveling Count", "raw"),
    174: ("Unexpected Power Loss", "raw"),
    175: ("Program Fail Count (Chip)", "raw"),
    176: ("Erase Fail Count (Chip)", "raw"),
    177: ("Wear Leveling Count", "raw"),
    178: ("Used Reserved Block Count (Chip)", "raw"),
    179: ("Used Reserved Block Count (Total)", "raw"),
    180: ("Unused Reserved Block Count", "raw"),
    181: ("Program Fail Count (Total)", "raw"),
    182: ("Erase Fail Count (Total)", "raw"),
    183: ("Runtime Bad Block", "raw"),
    184: ("End-to-End Error", "raw"),
    187: ("Reported Uncorrectable Errors", "raw"),
    188: ("Command Timeout", "raw"),
    190: ("Airflow Temperature", "temp"),
    192: ("Power-Off Retract Count", "raw"),
    194: ("Temperature", "temp"),
    195: ("Hardware ECC Recovered", "raw"),
    196: ("Reallocation Event Count", "raw"),
    197: ("Current Pending Sector Count", "raw"),
    198: ("Offline Uncorrectable", "raw"),
    199: ("UDMA CRC Error Count", "raw"),
    202: ("Data Address Mark Errors", "raw"),
    206: ("Flying Height", "raw"),
    210: ("Success RAIN Recovery Count", "raw"),
    231: ("SSD Life Left", "percent"),
    232: ("Available Reserved Space", "percent"),
    233: ("Media Wearout Indicator", "raw"),
    234: ("Thermal Throttle Status", "raw"),
    235: ("Good Block Count", "raw"),
    241: ("Total LBAs Written", "lba"),
    242: ("Total LBAs Read", "lba"),
    243: ("Total NAND Writes", "lba"),
    244: ("Total NAND Reads", "lba"),
    249: ("NAND Writes (1GiB)", "raw"),
}


SMART_PROFILES = {
    "silicon_motion": {
        9:   ("Power-On Hours", "raw"),
        12:  ("Power Cycle Count", "raw"),
        160: ("Uncorrectable Sector Count", "raw"),
        161: ("Valid Spare Block Count", "raw"),
        163: ("Initial Invalid Block Count", "raw"),
        164: ("Total Erase Count", "raw"),
        165: ("Max Erase Count", "raw"),
        166: ("Min Erase Count", "raw"),
        167: ("Average Erase Count", "raw"),
        168: ("Max Erase Count (spec)", "raw"),
        169: ("Remaining Life", "percent"),
        177: ("Wear Leveling Count", "raw"),
        194: ("Temperature", "temp"),
        241: ("Total Host Writes", "lba_32mb"),
        242: ("Total Host Reads", "lba_32mb"),
    },
    "phison": {
        1:   ("Read Error Rate", "raw"),
        5:   ("Retired Block Count", "raw"),
        9:   ("Power-On Hours", "raw"),
        12:  ("Power Cycle Count", "raw"),
        167: ("SSD Protect Mode", "raw"),
        168: ("SATA PHY Error Count", "raw"),
        169: ("Bad Block Count", "raw"),
        170: ("Bad Block Count (spare)", "raw"),
        171: ("Program Fail Count", "raw"),
        172: ("Erase Fail Count", "raw"),
        173: ("Wear Leveling Count", "raw"),
        174: ("Unexpected Power Loss", "raw"),
        175: ("Program Fail Count (worst)", "raw"),
        181: ("Program Fail Count (total)", "raw"),
        182: ("Erase Fail Count (total)", "raw"),
        187: ("Reported Uncorrectable", "raw"),
        192: ("Unsafe Shutdown Count", "raw"),
        194: ("Temperature", "temp"),
        196: ("Reallocation Event Count", "raw"),
        199: ("UDMA CRC Error Count", "raw"),
        232: ("Available Reserve Space", "percent"),
        241: ("Total Writes", "gib"),
        242: ("Total Reads", "gib"),
    },
    "realtek": {
        1:   ("Read Error Rate", "raw"),
        5:   ("Reallocated Sectors", "raw"),
        9:   ("Power-On Hours", "raw"),
        12:  ("Power Cycle Count", "raw"),
        161: ("GDN", "raw"),
        162: ("Total Erase Count", "raw"),
        163: ("Max PE Cycles", "raw"),
        164: ("Average Erase Count", "raw"),
        166: ("Total Bad Blocks", "raw"),
        167: ("SSD Protect Mode", "raw"),
        168: ("SATA PHY Error Count", "raw"),
        169: ("Remaining Life", "percent"),
        171: ("Program Fail Count", "raw"),
        172: ("Erase Fail Count", "raw"),
        174: ("Unexpected Power Loss", "raw"),
        175: ("ECC Error Count", "raw"),
        181: ("Unaligned Access Count", "raw"),
        187: ("Uncorrectable Errors", "raw"),
        194: ("Temperature", "temp"),
        195: ("Cumulative ECC Correction", "raw"),
        196: ("Reallocation Event Count", "raw"),
        199: ("UDMA CRC Error Count", "raw"),
        206: ("Min Erase Count", "raw"),
        207: ("Max Erase Count", "raw"),
        232: ("Available Reserve Space", "percent"),
        241: ("Total Host Writes", "gib"),
        242: ("Total Host Reads", "gib"),
        249: ("Total NAND Writes TLC", "gib"),
        250: ("Total NAND Writes SLC", "gib"),
    },
    "samsung": {
        5:   ("Reallocated Sectors", "raw"),
        9:   ("Power-On Hours", "raw"),
        12:  ("Power Cycle Count", "raw"),
        177: ("Wear Leveling Count", "raw"),
        179: ("Used Reserved Block Count", "raw"),
        180: ("Unused Reserved Block Count", "raw"),
        181: ("Program Fail Count", "raw"),
        182: ("Erase Fail Count", "raw"),
        183: ("Runtime Bad Block", "raw"),
        187: ("Uncorrectable Error Count", "raw"),
        190: ("Airflow Temperature", "temp"),
        194: ("Temperature", "temp_minmax"),
        195: ("ECC Error Rate", "raw"),
        199: ("CRC Error Count", "raw"),
        206: ("Flying Height", "raw"),
        235: ("POR Recovery Count", "raw"),
        241: ("Total LBAs Written", "lba"),
        242: ("Total LBAs Read", "lba"),
    },
    "micron": {
        1:   ("Raw Read Error Rate", "raw"),
        5:   ("Reallocated Block Count", "raw"),
        9:   ("Power-On Hours", "raw"),
        12:  ("Power Cycle Count", "raw"),
        170: ("Reserved Block Count", "raw"),
        171: ("Program Fail Count", "raw"),
        172: ("Erase Fail Count", "raw"),
        173: ("Average Block Erase Count", "raw"),
        174: ("Unexpected Power Loss", "raw"),
        180: ("Unused Reserve NAND Blocks", "raw"),
        183: ("SATA Downshift Error Count", "raw"),
        184: ("End-to-End Error", "raw"),
        187: ("Reported Uncorrectable", "raw"),
        194: ("Temperature", "temp_minmax"),
        197: ("Current Pending Sectors", "raw"),
        198: ("Offline Uncorrectable", "raw"),
        199: ("UDMA CRC Error Count", "raw"),
        202: ("Percent Lifetime Remaining", "percent_inv"),
        206: ("Write Error Rate", "raw"),
        210: ("RAIN Success Recovery", "raw"),
        241: ("Total LBAs Written", "lba_32mb"),
        242: ("Total LBAs Read", "lba_32mb"),
    },
    "wd_sandisk": {
        1:   ("Read Error Rate", "raw"),
        5:   ("Reallocated Sector Count", "raw"),
        9:   ("Power-On Hours", "raw"),
        12:  ("Power Cycle Count", "raw"),
        177: ("Wear Leveling Count", "raw"),
        179: ("Used Reserved Block Count", "raw"),
        181: ("Program Fail Count", "raw"),
        182: ("Erase Fail Count", "raw"),
        187: ("Uncorrectable Error Count", "raw"),
        188: ("Command Timeout", "raw"),
        194: ("Temperature", "temp"),
        195: ("ECC Error Count", "raw"),
        199: ("UDMA CRC Error Count", "raw"),
        232: ("Available Reserved Space", "percent"),
        241: ("Total LBAs Written", "lba"),
        242: ("Total LBAs Read", "lba"),
    },
}


USB_BRIDGE_PROFILES = {
    (0x152D, 0x0578): ("JMicron JMS578", "jmicron"),
    (0x152D, 0x0583): ("JMicron JMS583", "jmicron"),
    (0x152D, 0x1561): ("JMicron JMS561", "jmicron"),
    (0x152D, 0x2338): ("JMicron JMS583", "jmicron"),
    (0x152D, 0x0567): ("JMicron JMS567", "jmicron"),
    (0x174C, 0x55AA): ("ASMedia ASM1153", "sat"),
    (0x174C, 0x235C): ("ASMedia ASM2354", "sat"),
    (0x174C, 0x5106): ("ASMedia ASM1051", "sat"),
    (0x0BDA, 0x9210): ("Realtek RTL9210", "sat"),
    (0x0BDA, 0x9220): ("Realtek RTL9220", "sat"),
    (0x04B4, 0x6830): ("Cypress CY7C68300", "cypress"),
    (0x04FC, 0x0C25): ("Sunplus SPIF225A", "sunplus"),
    (0x1BCF, 0x0C31): ("Innodisk", "sat"),
    (0x0480, 0xA200): ("Toshiba", "sat"),
    (0x14CD, 0x6600): ("Super Top", "sat"),
}