import io
import struct
import lz4.block
from dataclasses import dataclass
from typing import Generator

ROBLOX_HEADER = b"<roblox!\x89\xff\r\n\x1a\n"


class InvalidPlaceFileError(Exception):
    pass


@dataclass
class Chunk:
    name: str
    data: bytes
    compressed_len: int
    uncompressed_len: int


def check_header(stream: io.BytesIO) -> int:
    magic = stream.read(len(ROBLOX_HEADER))
    if magic != ROBLOX_HEADER:
        raise InvalidPlaceFileError("File does not start with Roblox binary header")
    
    version = struct.unpack("<H", stream.read(2))[0]
    # version 0 is standard rbxl/rbxm format
    if version != 0:
        raise InvalidPlaceFileError(f"Unsupported binary version: {version}")
    
    # 4 bytes class count, 4 bytes instance count, 8 reserved bytes
    stream.seek(16, io.SEEK_CUR)
    return version


def read_chunks(data: bytes) -> Generator[Chunk, None, None]:
    """Yields decompressed chunks from binary place or model data."""
    stream = io.BytesIO(data)
    check_header(stream)

    while True:
        name_bytes = stream.read(4)
        if len(name_bytes) < 4:
            break
            
        name = name_bytes.decode("latin1", errors="replace").strip("\x00")
        header_raw = stream.read(12)
        if len(header_raw) < 12:
            break
            
        compressed_len, uncompressed_len, _ = struct.unpack("<III", header_raw)
        
        # Some older tools or specific chunks write uncompressed bytes directly
        # when compressed_len is equal to uncompressed_len and lz4 fails
        if compressed_len == 0:
            chunk_payload = stream.read(uncompressed_len)
            decompressed = chunk_payload
        else:
            raw_payload = stream.read(compressed_len)
            if len(raw_payload) != compressed_len:
                raise InvalidPlaceFileError(f"Truncated chunk payload for {name}")
            
            if uncompressed_len == 0:
                decompressed = b""
            else:
                try:
                    decompressed = lz4.block.decompress(raw_payload, uncompressed_size=uncompressed_len)
                except Exception:
                    # fallback if block header had uncompressed payload raw
                    decompressed = raw_payload
            
        yield Chunk(
            name=name,
            data=decompressed,
            compressed_len=compressed_len,
            uncompressed_len=uncompressed_len
        )
        
        if name.startswith("END"):
            break
