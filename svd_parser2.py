###################################################################################################
# IMPORTS
###################################################################################################

# Requires "cmsis_svd" library -> pip install -U cmsis-svd
import cmsis_svd as svd

# Standard libraries
from dataclasses import dataclass
import re
import os

###################################################################################################
# CONFIGURATION
###################################################################################################

# Output file path
OUTPUT_PATH: str = "D:\\main\\projects\\sarp\\svd_parser\\output.h"

# Path to SVD data directory -> git clone --depth=1 -b main https://github.com/cmsis-svd/cmsis-svd-data.git
SVD_PKG_PATH: str = "D:\\main\\projects\\sarp\\svd_parser\\cmsis-svd-data\\data"

# Target device vendor name
VENDOR_NAME: str = "STMicro"

# Core 1 SVD file name
SVD_NAME: str = "STM32H7x5_CM7.svd"

###################################################################################################
# ADVANCED CONFIG
###################################################################################################

PERIPH_DIGIT_ENUM: bool = True
PERIPH_ALPHA_ENUM: bool = True
PERIPH_ENUM_BLIST: list[str] = []
MIN_PERIPH_ENUM_LEN: int = 1
MAX_PERIPH_ENUM_LEN: int = 100

ISR_DIGIT_ENUM: bool = True
ISR_ALPHA_ENUM: bool = False
ISR_PERIPH_ENUM_BLIST: list[str] = []
ISR_ENUM_BLIST: list[str] = []
MIN_ISR_ENUM_LEN: int = 1
MAX_ISR_ENUM_LEN: int = 100

REG_DIGIT_ENUM: bool = True
REG_ALPHA_ENUM: bool = False
REG_PERIPH_ENUM_BLIST: list[str] = []
REG_ENUM_BLIST: list[str] = []
MIN_REG_ENUM_LEN: int = 3
MAX_REG_ENUM_LEN: int = 100

FIELD_DIGIT_ENUM: bool = True
FIELD_ALPHA_ENUM: bool = False
FIELD_PERIPH_ENUM_BLIST: list[str] = []
FIELD_REG_ENUM_BLIST: list[str] = []
FIELD_ENUM_BLIST: list[str] = []
MIN_FIELD_ENUM_LEN: int = 3
MAX_FIELD_ENUM_LEN: int = 100

INDENT: str = "    "

###################################################################################################
# SVD PROCESSING
###################################################################################################

parser = svd.SVDParser.for_packaged_svd(package_root = SVD_PKG_PATH, vendor = VENDOR_NAME, filename = SVD_NAME)
device = parser.get_device(xml_validation = False)

# SPECIAL PROCESSING FOR STM32H745
for periph in device.peripherals:
    if periph.interrupts:
        for isr in periph.interrupts.copy():
            if isr.value == 127 and periph.name != "ADC3":
                periph.interrupts.remove(isr)

# Compares the fields of two registers
def cmp_fields(x, y):
    if (x.fields == None) != (y.fields == None):
        return False
    if x.fields:
        for field_x, field_y in zip(x.fields, y.fields):
            if (field_x.bit_offset != field_y.bit_offset or 
                field_x.bit_width != field_y.bit_width):
                return False
    return True

# Compares the registers of two peripherals
def cmp_registers(x, y):
    if (x.registers == None) != (y.registers == None):
        return False
    if x.registers:
        for reg_x, reg_y in zip(x.registers, y.registers):
            if (reg_x.size != reg_y.size or
                reg_x.address_offset != reg_y.address_offset or
                reg_x.access != reg_y.access or 
                not cmp_fields(reg_x, reg_y)):
                return False
    return True

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
    return new_desc.strip()

# Misc formatting
for periph in device.peripherals:
    periph.dim_name = None
    if periph.interrupts:
        for isr in periph.interrupts:
            if isr.description:
                isr.description = fmt_desc(isr.description)
            else:
                isr.description = "No description."
    if periph.registers:
        for reg in periph.registers:
            reg.dim_name = None
            if reg.description:
                reg.description = fmt_desc(reg.description)
            else:
                reg.description = "No description."
            if reg.access is None: reg.access = svd.parser.SVDAccessType.READ_WRITE
            if len(reg.name.split('_')) > 1: 
                new_reg_name: str = ""
                for rword in reg.name.split('_'):
                    if not any(x.strip("0123456789") == rword for x in periph.name.split("_")):
                        new_reg_name += f'{rword}_'
                if len([x for x in periph.registers if x.name == new_reg_name[:-1]]) == 0:
                    reg.name = new_reg_name[:-1]
            if reg.fields:
                for field in reg.fields:
                    field.dim_name = None
                    if field.description:
                        field.description = fmt_desc(field.description)
                    else:
                        field.description = "No description."

