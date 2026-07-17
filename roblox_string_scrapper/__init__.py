"""CLI tool to parse binary Roblox files and dump strings and scripts."""

from roblox_string_scrapper.reader import BinaryRobloxFile
from roblox_string_scrapper.extractor import (
    extract_raw_strings,
    extract_remote_events,
    extract_scripts,
    extract_asset_ids,
)

__version__ = "0.2.1"

__all__ = [
    "BinaryRobloxFile",
    "extract_raw_strings",
    "extract_remote_events",
    "extract_scripts",
    "extract_asset_ids",
]
