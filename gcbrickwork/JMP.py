import copy
from dataclasses import dataclass
from enum import IntEnum

from .Bytes_Helper import *

JMP_HEADER_SIZE: int = 12
JMP_STRING_BYTE_LENGTH = 32

type JMPValue = int | str | float


class JMPEntry(dict["JMPFieldHeader", JMPValue]):
    """
    A JMP entry (row) that allows accessing fields by string name or JMPFieldHeader.
    This is a simple wrapper around a dict to allow getting values by string instead of having to use JMPFieldHeaders.
    """
    def _find_entry_field(self, jmp_field: "int | str | JMPFieldHeader") -> "JMPFieldHeader":
        """Finds a specific JMP field by its hash value or field name. Can return None as well if no field found."""
        if isinstance(jmp_field, str):
            field: JMPFieldHeader = next((field for field in self.keys() if field.field_name == jmp_field), None)
        elif isinstance(jmp_field, int):
            field: JMPFieldHeader = next((field for field in self.keys() if field.field_hash == jmp_field), None)
        elif isinstance(jmp_field, JMPFieldHeader):
            field = jmp_field
        else:
            raise ValueError(f"Cannot index JMPEntry with value of type {type(jmp_field)}")

        if field is None:
            raise KeyError(f"No JMPHeaderField was found with name/hash '{str(jmp_field)}'")
        return field


    def __getitem__(self, key: "str | int | JMPFieldHeader") -> JMPValue:
        """Gets a specific JMPHeaderField by its name, hash, or field directly."""
        return super().__getitem__(self._find_entry_field(key))


    def __setitem__(self, key: "str | int | JMPFieldHeader", value: JMPValue):
        """Updates a specific JMPHeaderField by its name, hash, or field directly to the provided value."""
        super().__setitem__(self._find_entry_field(key), value)


class JMPFileError(Exception):
    """Used to return various JMP File related errors."""
    pass


class JMPType(IntEnum):
    """Indicates the type of field the Field header is."""
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
    field_data_type: JMPType = None


    def __init__(self, jmp_hash: int, jmp_bitmask: int, jmp_start_byte: int, jmp_shift_byte: int, jmp_data_type: int):
        self.field_hash = jmp_hash
        self.field_name = str(self.field_hash)
        self.field_bitmask = jmp_bitmask
        self.field_start_byte = jmp_start_byte
        self.field_shift_byte = jmp_shift_byte
        self.field_data_type = JMPType(jmp_data_type)


    def __str__(self):
        return str(self.__dict__)


    def __hash__(self):
        return id(self)


    def __eq__(self, other):
        return self is other


    def validate_header(self):
        if not isinstance(self.field_hash, int):
            raise JMPFileError("JMPFieldHeader Field Hash must be of type integer.")
        elif not (0 <= self.field_hash <= 2**32 - 1):
            raise JMPFileError(f"JMPFieldHeader Field Hash must be between 0 and '{str(2**32 - 1)}'")

        if not isinstance(self.field_bitmask, int):
            raise JMPFileError("JMPFieldHeader Field BitMask must be of type integer.")
        elif not (0 <= self.field_bitmask <= 2**32-1):
            raise JMPFileError(f"JMPFieldHeader Field BitMask must be between 0 and '{str(2**32-1)}'")

        if not isinstance(self.field_start_byte, int):
            raise JMPFileError("JMPFieldHeader Start Byte must be of type integer.")
        elif not self.field_start_byte % 4 == 0:
            raise JMPFileError("JMPFieldHeader Start Byte must be divisible by '4'.")
        elif not (0 <= self.field_start_byte <= 2**16 - 1):
            raise JMPFileError(f"JMPFieldHeader Start Byte must be between 0 and '{str(2**16 - 1)}'")

        if not isinstance(self.field_shift_byte, int):
            raise JMPFileError("JMPFieldHeader Shift Byte must be of type integer.")
        elif not (0 <= self.field_shift_byte <= 2**8 - 1):
            raise JMPFileError(f"JMPFieldHeader Shift Byte must be between 0 and '{str(2**8 - 1)}'")