# Format interrupts
isr_dim: dict[str, int] = {}
isr_dim_name: dict[int, str] = {}
isr_dim_index: dict[int, int] = {}
for periph1 in device.peripherals:
    if periph1.interrupts and not any(x == periph1.name for x in ISR_PERIPH_ENUM_BLIST):
        isr_cname_xlist: list[int] = []
        for isr1 in periph1.interrupts:
            if isr_dim_name.get(isr1.value) is None and not any(x == isr1.name for x in ISR_ENUM_BLIST):
                def abort():
                    dname = isr_dim_name.get(isr1.value)
                    if dname is not None:
                        isr_dim[dname] = None
                        isr_cname_xlist.append(dname)
                        for periph3 in device.peripherals:
                            if periph3.interrupts:
                                for isr3 in periph3.interrupts:
                                    if isr_dim_name.get(isr3.value) == dname:
                                        isr_dim_name[isr3.value] = None
                                        isr_dim_index[isr3.value] = None
                isr_num_list: list[int] = []
                for periph2 in device.peripherals:
                    if periph2.interrupts and not any(x == periph2.name for x in ISR_PERIPH_ENUM_BLIST):
                        for isr2 in periph2.interrupts:
                            if (isr1.value != isr2.value and isr_dim_name.get(isr2.value) is None and 
                                not any(x == isr2.name for x in ISR_ENUM_BLIST)):
                                for c1, c2, i in zip(isr1.name, isr2.name, range(min(len(isr1.name), len(isr2.name)))):
                                    if ISR_DIGIT_ENUM and c1 != c2 and c1.isdigit() and c2.isdigit():
                                        isr1_cname = isr1.name[:i] + isr1.name[i:].lstrip('0123456789')
                                        isr2_cname = isr2.name[:i] + isr2.name[i:].lstrip('0123456789')
                                        if isr1_cname == isr2_cname:
                                            isr1_num = int(re.search('[0-9]+', isr1.name[i:]).group())
                                            isr2_num = int(re.search('[0-9]+', isr2.name[i:]).group())
                                            if max(isr1_num, isr2_num) < MAX_ISR_ENUM_LEN:
                                                common_name = isr1.name[:i] + "X" + isr1.name[i:].lstrip('0123456789')
                                                if common_name not in isr_cname_xlist:
                                                    isr_dim_name[isr1.value] = common_name
                                                    isr_dim_index[isr1.value] = isr1_num
                                                    isr_dim_name[isr2.value] = common_name
                                                    isr_dim_index[isr2.value] = isr2_num
                                                    isr_num_list.append(isr2_num)
                                                    if isr_dim.get(common_name):
                                                        isr_dim[common_name] = max(isr_dim[common_name], isr2_num + 1)
                                                    else:
                                                        isr_num_list.append(isr1_num)
                                                        isr_dim[common_name] = max(isr1_num, isr2_num) + 1
                                            else:
                                                abort()
                                if isr_dim_name.get(isr2.value) is None:
                                    for c1, c2, i in zip(isr1.name, isr2.name, range(min(len(isr1.name), len(isr2.name)))):
                                        if ISR_ALPHA_ENUM and c1 != c2 and c1.isupper() and c2.isupper():
                                            isr1_cname = isr1.name[:i] + isr1.name[(i + 1):]
                                            isr2_cname = isr2.name[:i] + isr2.name[(i + 1):]
                                            if isr1_cname == isr2_cname:
                                                isr1_num = ord(isr1.name[i].lower()) - ord('a')
                                                isr2_num = ord(isr2.name[i].lower()) - ord('a')
                                                if max(isr1_num, isr2_num) < MAX_ISR_ENUM_LEN:
                                                    common_name = isr1.name[:i] + "X" + isr1.name[(i + 1):]
                                                    if common_name not in isr_cname_xlist:
                                                        isr_dim_name[isr1.value] = common_name
                                                        isr_dim_index[isr1.value] = isr1_num
                                                        isr_dim_name[isr2.value] = common_name
                                                        isr_dim_index[isr2.value] = isr2_num
                                                        isr_num_list.append(isr2_num)
                                                        if isr_dim.get(common_name):
                                                            isr_dim[common_name] = max(isr_dim[common_name], isr2_num + 1)
                                                        else:
                                                            isr_num_list.append(isr1_num)
                                                            isr_dim[common_name] = max(isr1_num, isr2_num) + 1
                                                else:
                                                    abort()
                if len(isr_num_list) > 0:
                    if len(isr_num_list) < MIN_ISR_ENUM_LEN:
                        abort()

