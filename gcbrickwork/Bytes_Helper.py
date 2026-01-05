# Based on some functions that were created in: https://github.com/LagoLunatic/gclib/blob/master/gclib/fs_helpers.py

from io import BytesIO
import struct


class ByteHelperError(Exception):
    pass

GC_ENCODING_STR = "shift_jis"

def read_u8(data: BytesIO, offset: int) -> int:
    data_length = data.seek(offset, 2)
    length = 1
    if offset + length > data_length:
        raise ByteHelperError(f"Offset {str(offset)} + Length {str(length)} is longer than the data size {str(data_length)}.")
    data.seek(offset)
    return struct.unpack(">B", data.read(length))[0]

def read_u16(data: BytesIO, offset: int) -> int:
    data_length = data.seek(offset, 2)
    length = 2
    if offset + length > data_length:
        raise ByteHelperError(f"Offset {str(offset)} + Length {str(length)} is longer than the data size {str(data_length)}.")
    data.seek(offset)
    return struct.unpack(">H", data.read(length))[0]

def read_u32(data: BytesIO, offset: int) -> int:
    data_length = data.seek(offset, 2)
    length = 4
    if offset + length > data_length:
        raise ByteHelperError(f"Offset {str(offset)} + Length {str(length)} is longer than the data size {str(data_length)}.")
    data.seek(offset)
    return struct.unpack(">I", data.read(length))[0]

def read_s32(data: BytesIO, offset: int) -> int:
    data_length = data.seek(offset, 2)
    length = 4
    if offset + length > data_length:
        raise ByteHelperError(f"Offset {str(offset)} + Length {str(length)} is longer than the data size {str(data_length)}.")
    data.seek(offset)
    return struct.unpack(">i", data.read(length))[0]

def read_float(data: BytesIO, offset: int) -> int:
    data_length = data.seek(offset, 2)
    length = 4
    if offset + length > data_length:
        raise ByteHelperError(f"Offset {str(offset)} + Length {str(length)} is longer than the data size {str(data_length)}.")
    data.seek(offset)
    return struct.unpack(">f", data.read(length))[0]


def write_u8(data: BytesIO, offset: int, new_value: int):
    new_bytes = struct.pack(">B", new_value)
    data.seek(offset)
    data.write(new_bytes)

def write_u16(data: BytesIO, offset: int, new_value: int):
    new_bytes = struct.pack(">H", new_value)
    data.seek(offset)
    data.write(new_bytes)

def write_u32(data: BytesIO, offset: int, new_value: int):
    new_bytes = struct.pack(">I", new_value)
    data.seek(offset)
    data.write(new_bytes)

def write_s32(data: BytesIO, offset: int, new_value: int):
    new_bytes = struct.pack(">i", new_value)
    data.seek(offset)
    data.write(new_bytes)

def write_float(data: BytesIO, offset: int, new_value: float):
    new_bytes = struct.pack(">f", new_value)
    data.seek(offset)
    data.write(new_bytes)


def read_str_until_null_character(data: BytesIO, offset: int, max_length: int) -> str:
    data_length = data.seek(offset, 2)
    if (offset + max_length) > data_length:
        raise ByteHelperError(f"Offset {str(offset)} + Length {str(max_length)} is longer than the data size {str(data_length)}.")

    temp_offset = offset
    while temp_offset < data_length:
        data.seek(temp_offset)
        char = data.read(1)
        if char == b"\0":
            break
        temp_offset += 1
        if (temp_offset - offset) == max_length:
            break

    data.seek(offset)
    string = data.read(temp_offset-offset).decode(GC_ENCODING_STR)
    return string

def write_str(data: BytesIO, offset: int, new_string: str, max_length: int, padding_byte: bytes = b"\0"):
    encoded_string = new_string.encode(GC_ENCODING_STR)
    str_len = len(encoded_string)
    if str_len > max_length:
        raise ByteHelperError(f"String \"{new_string}\" is too long (max length: {str(max_length)})")

    padding_length = max_length - str_len
    new_value = encoded_string + (padding_byte * padding_length)

    data.seek(offset)
    data.write(new_value)
