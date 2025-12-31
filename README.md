# gcbrickwork
A library of tools to read various GameCube files and components, then parses them out into structured data.  
Allows you to read, write, and update data via BytesIO streams, which can then be fed back into their original files.

## How to install
Available on PyPi:
pip install gcbrickwork

## Supported Files
| File Name / Format        | Supported? |
|:--------------------------|:----------:|
| .prm / parameters / param |✅|
| .jmp / jump               |✅|

~ indicates a type of file that is in progress

## Type of files explained:
### Parameter / PRM:
These types of files typically contain various data about a given actor / character in their respective game.  
The actor / character it relates to is typically indicated by its file name.  
The structure of these files break down in the following way:
* First 4 bytes indicate the number of entries that exists within the file.
* For each entry / field:
  * The first 2 bytes of an entry indicate some sort of hash.
  * The next 2 bytes indicate how long the string name is of the field / entry.
  * The next X bytes are read based on the previous 2 bytes values. Ex: If the name is supposed to be 6 bytes long,
  get the next 6 bytes to capture the entry / field's name.
  * The next 4 bytes will capture the byte size of the expected value. The following are the current known types:
    * Byte (single byte)
    * Short (two bytes)
    * Int / Float (Note: Due to how this data is parsed from bytes, there is no indicator for when something is an integer
    vs when something is a float. Instead, this library will pass the value back in hex, leaving it up to the user to
    decide if it is a float or not. You can decide this based on the name or how the data looks. Ex: Gravity would be a float)
    * Vector Data (12 bytes). This is usually just a Vector3 in c/c++, or just three floats in other words.
    * Color Data (16 bytes). This is usually 4 integers next to each other, representing Red, Green, Blue, and opacity.

### Jump / JMP
These types of files typically table-like structures that are loaded into RAM during run-time.
These files are similar to modern day data-tables.
* JMP Files contain a giant header block and data entry block.
  * The header block contains the definition of all field headers (columns) and field level data. Loads the first 16 bytes to determine (in order):
    * How many data entries there are
    * How many fields are defined
    * The total size of the header block
    * The number of data files that are defined in the file.
    * Each of these are 4 bytes long, with the first 8 bytes being signed integers and the second 8 bytes are unsigned.
      * JMP File Headers are comprised of 12 bytes in total:
        * The first 4 bytes represent the field's hash. Currently, it is un-known how a field's name becomes a hash.
          * There may be specific games that have created associations from field hash -> field internal name.
        * The second 4 bytes represent the field's bitmask
        * The next 2 bytes represent the starting byte for the field within a given data line in the JMP file.
        * The second to last byte represents the shift bytes, which is required when reading certain field data.
        * The last byte represents the data type, as defined as either Int, Str, or Floats.
      * Order of the JMPFileHeaders does not matter in JMP files, as long as all fields used are defined.
  * The data block contains the table row data one line at a time.
    * Each row is represented by multiple columns of data, each of which should match to a JMP field header and its respective value type (Int, Str, Float, etc.)
  * It should be noted that there will be extra bytes typically at the end of a jmp file, which are padded with "@".
    * These paddings can be anywhere from 1 to 31 bytes, up until the total bytes is divisible by 32.