# Format peripherals
periph_dim: dict[str, int] = {} 
periph_cname_xlist: list[str] = []
for periph1 in device.peripherals:
    if periph1.dim_name is None and not any(x == periph1.name for x in PERIPH_ENUM_BLIST):
        def abort():
            dname = periph1.dim_name
            periph_dim[dname] = None
            periph_cname_xlist.append(dname)
            for periph3 in device.peripherals:
                if periph3.dim_name == dname:
                    periph3.dim_name = None
                    periph3.dim_index = None
        periph_num_list: list[int] = []
        for periph2 in device.peripherals:
            if periph2.dim_name is None and not any(x == periph2.name for x in PERIPH_ENUM_BLIST):
                for c1, c2, i in zip(periph1.name, periph2.name, range(min(len(periph1.name), len(periph2.name)))):
                    if PERIPH_DIGIT_ENUM and c1 != c2 and c1.isdigit() and c2.isdigit():
                        periph1_cname = periph1.name[:i] + periph1.name[i:].lstrip('0123456789')
                        periph2_cname = periph2.name[:i] + periph2.name[i:].lstrip('0123456789')
                        if periph1_cname == periph2_cname and cmp_registers(periph1, periph2):
                            periph1_num = int(re.search('[0-9]+', periph1.name[i:]).group())
                            periph2_num = int(re.search('[0-9]+', periph2.name[i:]).group())
                            if max(periph1_num, periph2_num) < MAX_PERIPH_ENUM_LEN:
                                common_name = periph1.name[:i] + "X" + periph1.name[i:].lstrip('0123456789')
                                if common_name not in periph_cname_xlist:
                                    periph1.dim_name = common_name
                                    periph1.dim_index = periph1_num
                                    periph2.dim_name = common_name
                                    periph2.dim_index = periph2_num
                                    periph_num_list.append(periph2_num)
                                    if periph_dim.get(common_name) is not None:
                                        periph_dim[common_name] = max(periph_dim[common_name], periph2_num + 1)
                                    else:
                                        periph_num_list.append(periph1_num)
                                        periph_dim[common_name] = max(periph1_num, periph2_num) + 1
                            else:
                                abort()
                if periph2.dim_name is None:
                    for c1, c2, i in zip(periph1.name, periph2.name, range(min(len(periph1.name), len(periph2.name)))):
                        if PERIPH_ALPHA_ENUM and c1 != c2 and c1.isupper() and c2.isupper():
                            periph1_cname = periph1.name[:i] + periph1.name[(i + 1):]
                            periph2_cname = periph2.name[:i] + periph2.name[(i + 1):]
                            if periph1_cname == periph2_cname and cmp_registers(periph1, periph2):
                                periph1_num = ord(periph1.name[i].lower()) - ord('a')
                                periph2_num = ord(periph2.name[i].lower()) - ord('a')
                                if max(periph1_num, periph2_num) < MAX_PERIPH_ENUM_LEN:
                                    common_name = periph1.name[:i] + "X" + periph1.name[(i + 1):]
                                    if common_name not in periph_cname_xlist:
                                        periph1.dim_name = common_name
                                        periph1.dim_index = periph1_num
                                        periph2.dim_name = common_name
                                        periph2.dim_index = periph2_num
                                        periph_num_list.append(periph2_num)
                                        if periph_dim.get(common_name) is not None:
                                            periph_dim[common_name] = max(periph_dim[common_name], periph2_num + 1)
                                        else:
                                            periph_num_list.append(periph1_num)
                                            periph_dim[common_name] = max(periph1_num, periph2_num) + 1
                                else:
                                    abort()
        if len(periph_num_list) > 0:
            if len(periph_num_list) < MIN_PERIPH_ENUM_LEN:
                abort()
                                    
# Format registers
reg_dim: dict[str, int] = {}
for periph in device.peripherals:
    if periph.registers and not any(x == periph.name for x in REG_PERIPH_ENUM_BLIST):
        reg_cname_xlist: list[str] = []
        for reg1 in periph.registers:
            if reg1.dim_name is None and not any(x == reg1.name for x in REG_ENUM_BLIST):
                def abort():
                    dname = reg1.dim_name
                    reg_dim[f'{periph.name}_{dname}'] = None
                    reg_cname_xlist.append(dname)
                    for reg3 in periph.registers:
                        if reg3.dim_name == dname:
                            reg3.dim_name = None
                            reg3.dim_index = None
                dim_num_list: list[int] = []
                for reg2 in periph.registers:
                    if reg2.dim_name is None and not any(x == reg2.name for x in REG_ENUM_BLIST):
                        for c1, c2, i in zip(reg1.name, reg2.name, range(min(len(reg1.name), len(reg2.name)))):
                            if REG_DIGIT_ENUM and c1 != c2 and c1.isdigit() and c2.isdigit():
                                reg1_cname = reg1.name[:i] + reg1.name[i:].lstrip('0123456789')
                                reg2_cname = reg2.name[:i] + reg2.name[i:].lstrip('0123456789')
                                if reg1_cname == reg2_cname and reg1_cname not in reg_cname_xlist:
                                    if cmp_fields(reg1, reg2):
                                        reg1_num = int(re.search('[0-9]+', reg1.name[i:]).group())
                                        reg2_num = int(re.search('[0-9]+', reg2.name[i:]).group())
                                        if max(reg1_num, reg2_num) < MAX_REG_ENUM_LEN:
                                            common_name = reg1.name[:i] + "X" + reg1.name[i:].lstrip('0123456789')
                                            reg1.dim_name = common_name
                                            reg1.dim_index = reg1_num
                                            reg2.dim_name = common_name
                                            reg2.dim_index = reg2_num
                                            dim_num_list.append(reg2_num)
                                            id = f'{periph.name}_{common_name}'
                                            if reg_dim.get(id) is not None:
                                                reg_dim[id] = max(reg_dim[id], reg2_num + 1)
                                            else:
                                                reg_dim[id] = max(reg1_num, reg2_num) + 1
                                                dim_num_list.append(reg1_num)
                                        else:
                                            abort()
                                    else:
                                        abort()
                        if reg2.dim_name is None:
                            for c1, c2, i in zip(reg1.name, reg2.name, range(min(len(reg1.name), len(reg2.name)))):
                                if REG_ALPHA_ENUM and c1 != c2 and c1.isupper() and c2.isupper():
                                    reg1_cname = reg1.name[:i] + reg1.name[(i + 1):]
                                    reg2_cname = reg2.name[:i] + reg2.name[(i + 1):]
                                    if reg1_cname == reg2_cname:
                                        if cmp_fields(reg1, reg2):
                                            reg1_num = ord(reg1.name[i].lower()) - ord('a')
                                            reg2_num = ord(reg2.name[i].lower()) - ord('a')
                                            if max(reg1_num, reg2_num) < MAX_REG_ENUM_LEN:
                                                common_name = reg1.name[:i] + "X" + reg1.name[(i + 1):]
                                                reg1.dim_name = common_name
                                                reg1.dim_index = reg1_num
                                                reg2.dim_name = common_name
                                                reg2.dim_index = reg2_num
                                                id = f'{periph.name}_{common_name}'
                                                dim_num_list.append(reg2_num)
                                                if reg_dim.get(id) is not None:
                                                    reg_dim[id] = max(reg_dim[id], reg2_num + 1)
                                                else:
                                                    dim_num_list.append(reg1_num)
                                                    reg_dim[id] = max(reg1_num, reg2_num) + 1
                                            else:
                                                abort()
                                        else:
                                            abort()
                if len(dim_num_list) > 0:
                    if len(dim_num_list) < MIN_REG_ENUM_LEN:
                        abort()

