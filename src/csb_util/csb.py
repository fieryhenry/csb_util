from __future__ import annotations
import enum
import io
import struct
from typing import Literal


class ReadError(enum.Enum):
    SUCCESS = 0
    INVALID_CSB_MAGIC = 1
    INVALID_BYTE_ORDER = 2
    INVALID_STRP_MAGIC = 3
    INVALID_LNP_MAGIC = 4
    INVALID_LNT_MAGIC = 5
    INCONSISTENT_TOTAL_LINES = 6
    INCONSISTENT_MAX_COLUMNS = 7
    INCONSISTENT_TOTAL_FIELDS = 8


def read_strp(
    f: io.BufferedReader, byte_order: str
) -> tuple[dict[int, str] | None, ReadError]:
    start_pos = f.tell()

    magic = f.read(4)
    if magic != b"STRP":
        return (None, ReadError.INVALID_STRP_MAGIC)

    block_length = struct.unpack(f"{byte_order}I", f.read(4))[0]

    end_pos = start_pos + block_length

    strings: dict[int, str] = {}

    str_count = struct.unpack(f"{byte_order}Q", f.read(8))[0]

    for _ in range(str_count):
        pos = f.tell()
        string = read_c_string(f)
        strings[pos] = string

    f.seek(end_pos)

    return (strings, ReadError.SUCCESS)


def get_unique_strs(lines: list[list[str]]) -> list[str]:

    strs: list[str] = []
    for line in lines:
        strs.extend(line)
    return list(dict.fromkeys(strs))


def write_strp(
    f: io.BufferedWriter, byte_order: str, lines: list[list[str]]
) -> dict[str, int]:
    f.write(b"STRP")

    strings = get_unique_strs(lines)

    str_map: dict[str, int] = {}

    str_block = io.BytesIO()
    str_block.write(struct.pack(f"{byte_order}Q", len(strings)))
    for string in strings:
        pos = f.tell() + str_block.tell() + 4
        str_map[string] = pos
        write_c_string(str_block, string)

    str_block_data = str_block.getvalue()

    block_length = len(str_block_data)

    f.write(struct.pack(f"{byte_order}I", block_length + 8))
    f.write(str_block_data)

    return str_map


def read_c_string(f: io.BufferedReader):
    string_bytes = bytearray()
    while True:
        byte = f.read(1)
        if byte == b"\x00":
            break
        string_bytes.append(byte[0])

    return string_bytes.decode("utf-8", errors="ignore")


def write_c_string(f: io.BufferedWriter | io.BytesIO, string: str):
    data = string.encode("utf-8", errors="ignore") + b"\x00"
    f.write(data)


def read_lnp(
    f: io.BufferedReader,
    byte_order: str,
    str_map: dict[int, str],
) -> tuple[dict[int, list[str]] | None, ReadError]:
    start_pos = f.tell()

    magic = f.read(4)
    if magic != b"LNP ":
        return (None, ReadError.INVALID_LNP_MAGIC)

    block_length = struct.unpack(f"{byte_order}I", f.read(4))[0]

    end_pos = start_pos + block_length

    total_lines = struct.unpack(f"{byte_order}Q", f.read(8))[0]

    lines: dict[int, list[str]] = {}

    for _ in range(total_lines):
        pos = f.tell()

        column_count = struct.unpack(f"{byte_order}Q", f.read(8))[0]
        line_start_pos = struct.unpack(f"{byte_order}Q", f.read(8))[0]

        f.seek(line_start_pos)

        line: list[str] = []

        for _ in range(column_count):
            str_pos = struct.unpack(f"{byte_order}Q", f.read(8))[0]
            string = str_map[str_pos]
            line.append(string)

        lines[pos] = line

    f.seek(end_pos)

    return (lines, ReadError.SUCCESS)


def write_lnp(
    f: io.BufferedWriter,
    byte_order: str,
    lines: list[list[str]],
    str_map: dict[str, int],
) -> list[int]:
    f.write(b"LNP ")

    line_block = io.BytesIO()

    line_map: list[int] = []
    line_block.write(struct.pack(f"{byte_order}Q", len(lines)))

    for line in lines:
        start_pos = f.tell() + line_block.tell() + 4
        line_block.write(struct.pack(f"{byte_order}Q", len(line)))
        line_block.write(struct.pack(f"{byte_order}Q", start_pos + 16))
        for val in line:
            pos = str_map[val]
            line_block.write(struct.pack(f"{byte_order}Q", pos))

        line_map.append(start_pos)

    line_block_data = line_block.getvalue()

    f.write(struct.pack(f"{byte_order}I", len(line_block_data) + 8))
    f.write(line_block_data)

    return line_map