class JMP:
    """
    JMP Files are table-structured format files that contain a giant header block and data entry block.
    These files remark a similar structure to modern day data tables.
        The header block contains the definition of all field headers (columns) and field data
            Definition of these headers does not matter.
        The data block contains the table row data one line at a time. Each row is represented as a single list index,
            where a dictionary maps the key (column) to the value.
    JMP Files also start with 16 bytes that are useful to explain the rest of the structure of the file.
    """
    _data_entries: list[JMPEntry] = []
    _fields: list[JMPFieldHeader] = []


    def __init__(self, fields: list[JMPFieldHeader], data_entries: list[JMPEntry]):
        self._fields = fields
        self.validate_jmp_fields()
        self._data_entries = data_entries
        self.validate_all_jmp_entries()


    def validate_jmp_fields(self):
        """Validates that the list of JMPFieldHeaders have correct information and confirms no duplicates are found."""
        field_hashes: list[int] = []
        for j_field in self._fields:
            if j_field.field_hash in field_hashes:
                raise JMPFileError(f"JMPFieldHeader with hash '{str(j_field.field_hash)}' already exists in JMPFieldHeaderList.")
            j_field.validate_header()
            field_hashes.append(j_field.field_hash)


    @property
    def fields(self) -> list[JMPFieldHeader]:
        """Returns the list of JMP Field Headers that are defined in this file."""
        return self._fields


    def add_jmp_header(self, jmp_field: JMPFieldHeader, default_val: JMPValue):
        """Adds a new JMPFieldHeader and a default value to all existing data entries."""
        jmp_field.validate_header()
        if jmp_field in self._fields or jmp_field.field_hash in [f.field_hash for f in self._fields]:
            raise JMPFileError(f"JMPFieldHeader with hash '{str(jmp_field.field_hash)}' already exists in JMPFieldHeaderList.")

        self._fields.append(jmp_field)
        for data_entry in self._data_entries:
            data_entry[jmp_field] = default_val


    def delete_jmp_header(self, field_key: str | int | JMPFieldHeader):
        """Deletes a JMPFieldHeader based on the provided field name, hash, or field itself.
        Automatically removes the field from all data entries as well, to avoid issues later on."""
        if isinstance(field_key, str) or isinstance(field_key, int):
            field = self.find_jmp_header(field_key)
        elif isinstance(field_key, JMPFieldHeader):
            field = field_key
        else:
            raise ValueError(f"Cannot index JMPEntry with value of type {type(field_key)}")

        if field is None:
            return

        self._fields.remove(field)
        for data_entry in self._data_entries:
            del data_entry[field]


    def map_hash_to_name(self, field_names: dict[int, str]):
        """
        Using the user provided dictionary, maps out the field hash to their designated name, making it easier to query.
        """
        for key, val in field_names.items():
            jmp_field: JMPFieldHeader = self.find_jmp_header(key)
            if jmp_field is None:
                continue
            jmp_field.field_name = val


    def find_jmp_header(self, field_key: str | int) -> JMPFieldHeader | None:
        """Finds a JMPFieldHeader based on either the field's name or its hash."""
        if isinstance(field_key, str):
            return next((j_field for j_field in self._fields if j_field.field_name == field_key), None)
        elif isinstance(field_key, int):
            return next((j_field for j_field in self._fields if j_field.field_hash == field_key), None)
        else:
            raise ValueError(f"Cannot index JMPEntry with value of type {type(field_key)}")


    @property
    def data_entries(self) -> list[JMPEntry]:
        """Returns the list of JMPEntry (rows) that are defined in this file."""
        return self._data_entries


    def clear_data_entries(self):
        """Resets data_entries into an empty list (no rows defined)"""
        self._data_entries = []


    def delete_jmp_entry(self, jmp_entry: int | JMPEntry):
        """Deletes a JMPEntry by either the Entry itself or the index number."""
        if isinstance(jmp_entry, int):
            entry: JMPEntry = self._data_entries[jmp_entry]
        elif isinstance(jmp_entry, JMPEntry):
            entry: JMPEntry = jmp_entry
        else:
            raise ValueError(f"Cannot index JMPEntry with value of type {type(jmp_entry)}")

        self._data_entries.remove(entry)


    def add_jmp_entry(self, jmp_entry: dict[str | int, JMPValue] | JMPEntry):
        """Adds a new data entry using field names or hashes as keys with complete field validation."""
        if not self._fields:
            raise JMPFileError("Cannot add a JMPEntry to the JMP with no defined fields.")
        elif jmp_entry is None or len(jmp_entry.keys()) == 0:
            raise JMPFileError("Cannot add an empty JMPEntry to the JMP.")

        self._data_entries.append(self.validate_jmp_entry(jmp_entry))


    def validate_jmp_entry(self, entry_data: dict[str | int, JMPValue] | JMPEntry) -> JMPEntry:
        """Validates the current JMPEntry does not have invalid fields, missing required fields, and correct values.
        If a required field (which is a field defined in the self.fields), a JMPFIleError is thrown."""
        entry_to_use: JMPEntry = JMPEntry()
        invalid_fields: list[str] = []
        for key, val in entry_data.items():
            if isinstance(key, str) or isinstance(key, int):
                jmp_field: JMPFieldHeader = self.find_jmp_header(key)
                if jmp_field is None:
                    invalid_fields.append(f"'{str(key)}' {"(name)" if isinstance(key, str) else "(hash)"}")
                    continue

                entry_to_use[jmp_field] = val
            elif isinstance(key, JMPFieldHeader):
                if not key in self._fields:
                    jmp_field: JMPFieldHeader = self.find_jmp_header(key.field_hash)
                    if jmp_field is None:
                        invalid_fields.append(f"'{str(key)}' {"(name)" if isinstance(key, str) else "(hash)"}")
                        continue
                    entry_to_use[jmp_field] = val
                    continue

                entry_to_use[key] = val
            else:
                raise JMPFileError("Entry keys must be field names (str) or field hashes (int)")

        if invalid_fields:
            raise JMPFileError(f"Invalid fields not found in JMP file schema: {', '.join(invalid_fields)}")

        # Validate the entry has all required fields
        missing_fields = set(self._fields) - set(entry_to_use.keys())
        if missing_fields:
            raise JMPFileError(f"Missing required JMP: {', '.join([f"(JMPFieldHeader) Name: '{f.field_name}'; " +
                f"Hash: '{str(f.field_hash)}'" for f in missing_fields])}")

        return entry_to_use


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
        header_size: int = header_block_size - 16 # JMP Field details start after the above 16 bytes
        if (header_size % JMP_HEADER_SIZE != 0 or not (header_size / JMP_HEADER_SIZE) == field_count or
            header_block_size > original_file_size):
            raise JMPFileError("When trying to read the header block of the JMP file, the size was bigger than " +
                "expected and could not be parsed properly.")
        fields = _load_headers(jmp_data, field_count)

        # Load all data entries / rows of this table.
        if header_block_size + (single_entry_size * data_entry_count) > original_file_size:
            raise JMPFileError("When trying to read the date entries block of the JMP file, the size was bigger than " +
                "expected and could not be parsed properly.")
        entries = _load_entries(jmp_data, data_entry_count, single_entry_size, header_block_size, fields)

        return cls(fields, entries)


    def create_new_jmp(self) -> BytesIO:
        """
        Create a new the file from the fields / _data_entries, as new entries / headers could have been added.
        Keeping the original structure of: Important 16 header bytes, Header Block, and then the Data entries block.
        """
        self.validate_jmp_fields()
        self.validate_all_jmp_entries()

        local_data: BytesIO = BytesIO()
        single_entry_size: int = self._calculate_entry_size()
        new_header_size: int = len(self._fields) * JMP_HEADER_SIZE + 16
        write_s32(local_data, 0, len(self._data_entries)) # Amount of data entries
        write_s32(local_data, 4, len(self._fields)) # Amount of JMP fields
        write_u32(local_data, 8, new_header_size) # Size of Header Block
        write_u32(local_data, 12, single_entry_size) # Size of a single data entry

        current_offset: int = self._update_headers(local_data)
        self._update_entries(local_data, current_offset, single_entry_size)

        # JMP Files are then padded with @ if their file size are not divisible by 32.
        curr_length = local_data.seek(0, 2)
        local_data.seek(curr_length)
        if curr_length % 32 > 0:
            write_str(local_data, curr_length, "", 32 - (curr_length % 32), "@".encode(GC_ENCODING_STR))
        return local_data


    def _update_headers(self, local_data: BytesIO) -> int:
        """ Add the individual headers to complete the header block """
        current_offset: int = 16
        for jmp_header in self._fields:
            write_u32(local_data, current_offset, jmp_header.field_hash)
            write_u32(local_data, current_offset + 4, jmp_header.field_bitmask)
            write_u16(local_data, current_offset + 8, jmp_header.field_start_byte)
            write_u8(local_data, current_offset + 10, jmp_header.field_shift_byte)
            write_u8(local_data, current_offset + 11, jmp_header.field_data_type)
            current_offset += JMP_HEADER_SIZE

        return current_offset


    def _update_entries(self, local_data: BytesIO, current_offset: int, entry_size: int):
        """ Add the all the data entry lines. Integers with bitmask 0xFFFFFFFF will write their values directly,
        while other integers will need to shift/mask their values accordingly."""
        for line_entry in self._data_entries:
            for key, val in line_entry.items():
                match key.field_data_type:
                    case JMPType.Int:
                        if key.field_bitmask == 0xFFFFFFFF: # Indicates the value should be written directly without changes.
                            new_val = val
                        else:
                            if not local_data.seek(0, 2) > current_offset + key.field_start_byte:
                                start_val: int = 0
                            else:
                                start_val: int = read_u32(local_data, current_offset + key.field_start_byte)
                            new_val: int = start_val | ((val << key.field_shift_byte) & key.field_bitmask)
                        write_u32(local_data, current_offset + key.field_start_byte, new_val)
                    case JMPType.Str:
                        write_str(local_data, current_offset + key.field_start_byte, val, JMP_STRING_BYTE_LENGTH)
                    case JMPType.Flt:
                        write_float(local_data, current_offset + key.field_start_byte, val)
            current_offset += entry_size


    def _calculate_entry_size(self) -> int:
        """Gets a deepy copy of the JMP header list to avoid messing with the actual order of fields."""
        jmp_fields: list[JMPFieldHeader] = copy.deepcopy(self._fields)
        sorted_jmp_fields = sorted(jmp_fields, key=lambda jmp_field: jmp_field.field_start_byte, reverse=True)
        return sorted_jmp_fields[0].field_start_byte + _get_field_size(JMPType(sorted_jmp_fields[0].field_data_type))


    def validate_all_jmp_entries(self):
        """
        Validates all entries have the same JMPFieldHeaders. All of them must have a value, even if its 0.
        If a data_entry defines a field that is not shared by the others, it will cause parsing errors later.
        """
        if self._data_entries is None or len(self._data_entries) == 0:
            return
        for jmp_entry in self._data_entries:
            self.validate_jmp_entry(jmp_entry)


