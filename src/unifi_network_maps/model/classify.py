"""Device and client type classification."""

from __future__ import annotations

from .helpers import first_string_field, get_field

# Client device category detection patterns
_CLIENT_NAME_PATTERNS: dict[str, tuple[str, ...]] = {
    "camera": ("camera", "cam", "doorbell", "uvc", "protect", "ring", "nest cam", "arlo"),
    "tv": ("tv", "television", "apple tv", "chromecast", "roku", "fire tv", "shield", "smart tv"),
    "phone": ("phone", "iphone", "android", "pixel", "galaxy", "mobile", "voip", "handset"),
    "printer": ("printer", "print", "laserjet", "inkjet", "epson", "canon", "brother", "hp "),
    "nas": ("nas", "synology", "qnap", "diskstation", "drobo", "freenas", "truenas"),
    "speaker": ("sonos", "homepod", "echo", "alexa", "google home", "speaker", "soundbar"),
    "game_console": ("playstation", "ps4", "ps5", "xbox", "nintendo", "switch", "steam deck"),
    "iot": ("sensor", "thermostat", "nest", "hue", "smart", "zigbee", "z-wave", "iot"),
}

# OUI/vendor patterns for manufacturer-based detection
_CLIENT_VENDOR_PATTERNS: dict[str, tuple[str, ...]] = {
    "camera": ("ubiquiti", "hikvision", "dahua", "axis", "ring", "arlo", "nest", "wyze"),
    "tv": ("samsung tv", "lg tv", "sony tv", "vizio", "tcl", "roku", "apple tv"),
    "phone": ("apple", "samsung mobile", "google pixel", "oneplus", "xiaomi"),
    "printer": ("hp inc", "canon", "epson", "brother", "lexmark", "xerox", "ricoh"),
    "nas": ("synology", "qnap", "western digital", "seagate", "netgear readynas"),
    "speaker": ("sonos", "bose", "harman", "bang & olufsen", "denon"),
    "game_console": ("sony interactive", "microsoft xbox", "nintendo"),
}

# UniFi product line mappings
_UNIFI_PRODUCT_CATEGORIES: dict[str, str] = {
    "protect": "camera",
    "talk": "phone",
    "access": "iot",
    "led": "iot",
    "connect": "iot",
}


def _classify_by_device_name(name: str) -> str | None:
    """Classify device by name when type field is missing."""
    lower = name.strip().lower()
    if "gateway" in lower or lower.startswith("gw"):
        return "gateway"
    if "switch" in lower:
        return "switch"
    if "ap" in lower:
        return "ap"
    return None


def classify_device_type(device: object) -> str:
    """Classify a network device into gateway, switch, ap, or other."""
    raw_type = get_field(device, "type")
    value = raw_type.strip().lower() if isinstance(raw_type, str) else ""
    if not value:
        raw_name = get_field(device, "name")
        name = raw_name if isinstance(raw_name, str) else ""
        return _classify_by_device_name(name) or "other"
    if value in {"gateway", "ugw", "usg", "udm", "udr", "uxg"}:
        return "gateway"
    if value == "ux":
        in_gw_mode = get_field(device, "in_gateway_mode")
        if in_gw_mode is False:
            return "ap"
        return "gateway"
    if value in {"switch", "usw"}:
        return "switch"
    if value in {"uap", "ap"} or "ap" in value:
        return "ap"
    return "other"


def _classify_by_name(name: str) -> str | None:
    """Classify client by display name heuristics."""
    name_lower = name.lower()
    for category, patterns in _CLIENT_NAME_PATTERNS.items():
        for pattern in patterns:
            if pattern in name_lower:
                return category
    return None


def _classify_by_vendor(vendor: str) -> str | None:
    """Classify client by OUI/vendor name."""
    vendor_lower = vendor.lower()
    for category, patterns in _CLIENT_VENDOR_PATTERNS.items():
        for pattern in patterns:
            if pattern in vendor_lower:
                return category
    return None


def _classify_by_unifi_info(ucore: dict[str, object]) -> str | None:
    """Classify client by UniFi device info (product_line, model)."""
    product_line = ucore.get("product_line")
    if isinstance(product_line, str):
        line_lower = product_line.lower()
        for line_prefix, category in _UNIFI_PRODUCT_CATEGORIES.items():
            if line_lower.startswith(line_prefix):
                return category
    for key in ("product_shortname", "computed_model", "product_model"):
        value = ucore.get(key)
        if isinstance(value, str):
            value_lower = value.lower()
            if any(cam in value_lower for cam in ("camera", "doorbell", "uvc", "g4", "g5")):
                return "camera"
            if "talk" in value_lower or "phone" in value_lower:
                return "phone"
    return None


def _client_ucore_info(client: object) -> dict[str, object] | None:
    """Get UniFi device info from client."""
    info = get_field(client, "unifi_device_info_from_ucore")
    if isinstance(info, dict):
        return info
    return None


def _client_ucore_display_name(client: object) -> str | None:
    """Get display name from UniFi device info."""
    ucore = _client_ucore_info(client)
    if not ucore:
        return None
    return first_string_field(ucore, "name", "computed_model", "product_model", "product_shortname")


def _client_vendor(client: object) -> str | None:
    """Get vendor/OUI from client."""
    return first_string_field(
        client, "oui", "vendor", "vendor_name", "manufacturer", "manufacturer_name"
    )


def _client_unifi_flag(client: object) -> bool | None:
    """Check explicit UniFi device flags."""
    for key in ("is_unifi", "is_unifi_device", "is_ubnt", "is_uap", "is_managed"):
        value = get_field(client, key)
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
    return None


def _ucore_has_device_info(ucore: dict[str, object]) -> bool:
    """Check whether a ucore dict contains any meaningful UniFi device data."""
    managed = ucore.get("managed")
    if isinstance(managed, bool) and managed:
        return True
    for key in ("product_line", "product_shortname", "name", "computed_model", "product_model"):
        value = ucore.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def client_is_unifi(client: object) -> bool:
    """Determine if a client is a UniFi device."""
    flag = _client_unifi_flag(client)
    if flag is not None:
        return flag
    ucore = _client_ucore_info(client)
    if ucore and _ucore_has_device_info(ucore):
        return True
    vendor = _client_vendor(client)
    if not vendor:
        return False
    normalized = vendor.lower()
    return "ubiquiti" in normalized or "unifi" in normalized


def classify_client_type(client: object) -> str:
    """Classify a client into a device category.

    Detection priority:
    1. UniFi device info (product_line, model)
    2. Display name heuristics
    3. OUI/vendor patterns

    Returns one of: camera, tv, phone, printer, nas, speaker, game_console, iot, client
    """
    ucore = _client_ucore_info(client)
    if ucore:
        category = _classify_by_unifi_info(ucore)
        if category:
            return category

    name = client_display_name(client)
    if name:
        category = _classify_by_name(name)
        if category:
            return category

    vendor = _client_vendor(client)
    if vendor:
        category = _classify_by_vendor(vendor)
        if category:
            return category

    return "client"


def client_display_name(client: object) -> str | None:
    """Get display name for a client."""
    name = first_string_field(client, "name")
    if name:
        return name
    preferred = _client_ucore_display_name(client)
    if preferred:
        return preferred
    return first_string_field(client, "hostname", "mac")
