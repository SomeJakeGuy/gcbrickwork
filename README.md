# gcbrickwork
A library of tools to read various GameCube files and components, then parses them out into structured data.  
Allows you to read, write, and update data via BytesIO streams, which can then be fed back into their original files.

## Supported Files
| File Name / Format        | Supported? |
|:--------------------------|:----------:|
| .prm / parameters / param |     ✅      |
| .jmp / jump               |     ~      |

~ indicates a type of file that is in progress

## Type of files explained:
### Parameter / PRM:
These types of files typically contain various data about a given actor / character in their respective game.  
The actor / character it relates to is typically indicated by its file name.  
The structure of these break down into the following way:
* First 4 bytes indicate the number of entries that exists witin the file.
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
