import pytest, struct
from io import BytesIO
from sys import exception

from gcbrickwork import JMP
from gcbrickwork.Bytes_Helper import ByteHelperError
from gcbrickwork.JMP import JMPFileError


def _jmp_sixteen_header(field_count: int=0, entry_count: int=0, header_size: int=0, entry_size: int=0) -> BytesIO:
    """Writes a quick jmp where only the first 16 bytes are specified."""
    # Calculate sizes
    field_count = field_count
    data_entry_count = entry_count
    header_block_size = header_size
    single_entry_size = entry_size

    io_data = BytesIO()
    io_data.write(struct.pack(">i", data_entry_count))  # Offset 0: data_entry_count (s32)
    io_data.write(struct.pack(">i", field_count))  # Offset 4: field_count (s32)
    io_data.write(struct.pack(">I", header_block_size))  # Offset 8: header_block_size (u32)
    io_data.write(struct.pack(">I", single_entry_size))  # Offset 12: single_entry_size (u32)
    return io_data

def _create_sample_jmp() -> BytesIO:
    """Creates a valid JMP file with 2 fields and 2 entries"""

    # Define field headers
    field1_hash = 0x12345678
    field1_bitmask = 0xFFFFFFFF  # Will be packed/unpacked as is
    field1_start_byte = 0
    field1_shift_byte = 0
    field1_type = 0  # JMPType.Int

    field2_hash = 0xABCDEF01
    field2_bitmask = 0
    field2_start_byte = 4
    field2_shift_byte = 0
    field2_type = 2  # JMPType.Flt

    field3_hash = 0xCCCCAAAA
    field3_bitmask = 0xFF  # Will be masked as needed
    field3_start_byte = 8
    field3_shift_byte = 0
    field3_type = 0  # JMPType.Int

    field4_hash = 0xDDDDBBBB
    field4_bitmask = 0x3F00 # Will be masked as needed
    field4_start_byte = 8
    field4_shift_byte = 8
    field4_type = 0  # JMPType.Int


    # Calculate sizes
    field_count = 4
    data_entry_count = 2
    header_block_size = 16 + (field_count * 12)
    single_entry_size = 8

    jmp_data: BytesIO = _jmp_sixteen_header(field_count, data_entry_count, header_block_size, single_entry_size)

    # Write field headers (24 bytes total, 12 bytes each)
    jmp_data.write(struct.pack(">I", field1_hash))
    jmp_data.write(struct.pack(">I", field1_bitmask))
    jmp_data.write(struct.pack(">H", field1_start_byte))
    jmp_data.write(struct.pack(">B", field1_shift_byte))
    jmp_data.write(struct.pack(">B", field1_type))

    jmp_data.write(struct.pack(">I", field2_hash))
    jmp_data.write(struct.pack(">I", field2_bitmask))
    jmp_data.write(struct.pack(">H", field2_start_byte))
    jmp_data.write(struct.pack(">B", field2_shift_byte))
    jmp_data.write(struct.pack(">B", field2_type))

    jmp_data.write(struct.pack(">I", field3_hash))
    jmp_data.write(struct.pack(">I", field3_bitmask))
    jmp_data.write(struct.pack(">H", field3_start_byte))
    jmp_data.write(struct.pack(">B", field3_shift_byte))
    jmp_data.write(struct.pack(">B", field3_type))

    jmp_data.write(struct.pack(">I", field4_hash))
    jmp_data.write(struct.pack(">I", field4_bitmask))
    jmp_data.write(struct.pack(">H", field4_start_byte))
    jmp_data.write(struct.pack(">B", field4_shift_byte))
    jmp_data.write(struct.pack(">B", field4_type))

    # Write data entries (16 bytes total, 8 bytes each)
    jmp_data.write(struct.pack(">I", 5))
    jmp_data.write(struct.pack(">f", 100.0))
    jmp_data.write(struct.pack(">I", 0 | ((5 << field3_shift_byte) & field3_bitmask) | ((42 << field4_shift_byte) & field4_bitmask)))

    jmp_data.write(struct.pack(">I", 10))
    jmp_data.write(struct.pack(">f", 200.0))
    jmp_data.write(struct.pack(">I", 2660))

    # Pad to 32-byte boundary with '@' characters
    current_size = jmp_data.tell()
    padding_needed = (32 - (current_size % 32)) % 32
    if padding_needed > 0:
        jmp_data.write(b'@' * padding_needed)

    return jmp_data