def _load_headers(header_data: BytesIO, field_count: int) -> list[JMPFieldHeader]:
    """
    Gets the list of all JMP headers that are available in this file. See JMPFieldHeader for exact structure.
    """
    current_offset: int = 16
    field_headers: list[JMPFieldHeader] = []

    for jmp_entry in range(field_count):
        entry_hash: int = read_u32(header_data, current_offset)
        entry_bitmask: int = read_u32(header_data, current_offset + 4)
        entry_start_byte: int = read_u16(header_data, current_offset + 8)
        entry_shift_byte: int = read_u8(header_data, current_offset + 10)
        entry_type: int = read_u8(header_data, current_offset + 11)
        field_headers.append(JMPFieldHeader(entry_hash, entry_bitmask, entry_start_byte, entry_shift_byte, entry_type))
        current_offset += JMP_HEADER_SIZE
    return field_headers


def _load_entries(entry_data: BytesIO, entry_count: int, entry_size: int, header_size: int,
    field_list: list[JMPFieldHeader]) -> list[JMPEntry]:
    """
    Loads all the rows one by one and populates each column's value per row.
    """
    data_entries: list[JMPEntry] = []

    for current_entry in range(entry_count):
        val_to_use: JMPValue | None = None
        new_entry: JMPEntry = JMPEntry()
        data_entry_start: int = (current_entry * entry_size) + header_size

        for jmp_header in field_list:
            match jmp_header.field_data_type:
                case JMPType.Int:
                    current_val: int = read_u32(entry_data, data_entry_start + jmp_header.field_start_byte)
                    val_to_use = (current_val & jmp_header.field_bitmask) >> jmp_header.field_shift_byte
                case JMPType.Str:
                    val_to_use = read_str_until_null_character(entry_data,
                        data_entry_start + jmp_header.field_start_byte, JMP_STRING_BYTE_LENGTH)
                case JMPType.Flt:
                    val_to_use = read_float(entry_data, data_entry_start + jmp_header.field_start_byte)

            new_entry[jmp_header] = val_to_use
        data_entries.append(new_entry)

    return data_entries


def _get_field_size(field_type: JMPType) -> int:
    match field_type:
        case JMPType.Int | JMPType.Flt:
            return 4
        case JMPType.Str:
            return 32
