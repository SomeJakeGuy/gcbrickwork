from dataclasses import dataclass
from enum import IntEnum

from .Bytes_Helper import *


JMP_HEADER_SIZE: int = 12
JMP_STRING_BYTE_LENGTH = 32

type JMPEntry = dict[JMPFieldHeader, int | str | float]

class JMPFileError(Exception):
    pass

class JMPType(IntEnum):
    Int = 0
    Str = 1
    Flt = 2 # Float based values.

@dataclass
class JMPFieldHeader:
    """
    JMP File Headers are comprised of 12 bytes in total.
    The first 4 bytes represent the field's hash. Currently, it is un-known how a field's name becomes a hash.
        There may be specific games that have created associations from field hash -> field internal name.
    The second 4 bytes represent the field's bitmask
    The next 2 bytes represent the starting byte for the field within a given data line in the JMP file.
    The second to last byte represents the shift bytes, which is required when reading certain field data.
    The last byte represents the data type, see JMPType for value -> type conversion
    """
    field_hash: int = 0
    field_name: str = None
    field_bitmask: int = 0
    field_start_byte: int = 0
    field_shift_byte: int = 0
    field_data_type: int = -1

    def __init__(self, jmp_hash: int, jmp_bitmask: int, jmp_startbyte: int, jmp_shiftbyte: int, jmp_data_type: int):
        self.field_hash = jmp_hash
        self.field_name = str(self.field_hash)
        self.field_bitmask = jmp_bitmask
        self.field_start_byte = jmp_startbyte
        self.field_shift_byte = jmp_shiftbyte
        self.field_data_type = jmp_data_type

    def __str__(self):
        return str(self.__dict__)


class JMP:
    """
    JMP Files are table-structured format files that contain a giant header block and data entry block.
        The header block contains the definition of all field headers (columns) and field level data
        The data block contains the table row data one line at a time. Each row is represented as a single list index,
            where a dictionary maps the key (column) to the value.
    JMP Files also start with 16 bytes that are useful to explain the rest of the structure of the file.
    """
    fields: list[JMPFieldHeader] = []
    data_entries: list[JMPEntry] = []
    single_entry_size: int = 0 # TODO Need to calculate this.

    def __init__(self, input_fields: list[JMPFieldHeader], data_entries: list[JMPEntry]):
        self.fields = input_fields
        self.data_entries = data_entries

    @classmethod
    def load_jmp(cls, jmp_data: BytesIO):
        """
        Loads the first 16 bytes to determine (in order): how many data entries there are, how many fields are defined,
            Gives the total size of the header block, and the number of data files that are defined in the file.
        Each of these are 4 bytes long, with the first 8 bytes being signed integers and the second 8 bytes are unsigned.
        It should be noted that there will be extra bytes typically at the end of a jmp file, which are padded with "@".
            These paddings can be anywhere from 1 to 31 bytes, up until the total bytes is divisible by 32.
        """
        original_file_size = jmp_data.seek(0, 2)

        # Get important file bytes
        data_entry_count: int = read_s32(jmp_data, 0)
        field_count: int = read_s32(jmp_data, 4)
        header_block_size: int = read_u32(jmp_data, 8)
        single_entry_size: int = read_u32(jmp_data, 12)

        # Load all headers of this file
        header_block_bytes: bytes = jmp_data.read(header_block_size - 16) # Field details start after the above 16 bytes
        if (len(header_block_bytes) % JMP_HEADER_SIZE != 0 or not (len(header_block_bytes) / JMP_HEADER_SIZE) ==
            field_count or header_block_size > original_file_size):
            raise JMPFileError("When trying to read the header block of the JMP file, the size was bigger than " +
                "expected and could not be parsed properly.")
        fields = _load_headers(jmp_data, field_count)

        # Load all data entries / rows of this table.
        if header_block_size + (single_entry_size * data_entry_count) > original_file_size:
            raise JMPFileError("When trying to read the date entries block of the JMP file, the size was bigger than " +
                "expected and could not be parsed properly.")
        entries = _load_entries(jmp_data, data_entry_count, single_entry_size, header_block_size, fields)

        return cls(fields, entries)

    def map_hash_to_name(self, field_names: dict[int, str]):
        """
        Using the user provided dictionary, maps out the field hash to their designated name, making it easier to query.
        """
        for key, val in field_names.items():
            jmp_field: JMPFieldHeader = self.find_field_by_hash(key)
            if jmp_field is None:
                continue
            jmp_field.field_name = val

    def find_field_by_hash(self, jmp_field_hash: int) -> JMPFieldHeader | None:
        return next((jfield for jfield in self.fields if jfield.field_hash == jmp_field_hash), None)

    def find_field_by_name(self, jmp_field_name: str) -> JMPFieldHeader | None:
        return next((jfield for jfield in self.fields if jfield.field_name == jmp_field_name), None)

    def create_new_jmp(self) -> BytesIO:
        """
        Create a new the file from the fields / data_entries, as new entries / headers could have been added. Keeping the
        original structure of: Important 16 header bytes, Header Block, and then the Data entries block.
        """
        local_data = BytesIO()
        new_header_size: int = len(self.fields) * JMP_HEADER_SIZE + 16
        write_s32(local_data, 0, len(self.data_entries)) # Amount of data entries
        write_s32(local_data, 4, len(self.fields)) # Amount of JMP fields
        write_u32(local_data, 8, new_header_size) # Size of Header Block
        write_u32(local_data, 12, self.single_entry_size) # Size of a single data entry

        current_offset: int = self._update_headers(local_data)
        self._update_entries(local_data, current_offset)

        # JMP Files are then padded with @ if their file size are not divisible by 32.
        curr_length = local_data.seek(0, 2)
        local_data.seek(curr_length)
        if curr_length % 32 > 0:
            write_str(local_data, curr_length, "", curr_length % 32, "@".encode(GC_ENCODING_STR))
        return local_data

    def _update_headers(self, local_data: BytesIO) -> int:
        # Add the individual headers to complete the header block
        current_offset: int = 16
        for jmp_header in self.fields:
            write_u32(local_data, current_offset, jmp_header.field_hash)
            write_u32(local_data, current_offset + 4, jmp_header.field_bitmask)
            write_u16(local_data, current_offset + 8, jmp_header.field_start_byte)
            write_u8(local_data, current_offset + 10, jmp_header.field_shift_byte)
            write_u8(local_data, current_offset + 11, jmp_header.field_data_type)
            current_offset += JMP_HEADER_SIZE

        return current_offset

    def _update_entries(self, local_data: BytesIO, current_offset: int):
        # Add the all the data entry lines.
        for line_entry in self.data_entries:
            for key, val in line_entry.items():
                match key.field_data_type:
                    case JMPType.Int:
                        new_val = (val << key.field_shift_byte) | key.field_bitmask
                        write_u32(local_data, current_offset + key.field_start_byte, new_val)
                    case JMPType.Str:
                        write_str(local_data, current_offset + key.field_start_byte, val, JMP_STRING_BYTE_LENGTH)
                    case JMPType.Flt:
                        write_float(local_data, current_offset + key.field_start_byte, val)
            current_offset += self.single_entry_size


