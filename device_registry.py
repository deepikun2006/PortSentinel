# device_registry.py

import re


# ==========================================================
# PortSentinel USB Vendor Registry
# ==========================================================
# This is a practical offline USB Vendor ID database focused on:
# - keyboards
# - mice
# - USB receivers
# - storage devices
# - adapters
# - phones
# - common USB controller chipsets
# - development boards often seen in HID/security testing
#
# Important:
# Vendor recognition does NOT mean a device is trusted.
# Only devices inside TRUSTED_DEVICES are treated as trusted.
# ==========================================================


VENDOR_DB = {
    # ======================================================
    # Major PC / laptop / OEM vendors
    # ======================================================
    "03F0": "HP, Inc.",
    "045E": "Microsoft Corp.",
    "04CA": "Lite-On Technology Corp.",
    "0502": "Acer, Inc.",
    "05E3": "Genesys Logic, Inc.",
    "064E": "Suyin Corp.",
    "06CB": "Synaptics, Inc.",
    "0A5C": "Broadcom Corp.",
    "0B05": "ASUSTek Computer, Inc.",
    "0BDA": "Realtek Semiconductor Corp.",
    "1022": "AMD",
    "1044": "Giga-Byte Technology Co., Ltd.",
    "1462": "Micro-Star International",
    "17EF": "Lenovo",
    "413C": "Dell Computer Corp.",
    "8086": "Intel Corp.",
    "8087": "Intel Corp.",

    # ======================================================
    # Common keyboard / mouse / input-device vendors
    # ======================================================
    "046A": "Cherry GmbH",
    "046D": "Logitech, Inc.",
    "047D": "Kensington",
    "04B4": "Cypress Semiconductor",
    "04D9": "Holtek Semiconductor, Inc.",
    "04F2": "Chicony Electronics Co., Ltd.",
    "04F3": "ELAN Microelectronics Corp.",
    "056A": "Wacom Co., Ltd.",
    "05A4": "Ortek Technology, Inc.",
    "0603": "Novatek Microelectronics Corp.",
    "062A": "MosArt / Primax Electronics",
    "0738": "Mad Catz / Saitek",
    "0853": "Topre Corp.",
    "093A": "PixArt Imaging, Inc.",
    "09DA": "A4Tech Co., Ltd.",
    "0D62": "Darfon Electronics Corp.",
    "1038": "SteelSeries ApS",
    "1241": "Belkin Components",
    "145F": "Trust International B.V.",
    "1532": "Razer USA, Ltd.",
    "1770": "Sweex",
    "1B1C": "Corsair",
    "1E7D": "ROCCAT GmbH",
    "24F0": "Metadot / Das Keyboard",
    "2516": "Cooler Master Co., Ltd.",
    "258A": "SINO WEALTH Electronic Ltd.",
    "2E3C": "Glorious LLC",
    "31E3": "Wooting Technologies B.V.",
    "3434": "Keychron",
    "3633": "Pulsar Gaming Gears",
    "320F": "Yunzii / Epomaker-compatible Keyboard Controller",

    # ======================================================
    # Gaming / headset / accessory vendors
    # ======================================================
    "03EB": "Atmel Corp.",
    "047F": "Plantronics, Inc.",
    "054C": "Sony Corp.",
    "0B0E": "GN Netcom / Jabra",
    "0D8C": "C-Media Electronics, Inc.",
    "0EC2": "SteelSeries / Gaming Audio Device",
    "1395": "Sennheiser Communications",
    "194F": "Lab126 / Amazon Devices",
    "1B3F": "Generalplus Technology, Inc.",
    "2DC8": "8BitDo",
    "2E24": "HyperX / Kingston Gaming",
    "31B2": "NZXT, Inc.",

    # ======================================================
    # USB storage brands and flash-drive vendors
    # ======================================================
    "048D": "Integrated Technology Express, Inc.",
    "04E8": "Samsung Electronics Co., Ltd.",
    "054C": "Sony Corp.",
    "058F": "Alcor Micro Corp.",
    "0781": "SanDisk Corp.",
    "090C": "Silicon Motion, Inc.",
    "0930": "Toshiba / Kioxia Corp.",
    "0951": "Kingston Technology",
    "0BC2": "Seagate RSS LLC",
    "0DD8": "Netac Technology Co., Ltd.",
    "1058": "Western Digital",
    "125F": "ADATA Technology Co., Ltd.",
    "13FE": "Phison Electronics Corp.",
    "154B": "PNY Technologies",
    "174C": "ASMedia Technology, Inc.",
    "18A5": "Verbatim",
    "1B1C": "Corsair",
    "1F75": "Innostor Technology Corp.",
    "2109": "VIA Labs, Inc.",
    "2537": "Norelsys",
    "8564": "Transcend Information, Inc.",
    "8644": "Intenso GmbH",

    # ======================================================
    # USB controller / bridge / hub chipsets
    # ======================================================
    "0403": "FTDI",
    "0424": "Microchip Technology / SMSC",
    "04B4": "Cypress Semiconductor",
    "04CC": "ST-Ericsson",
    "0525": "Netchip Technology, Inc.",
    "05E3": "Genesys Logic, Inc.",
    "067B": "Prolific Technology, Inc.",
    "0718": "Imation Corp.",
    "0764": "Cyber Power System, Inc.",
    "10C4": "Silicon Labs",
    "152D": "JMicron Technology Corp.",
    "1A40": "Terminus Technology, Inc.",
    "1A86": "QinHeng Electronics / WCH",
    "1D6B": "Linux Foundation",
    "2109": "VIA Labs, Inc.",
    "214B": "Huasheng Electronics",
    "2A4A": "Prusa Research",

    # ======================================================
    # Wireless / network / Bluetooth adapters
    # ======================================================
    "050D": "Belkin Components",
    "07B8": "AboCom Systems, Inc.",
    "07D1": "D-Link System",
    "0846": "NetGear, Inc.",
    "0A12": "Cambridge Silicon Radio / CSR",
    "0BDA": "Realtek Semiconductor Corp.",
    "0CF3": "Qualcomm Atheros",
    "0E8D": "MediaTek Inc.",
    "1286": "Marvell Semiconductor",
    "148F": "Ralink Technology Corp.",
    "1690": "Askey Computer Corp.",
    "2001": "D-Link Corp.",
    "2357": "TP-Link Technologies Co., Ltd.",
    "7392": "Edimax Technology Co., Ltd.",

    # ======================================================
    # Phones / tablets / mobile devices
    # ======================================================
    "04E8": "Samsung Electronics Co., Ltd.",
    "05AC": "Apple, Inc.",
    "0BB4": "HTC Corp.",
    "1004": "LG Electronics",
    "12D1": "Huawei Technologies Co., Ltd.",
    "18D1": "Google, Inc.",
    "19D2": "ZTE Corp.",
    "22B8": "Motorola PCS",
    "2717": "Xiaomi Communications Co., Ltd.",
    "2A70": "OnePlus Technology",
    "2D95": "Vivo Mobile Communication Co., Ltd.",
    "2E04": "HMD Global / Nokia",
    "22D9": "OPPO Electronics Corp.",

    # ======================================================
    # Cameras / webcams / imaging devices
    # ======================================================
    "046D": "Logitech, Inc.",
    "04F2": "Chicony Electronics Co., Ltd.",
    "05A9": "OmniVision Technologies, Inc.",
    "05C8": "Foxlink / Cheng Uei Precision",
    "064E": "Suyin Corp.",
    "0AC8": "Z-Star Microelectronics Corp.",
    "0C45": "Microdia",
    "13D3": "IMC Networks",
    "1BCF": "Sunplus Innovation Technology, Inc.",

    # ======================================================
    # Printers / scanners / office devices
    # ======================================================
    "03F0": "HP, Inc.",
    "04A9": "Canon, Inc.",
    "04B8": "Seiko Epson Corp.",
    "04F9": "Brother Industries, Ltd.",
    "043D": "Lexmark International, Inc.",
    "055F": "Mustek Systems, Inc.",
    "06DA": "Microtek International, Inc.",
    "0924": "Xerox",
    "1083": "Canon Electronics, Inc.",

    # ======================================================
    # Development boards / serial adapters / HID testing tools
    # ======================================================
    "03EB": "Atmel Corp.",
    "0403": "FTDI",
    "04D8": "Microchip Technology, Inc.",
    "0483": "STMicroelectronics",
    "10C4": "Silicon Labs",
    "16C0": "Van Ooijen Technische Informatica / Teensy-compatible",
    "1A86": "QinHeng Electronics / WCH",
    "1FC9": "NXP Semiconductors",
    "2341": "Arduino SA",
    "239A": "Adafruit Industries",
    "2886": "Seeed Studio",
    "2E8A": "Raspberry Pi",
    "303A": "Espressif Systems",
    "Cafe": "TinyUSB / Embedded USB Stack",

    # ======================================================
    # Security-test / programmable HID related IDs
    # ======================================================
    "16C0": "Teensy / V-USB Compatible Device",
    "1D50": "OpenMoko, Inc.",
    "2341": "Arduino SA",
    "2E8A": "Raspberry Pi",
    "303A": "Espressif Systems",
}


