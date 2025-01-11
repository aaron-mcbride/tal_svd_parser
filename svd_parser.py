###################################################################################################
# IMPORTS
###################################################################################################

# Requires "cmsis_svd" library -> pip install -U cmsis-svd
import cmsis_svd as svd

# Standard libraries
import traceback as tb
import os
import time

###################################################################################################
# CONFIGURATION
###################################################################################################

# Path to SVD data directory -> git clone --depth=1 -b main https://github.com/cmsis-svd/cmsis-svd-data.git
SVD_DATA_PATH: str = "D:\\main\\projects\\sarp\\svd_parser\\cmsis-svd-data\\data"

# Output file path
OUTPUT_PATH: str = "D:\\main\\projects\\sarp\\svd_parser\\output.h"

# Target device vendor name
VENDOR_NAME: str = "STMicro"

# Core 1 SVD file name
CORE1_SVD_NAME: str = "STM32H7x5_CM7.svd"

# Core 2 SVD file name (None if single-core)
CORE2_SVD_NAME: str | None = "STM32H7x5_CM4.svd"

# Core 1 prefix (None if single-core)
CORE1_PREFIX: str | None = "CM7"

# Core 2 prefix (None if single-core)
CORE2_PREFIX: str | None = "CM4"

# Minimum column number of macro definitions
MIN_DEF_COL: int = 50

# Number of spaces per indent level
INDENT: int = 2

# Fallback access type for registers when no specified
FALLBACK_REG_ACCESS: svd.parser.SVDAccessType = svd.parser.SVDAccessType.READ_WRITE

# Minimum column for macro definitions
MIN_DEF_COL = 0

###################################################################################################
# SVD PROCESSING
###################################################################################################

deriv_off: dict[str, list[int]] = {}
deriv_name: dict[str, list[str]] = {}

# Remove output file if it exists
if os.path.isfile(OUTPUT_PATH):
    os.remove(OUTPUT_PATH)

