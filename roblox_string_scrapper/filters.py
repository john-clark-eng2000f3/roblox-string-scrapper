import re
import math
from collections import Counter

# noisy property names and class metadata that studio dumps into PROP chunks
ENGINE_INTERNALS = {
    "Instance",
    "Workspace",
    "DataModel",
    "Camera",
    "Terrain",
    "Part",
    "CFrame",
    "Vector3",
    "Color3",
    "BrickColor",
    "PhysicalProperties",
    "SharedString",
    "Attributes",
    "Tags",
    "UniqueId",
    "HistoryId",
    "SourceAssetId",
    "Deflate",
    "Zstd",
    "BinaryFormatVersion",
    "Humanoid",
    "ScriptContext",
    "RunService",
    "Players",
    "ReplicatedStorage",
    "ServerStorage",
    "ServerScriptService",
    "StarterGui",
    "StarterPlayer",
    "StarterPlayerScripts",
    "StarterCharacterScripts",
}

_HEX_PATTERN = re.compile(r"^[0-9a-fA-F]{24,}$|^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_REPEATED_PUNCT = re.compile(r"^[\W_]{3,}$")
_GUID_NOISE = re.compile(r"^[0-9A-Z]{32}$")


def is_garbage(s: str, min_len: int = 4, max_entropy: float = 4.8) -> bool:
    """Quick filter to drop unprintable chunks, binary residues, and noisy hashes."""
    if len(s) < min_len:
        return True
    
    # check if printable characters ratio is way too low
    printable_count = sum(1 for c in s if 32 <= ord(c) <= 126 or c in "\n\r\t")
    if printable_count / len(s) < 0.85:
        return True

    clean = s.strip()
    if _REPEATED_PUNCT.match(clean):
        return True

    if _HEX_PATTERN.match(clean) or _GUID_NOISE.match(clean):
        return True

    # print(f"debug entropy: {s} -> {calc_entropy(s):.2f}")
    if len(s) > 30 and calc_entropy(s) > max_entropy:
        return True

    return False


def is_engine_internal(s: str) -> bool:
    return s in ENGINE_INTERNALS


def calc_entropy(s: str) -> float:
    # Shannon entropy to spot leftover compressed chunks
    counts = Counter(s)
    total = len(s)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def strip_non_ascii(raw_bytes: bytes) -> str:
    # quick decimate for raw dumps
    return "".join(chr(b) if 32 <= b <= 126 or b in (10, 13, 9) else "" for b in raw_bytes)
