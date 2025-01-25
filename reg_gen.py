###################################################################################################
# CONFIGURATION
###################################################################################################

# Path to SVD file
SVD_PATH: str = "D:\\main\\projects\\sarp\\svd_parser\\cmsis-svd-data\\data\\STMicro\\STM32H7x5_CM7.svd"

# Output file path
OUTPUT_PATH: str = "D:\\main\\projects\\sarp\\svd_parser\\reg.h"

###################################################################################################
# IMPORTS
###################################################################################################

# Requires "cmsis_svd" library -> pip install -U cmsis-svd
import cmsis_svd as svd

# Standard libraries
import re
import os

###################################################################################################
# IMPLEMENTATION UTILITIES
###################################################################################################

# Access qualifier "map"
access_qual: dict[svd.parser.SVDAccessType, str] = {
    svd.parser.SVDAccessType.READ_ONLY: "RO_",
    svd.parser.SVDAccessType.WRITE_ONLY: "WO_",
    svd.parser.SVDAccessType.READ_WRITE: "RW_",
    svd.parser.SVDAccessType.WRITE_ONCE: "WO_",
    svd.parser.SVDAccessType.READ_WRITE_ONCE: "RW_",
    None: "RW_"
}

# Formats a SVD description string
def fmt_desc(desc: str) -> str:
    new_desc = ""
    is_first = True
    for word in desc.split():
        if is_first: 
            new_desc += word[0].upper() + word[1:]
        elif not word.isupper(): 
            new_desc += word.lower()
        else: 
            new_desc += word
        new_desc += " "
        is_first = word[-1] == "."
    new_desc = new_desc.replace("\n", " ")
    new_desc = new_desc.strip()
    new_desc += "."
    return new_desc

###################################################################################################
# PARSER
###################################################################################################

device = svd.parser.SVDParser.for_xml_file(SVD_PATH).get_device()

if os.path.exists(OUTPUT_PATH): 
    os.remove(OUTPUT_PATH)

with open(OUTPUT_PATH, "w") as file:

    file.write(f'  #define RO_ const volatile\n')
    file.write(f'  #define WO_ volatile\n')
    file.write(f'  #define RW_ volatile\n')    

    if device.peripherals:
        for peripheral in device.peripherals:

            max_reg_name_len: int = 0
            if peripheral.registers:
                for register in peripheral.registers:
                    max_reg_name_len = max(max_reg_name_len, len(register.name))

            max_field_name_len: int = 0
            if peripheral.registers:
                for register in peripheral.registers:
                    if register.fields:
                        for field in register.fields:
                            max_field_name_len = max(max_field_name_len, len(field.name))

            max_off_len: int = 0
            if peripheral.registers:
                for register in peripheral.registers:
                    if register.fields:
                        for field in register.fields:
                            max_off_len = max(max_off_len, len(str(field.bit_offset)))

            if peripheral.registers:

                for register in peripheral.registers:
                    if register.access == None:
                        register.access == svd.parser.SVDAccessType.READ_WRITE

                file.write(f'\n')
                file.write(f'  /*************************************************************************************************\n')
                file.write(f'   * @section {peripheral.name.upper()} Definitions\n')
                file.write(f'   *************************************************************************************************/\n')
                file.write(f'\n')
                file.write(f'  /**** @subsection Register Definitions ****/\n')
                file.write(f'\n')

                for register in peripheral.registers:

                    name: str = f'{peripheral.name.upper()}_{register.name.upper()}_PTR'
                    cast: str = f'(*({access_qual[register.access]} uint{register.size}_t*)'
                    value: str = f'UINT32_C(0x{peripheral.base_address + register.address_offset:0{register.size // 4}X})'
                    cmt: str = f'/** @brief {fmt_desc(register.description)} */'

                    this_def_len = len(register.name)
                    def_gap: int = (max_reg_name_len - this_def_len) + 3
                    file.write(f'  #define {name}{" "*def_gap}{cast}{value})   {cmt}\n')
                               
                file.write(f'\n')
                file.write(f'  /**** @subsection Field Mask Definitions ****/\n')
                file.write(f'\n')
                    
                for register in peripheral.registers:
                    if register.fields:
                        for field in register.fields:

                            name: str = f'{peripheral.name.upper()}_{register.name.upper()}_{field.name.upper()}_MSK'
                            i_mask: int = (((1 << field.bit_width) - 1) << field.bit_offset)
                            value: str = f'UINT{register.size}_C(0x{i_mask:0{register.size // 4}X})'
                            cmt: str = f'/** @brief {fmt_desc(field.description)} */'

                            this_def_len: int = len(register.name) + len(field.name)
                            def_gap: int = ((max_reg_name_len + max_field_name_len) - this_def_len) + 3
                            file.write(f'  #define {name}{" "*(def_gap)}{value}   {cmt}\n')

                file.write(f'\n')
                file.write(f'  /**** @subsection Field Position Definitions ****/\n')
                file.write(f'\n')

                for register in peripheral.registers:
                    if register.fields:
                        for field in register.fields:
                            
                            name: str = f'{peripheral.name.upper()}_{register.name.upper()}_{field.name.upper()}_POS'
                            value: str = f'INT32_C({field.bit_offset})'
                            cmt: str = f'/** @brief {fmt_desc(field.description)} */'

                            this_def_len: int = len(register.name) + len(field.name)
                            def_gap: int = ((max_reg_name_len + max_field_name_len) - this_def_len) + 3
                            cmt_gap: int = (max_off_len - len(str(field.bit_offset))) + 3
                            file.write(f'  #define {name}{" "*def_gap}{value}{" "*cmt_gap}{cmt}\n')