# Catch errors durring SVD processing
try:

    # Configure parser and get device for core 1
    print("Loading SVD file for core 1...")
    parser1 = svd.SVDParser.for_packaged_svd(package_root = SVD_DATA_PATH, vendor = VENDOR_NAME, filename = CORE1_SVD_NAME)
    print("Parsing SVD file for core 1...")
    device1 = parser1.get_device(xml_validation = False)
    if device1 is None: 
        raise Exception("Invalid SVD file for core 1.")
    print("SVD file for core 1 loaded and parsed successfully!")

    # If dual-core, merge SVD files:
    if CORE2_SVD_NAME:

        # Configure parser and get device for core 2 (if dual-core)
        print("Loading SVD file for core 2...")
        parser2 = svd.SVDParser.for_packaged_svd(package_root = SVD_DATA_PATH, vendor = VENDOR_NAME, filename = CORE2_SVD_NAME)
        print("Parsing SVD file for core 2...")
        device2 = parser2.get_device(xml_validation = False)
        if device2 is None:
            raise Exception("Invalid SVD file for core 2.")
        print("SVD file for core 2 loaded and parsed successfully!")

        # Iterate through peripherals in core 1 -> core 2
        for peripheral1 in device1.peripherals:
            print(f'Merging core 1 peripheral: {peripheral1.name.upper()}...')
            peripheral_found: bool = False
            for peripheral2 in device2.peripherals:
                if (peripheral2.name == peripheral1.name and
                    peripheral2.base_address == peripheral1.base_address):
                    peripheral_found = True

                    # Find interrupts only in core 1 and rename them
                    if peripheral1.interrupts:
                        for interrupt1 in peripheral1.interrupts:
                            if (not peripheral2.interrupts or 
                                not any(interrupt2.name == interrupt1.name and 
                                        interrupt2.value == interrupt1.value 
                                        for interrupt2 in peripheral2.interrupts)):
                                interrupt1.name = f'{CORE1_PREFIX}_{interrupt1.name}'

                    # Iterate through registers in core 1 -> core 2
                    if peripheral1.registers:
                        for register1 in peripheral1.registers:
                            register_found: bool = False
                            if peripheral2.registers:
                                for register2 in peripheral2.registers:
                                    if (register2.name == register1.name and
                                        register2.address_offset == register1.address_offset and
                                        register2.size == register1.size and
                                        register2.access == register1.access):
                                        register_found = True

                                        # Find fields only in core 1 and rename them
                                        if register1.fields:
                                            for field1 in register1.fields:
                                                if (not register2.fields or 
                                                    not any(field2.name == field1.name and
                                                            field2.bit_offset == field1.bit_offset and
                                                            field2.bit_width == field1.bit_width
                                                            for field2 in register2.fields)):
                                                    field1.name = f'{CORE1_PREFIX}_{field1.name}'

                            # If register only in core 1, rename it
                            if not register_found:
                                register1.name = f'{CORE1_PREFIX}_{register1.name}'

            # If peripheral only in core 1, rename it
            if not peripheral_found:
                peripheral1.name = f'{CORE1_PREFIX}_{peripheral1.name}'
                    
        # Iterate through peripherals in core 2 -> core 1
        for peripheral2 in device2.peripherals:
            print(f'Merging core 2 peripheral: {peripheral2.name.upper()}...')
            peripheral_found: bool = False
            for peripheral1 in device1.peripherals:
                if (peripheral2.name == peripheral1.name and
                    peripheral2.base_address == peripheral1.base_address):
                    peripheral_found = True

                    # Find interrupts only in core 2, rename them and add them to core 1
                    if peripheral2.interrupts:
                        for interrupt2 in peripheral2.interrupts:
                            if (not peripheral1.interrupts or 
                                not any(interrupt1.name == interrupt2.name and 
                                        interrupt1.value == interrupt2.value 
                                        for interrupt1 in peripheral1.interrupts)):
                                interrupt2.name = f'{CORE2_PREFIX}_{interrupt2.name}'
                                peripheral1.interrupts.append(interrupt2)

                    # Iterate through registers in core 2 -> core 1
                    if peripheral2.registers:
                        for register2 in peripheral2.registers:
                            register_found: bool = False
                            if peripheral1.registers:
                                for register1 in peripheral1.registers:
                                    if (register2.name == register1.name and
                                        register2.address_offset == register1.address_offset and
                                        register2.size == register1.size and
                                        register2.access == register1.access):
                                        register_found = True

                                        # Find fields only in core 2, rename them and add them to core 1
                                        if register2.fields:
                                            for field2 in register2.fields:
                                                if (not register1.fields or 
                                                    not any(field1.name == field2.name and
                                                            field1.bit_offset == field2.bit_offset and
                                                            field1.bit_width == field2.bit_width
                                                            for field1 in register1.fields)):
                                                    field2.name = f'{CORE2_PREFIX}_{field2.name}'
                                                    register1.fields.append(field2)

                            # If register only in core 2, rename it and add it to core 1
                            if not register_found:
                                register2.name = f'{CORE2_PREFIX}_{register2.name}'
                                peripheral1.registers.append(register2)

            # If peripheral only in core 2, rename it and add it to core 1
            if not peripheral_found:
                peripheral2.name = f'{CORE2_PREFIX}_{peripheral2.name}'
                device1.peripherals.append(peripheral2)

    # Iterate through peripherals in merged device
    for peripheral in device1.peripherals:
        print(f'Formatting peripheral: {peripheral.name.upper()}...')

        # If not description specified, say so
        if not peripheral.description:
            peripheral.description = "No description."

        # Iterate through registers in merged device
        for register in peripheral.registers:

            # If no access type specified set to read/write
            if not register.access:
                register.access = FALLBACK_REG_ACCESS

            # If not description specified, say so
            if not register.description:
                register.description = "No description."
            
            # Iterate through fields in merged device
            for field in register.fields:
                
                # If no description specified, say so
                if not field.description:
                    field.description = "No description."       

# If error occurs durring SVD processing:
except Exception as e:

    # Print error msg and trace then exit
    print("Error occured durring SVD processing.")
    tb.print_exc()
    exit()

# If no errors, print success message
print("SVD processing successful!")

###################################################################################################
# FILE GENERATION
###################################################################################################

# Qualifiers associated with different register access types
REG_QUAL: dict[svd.parser.SVDAccessType, str] = {
    svd.parser.SVDAccessType.READ_ONLY: "const volatile",
    svd.parser.SVDAccessType.WRITE_ONLY: "volatile",
    svd.parser.SVDAccessType.READ_WRITE: "volatile",
    svd.parser.SVDAccessType.WRITE_ONCE: "volatile",
    svd.parser.SVDAccessType.READ_WRITE_ONCE: "volatile"
}

# Formats a SVD description string
def fmt_desc(desc: str) -> str:
    new_desc = ""
    is_first = True

    # Iterate through word and ajust capitalization
    for word in desc.split():
        if is_first: 
            new_desc += word[0].upper() + word[1:]
        elif not word.isupper(): 
            new_desc += word.lower()
        else: 
            new_desc += word
        
        # Add space between words
        new_desc += " "
        is_first = word[-1] == "."
    
    # Strip new description to remove trailing space
    return new_desc.strip()

