import struct
import lz4.block
import pytest
from roblox_string_scrapper.reader import RbxReader, RbxChunk


def build_test_rbxl_header(num_types: int = 1, num_instances: int = 1) -> bytes:
    magic = b"<roblox!\x89\xff\x0d\x0a\x1a\x0a"
    version = struct.pack("<H", 0)
    counts = struct.pack("<II", num_types, num_instances)
    reserved = b"\x00" * 8
    return magic + version + counts + reserved


def build_lz4_chunk(chunk_name: bytes, payload: bytes, force_raw: bool = False) -> bytes:
    if force_raw:
        comp_len = 0
        decomp_len = len(payload)
        header = chunk_name + struct.pack("<III", comp_len, decomp_len, 0)
        return header + payload
    
    compressed = lz4.block.compress(payload, store_size=False)
    comp_len = len(compressed)
    decomp_len = len(payload)
    # 4-byte chunk name, 4-byte comp len, 4-byte decomp len, 4-byte reserved
    header = chunk_name + struct.pack("<III", comp_len, decomp_len, 0)
    return header + compressed


def test_valid_header_parsing():
    raw = build_test_rbxl_header(2, 10)
    reader = RbxReader(raw)
    assert reader.num_types == 2
    assert reader.num_instances == 10


def test_invalid_magic_raises():
    corrupted = b"NOT_ROBLOX_DATA_HERE_123456789"
    with pytest.raises(ValueError, match="Invalid Roblox file header"):
        RbxReader(corrupted)


def test_chunk_decompression():
    test_payload = b"Hello Roblox Chunk Storage System Test String"
    chunk_bytes = build_lz4_chunk(b"PROP", test_payload)
    
    full_stream = build_test_rbxl_header() + chunk_bytes + build_lz4_chunk(b"END\x00", b"")
    reader = RbxReader(full_stream)
    chunks = list(reader.iter_chunks())
    
    assert len(chunks) == 2
    assert chunks[0].name == "PROP"
    assert chunks[0].data == test_payload
    assert chunks[1].name == "END\x00"


def test_uncompressed_chunk_fallback():
    raw_payload = b"print('fallback uncompressed chunk data')"
    chunk_bytes = build_lz4_chunk(b"PROP", raw_payload, force_raw=True)
    
    full_stream = build_test_rbxl_header() + chunk_bytes + build_lz4_chunk(b"END\x00", b"")
    reader = RbxReader(full_stream)
    chunks = list(reader.iter_chunks())
    assert chunks[0].data == raw_payload


def test_truncated_stream_stops_gracefully():
    raw = build_test_rbxl_header() + b"PROP\x05\x00"
    reader = RbxReader(raw)
    chunks = list(reader.iter_chunks())
    assert len(chunks) == 0