INPUT_VENDOR_IDS = {
    "045E", "046A", "046D", "047D", "04D9", "04F2", "04F3", "056A",
    "0603", "062A", "0738", "0853", "093A", "09DA", "0D62", "1038",
    "1241", "145F", "1532", "1770", "1B1C", "1E7D", "24F0", "2516",
    "258A", "2E3C", "31E3", "3434", "3633", "320F",
}

STORAGE_VENDOR_IDS = {
    "048D", "04E8", "054C", "058F", "0781", "090C", "0930", "0951",
    "0BC2", "0DD8", "1058", "125F", "13FE", "154B", "174C", "18A5",
    "1F75", "2109", "2537", "8564", "8644",
}

MOBILE_VENDOR_IDS = {
    "04E8", "05AC", "0BB4", "1004", "12D1", "18D1", "19D2", "22B8",
    "2717", "2A70", "2D95", "2E04", "22D9",
}

DEVELOPMENT_BOARD_VENDOR_IDS = {
    "03EB", "0403", "04D8", "0483", "10C4", "16C0", "1A86", "1FC9",
    "2341", "239A", "2886", "2E8A", "303A",
}


# ==========================================================
# Trusted devices for your environment
# ==========================================================
# Format:
# "VID:PID": "Friendly device name"
#
# Only add devices you personally own and recognize.
# Do not add a whole vendor here.
# ==========================================================

