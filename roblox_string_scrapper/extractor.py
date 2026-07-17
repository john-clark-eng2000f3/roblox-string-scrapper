import io
import re
import struct
from dataclasses import dataclass, field
from typing import List, Set, Dict
from roblox_string_scrapper.reader import Chunk

URL_REGEX = re.compile(rb'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s"\'<>`\x00-\x1f]*)?')
ASSET_ID_REGEX = re.compile(rb'(?:rbxassetid://|asset/\?id=|rbxasset://|rbxthumb://)(\d+)')
WEBHOOK_REGEX = re.compile(rb'https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[a-zA-Z0-9_\-]+')

# Look for printable strings of reasonable length
PRINTABLE_REGEX = re.compile(rb'[\x20-\x7E\t\r\n]{4,}')


@dataclass
class ExtractionResult:
    shared_strings: List[str] = field(default_factory=list)
    urls: Set[str] = field(default_factory=set)
    webhooks: Set[str] = field(default_factory=set)
    asset_ids: Set[int] = field(default_factory=set)
    remote_names: Set[str] = field(default_factory=set)
    scripts: Dict[str, str] = field(default_factory=dict)
    raw_strings: List[str] = field(default_factory=list)


def parse_sstr_chunk(chunk_data: bytes) -> List[bytes]:
    stream = io.BytesIO(chunk_data)
    if len(chunk_data) < 8:
        return []
    _version, count = struct.unpack("<II", stream.read(8))
    
    # TODO: handle compressed string tables in older version 0 chunks if we hit any in the wild
    strings = []
    for _ in range(count):
        stream.seek(16, io.SEEK_CUR)  # md5 digest
        len_buf = stream.read(4)
        if len(len_buf) < 4:
            break
        str_len = struct.unpack("<I", len_buf)[0]
        val = stream.read(str_len)
        strings.append(val)
    return strings


def parse_inst_chunk(data: bytes) -> tuple:
    # class_id (4 bytes), class_name (str), is_service (1 byte), inst_count (4 bytes), inst_ids
    if len(data) < 9:
        return 0, "", 0, []
    stream = io.BytesIO(data)
    class_id = struct.unpack("<I", stream.read(4))[0]
    name_len = struct.unpack("<I", stream.read(4))[0]
    class_name = stream.read(name_len).decode("latin1", errors="ignore")
    _is_service = stream.read(1)
    inst_count = struct.unpack("<I", stream.read(4))[0]
    
    # IDs are zigzag delta-encoded
    raw_ids = []
    for _ in range(inst_count):
        b = stream.read(4)
        if len(b) < 4:
            break
        raw_ids.append(struct.unpack(">i", b)[0])
    
    # decode interleaved delta
    inst_ids = []
    curr = 0
    for v in raw_ids:
        curr += v
        inst_ids.append(curr)
        
    return class_id, class_name, inst_count, inst_ids


def scan_chunks(chunks: List[Chunk]) -> ExtractionResult:
    result = ExtractionResult()
    remote_class_ids = set()
    
    for chunk in chunks:
        for u in URL_REGEX.findall(chunk.data):
            decoded = u.decode("latin1", errors="ignore")
            result.urls.add(decoded)
            if b"api/webhooks" in u:
                result.webhooks.add(decoded)
                
        for aid in ASSET_ID_REGEX.findall(chunk.data):
            try:
                result.asset_ids.add(int(aid))
            except ValueError:
                pass
                
        if chunk.name == "INST":
            cid, cname, _, _ = parse_inst_chunk(chunk.data)
            if cname in ("RemoteEvent", "RemoteFunction", "UnreliableRemoteEvent"):
                remote_class_ids.add(cid)
                
        elif chunk.name == "SSTR":
            for raw in parse_sstr_chunk(chunk.data):
                try:
                    result.shared_strings.append(raw.decode("utf-8"))
                except UnicodeDecodeError:
                    result.shared_strings.append(raw.decode("latin1", errors="replace"))
                    
        elif chunk.name == "PROP":
            # find lua scripts embedded as raw text in properties
            # check if chunk carries Source property (type 0x01 string)
            if len(chunk.data) > 10:
                stream = io.BytesIO(chunk.data)
                _cid = struct.unpack("<I", stream.read(4))[0]
                prop_len = struct.unpack("<I", stream.read(4))[0]
                prop_name = stream.read(prop_len).decode("latin1", errors="ignore")
                prop_type = stream.read(1)
                
                # type 0x01 is string/buffer
                if prop_name in ("Source", "LinkedSource", "ScriptGuid") and prop_type == b"\x01":
                    # strings are array of [len + text]
                    while True:
                        slen_bytes = stream.read(4)
                        if len(slen_bytes) < 4:
                            break
                        slen = struct.unpack("<I", slen_bytes)[0]
                        code = stream.read(slen)
                        if len(code) == slen and slen > 0:
                            # if Luau bytecode (starts with version byte e.g. \x03 or \x04 or \x05 or -- comment)
                            text = code.decode("utf-8", errors="ignore")
                            if text.strip():
                                result.scripts[f"{prop_name}_{len(result.scripts)}"] = text
                                
        # extract generic printable strings that look useful
        for m in PRINTABLE_REGEX.finditer(chunk.data):
            s = m.group(0).decode("latin1", errors="ignore").strip()
            if len(s) >= 6 and not s.startswith("http") and not s.isdigit():
                result.raw_strings.append(s)
                
    return result