def _load_headers(header_data: BytesIO, field_count: int) -> list[JMPFieldHeader]:
    """
    Gets the list of all JMP headers that are available in this file. See JMPFieldHeader for exact structure.
    """
    current_offset: int = 16
    field_headers: list[JMPFieldHeader] = []

    for jmp_entry in range(field_count):
        entry_hash: int = read_u32(header_data, current_offset)
        entry_bitmask: int = read_u32(header_data, current_offset + 4)
        entry_startbyte: int = read_u16(header_data, current_offset + 8)
        entry_shiftbyte: int = read_u8(header_data, current_offset + 10)
        entry_type: int = read_u8(header_data, current_offset + 11)
        if not entry_type in JMPType:
            raise ValueError("Unimplemented JMP type detected: " + str(entry_type))
        field_headers.append(JMPFieldHeader(entry_hash, entry_bitmask, entry_startbyte, entry_shiftbyte, entry_type))
        current_offset += JMP_HEADER_SIZE
    return field_headers

def _load_entries(entry_data: BytesIO, entry_count: int, entry_size: int, header_size: int,
    field_list: list[JMPFieldHeader]) -> list[JMPEntry]:
    """
    Loads all the rows one by one and populates each column's value per row.
    """
    data_entries: list[JMPEntry] = []

    for current_entry in range(entry_count):
        new_entry: JMPEntry = {}
        data_entry_start: int = (current_entry * entry_size) + header_size

        for jmp_header in field_list:
            match jmp_header.field_data_type:
                case JMPType.Int:
                    current_val: int = read_u32(entry_data, data_entry_start + jmp_header.field_start_byte)
                    new_entry[jmp_header] = (current_val >> jmp_header.field_shift_byte) & jmp_header.field_bitmask
                case JMPType.Str:
                    new_entry[jmp_header] = read_str_until_null_character(entry_data,
                        data_entry_start + jmp_header.field_start_byte, JMP_STRING_BYTE_LENGTH)
                case JMPType.Flt:
                    new_entry[jmp_header] = read_float(entry_data,  data_entry_start + jmp_header.field_start_byte)
        data_entries.append(new_entry)

    return data_entries