def read_lnt(
    f: io.BufferedReader, byte_order: str, line_map: dict[int, list[str]]
) -> tuple[list[list[str]] | None, ReadError]:
    start_pos = f.tell()

    magic = f.read(4)
    if magic != b"LNT ":
        return (None, ReadError.INVALID_LNT_MAGIC)

    block_length = struct.unpack(f"{byte_order}I", f.read(4))[0]

    end_pos = start_pos + block_length

    total_lines = struct.unpack(f"{byte_order}Q", f.read(8))[0]

    lines: list[list[str]] = []

    for _ in range(total_lines):
        line_pos = struct.unpack(f"{byte_order}Q", f.read(8))[0]
        line = line_map[line_pos]
        lines.append(line)

    f.seek(end_pos)

    return (lines, ReadError.SUCCESS)


def write_lnt(
    f: io.BufferedWriter,
    byte_order: str,
    lines: list[list[str]],
    line_map: list[int],
):
    f.write(b"LNT ")

    line_block = io.BytesIO()

    line_block.write(struct.pack(f"{byte_order}Q", len(lines)))
    for pos in line_map:
        line_block.write(struct.pack(f"{byte_order}Q", pos))

    line_block_data = line_block.getvalue()

    f.write(struct.pack(f"{byte_order}I", len(line_block_data) + 8))
    f.write(line_block_data)


def read_csb(
    f: io.BufferedReader, validate_result: bool = True
) -> tuple[list[list[str]] | None, ReadError]:
    magic = f.read(4)
    if magic != b"CSB ":
        return (None, ReadError.INVALID_CSB_MAGIC)

    order_bytes = f.read(2)
    if order_bytes == b"\xFF\xFE":
        byte_order = "<"
    elif order_bytes == b"\xFE\xFF":
        byte_order = ">"
    else:
        return (None, ReadError.INVALID_BYTE_ORDER)

    f.read(6)  # idk

    total_fields = struct.unpack(f"{byte_order}I", f.read(4))[0]
    max_columns = struct.unpack(f"{byte_order}I", f.read(4))[0]
    total_lines = struct.unpack(f"{byte_order}I", f.read(4))[0]

    str_map, err = read_strp(f, byte_order)
    if str_map is None:
        return (None, err)

    line_map, err = read_lnp(f, byte_order, str_map)
    if line_map is None:
        return (None, err)

    lines, err = read_lnt(f, byte_order, line_map)
    if lines is None:
        return (None, err)

    if validate_result:
        if len(lines) != total_lines:
            return (None, ReadError.INCONSISTENT_TOTAL_LINES)

        counted_fields = 0
        counted_columns = 0
        for line in lines:
            line_len = len(line)
            counted_columns = max(counted_columns, line_len)
            counted_fields += line_len

        if counted_fields != total_fields:
            return (None, ReadError.INCONSISTENT_TOTAL_FIELDS)

        if counted_columns != max_columns:
            return (None, ReadError.INCONSISTENT_MAX_COLUMNS)

    return (lines, ReadError.SUCCESS)


def write_csb(
    f: io.BufferedWriter, lines: list[list[str]], byte_order: Literal["<", ">"] = "<"
):
    f.write(b"CSB ")

    if byte_order == "<":
        order_bytes = b"\xFF\xFE"
    else:
        order_bytes = b"\xFE\xFF"

    f.write(order_bytes)

    f.write(b"\x00\x01\xFF\xFF\x00\x00")  # idk what these do

    total_fields = 0
    max_columns = 0
    total_lines = len(lines)
    for line in lines:
        line_len = len(line)
        total_fields += line_len
        max_columns = max(line_len, max_columns)

    f.write(struct.pack(f"{byte_order}I", total_fields))
    f.write(struct.pack(f"{byte_order}I", max_columns))
    f.write(struct.pack(f"{byte_order}I", total_lines))

    str_map = write_strp(f, byte_order, lines)
    line_map = write_lnp(f, byte_order, lines, str_map)
    write_lnt(f, byte_order, lines, line_map)


def write_csv(f: io.TextIOWrapper, lines: list[list[str]]):
    f.write("\n".join([",".join(line) for line in lines]))


def read_csv(f: io.TextIOWrapper) -> list[list[str]]:
    lines: list[list[str]] = []
    for line in f.read().split("\n"):
        lines.append(line.split(","))
    return lines
