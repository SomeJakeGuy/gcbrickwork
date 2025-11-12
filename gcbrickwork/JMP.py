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
    field_name: str = None
    field_bitmask: int = 0
    field_start_bit: int = 0
    field_shift_bit: int = 0
    field_data_type: int = -1

    def __init__(self, header_bytes: bytes):
        self.field_hash, self.field_bitmask, self.field_start_bit, self.field_shift_bit, self.field_data_type = (
            struct.unpack(">I I H B B", header_bytes))
        if self.field_data_type not in JMPType:
            raise Exception("Unknown JMP Data Type provided: " + str(self.field_data_type))
        self.field_name = str(self.field_hash)

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
    fields: list[JMPFieldHeader] = []
    _single_entry_size: int = 0

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
        original_file_size = self.data.seek(0, 2)

        # Get important file bytes
        self.data.seek(0)
        data_entry_count: int = int(struct.unpack(">i", self.data.read(4))[0])
        field_count: int = int(struct.unpack(">i", self.data.read(4))[0])
        header_block_size: int = int(struct.unpack(">I", self.data.read(4))[0])
        self._single_entry_size: int = int(struct.unpack(">I", self.data.read(4))[0])

        # Load all headers of this file
        header_block_bytes: bytes = self.data.read(header_block_size - 16) # Field details start after the above 16 bytes
        if (len(header_block_bytes) % JMP_HEADER_SIZE != 0 or not (len(header_block_bytes) / JMP_HEADER_SIZE) ==
            field_count or header_block_size > original_file_size):
            raise Exception("When trying to read the header block of the JMP file, the size was bigger than expected " +
                "and could not be parsed properly.")
        self.data.seek(16) # Start after the previous important 16 bytes.
        self.fields = self._load_headers(field_count)

        # Load all data entries / rows of this table.
        self._load_entries(data_entry_count, self._single_entry_size, header_block_size, self.fields)

    def _load_headers(self, field_count: int) -> list[JMPFieldHeader]:
        """
        Gets the list of all JMP headers that are available in this file. See JMPFieldHeader for exact structure.
        """
        field_headers: list[JMPFieldHeader] = []

        for _ in range(field_count):
            field_headers.append(JMPFieldHeader(self.data.read(JMP_HEADER_SIZE)))
        return field_headers

    def _load_entries(self, data_entry_count: int, data_entry_size: int, header_size: int, field_list: list[JMPFieldHeader]):
        """
        Loads all the rows one by one and populates each column's value per row.
        """
        for current_entry in range(data_entry_count):
            new_entry: dict[JMPFieldHeader, int | str | float] = {}
            data_entry_start: int = (current_entry * data_entry_size)+header_size

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

    def map_hash_to_name(self, field_names: dict[int | str, str]):
        """
        Using the user provided dictionary, maps out the field hash to their designated name, making it easier to query.
        """
        for key, val in field_names.items():
            jmp_field: JMPFieldHeader = self.find_field_by_hash(int(key))
            if jmp_field is None:
                continue
            jmp_field.field_name = val

    def find_field_by_hash(self, jmp_field_hash: int) -> JMPFieldHeader | None:
        return next((jfield for jfield in self.fields if jfield.field_hash == jmp_field_hash), None)

    def find_field_by_name(self, jmp_field_name: str) -> JMPFieldHeader | None:
        return next((jfield for jfield in self.fields if jfield.field_name == jmp_field_name), None)

    def update_file(self):
        """
        Recreate the file from the fields / data_entries, as new entries / headers could have been added. Keeping the
        original structure of: Important 16 header bytes, Header Block, and then the Data entries block.
        """
        local_data = BytesIO()
        new_header_size: int = len(self.fields)*JMP_HEADER_SIZE+16
        local_data.write(struct.pack(">I I", len(self.data_entries), len(self.fields)))
        local_data.write(struct.pack(">I I", new_header_size, self._single_entry_size))

        # Add the individual headers to complete the header block
        for jmp_header in self.fields:
            local_data.write(struct.pack(">I I H B B", jmp_header.field_hash, jmp_header.field_bitmask,
                jmp_header.field_start_bit, jmp_header.field_shift_bit, jmp_header.field_data_type))

        # Add the all the data entry lines. Ints have special treatment consideration as they have a bitmask, so
        # the original data must be read to ensure the unrelated bits are preserved.
        for line_entry in self.data_entries:
            current_offset: int = new_header_size + (self.data_entries.index(line_entry) + self._single_entry_size)
            for key, val in line_entry.items():
                local_data.seek(current_offset + key.field_start_bit)
                match key.field_data_type:
                    case JMPType.Int:
                        old_val = struct.unpack(">I", self.data.read(4))[0]
                        new_val = ((old_val & ~key.field_bitmask) | ((val << key.field_shift_bit) & key.field_bitmask))
                        local_data.seek(current_offset + key.field_start_bit)
                        local_data.write(struct.pack(">I", new_val))
                    case JMPType.Str:
                        length_to_use = JMP_STRING_BYTE_LENGTH - len(val)
                        local_data.write(struct.pack(f">{str(JMP_STRING_BYTE_LENGTH)}s", val.encode("shift_jis") + (b"\0" * length_to_use)))
                    case JMPType.Flt:
                        local_data.write(struct.pack(">f", val))

        # JMP Files are then padded with @ if their file size are not divisible by 32.
        curr_length = local_data.seek(0, 2)
        local_data.seek(curr_length)
        if curr_length % 32 > 0:
            local_data.write(struct.pack(f"{str(curr_length % 32)}s", b"@" * (curr_length % 32)))

        self.data = local_data