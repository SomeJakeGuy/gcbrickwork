import struct
from enum import IntEnum
from io import BytesIO


JMP_HEADER_SIZE: int = 12
JMP_STRING_BYTE_LENGTH = 32

class JMPType(IntEnum):
    Int = 0
    Str = 1
    Flt = 2 # Float based values.


class JMPFieldHeader:
    """
    JMP File Headers are comprised of 12 bytes in total.
    The first 4 bytes represent the field's hash. Currently, it is un-known how a field's name becomes a hash.
        There may be specific games that have created associations from field hash -> field internal name.
    The second 4 bytes represent the field's bitmask
    The next 2 bytes represent the starting bit for the field within a given data line in the JMP file.
    The second to last byte represents the shift bits, which is required when reading certain field data.
    The last byte represents the data type, see JMPType for value -> type conversion
    """
    field_hash: int = 0
    field_name: str = ""
    field_bitmask: int = 0
    field_start_bit: int = 0
    field_shift_bit: int = 0
    field_data_type: int = -1

    def __init__(self, header_bytes: bytes):
        self.field_hash, self.field_bitmask, self.field_start_bit, self.field_shift_bit, self.field_data_type = (
            struct.unpack(">I I H B B", header_bytes))
        if self.field_data_type not in JMPType:
            raise Exception("Unknown JMP Data Type provided: " + str(self.field_data_type))

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
    data: BytesIO = None
    data_entries: list[dict[JMPFieldHeader, int | str | float]] = []

    def __init__(self, jmp_data: BytesIO):
        self.data = jmp_data

    def load_file(self):
        """
        Loads the first 16 bytes to determine (in order): how many data entries there are, how many fields are defined,
            Gives the total size of the header block, and the number of data files that are defined in the file.
        Each of these are 4 bytes long, with the first 8 bytes being signed integers and the second 8 bytes are unsigned.
        It should be noted that there will be extra bytes typically at the end of a jmp file, which are padded with "@".
            These paddings can be anywhere from 1 to 15 bytes, up until the total bytes is divisible by 16.
        """
        self.data.seek(0)
        original_file_size: int = len(self.data.getvalue())

        # Get important file bytes
        data_entry_count: int = int(struct.unpack(">i", self.data.read(4))[0])
        field_count: int = int(struct.unpack(">i", self.data.read(4))[0])
        header_block_size: int = int(struct.unpack(">I", self.data.read(4))[0])
        single_data_entry_size: int = int(struct.unpack(">I", self.data.read(4))[0])

        # Load all headers of this file
        header_block_bytes: bytes = self.data.read(header_block_size - 16) # Field details start after the above 16 bytes
        if len(header_block_bytes) % JMP_HEADER_SIZE != 0 or not (len(header_block_bytes) / JMP_HEADER_SIZE) == field_count:
            raise Exception("When trying to read the header block of the JMP file, the size was bigger than expected " +
                "and could not be parsed properly.")
        self.data.seek(16) # Start after the previous important 16 bytes.
        jmp_headers: list[JMPFieldHeader] = self._load_headers(field_count)

        # Load all data entries / rows of this table.
        self._load_entries(data_entry_count, single_data_entry_size, jmp_headers)


    def _load_headers(self, field_count: int) -> list[JMPFieldHeader]:
        """
        Gets the list of all JMP headers that are available in this file.
        """
        field_headers: list[JMPFieldHeader] = []

        for _ in range(field_count):
            field_headers.append(JMPFieldHeader(self.data.read(JMP_HEADER_SIZE)))
        return field_headers

    def _load_entries(self, data_entry_count: int, data_entry_size: int, field_list: list[JMPFieldHeader]):
        """
        Loads all the rows one by one and populates each column's value per row.
        """

        for current_entry in range(data_entry_count):
            new_entry: dict[JMPFieldHeader, int | str | float] = {}
            data_entry_start: int = current_entry * data_entry_size

            for jmp_header in field_list:
                self.data.seek(data_entry_start + jmp_header.field_start_bit)

                match jmp_header.field_data_type:
                    case JMPType.Int:
                        current_val: int = int(struct.unpack(">I", self.data.read(4))[0])
                        new_entry[jmp_header] = (current_val & jmp_header.field_bitmask) >> jmp_header.field_shift_bit
                    case JMPType.Str:
                        new_entry[jmp_header] = self.data.read(JMP_STRING_BYTE_LENGTH).decode("shift_jis").rstrip("\0")
                    case JMPType.Flt:
                        new_entry[jmp_header] = float(struct.unpack(">f", self.data.read(4))[0])

            self.data_entries.append(new_entry)