# Ensure register name is formatted correctly
def reg_name(register: svd.parser.SVDRegister, periph_name: str) -> str:
    new_reg_name: str = ""
    for r_word in register.name.upper().split("_"):
        if all(r_word != x for x in periph_name.split("_")):
            new_reg_name += r_word + "_"
    new_reg_name = new_reg_name[:-1]
    return new_reg_name

# Catch errors durring file generation
try:
    
    # Open output file
    with open(OUTPUT_PATH, "w") as file:

        # Write file header
        file.write(f'/**\n')
        file.write(f' * This file is part of the Titan Flight Computer Project\n')
        file.write(f' * Copyright (c) 2024 UW SARP\n')
        file.write(f' *\n')
        file.write(f' * This program is free software: you can redistribute it and/or modify\n')
        file.write(f' * it under the terms of the GNU General Public License as published by\n')
        file.write(f' * the Free Software Foundation, version 3.\n')
        file.write(f' *\n')
        file.write(f' * This program is distributed in the hope that it will be useful, but\n')
        file.write(f' * WITHOUT ANY WARRANTY; without even the implied warranty of\n')
        file.write(f' * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU\n')
        file.write(f' * General Public License for more details.\n')
        file.write(f' *\n')
        file.write(f' * You should have received a copy of the GNU General Public License\n')
        file.write(f' * along with this program. If not, see <http://www.gnu.org/licenses/>.\n')
        file.write(f' *\n')
        file.write(f' * @file __PATH__\n')
        file.write(f' * @authors __AUTHORS__\n')
        file.write(f' * @brief __BRIEF__.\n')
        file.write(f' */\n')
        file.write("\n")
        file.write(f'#ifndef __GUARD__\n')
        file.write(f'#define __GUARD__\n')
        file.write("\n")
        file.write(f'{" "*INDENT}#include <stdint.h>\n')
        file.write("\n")
        file.write(f'{" "*INDENT}#ifdef __cplusplus\n')
        file.write(f'{" "*(INDENT*2)}extern "C" {{\n')
        file.write(f'{" "*INDENT}#endif\n')
        file.write("\n")

        # Iterate through peripherals
        for peripheral in device1.peripherals:
            
            # Print out current peripheral
            print(f'Generating definitions for peripheral: {peripheral.name.upper()}...')

            # Ensure peripheral has associated information
            if peripheral.registers or peripheral.interrupts:

                # Ensure peripheral is not derived
                is_derived: bool = False
                if peripheral.derived_from:
                    for parent_periph in device1.peripherals:
                        if parent_periph.name == peripheral.derived_from:
                            is_derived = True
                            break
                if is_derived:
                    continue

                # Get peripheral name
                periph_name: str = peripheral.name.upper()
                if peripheral.group_name:
                    for deriv_periph in device1.peripherals:
                        if (deriv_periph.derived_from and deriv_periph.derived_from == peripheral.name):
                            periph_name = ""
                            for parent_char, deriv_char in zip(peripheral.name.upper(), deriv_periph.name.upper()):
                                if parent_char == deriv_char:
                                    periph_name += parent_char

                # Write peripheral section header
                file.write(f'{" "*(INDENT*2)}/**********************************************************************************************\n')
                file.write(f'{" "*(INDENT*2)} * @section {periph_name} Definitions\n')
                file.write(f'{" "*(INDENT*2)} **********************************************************************************************/\n')
                file.write("\n")

                # If peripheral or derived has associated IRQ interrupts
                if peripheral.interrupts or any(x.interrupts for x in device1.peripherals if 
                                                x.derived_from and x.derived_from == peripheral.name):

                    # Determine maximum length of interrupt values/names
                    max_isr_digits: int = 0
                    max_isr_name_len: int = 0
                    for x in device1.peripherals:
                        if (x.name == peripheral.name or (x.derived_from and x.derived_from == peripheral.name)):
                            if x.interrupts:
                                for interrupt in x.interrupts:
                                    if len(str(interrupt.value)) > max_isr_digits:
                                        max_isr_digits = len(str(interrupt.value))
                                    if len(interrupt.name) > max_isr_name_len:
                                        max_isr_name_len = len(interrupt.name)

                    # Write interrupt subsection header
                    file.write(f'{" "*(INDENT*2)}/** @subsection {periph_name} IRQ interrupt definitions */\n')
                    file.write("\n")

                    # Iterate through interrupts and write their definitions
                    for x in device1.peripherals:
                        if x.name == peripheral.name or (x.derived_from and x.derived_from == peripheral.name):
                            if x.interrupts:
                                for interrupt in x.interrupts:
                                    isr_decl: str = f'#define _{interrupt.name.upper()}_IRQ'
                                    isr_value: int = interrupt.value
                                    isr_def: str = f'INT32_C({isr_value})'
                                    isr_comment: str = f'/** @brief {fmt_desc(interrupt.description)} */'
                                    isr_gap: int = max((max_isr_name_len + 3) - len(interrupt.name), MIN_DEF_COL - len(isr_decl))
                                    isr_c_gap: int = (max_isr_digits - len(str(isr_value))) + 1
                                    file.write(f'{" "*(INDENT*2)}{isr_decl}{" "*isr_gap}{isr_def}{" "*isr_c_gap}{isr_comment}\n')
                    file.write("\n")

                # If peripheral has associated registers
                if peripheral.registers:

                    # If peripheral has any derived peripherals
                    if any(x.derived_from and x.derived_from == peripheral.name for x in device1.peripherals):

                        # Determine maximum number of digits in deriv offset and name length
                        max_deriv_digits: int = max(len(str(x.base_address - peripheral.base_address)) for x in 
                                device1.peripherals if x.derived_from and x.derived_from == peripheral.name)
                        max_deriv_name_len: int = max(len(x.name) for x in device1.peripherals if x.name == peripheral.name or 
                                                      (x.derived_from and x.derived_from == peripheral.name))

                        # Write the peripheral instance subsection header
                        file.write(f'{" "*(INDENT*2)}/** @subsection {periph_name} instance offset definitions */\n')
                        file.write("\n")

                        # Write the peripheral instance offset definitions
                        for deriv_periph in device1.peripherals:
                            if (deriv_periph.name == peripheral.name or (deriv_periph.derived_from and 
                                deriv_periph.derived_from == peripheral.name)):
                                deriv_decl: str = f'#define _{deriv_periph.name.upper()}_OFF'
                                deriv_value: int = deriv_periph.base_address - peripheral.base_address
                                deriv_def: str = f'INT32_C({deriv_value})'
                                deriv_comment: str = f'/** @brief {deriv_periph.name.upper()} instance offset. */'
                                deriv_gap: int = max((max_deriv_name_len + 3) - len(deriv_periph.name), MIN_DEF_COL - len(deriv_decl))
                                deriv_c_gap: int = (max_deriv_digits - len(str(deriv_value))) + 1
                                file.write(f'{" "*(INDENT*2)}{deriv_decl}{" "*deriv_gap}{deriv_def}{" "*deriv_c_gap}{deriv_comment}\n')
                        file.write("\n")

                    # Determine maximum length of register qualifiers/names
                    max_reg_qual_len: int = max(len(REG_QUAL[register.access]) for register in peripheral.registers)
                    max_reg_name_len: int = max(len(reg_name(register, periph_name)) for register in peripheral.registers)

                    # Write the register subsection header
                    file.write(f'{" "*(INDENT*2)}/** @subsection {periph_name} register reference definitions */\n')
                    file.write("\n")

                    # Iterate through registers and write their definitions
                    for register in peripheral.registers:
                        rname: str = reg_name(register, periph_name)
                        reg_decl: str = f'#define _{periph_name}_{rname}_REG'
                        reg_value: int = peripheral.base_address + register.address_offset
                        reg_def: str = (f'(*({REG_QUAL[register.access]} uint{register.size}_t*)'
                                        f'UINT{register.size}_C(0x{reg_value:0{peripheral.size // 4}X}))')
                        reg_comment: str = f'/** @brief {fmt_desc(register.description)} */'
                        reg_gap: int = max((max_reg_name_len + 3) - len(rname), MIN_DEF_COL - len(reg_decl))
                        reg_c_gap: int = (max_reg_qual_len - len(REG_QUAL[register.access])) + 1
                        file.write(f'{" "*(INDENT*2)}{reg_decl}{" "*reg_gap}{reg_def}{" "*reg_c_gap}{reg_comment}\n')
                    file.write("\n")
                    
                    # Write the reset value subsection header
                    file.write(f'{" "*(INDENT*2)}/** @subsection {periph_name} register reset value definitions */\n')
                    file.write("\n")

                    # Iterate through registers and write their reset value definitions
                    for register in peripheral.registers:
                        if register.reset_value is not None:
                            rname: str = reg_name(register, periph_name)
                            reset_decl: str = f'#define _{periph_name}_{rname}_RST'
                            reset_value: int = register.reset_value
                            reset_def: str = f'UINT{register.size}_C(0x{reset_value:0{peripheral.size // 4}X})'
                            reset_comment: str = f'/** @brief {fmt_desc(register.description)} */'
                            reset_gap: int = max((max_reg_name_len + 3) - len(rname), 
                                                 MIN_DEF_COL - len(reset_decl))
                            file.write(f'{" "*(INDENT*2)}{reset_decl}{" "*reset_gap}{reset_def} {reset_comment}\n')
                    file.write("\n")

                    # If any register has associated fields
                    if any(x.fields for x in peripheral.registers):

                        # Determine the maximum length of field names
                        max_field_name_len: int = 0
                        for register in peripheral.registers:
                            if register.fields:
                                for field in register.fields:
                                    rname: str = reg_name(register, periph_name)
                                    field_name_len: int = len(rname) + len(field.name)
                                    if field_name_len > max_field_name_len:
                                        max_field_name_len = field_name_len

                        # Write the field mask subsection header
                        file.write(f'{" "*(INDENT*2)}/** @subsection {periph_name} field mask definitions */\n')
                        file.write("\n")

                        # Iterate through fields and write their mask definitions
                        for register in peripheral.registers:
                            if register.fields:
                                for field in register.fields:
                                    rname: str = reg_name(register, periph_name)
                                    mask_decl: str = f'#define _{periph_name}_{rname}_{field.name.upper()}_MASK'
                                    mask_value: int = ((1 << field.bit_width) - 1) << field.bit_offset
                                    mask_def: str = f'UINT{register.size}_C(0x{mask_value:0{peripheral.size // 4}X})'
                                    mask_comment: str = f'/** @brief {fmt_desc(field.description)} */'
                                    mask_gap: int = max((max_field_name_len + 3) - (len(rname) + len(field.name)), 
                                                        MIN_DEF_COL - len(mask_decl))
                                    file.write(f'{" "*(INDENT*2)}{mask_decl}{" "*mask_gap}{mask_def} {mask_comment}\n')
                        file.write("\n")

                        # Determine maximum length of field positions
                        max_field_pos_digits: int = 0
                        for register in peripheral.registers:
                            if register.fields:
                                for field in register.fields:
                                    field_pos_digits: int = len(str(field.bit_offset))
                                    if field_pos_digits > max_field_pos_digits:
                                        max_field_pos_digits = field_pos_digits

                        # Write the field position subsection header
                        file.write(f'{" "*(INDENT*2)}/** @subsection {periph_name} field position definitions */\n')
                        file.write("\n")
                                    
                        # Iterate through fields and write their position definitions
                        for register in peripheral.registers:
                            if register.fields:
                                for field in register.fields:
                                    rname: str = reg_name(register, periph_name)
                                    pos_decl: str = f'#define _{periph_name}_{rname}_{field.name.upper()}_POS'
                                    pos_value: int = field.bit_offset
                                    pos_def: str = f'INT{register.size}_C({field.bit_offset})'
                                    pos_comment: str = f'/** @brief {fmt_desc(field.description)} */'
                                    pos_gap: int = max((max_field_name_len + 3) - (len(rname) + len(field.name)), 
                                                       MIN_DEF_COL - len(pos_decl))
                                    pos_c_gap: int = (max_field_pos_digits - len(str(pos_value))) + 1
                                    file.write(f'{" "*(INDENT*2)}{pos_decl}{" "*pos_gap}{pos_def}{" "*pos_c_gap}{pos_comment}\n')
                        file.write("\n")

        # Write file footer
        file.write(f'{" "*INDENT}#ifdef __cplusplus\n')
        file.write(f'{" "*(INDENT*2)}}} /* extern "C" */\n')
        file.write(f'{" "*INDENT}#endif\n')
        file.write("\n")
        file.write(f'#endif /* __GUARD__ */')
    
# If error occurs durring file generation:
except Exception as e:

    # Print error msg and traceback
    print("Error occured durring file generation.")
    tb.print_exc()

    # Delete partial output file
    if os.path.exists(OUTPUT_PATH):
        print("Deleting incomplete output file.")
        # os.remove(OUTPUT_PATH)
        exit()

# If no errors, print success message
print("File generation successful!")