# Format fields
field_dim: dict[str, int] = {}
for periph in device.peripherals:
    if periph.registers and not any(x == periph.name for x in FIELD_PERIPH_ENUM_BLIST):
        for reg in periph.registers:
            if reg.fields and not any(x == reg.name for x in FIELD_REG_ENUM_BLIST):
                field_cname_xlist: list[str] = []
                for field1 in reg.fields:
                    if field1.dim_name is None and not any(x == field1.name for x in FIELD_ENUM_BLIST):
                        def abort():
                            dname = field1.dim_name
                            field_dim[f'{periph.name}_{reg.name}_{dname}'] = None
                            field_cname_xlist.append(dname)
                            for field3 in reg.fields:
                                if field3.dim_name == dname:
                                    field3.dim_name = None
                                    field3.dim_index = None
                        field_num_list: list[int] = []
                        for field2 in reg.fields:
                            if field2.dim_name is None and not any(x == field2.name for x in FIELD_ENUM_BLIST):
                                for c1, c2, i in zip(field1.name, field2.name, range(min(len(field1.name), len(field2.name)))):
                                    if FIELD_DIGIT_ENUM and c1 != c2 and c1.isdigit() and c2.isdigit():
                                        field1_cname = field1.name[:i] + field1.name[i:].lstrip('0123456789')
                                        field2_cname = field2.name[:i] + field2.name[i:].lstrip('0123456789')
                                        if field1_cname == field2_cname:
                                            field1_num = int(re.search('[0-9]+', field1.name[i:]).group())
                                            field2_num = int(re.search('[0-9]+', field2.name[i:]).group())
                                            if max(field1_num, field2_num) < MAX_FIELD_ENUM_LEN:
                                                common_name = field1.name[:i] + "X" + field1.name[i:].lstrip('0123456789')
                                                if common_name not in field_cname_xlist:
                                                    field1.dim_name = common_name
                                                    field1.dim_index = field1_num
                                                    field2.dim_name = common_name
                                                    field2.dim_index = field2_num
                                                    field_num_list.append(field2_num)
                                                    id = f'{periph.name}_{reg.name}_{common_name}'
                                                    if field_dim.get(id) is not None:
                                                        field_dim[id] = max(field_dim[id], field2_num + 1)
                                                    else:
                                                        field_num_list.append(field1_num)
                                                        field_dim[id] = max(field1_num, field2_num) + 1
                                            else:
                                                abort()
                                if field2.dim_name is None:
                                    for c1, c2, i in zip(field1.name, field2.name, range(min(len(field1.name), len(field2.name)))):
                                        if FIELD_ALPHA_ENUM and c1 != c2 and c1.isupper() and c2.isupper():
                                            field1_cname = field1.name[:i] + field1.name[(i + 1):]
                                            field2_cname = field2.name[:i] + field2.name[(i + 1):]
                                            if field1_cname == field2_cname:
                                                field1_num = ord(field1.name[i].lower()) - ord('a')
                                                field2_num = ord(field2.name[i].lower()) - ord('a')
                                                if max(field1_num, field2_num) < MAX_FIELD_ENUM_LEN:
                                                    common_name = field1.name[:i] + "X" + field1.name[(i + 1):]
                                                    if common_name not in field_cname_xlist:
                                                        field1.dim_name = common_name
                                                        field1.dim_index = field1_num
                                                        field2.dim_name = common_name
                                                        field2.dim_index = field2_num
                                                        field_num_list.append(field2_num)
                                                        id = f'{periph.name}_{reg.name}_{common_name}'
                                                        if field_dim.get(id) is not None:
                                                            field_dim[id] = max(field_dim[id], field2_num + 1)
                                                        else:
                                                            field_num_list.append(field1_num)
                                                            field_dim[id] = max(field1_num, field2_num) + 1
                                                else:
                                                    abort()
                        if len(field_num_list) > 0:
                            if len(field_num_list) < MIN_FIELD_ENUM_LEN:
                                abort()

###################################################################################################
# OUTPUT GENERATION
###################################################################################################

# FIX DMA_STR ISR
# 

# for periph in device.peripherals:
#     if periph.registers:
#         for reg in periph.registers:
#             if reg.dim_name:
#                 print(f'DIM: {periph.name} {reg.name}, {reg.dim_name}, {reg.dim_index}, {reg_dim[f"{periph.name}_{reg.dim_name}"]}')
#             else:
#                 print(f'NONE: {periph.name} {reg.name}')

# Qualifiers associated with different register access types
REG_QUAL: dict[svd.parser.SVDAccessType, str] = {
    svd.parser.SVDAccessType.READ_ONLY: "_RO",
    svd.parser.SVDAccessType.WRITE_ONLY: "_RW",
    svd.parser.SVDAccessType.READ_WRITE: "_RW",
    svd.parser.SVDAccessType.WRITE_ONCE: "_RW",
    svd.parser.SVDAccessType.READ_WRITE_ONCE: "_RW"
}

