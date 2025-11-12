import io
from dataclasses import dataclass
from enum import IntEnum

from .Bytes_Helper import *


class PRMType(IntEnum):
    Byte = 1
    Short = 2
    Number = 4
    Vector = 12 # Ties out to PRMVector
    Color = 16 # Ties out to PRMColor


@dataclass
class PRMColor:
    """C/C++ Clr (color) object representation"""
    red_value: int = 0
    green_value: int = 0
    blue_value: int = 0
    opacity: int = 0

    def __init__(self, red: int, green: int, blue: int, opacity: int):
        self.red_value = red
        self.green_value = green
        self.blue_value = blue
        self.opacity = opacity

    def __str__(self):
        return (f"Red Val: {str(self.red_value)}; Green Val: {str(self.green_value)}; " +
                f"Blue Val: {str(self.blue_value)}; Opacity Val: {str(self.green_value)}")

    def __len__(self):
        return 16


@dataclass
class PRMVector:
    """C/C++ Vector3 object equivalent. Float representation of things like positions, scale, directions, etc."""
    float_one: float = 0.0
    float_two: float = 0.0
    float_three: float = 0.0

    def __init__(self, first_float: float, second_float: float, third_float: float):
        self.float_one = first_float
        self.float_two = second_float
        self.float_three = third_float

    def __str__(self):
        return f"First Float: {str(self.float_one)}; Second Float: {str(self.float_two)}; Third Float: {str(self.float_three)}"

    def __len__(self):
        return 12


@dataclass
class PRMFieldEntry:
    """
    PRM fields are defined one after the other within a PRM file and have the following data structure:
        Read an unsigned short to get the field's hash value.
        Read an unsigned short to get the field name's length
        Based on the previous short read, read the next X number of bits to get the field name.
        Read an unsigned integer to then figure out the type of data the value is stored as.
        Based on that data type, get the corresponding value and converted type
            Int/Floats are NOT converted due to the fact there is NO indicator to know when to use either.
    """
    field_hash: int = 0
    field_name: str = None
    field_name_size: int = 0
    field_type: PRMType = None
    field_value: bytes | int | PRMColor | PRMVector = None

    def __init__(self, entry_hash: int, name: str, name_size: int, entry_type: PRMType, value: bytes | int | PRMColor | PRMVector):
        self.field_hash = entry_hash
        self.field_name = name
        self.field_name_size = name_size
        self.field_type = entry_type
        self.field_value = value

    def __str__(self):
        return f"Field Hash: {str(self.field_hash)}; Name: {self.field_name}; Value: {str(self.field_value)}"


class PRM:
    data: BytesIO = None
    data_entries: list[PRMFieldEntry] = []

    def __init__(self, prm_data: BytesIO):
        self.data = prm_data

    def load_file(self) -> None:
        """
        PRM Files are parameterized files that have one or more parameters that can be changed/manipulated.
        These files typically host values that would change frequently and are read by the program at run-time.
        PRM Files start with 4 bytes as an unsigned int to tell how many parameters are defined.
        After the file then reads the fields in the following manner:
            Read an unsigned short to get the field's hash value.
            Read an unsigned short to get the field name's length
            Based on the previous short read, read the next X number of bits to get the field name.
            Read an unsigned integer to then figure out the type of data the value is stored as.
            Based on that data type, get the corresponding value and converted type
                Int/Floats are NOT converted due to the fact there is NO indicator to know when to use either.
        """
        current_offset: int = 0
        num_of_entries: int = read_u32(self.data, 0)
        current_offset += 4

        for entry_num in range(num_of_entries):
            entry_hash: int = read_u16(self.data, current_offset)
            entry_name_length: int = read_u16(self.data, current_offset + 2)
            entry_name: str = read_str_until_null_character(self.data, current_offset + 4, entry_name_length)
            current_offset += entry_name_length + 4

            entry_size: int = read_u32(self.data, current_offset)
            match entry_size:
                case PRMType.Byte | PRMType.Number:
                    entry_value: bytes = self.data.read(entry_size)
                case PRMType.Short:
                    entry_value: int = read_u16(self.data, current_offset)
                case PRMType.Vector:
                    float_one: float = read_float(self.data, current_offset)
                    float_two: float = read_float(self.data, current_offset + 4)
                    float_three: float = read_float(self.data, current_offset + 8)
                    entry_value: PRMVector = PRMVector(float_one, float_two, float_three)
                case PRMType.Color:
                    color_one: int = read_u32(self.data, current_offset)
                    color_two: int = read_u32(self.data, current_offset + 4)
                    color_three: int = read_u32(self.data, current_offset + 8)
                    color_four: int = read_u32(self.data, current_offset + 12)
                    entry_value: PRMColor = PRMColor(color_one, color_two, color_three, color_four)
                case _:
                    raise ValueError("Unimplemented PRM type detected: " + str(entry_size))
            current_offset += entry_size
            self.data_entries.append(PRMFieldEntry(entry_hash, entry_name, entry_name_length, entry_size, entry_value))

    def update_file(self) -> None:
        """
        Using the provided fields and values, re-create the file in the data structure described in load_file, which
            at a high level requires the first four bytes to be the number of PRM fields, then the PRM fields/data.
        It should be noted that there is NO padding at the end of these files.
        """
        current_offset: int = 0
        self.data = io.BytesIO()
        write_u32(self.data, 0, len(self.data_entries))
        current_offset += 4

        for prm_entry in self.data_entries:
            write_u16(self.data, current_offset, prm_entry.field_hash)
            write_u16(self.data, current_offset + 2, prm_entry.field_name_size)
            write_str(self.data, current_offset + 4, prm_entry.field_name, prm_entry.field_name_size)
            current_offset += prm_entry.field_name_size + 4
            match prm_entry.field_type:
                case PRMType.Byte:
                    write_u8(self.data, current_offset, int.from_bytes(prm_entry.field_value, "big"))
                case PRMType.Short:
                    write_u16(self.data, current_offset, prm_entry.field_value)
                case PRMType.Number:
                    write_u32(self.data, current_offset, int.from_bytes(prm_entry.field_value, "big"))
                case PRMType.Vector:
                    val: PRMVector = prm_entry.field_value
                    write_float(self.data, current_offset, val.float_one)
                    write_float(self.data, current_offset + 4, val.float_two)
                    write_float(self.data, current_offset + 8, val.float_three)
                case PRMType.Color:
                    val: PRMColor = prm_entry.field_value
                    write_u32(self.data, current_offset, val.red_value)
                    write_u32(self.data, current_offset + 4, val.green_value)
                    write_u32(self.data, current_offset + 8, val.blue_value)
                    write_u32(self.data, current_offset + 12, val.opacity)
            current_offset+=prm_entry.field_type

    def get_entry(self, field_name: str) -> PRMFieldEntry:
        return next(entry for entry in self.data_entries if entry.field_name == field_name)

    def print_entries(self):
        for _ in self.data_entries:
            print(str(_))