import io
from dataclasses import dataclass
from enum import IntEnum

from .Bytes_Helper import *


type PRMValue = bytes | int | PRMColor | PRMVector


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
        return (f"Red Val: 0x{hex(self.red_value)}; Green Val: 0x{hex(self.green_value)}; " +
                f"Blue Val: 0x{hex(self.blue_value)}; Opacity Val: 0x{hex(self.green_value)}")


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


    def __len__(self):
        return 12


@dataclass
class PRMFieldEntry:
    """
    PRM fields are defined one after the other within a PRM file and have the following data structure:
        An unsigned short to get the field's hash value.
        An unsigned short to get the field name's length
        Based on the previous short, read the next X number of bytes to get the field name as a str.
        An unsigned integer to then figure out the type of data the value is stored as.
        Based on that data type, get the corresponding value and converted type
            Int/Floats are NOT converted due to the fact there is NO indicator to know when to use either.
            Except for Color / Vector, as they have their own defined types.
    """
    field_hash: int = 0
    field_name: str = None
    field_type: PRMType = None
    field_value: PRMValue = None


    def __init__(self, entry_hash: int, name: str, entry_type: PRMType, value: PRMValue):
        self.field_hash = entry_hash
        self.field_name = name
        self.field_type = entry_type
        self.field_value = value


    def __str__(self):
        return f"Field Hash: {str(self.field_hash)}; Name: {self.field_name}; Value: {str(self.field_value)}"


class PRM:
    """ PRM Files are parameterized files that have one or more parameters that can be changed/manipulated.
        These files typically host values that would change frequently and are read by the program at run-time.
        PRM Files start with 4 bytes as an unsigned int to tell how many parameters are defined.
        The structure of the entries can be found in PRMFieldEntry. """
    data_entries: list[PRMFieldEntry] = []


    def __init__(self, input_entries: list[PRMFieldEntry]):
        self.data_entries = input_entries


    @classmethod
    def load_prm(cls, prm_data: BytesIO):
        """ Loads the various prm values from the file into a list of PRMFieldEntries
        """
        entry_value: PRMValue | None = None
        prm_entries: list[PRMFieldEntry] = []
        current_offset: int = 0
        num_of_entries: int = read_u32(prm_data, 0)
        current_offset += 4

        for entry_num in range(num_of_entries):
            entry_hash: int = read_u16(prm_data, current_offset)
            entry_name_length: int = read_u16(prm_data, current_offset + 2)
            entry_name: str = read_str_until_null_character(prm_data, current_offset + 4, entry_name_length)
            current_offset += entry_name_length + 4

            entry_size: int = read_u32(prm_data, current_offset)
            current_offset += 4
            match entry_size:
                case PRMType.Byte | PRMType.Number:
                    entry_value: bytes = prm_data.read(entry_size)
                case PRMType.Short:
                    entry_value: int = read_u16(prm_data, current_offset)
                case PRMType.Vector:
                    float_one: float = read_float(prm_data, current_offset)
                    float_two: float = read_float(prm_data, current_offset + 4)
                    float_three: float = read_float(prm_data, current_offset + 8)
                    entry_value: PRMVector = PRMVector(float_one, float_two, float_three)
                case PRMType.Color:
                    color_one: int = read_u32(prm_data, current_offset)
                    color_two: int = read_u32(prm_data, current_offset + 4)
                    color_three: int = read_u32(prm_data, current_offset + 8)
                    color_four: int = read_u32(prm_data, current_offset + 12)
                    entry_value: PRMColor = PRMColor(color_one, color_two, color_three, color_four)
                case _:
                    raise ValueError("Unimplemented PRM type detected: " + str(entry_size))
            current_offset += entry_size
            prm_entries.append(PRMFieldEntry(entry_hash, entry_name, entry_size, entry_value))

        return cls(prm_entries)


    def create_new_prm(self) -> BytesIO:
        """
        Using the provided fields and values, re-create the file in the data structure described in load_prm, which
            at a high level requires the first four bytes to be the number of PRM fields, then the PRM fields/data.
        It should be noted that there is NO padding at the end of these files.
        """
        current_offset: int = 0
        local_data = io.BytesIO()
        write_u32(local_data, 0, len(self.data_entries))
        current_offset += 4

        for prm_entry in self.data_entries:
            write_u16(local_data, current_offset, prm_entry.field_hash)
            write_u16(local_data, current_offset + 2, len(prm_entry.field_name))
            write_str(local_data, current_offset + 4, prm_entry.field_name, len(prm_entry.field_name))
            current_offset += len(prm_entry.field_name) + 4

            write_u32(local_data, current_offset, prm_entry.field_type)
            current_offset += 4
            match prm_entry.field_type:
                case PRMType.Byte:
                    write_u8(local_data, current_offset, int.from_bytes(prm_entry.field_value, "big"))
                case PRMType.Short:
                    write_u16(local_data, current_offset, prm_entry.field_value)
                case PRMType.Number:
                    if isinstance(prm_entry.field_value, float):
                        write_float(local_data, current_offset, prm_entry.field_value)
                    elif isinstance(prm_entry.field_value, int):
                        write_u32(local_data, current_offset, prm_entry.field_value)
                    elif isinstance(prm_entry.field_value, bytes):
                        if len(prm_entry.field_value) > 4:
                            raise ValueError(f"PRM field '{prm_entry.field_name}' can only have up to '4' bytes.")
                        elif len(prm_entry.field_value) < 4:
                            prm_entry.field_value = (b"\0" * (4 - len(prm_entry.field_value))) + prm_entry.field_value
                        local_data.seek(current_offset)
                        local_data.write(prm_entry.field_value)
                    else:
                        raise ValueError(f"Unexpected PRM Number value of type {type(prm_entry.field_value)}")
                case PRMType.Vector:
                    if not isinstance(prm_entry.field_value, PRMVector):
                        raise ValueError(f"Unexpected PRMVector value of type {type(prm_entry.field_value)}")
                    val: PRMVector = prm_entry.field_value
                    write_float(local_data, current_offset, val.float_one)
                    write_float(local_data, current_offset + 4, val.float_two)
                    write_float(local_data, current_offset + 8, val.float_three)
                case PRMType.Color:
                    if not isinstance(prm_entry.field_value, PRMColor):
                        raise ValueError(f"Unexpected PRMColor value of type {type(prm_entry.field_value)}")
                    val: PRMColor = prm_entry.field_value
                    write_u32(local_data, current_offset, val.red_value)
                    write_u32(local_data, current_offset + 4, val.green_value)
                    write_u32(local_data, current_offset + 8, val.blue_value)
                    write_u32(local_data, current_offset + 12, val.opacity)
            current_offset += prm_entry.field_type

        return local_data


    def get_prm_entry(self, prm_field: str | int) -> PRMFieldEntry:
        """Gets a PRMFieldEntry based on a provided field name/hash."""
        if isinstance(prm_field, str):
            return next(prm_entry for prm_entry in self.data_entries if prm_entry.field_name == prm_field)
        elif isinstance(prm_field, int):
            return next(prm_entry for prm_entry in self.data_entries if prm_entry.field_hash == prm_field)
        else:
            raise ValueError(f"Cannot index PRMFieldEntry with value of type {type(prm_field)}")


    def update_prm_entry(self, prm_field: str | int, prm_value: PRMValue):
        """Updates a PRMFieldEntry based on a provided field/value."""
        prm_entry: PRMFieldEntry = self.get_prm_entry(prm_field)
        prm_entry.field_value = prm_value