if os.path.exists(OUTPUT_PATH): 
    os.remove(OUTPUT_PATH)
with open(OUTPUT_PATH, 'w') as file:   

    file.write(f"{INDENT}#include <stdint.h>\n")
    file.write("\n")

    file.write(f'{INDENT}#define _RO const volatile\n')
    file.write(f'{INDENT}#define _RW volatile\n')

    periph_xlist: list[str] = []
    for periph1 in device.peripherals:
        if periph1.dim_name:
            if periph1.dim_name in periph_xlist: continue
            periph_xlist.append(periph1.dim_name)

        periph_name: str = periph1.dim_name if periph1.dim_name else periph1.name
        periph_name = periph_name.upper()

        header_written: bool = False
        def write_header():
            file.write(f'{INDENT}/**********************************************************************************************\n')
            file.write(f'{INDENT} * @section {periph_name} Definitions\n')
            file.write(f'{INDENT} **********************************************************************************************/\n')
            file.write("\n")       

        if periph1.interrupts:
            isr_decl_list: list[str] = []
            isr_def_list: list[str] = []
            isr_comment_list: list[str] = []
            isr_array_list: list[bool] = []
            isr_xlist: list[str] = []
            for isr in periph1.interrupts:
                if isr_dim_name.get(isr.value) is not None:
                    if isr_dim_name[isr.value] in isr_xlist: continue
                    isr_xlist.append(isr_dim_name[isr.value])
                    dim_value_list: list[int] = []
                    dim_comment_list: list[str] = []
                    for i in range(isr_dim[isr_dim_name[isr.value]]):
                        for periph2 in device.peripherals:
                            if periph2.interrupts:
                                for isr2 in periph2.interrupts:
                                    if (isr_dim_name.get(isr2.value) == isr_dim_name[isr.value] and 
                                        isr_dim_index[isr2.value] == i):
                                        dim_value_list.append(isr2.value)
                                        dim_comment_list.append(f'/** @brief {isr2.description} */')
                        if len(dim_value_list) == i:
                            dim_value_list.append(-1)
                            dim_comment_list.append("/** @brief Invalid index. */")
                    max_index_len = max([len(str(x)) for x in dim_value_list], default = 1) + 3
                    isr_decl_list.append(f'{isr_dim_name[isr.value].upper()}_IRQ'
                        f'[{isr_dim[isr_dim_name[isr.value]]}]')
                    isr_def_list.append(f'{{\n{("".join(f'{INDENT}  INT32_C({x}), {" "*(max_index_len - len(str(x)))}{cmt}\n' 
                                                        for x, cmt in zip(dim_value_list, dim_comment_list)))}{INDENT}}}')
                    isr_comment_list.append("")
                    isr_array_list.append(True)
                else:
                    isr_decl_list.append(f'{isr.name.upper()}_IRQ')
                    isr_def_list.append(f'INT32_C({str(isr.value)})')
                    isr_array_list.append(False)
                    isr_comment_list.append(f'/** @brief {isr.description} */')
            if len(isr_decl_list) > 0:
                if not header_written:
                    header_written = True
                    write_header()
                if any(x for x in isr_array_list):
                    file.write(f'{INDENT}/** @subsection {periph_name} IRQ interrupt array definitions */\n')
                    file.write("\n")
                    max_isr_decl_len = max([len(x) for x in isr_decl_list if isr_array_list[isr_decl_list.index(x)]], default = 1)
                    for isr_decl, isr_def, isr_array in zip(isr_decl_list, isr_def_list, isr_array_list):
                        if isr_array:
                            # isr_def_gap = (max_isr_decl_len - len(isr_decl)) + 1
                            isr_def_gap = 1
                            file.write(f'{INDENT}static const int32_t {isr_decl}{" "*isr_def_gap}= {isr_def};\n')
                            file.write("\n")
                if any(not x for x in isr_array_list):
                    file.write(f'{INDENT}/** @subsection {periph_name} IRQ interrupt definitions */\n')
                    file.write("\n")
                    max_isr_decl_len = max([len(x) for x in isr_decl_list if not isr_array_list[isr_decl_list.index(x)]], default = 1)
                    max_isr_def_len = max([len(x) for x in isr_def_list if not isr_array_list[isr_def_list.index(x)]], default = 1)
                    for isr_decl, isr_def, isr_comment, isr_array in zip(isr_decl_list, isr_def_list, isr_comment_list, isr_array_list):
                        if not isr_array:
                            # isr_def_gap = (max_isr_decl_len - len(isr_decl)) + 1
                            isr_def_gap = 1
                            isr_cmt_gap = ((max_isr_decl_len + max_isr_def_len) - (len(isr_decl) + len(isr_def))) + 3
                            file.write(f'{INDENT}static const int32_t {isr_decl}{" "*isr_def_gap}= {isr_def};{" "*isr_cmt_gap}{isr_comment}\n')
                    file.write("\n")

        if periph1.registers:
            first_reg: bool = True
            reg_pre_list: list[str] = []
            reg_decl_list: list[str] = []
            reg_def_list: list[str] = []
            reg_array_list: list[bool] = []
            reg_cmt_list: list[str] = []
            reg_xlist: list[str] = []
            for reg1 in periph1.registers:
                if reg1.dim_name:
                    if reg1.dim_name in reg_xlist: continue
                    reg_xlist.append(reg1.dim_name)
                    if periph1.dim_name:
                        dim1_def_list: list[str] = []
                        for i in range(periph_dim[periph1.dim_name]):
                            dim2_def_list: list[str] = []
                            dim2_cmt_list: list[str] = []
                            for periph2 in device.peripherals:
                                if periph2.dim_name == periph1.dim_name and periph2.dim_index == i:
                                    for j in range(reg_dim[f'{periph1.name}_{reg1.dim_name}']):
                                        for reg2 in periph2.registers:
                                            if reg2.dim_name == reg1.dim_name and reg2.dim_index == j:
                                                reg_addr: int = periph2.base_address + reg2.address_offset
                                                dim2_def_list.append(f'UINT{reg1.size}_C(0x{reg_addr:0{reg1.size // 4}X})')
                                                dim2_cmt_list.append(f'/** @brief {reg2.description} */')
                                        if len(dim2_def_list) == j:
                                            dim2_def_list.append(f'UINT{reg1.size}_C(0x{0:0{reg1.size // 4}X})')
                                            dim2_cmt_list.append("/** @brief Invalid index. */")
                            if len(dim2_def_list) == 0:
                                for j in range(reg_dim[f'{periph1.name}_{reg1.dim_name}']):
                                    dim2_def_list.append(f'UINT{reg1.size}_C(0x{0:0{reg1.size // 4}X})')
                                    dim2_cmt_list.append("/** @brief Invalid index. */")
                            reg_cast: str = f'({REG_QUAL[reg1.access]} uint{reg1.size}_t* const)'
                            max_dim_def_len = max([len(x) for x in dim2_def_list], default = 1) + 3
                            dim1_def_list.append(f'{{\n{("".join(f'{INDENT*2}{reg_cast}{x},{" "*(max_dim_def_len - len(x))}{cmt}\n' 
                                                                 for x, cmt in zip(dim2_def_list, dim2_cmt_list)))}{INDENT}  }}')
                        reg_decl_list.append(f'{periph_name}_{reg1.dim_name.upper()}_REG'
                            f'[{periph_dim[periph1.dim_name]}][{reg_dim[f'{periph1.name}_{reg1.dim_name}']}]')
                        reg_def_list.append(f'{{\n{("".join(f'{INDENT}  {x},\n' for x in dim1_def_list))}{INDENT}}}')
                        reg_array_list.append(True)
                        reg_cmt_list.append("")
                    else:
                        dim_def_list: list[str] = []
                        dim_cmt_list: list[str] = []
                        for i in range(reg_dim[f'{periph1.name}_{reg1.dim_name}']):
                            for reg2 in periph1.registers:
                                if reg2.dim_name == reg1.dim_name and reg2.dim_index == i:
                                    reg_addr: int = periph1.base_address + reg2.address_offset
                                    dim_def_list.append(f'UINT{reg1.size}_C(0x{reg_addr:0{reg1.size // 4}X})')
                                    dim_cmt_list.append(f'/** @brief {reg2.description} */')
                            if len(dim_def_list) == i:
                                dim_def_list.append(f'UINT{reg1.size}_C(0x{0:0{reg1.size // 4}X})')
                                dim_cmt_list.append("/** @brief Invalid index. */")
                        reg_decl_list.append(f'{periph_name}_{reg1.dim_name.upper()}_REG'
                            f'[{reg_dim[f'{periph1.name}_{reg1.dim_name}']}]')
                        max_dim_def_len = max([len(x) for x in dim_def_list], default = 1) + 3
                        reg_cast: str = f'({REG_QUAL[reg1.access]} uint{reg1.size}_t* const)'
                        reg_def_list.append(f'{{\n{("".join(f'{INDENT}  {reg_cast}{x},{" "*(max_dim_def_len - len(x))}{cmt}\n' 
                                                            for x, cmt in zip(dim_def_list, dim_cmt_list)))}{INDENT}}}')
                        reg_array_list.append(True)
                        reg_cmt_list.append("")
                else:
                    if periph1.dim_name:
                        dim_def_list: list[str] = []
                        dim_cmt_list: list[str] = []
                        for i in range(periph_dim[periph1.dim_name]):
                            for periph2 in device.peripherals:
                                if periph2.dim_name == periph1.dim_name and periph2.dim_index == i:
                                    for reg2 in periph2.registers:
                                        if reg2.address_offset == reg1.address_offset:
                                            reg_addr: int = periph2.base_address + reg2.address_offset
                                            dim_def_list.append(f'UINT{reg1.size}_C(0x{reg_addr:0{reg1.size // 4}X})')
                                            dim_cmt_list.append(f'/** @brief {reg2.description} */')
                                            break
                            if len(dim_def_list) == i:
                                dim_def_list.append(f'UINT{reg1.size}_C(0x{0:0{reg1.size // 4}X})')
                                dim_cmt_list.append("/** @brief Invalid index. */")
                        reg_decl_list.append(f'{periph_name}_{reg1.name.upper()}_REG'
                            f'[{periph_dim[periph1.dim_name]}]')
                        max_dim_def_len = max([len(x) for x in dim_def_list], default = 1) + 3
                        reg_cast: str = f'({REG_QUAL[reg1.access]} uint{reg1.size}_t* const)'
                        reg_def_list.append(f'{{\n{("".join(f'{INDENT}  {reg_cast}{x},{" "*(max_dim_def_len - len(x))}{cmt}\n' 
                                                            for x, cmt in zip(dim_def_list, dim_cmt_list)))}{INDENT}}}')
                        reg_array_list.append(True)
                        reg_cmt_list.append("")
                    else:
                        reg_decl_list.append(f'{periph_name}_{reg1.name.upper()}_REG')
                        reg_addr: int = periph1.base_address + reg1.address_offset
                        reg_cast: str = f'({REG_QUAL[reg1.access]} uint{reg1.size}_t* const)'
                        reg_def_list.append(f'{reg_cast}UINT{reg1.size}_C(0x{reg_addr:0{reg1.size // 4}X})')
                        reg_array_list.append(False)
                        reg_cmt_list.append(f'/** @brief {reg1.description} */')
                reg_pre_list.append(f'static {REG_QUAL[reg1.access]} uint{reg1.size}_t* const')
            if len(reg_decl_list) > 0:
                if not header_written:
                    header_written = True
                    write_header()
                if any(x for x in reg_array_list):
                    file.write(f'{INDENT}/** @subsection {periph_name} register array definitions */\n')
                    file.write("\n")
                    max_reg_pre_len = max([len(x) for x in reg_pre_list if reg_array_list[reg_pre_list.index(x)]], default = 1)
                    max_reg_decl_len = max([len(x) for x in reg_decl_list if reg_array_list[reg_decl_list.index(x)]], default = 1)
                    for reg_pre, reg_decl, reg_def, reg_array in zip(reg_pre_list, reg_decl_list, reg_def_list, reg_array_list):
                        if reg_array:
                            # reg_def_gap = ((max_reg_decl_len + max_reg_pre_len) - (len(reg_pre) + len(reg_decl))) + 3
                            reg_def_gap = 1
                            file.write(f'{INDENT}{reg_pre} {reg_decl}{" "*reg_def_gap}= {reg_def};\n')
                            file.write("\n")
                if any(not x for x in reg_array_list):
                    file.write(f'{INDENT}/** @subsection {periph_name} register definitions */\n')
                    file.write("\n")
                    max_reg_pre_len = max([len(x) for x in reg_pre_list if not reg_array_list[reg_pre_list.index(x)]], default = 1)
                    max_reg_decl_len = max([len(x) for x in reg_decl_list if not reg_array_list[reg_decl_list.index(x)]], default = 1)
                    for reg_pre, reg_decl, reg_def, reg_cmt, reg_array in zip(reg_pre_list, reg_decl_list, reg_def_list, reg_cmt_list, reg_array_list):
                        if not reg_array:
                            reg_cmt_gap = ((max_reg_decl_len + max_reg_pre_len) - (len(reg_pre) + len(reg_decl))) + 3
                            # reg_def_gap = ((max_reg_decl_len + max_reg_pre_len) - (len(reg_pre) + len(reg_decl))) + 3
                            reg_def_gap = 1
                            file.write(f'{INDENT}{reg_pre} {reg_decl}{" "*reg_def_gap}= {reg_def};{" "*reg_cmt_gap}{reg_cmt}\n')
                    file.write("\n")

        field_xlist: list[str] = []
        field_decl_list: list[str] = []
        field_def_list: list[str] = []
        field_array_list: list[bool] = []
        field_cmt_list: list[str] = []
        for reg in periph1.registers:
            if reg.fields:
                reg_name: str = reg.dim_name if reg.dim_name else reg.name
                reg_name = reg_name.upper()
                for field1 in reg.fields:
                    if field1.bit_width != reg.size:
                        if field1.dim_name:
                            if field1.dim_name in field_xlist: continue
                            field_xlist.append(field1.dim_name)
                            dim_mask_list: list[int] = []
                            dim_cmt_list: list[str] = []
                            for i in range(field_dim[f'{periph1.name}_{reg.name}_{field1.dim_name}']):
                                for field2 in reg.fields:
                                    if field2.dim_name == field1.dim_name and field2.dim_index == i:
                                        dim_mask_list.append(((1 << field2.bit_width) - 1) << field2.bit_offset)
                                        dim_cmt_list.append(f'/** @brief {field2.description} */')
                                if len(dim_mask_list) == i:
                                    dim_mask_list.append(0)
                                    dim_cmt_list.append("/** @brief Invalid index. */")
                            field_decl_list.append(f'{periph_name}_{reg_name}_{field1.dim_name.upper()}_MASK'
                                f'[{field_dim[f"{periph1.name}_{reg.name}_{field1.dim_name}"]}]')
                            field_def_list.append(f'{{\n{("".join(f'{INDENT}  UINT{reg.size}_C(0x{x:0{reg.size // 4}X}),'
                                f'   {cmt}\n' for x, cmt in zip(dim_mask_list, dim_cmt_list)))}{INDENT}}}')
                            field_array_list.append(True)
                            field_cmt_list.append("")
                        else:
                            mask_value: int = ((1 << field1.bit_width) - 1) << field1.bit_offset
                            field_decl_list.append(f'{periph_name}_{reg_name}_{field1.name.upper()}_MASK')
                            field_def_list.append(f'UINT{reg.size}_C(0x{mask_value:0{reg.size // 4}X})')
                            field_array_list.append(False)
                            field_cmt_list.append(f'/** @brief {field1.description} */')
        if len(field_decl_list) > 0:
            if not header_written:
                header_written = True
                write_header()
            if any(x for x in field_array_list):
                file.write(f'{INDENT}/** @subsection {periph_name} field mask array definitions */\n')
                file.write("\n")
                max_field_decl_len = max([len(x) for x in field_decl_list if field_array_list[field_decl_list.index(x)]], default = 1)
                for field_decl, field_def, field_array in zip(field_decl_list, field_def_list, field_array_list):
                    if field_array:
                        # field_def_gap = (max_field_decl_len - len(field_decl)) + 1
                        field_def_gap = 1
                        file.write(f'{INDENT}static const uint{reg.size}_t {field_decl}{" "*field_def_gap}= {field_def};\n')
                        file.write("\n")
            if any(not x for x in field_array_list):
                file.write(f'{INDENT}/** @subsection {periph_name} field mask definitions */\n')
                file.write("\n")
                max_field_decl_len = max([len(x) for x in field_decl_list if not field_array_list[field_decl_list.index(x)]], default = 1)
                max_field_def_len = max([len(x) for x in field_def_list if not field_array_list[field_def_list.index(x)]], default = 1)
                for field_decl, field_def, field_cmt, field_array in zip(field_decl_list, field_def_list, field_cmt_list, field_array_list):
                    if not field_array:
                        field_cmt_gap = ((max_field_decl_len + max_field_def_len) - (len(field_decl) + len(field_def))) + 3
                        # field_def_gap = (max_field_decl_len - len(field_decl)) + 1
                        field_def_gap = 1
                        file.write(f'{INDENT}static const uint32_t {field_decl}{" "*field_def_gap}= {field_def};{" "*field_cmt_gap}{field_cmt}\n')
                file.write("\n")

        field_xlist: list[str] = []
        field_decl_list: list[str] = []
        field_array_list: list[bool] = []
        field_def_list: list[str] = []
        field_cmt_list: list[str] = []
        for reg in periph1.registers:
            if reg.fields:
                for field1 in reg.fields:
                    if field1.bit_width != reg.size:
                        if field1.dim_name:
                            if field1.dim_name in field_xlist: continue
                            field_xlist.append(field1.dim_name)
                            dim_pos_list: list[int] = []
                            dim_cmt_list: list[str] = []
                            for i in range(field_dim[f'{periph1.name}_{reg.name}_{field1.dim_name}']):
                                for field2 in reg.fields:
                                    if field2.dim_name == field1.dim_name and field2.dim_index == i:
                                        dim_pos_list.append(field2.bit_offset)
                                        dim_cmt_list.append(f'/** @brief {field2.description} */')
                                if len(dim_pos_list) == i:
                                    dim_pos_list.append(-1)
                                    dim_cmt_list.append("/** @brief Invalid index. */")
                            max_field_def_len = max([len(str(x)) for x in dim_pos_list], default = 1) + 3
                            field_decl_list.append(f'{periph_name}_{reg_name}_{field1.dim_name.upper()}_POS'
                                f'[{field_dim[f"{periph1.name}_{reg.name}_{field1.dim_name}"]}]')
                            field_def_list.append(f'{{\n{("".join(f'{INDENT}  INT32_C({x}),{" "*(max_field_def_len - len(str(x)))}{cmt}\n' 
                                for x, cmt in zip(dim_pos_list, dim_cmt_list)))}{INDENT}}}')
                            field_array_list.append(True)
                            field_cmt_list.append("")
                        else:
                            field_decl_list.append(f'{periph_name}_{reg_name}_{field1.name.upper()}_POS')
                            field_def_list.append(f'INT32_C({field1.bit_offset})')
                            field_array_list.append(False)
                            field_cmt_list.append(f'/** @brief {field1.description} */')
        if len(field_decl_list) > 0:
            if not header_written:
                header_written = True
                write_header()
            if any(x for x in field_array_list):
                file.write(f'{INDENT}/** @subsection {periph_name} field position array definitions */\n')
                file.write("\n")
                max_field_decl_len = max([len(x) for x in field_decl_list if field_array_list[field_decl_list.index(x)]], default = 1)
                for field_decl, field_def, field_array in zip(field_decl_list, field_def_list, field_array_list):
                    if field_array:
                        # field_def_gap = (max_field_decl_len - len(field_decl)) + 1
                        field_def_gap = 1
                        file.write(f'{INDENT}static const int32_t {field_decl}{" "*field_def_gap}= {field_def};\n')
                        file.write("\n")
            if any(not x for x in field_array_list):
                file.write(f'{INDENT}/** @subsection {periph_name} field position definitions */\n')
                file.write("\n")
                max_field_def_len = max([len(x) for x in field_def_list if not field_array_list[field_def_list.index(x)]], default = 1)
                max_field_decl_len = max([len(x) for x in field_decl_list if not field_array_list[field_decl_list.index(x)]], default = 1)
                for field_decl, field_def, field_cmt, field_array in zip(field_decl_list, field_def_list, field_cmt_list, field_array_list):
                    if not field_array:
                        field_cmt_gap = ((max_field_decl_len + max_field_def_len) - (len(field_decl) + len(field_def))) + 3
                        # field_def_gap = (max_field_decl_len - len(field_decl)) + 1
                        field_def_gap = 1
                        file.write(f'{INDENT}static const int32_t {field_decl}{" "*field_def_gap}= {field_def};{" "*field_cmt_gap}{field_cmt}\n')
                file.write("\n")