def test_none_jmp_data():
    """Tests JMP type creation when None type is provided"""
    with pytest.raises(AttributeError):
        JMP.load_jmp(None)

def test_empty_jmp_data():
    """Tests JMP type creation when empty BytesIO is provided"""
    with pytest.raises(ByteHelperError):
        JMP.load_jmp(BytesIO())

def test_jmp_first_sixteen_bytes():
    """Tests JMP type creation when only the first 16 bytes are provided"""
    with pytest.raises(JMPFileError):
        JMP.load_jmp(_jmp_sixteen_header())

def test_full_jmp():
    """Tests the whole JMP file is read correctly"""
    try:
        JMP.load_jmp(_create_sample_jmp())
    except exception as ex:
        raise pytest.fail("Reading JMP Sample raised an exception: {0}".format(ex))

def test_jmp_save():
    """Ensures JMP file can be saved as expected."""
    try:
        temp_jmp: JMP = JMP.load_jmp(_create_sample_jmp())
        temp_jmp.create_new_jmp()
    except exception as ex:
        raise pytest.fail("Saving JMP Sample raised an exception: {0}".format(ex))

def test_non_jmp_header_type_get():
    """Checks if an invalid JMP Header type is used to get a key"""
    temp_jmp: JMP = JMP.load_jmp(_create_sample_jmp())
    with pytest.raises(ValueError):
        temp_jmp.data_entries[0][None] = []

def test_non_existent_jmp_header_type_get():
    """Checks for when a jmp header does not exist at all"""
    temp_jmp: JMP = JMP.load_jmp(_create_sample_jmp())
    with pytest.raises(KeyError):
        temp_jmp.data_entries[0].__getitem__("Ch)eery")

def test_jmp_list_value_then_save():
    """Updates an entry to have a list valid, which is not valid and should error out."""
    temp_jmp: JMP = JMP.load_jmp(_create_sample_jmp())
    temp_jmp.data_entries[0][0x12345678] = []
    with pytest.raises(struct.error):
        temp_jmp.create_new_jmp()

def test_jmp_read_is_correct():
    temp_jmp: JMP = JMP.load_jmp(_create_sample_jmp())
    assert (temp_jmp.data_entries[0][0x12345678] == 5)
    assert (temp_jmp.data_entries[0][0xABCDEF01] == 100.000000)
    assert (temp_jmp.data_entries[0][0xCCCCAAAA] == 5)
    assert (temp_jmp.data_entries[0][0xDDDDBBBB] == 42)

def test_jmp_read_save_then_reread():
    """Try to read, save, then re-read the data to check for data loss."""
    try:
        temp_jmp: JMP = JMP.load_jmp(_create_sample_jmp())
        temp_data: BytesIO = temp_jmp.create_new_jmp()
        JMP.load_jmp(temp_data)
    except exception as ex:
        raise pytest.fail("Reading, saving, then re-reading the JMP Sample raised an exception: {0}".format(ex))

def test_jmp_read_is_correct_after_reread():
    temp_jmp: JMP = JMP.load_jmp(_create_sample_jmp())
    temp_data: BytesIO = temp_jmp.create_new_jmp()
    temp_jmp = JMP.load_jmp(temp_data)
    assert (temp_jmp.data_entries[0][0x12345678] == 5)
    assert (temp_jmp.data_entries[0][0xABCDEF01] == 100.000000)
    assert (temp_jmp.data_entries[0][0xCCCCAAAA] == 5)
    assert (temp_jmp.data_entries[0][0xDDDDBBBB] == 42)