TRUSTED_DEVICES = {
    # Your mouse receiver from your PortSentinel log:
    # VID_062A / PID_4C01
    "062A:4C01": "Authorized MosArt / Primax Mouse Receiver",

    "046D:C52B": "Authorized Logitech Unifying Receiver",
    "045E:07A5": "Authorized Microsoft Office Mouse",
}


def normalize_usb_id(value, prefix=None):
    """
    Converts a USB identifier into a normalized uppercase four-character ID.

    Accepted examples:
        046d
        VID_046D
        PID_C52B
        0x046D
    """
    if value is None:
        return "Unknown"

    normalized = str(value).strip().upper()

    if not normalized or normalized == "UNKNOWN":
        return "Unknown"

    if prefix:
        normalized = normalized.removeprefix(f"{prefix.upper()}_")

    normalized = normalized.removeprefix("0X")

    match = re.fullmatch(r"[0-9A-F]{4}", normalized)

    if not match:
        return "Unknown"

    return normalized


def get_fingerprint(vid, pid):
    """
    Creates a consistent VID:PID fingerprint.

    Returns None when either identifier is unavailable or invalid.
    """
    normalized_vid = normalize_usb_id(vid, "VID")
    normalized_pid = normalize_usb_id(pid, "PID")

    if normalized_vid == "Unknown" or normalized_pid == "Unknown":
        return None

    return f"{normalized_vid}:{normalized_pid}"


def get_vendor_name(vid):
    """Returns the manufacturer associated with a USB Vendor ID."""
    normalized_vid = normalize_usb_id(vid, "VID")

    if normalized_vid == "Unknown":
        return "Unknown Vendor"

    return VENDOR_DB.get(normalized_vid, "Unknown Vendor")


def is_trusted_device(vid, pid):
    """Checks whether a VID:PID combination is in the trusted registry."""
    fingerprint = get_fingerprint(vid, pid)

    if fingerprint is None:
        return False

    return fingerprint in TRUSTED_DEVICES


def get_trusted_name(vid, pid):
    """Returns the trusted device name, or None if it is not registered."""
    fingerprint = get_fingerprint(vid, pid)

    if fingerprint is None:
        return None

    return TRUSTED_DEVICES.get(fingerprint)


def is_known_input_vendor(vid):
    """Returns True if the VID belongs to a known keyboard/mouse/input vendor."""
    normalized_vid = normalize_usb_id(vid, "VID")

    if normalized_vid == "Unknown":
        return False

    return normalized_vid in INPUT_VENDOR_IDS


def is_known_storage_vendor(vid):
    """Returns True if the VID belongs to a known storage vendor/controller."""
    normalized_vid = normalize_usb_id(vid, "VID")

    if normalized_vid == "Unknown":
        return False

    return normalized_vid in STORAGE_VENDOR_IDS


def is_known_mobile_vendor(vid):
    """Returns True if the VID belongs to a known phone/tablet vendor."""
    normalized_vid = normalize_usb_id(vid, "VID")

    if normalized_vid == "Unknown":
        return False

    return normalized_vid in MOBILE_VENDOR_IDS


def is_development_board_vendor(vid):
    """Returns True if the VID belongs to a dev board or programmable USB vendor."""
    normalized_vid = normalize_usb_id(vid, "VID")

    if normalized_vid == "Unknown":
        return False

    return normalized_vid in DEVELOPMENT_BOARD_VENDOR_IDS
