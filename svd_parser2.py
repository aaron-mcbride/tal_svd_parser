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
PERIPH_DIGIT_ENUM_EXC_LIST: list[str] = []
PERIPH_ALPHA_ENUM: bool = True
PERIPH_ALPHA_ENUM_EXC_LIST: list[str] = []
MIN_PERIPH_ENUM_LEN: int = 2
MAX_PERIPH_ENUM_LEN: int = 100

ISR_DIGIT_ENUM: bool = True
ISR_DIGIT_ENUM_EXC_LIST: list[str] = []
ISR_ALPHA_ENUM: bool = False
ISR_ALPHA_ENUM_EXC_LIST: list[str] = []
MIN_ISR_ENUM_LEN: int = 2
MAX_ISR_ENUM_LEN: int = 100

REG_DIGIT_ENUM: bool = True
REG_DIGIT_ENUM_EXC_LIST: list[str] = []
REG_ALPHA_ENUM: bool = False
REG_ALPHA_ENUM_EXC_LIST: list[str] = []
MIN_REG_ENUM_LEN: int = 2
MAX_REG_ENUM_LEN: int = 100

FIELD_DIGIT_ENUM: bool = True
FIELD_DIGIT_ENUM_EXC_LIST: list[str] = ["SAI1SRC", "SAI23SRC"]
FIELD_ALPHA_ENUM: bool = False
FIELD_ALPHA_ENUM_EXC_LIST: list[str] = []
MIN_FIELD_ENUM_LEN: int = 2
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

def diff_start_digit(text1: str, text2: str):
    if text1[0].isdigit() and text2[0].isdigit():
        for i in range(max(len(text1), len(text2))):
            c1 = None if i >= len(text1) else text1[i]
            c2 = None if i >= len(text2) else text2[i]
            if (c1 is not None and c1.isdigit()) or (c2 is not None and c2.isdigit()):
                if c1 != c2:
                    return True
            else:
                return False
    return False

def diff_start_alpha(text1: str, text2: str):
    return (text1[0] != text2[0] and 
            text1[0].isalpha() and text2[0].isalpha() and 
            len(text1) == len(text2) and 
            (len(text1) == 1 or text1[1] == text2[1]))

# Compares the fields of two registers by digits
def cmp_fields_dig(x, y, x_num, y_num):
    if x.fields:
        if not y.fields:
            return False
        if len(x.fields) != len(y.fields):
            return False
        new_x_fields = x.fields.copy()
        new_y_fields = y.fields.copy()
        for field1 in x.fields:
            field_found: bool = False
            for field2 in y.fields:
                if field1.name == field2.name:
                    if (field1.bit_offset == field2.bit_offset and
                        field1.bit_width == field2.bit_width and
                        field1.access == field2.access):
                        field_found = True
                    else:
                        return False
                elif field1.bit_offset == field2.bit_offset and field1.bit_width == field2.bit_width:
                    if field1.access != field2.access:
                        return False
                    else:
                        for i in range(min(len(field1.name), len(field2.name))):
                            if diff_start_digit(field1.name[i:], field2.name[i:]):
                                field1_cname = field1.name[:i] + field1.name[i:].lstrip('0123456789')
                                field2_cname = field2.name[:i] + field2.name[i:].lstrip('0123456789')
                                common_name = field1.name[:i] + "x" + field1.name[i:].lstrip('0123456789')
                                if field1_cname == field2_cname:
                                    field1_num = int(re.search('[0-9]+', field1.name[i:]).group())
                                    field2_num = int(re.search('[0-9]+', field2.name[i:]).group())
                                    if field1_num == x_num and field2_num == y_num:
                                        field_found = True
                                        for xf in new_x_fields:
                                            if xf.name == field1.name:
                                                xf.name = common_name
                                        for yf in new_y_fields:
                                            if yf.name == field2.name:
                                                yf.name = common_name
                                        break
                                    else:
                                        return False
                        if field_found == False and x.get_parent_peripheral().name == "MDMA":
                            print(f'{field1.name}, {field2.name}')
            if not field_found:
                return False
        return (new_x_fields, new_y_fields)
    return (None, None)

# Compares the fields of two registers by alphabet
def cmp_fields_alpha(x, y, x_alpha, y_alpha):
    if x.fields:
        if not y.fields:
            return False
        if len(x.fields) != len(y.fields):
            return False
        new_x_fields = x.fields.copy()
        new_y_fields = y.fields.copy()
        for field1 in x.fields:
            field_found: bool = False
            for field2 in y.fields:
                if field_found: break
                if field1.name == field2.name:
                    if (field1.bit_offset == field2.bit_offset and
                        field1.bit_width == field2.bit_width and
                        field1.access == field2.access):
                        field_found = True
                        break
                    else:
                        return False
                elif field1.bit_offset == field2.bit_offset and field1.bit_width == field2.bit_width:
                    if field1.access != field2.access:
                        return False
                    else:
                        for i in range(min(len(field1.name), len(field2.name))):
                            if diff_start_alpha(field1.name[i:], field2.name[i:]):
                                field1_cname = field1.name[:i] + field1.name[(i + 1):]
                                field2_cname = field2.name[:i] + field2.name[(i + 1):]
                                common_name = field1.name[:i] + "x" + field1.name[(i + 1):]
                                if field1_cname == field2_cname:
                                    field1_num = ord(field1.name[i].lower()) - ord('a')
                                    field2_num = ord(field2.name[i].lower()) - ord('a')
                                    if field1_num == x_alpha and field2_num == y_alpha:
                                        field_found = True
                                        for xf in new_x_fields:
                                            if xf.name == field1:
                                                xf.name = common_name
                                        for yf in new_y_fields:
                                            if yf.name == field2:
                                                yf.name = common_name
                                        break
                                    else:
                                        return False
            if not field_found:
                return False
        return (new_x_fields, new_y_fields)
    return (None, None)
        
# Compares the registers of two peripherals
def cmp_registers_dig(x, y, x_num, y_num):
    if x.registers:
        if not y.registers:
            return False
        if len(x.registers) != len(y.registers):
            return False
        new_x_regs = x.registers.copy()
        new_y_regs = y.registers.copy()
        for reg1 in x.registers:
            reg_found: bool = None
            for reg2 in y.registers:
                if reg_found: break
                if reg1.name == reg2.name:
                    if (reg1.address_offset == reg2.address_offset and
                        reg1.size == reg2.size and
                        reg1.access == reg2.access and
                        cmp_fields_dig(reg1, reg2, x_num, y_num) is not False):
                        reg_found = True
                        break
                    else:
                        return False
                elif reg1.address_offset == reg2.address_offset and reg1.size == reg2.size:
                    new_fields = cmp_fields_dig(reg1, reg2, x_num, y_num)
                    if reg1.access != reg2.access or new_fields is False:
                        return False
                    else:
                        for i in range(min(len(reg1.name), len(reg2.name))):
                            if diff_start_digit(reg1.name[i:], reg2.name[i:]):
                                reg1_cname = reg1.name[:i] + reg1.name[i:].lstrip('0123456789')
                                reg2_cname = reg2.name[:i] + reg2.name[i:].lstrip('0123456789')
                                common_name = reg1.name[:i] + "x" + reg1.name[i:].lstrip('0123456789')
                                if reg1_cname == reg2_cname:
                                    reg1_num = int(re.search('[0-9]+', reg1.name[i:]).group())
                                    reg2_num = int(re.search('[0-9]+', reg2.name[i:]).group())
                                    if reg1_num == 0 and reg2_num == 0:
                                        reg_found = True
                                        for xr in new_x_regs:
                                            if xr == reg1:
                                                xr.name = common_name
                                                xr.fields = new_fields[0]
                                        for yr in new_y_regs:
                                            if yr == reg2:
                                                yr.name = common_name
                                                yr.fields = new_fields[1]
                                        break
                                    else:
                                        return False
            if not reg_found:
                return False
        return (new_x_regs, new_y_regs)
    return (None, None)

# Compares the registers of two peripherals by alphabet
def cmp_registers_alpha(x, y, x_alpha, y_alpha):
    if x.registers:
        if not y.registers:
            return False
        if len(x.registers) != len(y.registers):
            return False
        new_x_regs = x.registers.copy()
        new_y_regs = y.registers.copy()
        for reg1 in x.registers:
            reg_found: bool = None
            for reg2 in y.registers:
                if reg_found: break
                if reg1.name == reg2.name:
                    if (reg1.address_offset == reg2.address_offset and
                        reg1.size == reg2.size and
                        reg1.access == reg2.access and
                        cmp_fields_alpha(reg1, reg2, x_alpha, y_alpha) is not False):
                        reg_found = True
                        break
                    else:
                        return False
                elif reg1.address_offset == reg2.address_offset and reg1.size == reg2.size:
                    new_fields = cmp_fields_alpha(reg1, reg2, x_alpha, y_alpha)
                    if reg1.access != reg2.access or new_fields is False:
                        return False
                    else:
                        for i in range(min(len(reg1.name), len(reg2.name))):
                            if diff_start_alpha(reg1.name[i:], reg2.name[i:]):
                                reg1_cname = reg1.name[:i] + reg1.name[(i + 1):]
                                reg2_cname = reg2.name[:i] + reg2.name[(i + 1):]
                                common_name = reg1.name[:i] + "x" + reg1.name[(i + 1):]
                                if reg1_cname == reg2_cname:
                                    reg1_num = ord(reg1.name[i].lower()) - ord('a')
                                    reg2_num = ord(reg2.name[i].lower()) - ord('a')
                                    if reg1_num == x_alpha and reg2_num == y_alpha:
                                        reg_found = True
                                        for xr in new_x_regs:
                                            if xr == reg1:
                                                xr.name = common_name
                                                xr.fields = new_fields[0]
                                        for yr in new_y_regs:
                                            if yr == reg2:
                                                yr.name = common_name
                                                yr.fields = new_fields[1]
                                        break
                                    else:
                                        return False
            if not reg_found:
                return False
        return (new_x_regs, new_y_regs)
    return (None, None)

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
    periph.name = periph.name.upper()
    if periph.registers:
        for reg in periph.registers:
            reg.dim_name = None
            if reg.description:
                reg.description = fmt_desc(reg.description)
            else:
                reg.description = "No description."
            if reg.access is None: 
                reg.access = svd.parser.SVDAccessType.READ_WRITE
            reg.name = reg.name.upper()
            if reg.fields:
                for field in reg.fields:
                    field.dim_name = None
                    if field.description:
                        field.description = fmt_desc(field.description)
                    else:
                        field.description = "No description."
                    field.name = field.name.upper()

# Format interrupts
isr_dim: dict[str, int] = {}
isr_dim_name: dict[int, str] = {}
isr_dim_index: dict[int, int] = {}
for periph1 in device.peripherals:
    if periph1.interrupts:
        isr_cname_xlist: list[int] = []
        for isr1 in periph1.interrupts:
            if isr_dim_name.get(isr1.value) is None:
                def abort(common_name):
                    if common_name is not None:
                        isr_dim[common_name] = None
                        isr_cname_xlist.append(common_name)
                        for periph3 in device.peripherals:
                            if periph3.interrupts:
                                for isr3 in periph3.interrupts:
                                    if isr_dim_name.get(isr3.value) == common_name:
                                        isr_dim_name[isr3.value] = None
                                        isr_dim_index[isr3.value] = None
                cur_common_name: str = None
                isr_num_list: list[int] = []
                for periph2 in device.peripherals:
                    if periph2.interrupts:
                        for isr2 in periph2.interrupts:
                            if isr1.value != isr2.value and isr_dim_name.get(isr2.value) is None:
                                for c1, c2, i in zip(isr1.name, isr2.name, range(min(len(isr1.name), len(isr2.name)))):
                                    if (ISR_DIGIT_ENUM != (isr1.name in ISR_DIGIT_ENUM_EXC_LIST) and 
                                        diff_start_digit(isr1.name[i:], isr2.name[i:])):
                                        isr1_cname = isr1.name[:i] + isr1.name[i:].lstrip('0123456789')
                                        isr2_cname = isr2.name[:i] + isr2.name[i:].lstrip('0123456789')
                                        common_name = isr1.name[:i] + "x" + isr1.name[i:].lstrip('0123456789')
                                        isr1_num = int(re.search('[0-9]+', isr1.name[i:]).group())
                                        isr2_num = int(re.search('[0-9]+', isr2.name[i:]).group())
                                        if isr1_cname == isr2_cname and common_name not in isr_cname_xlist:
                                            if max(isr1_num, isr2_num) < MAX_ISR_ENUM_LEN:
                                                cur_common_name = common_name
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
                                                abort(common_name)
                                if isr_dim_name.get(isr2.value) is None:
                                    for c1, c2, i in zip(isr1.name, isr2.name, range(min(len(isr1.name), len(isr2.name)))):
                                        if (ISR_ALPHA_ENUM != (isr1.name in ISR_ALPHA_ENUM_EXC_LIST) and 
                                            diff_start_alpha(isr1.name[i:], isr2.name[i:])):
                                            isr1_cname = isr1.name[:i] + isr1.name[(i + 1):]
                                            isr2_cname = isr2.name[:i] + isr2.name[(i + 1):]
                                            common_name = isr1.name[:i] + "x" + isr1.name[(i + 1):]
                                            isr1_num = ord(isr1.name[i].lower()) - ord('a')
                                            isr2_num = ord(isr2.name[i].lower()) - ord('a')
                                            if isr1_cname == isr2_cname and common_name not in isr_cname_xlist:
                                                if max(isr1_num, isr2_num) < MAX_ISR_ENUM_LEN:
                                                    cur_common_name = common_name
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
                                                    abort(common_name)
                if len(isr_num_list) > 0:
                    if len(isr_num_list) < MIN_ISR_ENUM_LEN:
                        abort(cur_common_name)

# Format peripherals
periph_dim: dict[str, int] = {} 
periph_cname_xlist: list[str] = []
for periph1 in device.peripherals:
    if periph1.dim_name is None:
        dim_valid: bool = True
        def abort(common_name):
            periph_dim[common_name] = None
            periph_cname_xlist.append(common_name)
            for periph3 in device.peripherals:
                if periph3.dim_name == common_name:
                    periph3.dim_name = None
                    periph3.dim_index = None
        cur_common_name: str = None
        periph_num_list: list[int] = []
        new_periph: svd.parser.SVDPeripheralArray = device.peripherals.copy()
        for periph2 in device.peripherals:
            if periph2.dim_name is None and periph1.name != periph2.name:
                for c1, c2, i in zip(periph1.name, periph2.name, range(min(len(periph1.name), len(periph2.name)))):
                    if (PERIPH_DIGIT_ENUM != (periph1.name in PERIPH_DIGIT_ENUM_EXC_LIST) and diff_start_digit(periph1.name[i:], periph2.name[i:])):
                        periph1_cname = periph1.name[:i] + periph1.name[i:].lstrip('0123456789')
                        periph2_cname = periph2.name[:i] + periph2.name[i:].lstrip('0123456789')
                        common_name = periph1.name[:i] + "x" + periph1.name[i:].lstrip('0123456789')
                        periph1_num = int(re.search('[0-9]+', periph1.name[i:]).group())
                        periph2_num = int(re.search('[0-9]+', periph2.name[i:]).group())
                        new_registers = cmp_registers_dig(periph1, periph2, periph1_num, periph2_num)
                        if periph1_cname == periph2_cname and common_name not in periph_cname_xlist:
                            if max(periph1_num, periph2_num) < MAX_PERIPH_ENUM_LEN and new_registers is not False:
                                    for np in new_periph:
                                        if np.name == periph1.name:
                                            np.registers = new_registers[0]
                                        if np.name == periph2.name:
                                            np.registers = new_registers[1]
                                    cur_common_name = common_name
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
                                dim_valid = False
                                abort(common_name)
                if periph2.dim_name is None:
                    for c1, c2, i in zip(periph1.name, periph2.name, range(min(len(periph1.name), len(periph2.name)))):
                        if (PERIPH_ALPHA_ENUM != (periph1.name in PERIPH_ALPHA_ENUM_EXC_LIST) and 
                            diff_start_alpha(periph1.name[i:], periph2.name[i:])):
                            periph1_cname = periph1.name[:i] + periph1.name[(i + 1):]
                            periph2_cname = periph2.name[:i] + periph2.name[(i + 1):]
                            common_name = periph1.name[:i] + "x" + periph1.name[(i + 1):]
                            periph1_num = ord(periph1.name[i].lower()) - ord('a')
                            periph2_num = ord(periph2.name[i].lower()) - ord('a')
                            new_registers = cmp_registers_alpha(periph1, periph2, periph1_num, periph2_num)
                            if periph1_cname == periph2_cname and common_name not in periph_cname_xlist:
                                if max(periph1_num, periph2_num) < MAX_PERIPH_ENUM_LEN and new_registers is not False:
                                    for np in new_periph:
                                        if np.name == periph1.name:
                                            np.registers = new_registers[0]
                                        if np.name == periph2.name:
                                            np.registers = new_registers[1]
                                    cur_common_name = common_name
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
                                    dim_valid = False
                                    abort(common_name)
        if len(periph_num_list) > 0:
            if len(periph_num_list) < MIN_PERIPH_ENUM_LEN:
                abort(cur_common_name)
        if dim_valid:
            for o_periph in device.peripherals:
                for n_periph in new_periph:
                    if o_periph.name == n_periph.name:
                        o_periph.registers = n_periph.registers
                        break
      
# Format registers
reg_dim: dict[str, int] = {}
for periph in device.peripherals:
    if periph.registers:
        reg_cname_xlist: list[str] = []
        for reg1 in periph.registers:
            if reg1.dim_name is None:
                def abort(common_name):
                    reg_dim[f'{periph.name}_{common_name}'] = None
                    reg_cname_xlist.append(common_name)
                    for reg3 in periph.registers:
                        if reg3.dim_name == common_name:
                            reg3.dim_name = None
                            reg3.dim_index = None
                cur_common_name: str = None
                dim_num_list: list[int] = []
                new_reg: svd.parser.SVDRegisterArray = periph.registers.copy()
                for reg2 in periph.registers:
                    if reg2.dim_name is None and reg1.name != reg2.name and ((reg1.fields == None) == (reg2.fields == None)):
                        for c1, c2, i in zip(reg1.name, reg2.name, range(min(len(reg1.name), len(reg2.name)))):
                            if (REG_DIGIT_ENUM != (reg1.name in REG_DIGIT_ENUM_EXC_LIST) and 
                                diff_start_digit(reg1.name[i:], reg2.name[i:])):
                                reg1_cname = reg1.name[:i] + reg1.name[i:].lstrip('0123456789')
                                reg2_cname = reg2.name[:i] + reg2.name[i:].lstrip('0123456789')
                                common_name = reg1.name[:i] + "x" + reg1.name[i:].lstrip('0123456789')
                                reg1_num = int(re.search('[0-9]+', reg1.name[i:]).group())
                                reg2_num = int(re.search('[0-9]+', reg2.name[i:]).group())
                                new_fields = cmp_fields_dig(reg1, reg2, reg1_num, reg2_num)
                                if reg1_cname == reg2_cname and common_name not in reg_cname_xlist:
                                    if max(reg1_num, reg2_num) < MAX_REG_ENUM_LEN and new_fields is not False:
                                        for nr in new_reg:
                                            if nr.name == reg1.name:
                                                nr.fields = new_fields[0]
                                            if nr.name == reg2.name:
                                                nr.fields = new_fields[1]
                                        cur_common_name = common_name
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
                                        abort(common_name)
                        if reg2.dim_name is None:
                            for c1, c2, i in zip(reg1.name, reg2.name, range(min(len(reg1.name), len(reg2.name)))):
                                if (REG_ALPHA_ENUM != (reg1.name in REG_ALPHA_ENUM_EXC_LIST) and 
                                    diff_start_alpha(reg1.name[i:], reg2.name[i:])):
                                    reg1_cname = reg1.name[:i] + reg1.name[(i + 1):]
                                    reg2_cname = reg2.name[:i] + reg2.name[(i + 1):]
                                    common_name = reg1.name[:i] + "x" + reg1.name[(i + 1):]
                                    reg1_num = ord(reg1.name[i].lower()) - ord('a')
                                    reg2_num = ord(reg2.name[i].lower()) - ord('a')
                                    new_fields = cmp_fields_alpha(reg1, reg2, reg1_num, reg2_num)
                                    if reg1_cname == reg2_cname and common_name not in reg_cname_xlist:
                                        if max(reg1_num, reg2_num) < MAX_REG_ENUM_LEN and new_fields is not False:
                                            for nr in new_reg:
                                                if nr.name == reg1.name:
                                                    nr.fields = new_fields[0]
                                                if nr.name == reg2.name:
                                                    nr.fields = new_fields[1]
                                            cur_common_name = common_name
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
                                            abort(common_name)
                if len(dim_num_list) > 0:
                    if len(dim_num_list) < MIN_REG_ENUM_LEN:
                        abort(cur_common_name)
                if reg1.dim_name:
                    for o_reg in periph.registers:
                        for n_reg in new_reg:
                            if o_reg.name == n_reg.name:
                                o_reg.fields = n_reg.fields

# Format fields
field_dim: dict[str, int] = {}
for periph in device.peripherals:
    if periph.registers:
        for reg in periph.registers:
            if reg.fields:
                field_cname_xlist: list[str] = []
                for field1 in reg.fields:
                    if field1.dim_name is None:
                        def abort(common_name):
                            field_dim[f'{periph.name}_{reg.name}_{common_name}'] = None
                            field_cname_xlist.append(common_name)
                            for field3 in reg.fields:
                                if field3.dim_name == common_name:
                                    field3.dim_name = None
                                    field3.dim_index = None
                        cur_common_name: str = None
                        field_num_list: list[int] = []
                        for field2 in reg.fields:
                            if field2.dim_name is None and field1.name != field2.name:
                                for c1, c2, i in zip(field1.name, field2.name, range(min(len(field1.name), len(field2.name)))):
                                    if (FIELD_DIGIT_ENUM != (field1.name in FIELD_DIGIT_ENUM_EXC_LIST) and 
                                        diff_start_digit(field1.name[i:], field2.name[i:])):
                                        field1_cname = field1.name[:i] + field1.name[i:].lstrip('0123456789')
                                        field2_cname = field2.name[:i] + field2.name[i:].lstrip('0123456789')
                                        common_name = field1.name[:i] + "x" + field1.name[i:].lstrip('0123456789')
                                        field1_num = int(re.search('[0-9]+', field1.name[i:]).group())
                                        field2_num = int(re.search('[0-9]+', field2.name[i:]).group())
                                        if field1_cname == field2_cname and common_name not in field_cname_xlist:
                                            if max(field1_num, field2_num) < MAX_FIELD_ENUM_LEN:
                                                cur_common_name = common_name
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
                                                abort(common_name)
                                if field2.dim_name is None:
                                    for c1, c2, i in zip(field1.name, field2.name, range(min(len(field1.name), len(field2.name)))):
                                        if (FIELD_ALPHA_ENUM != (field1.name in FIELD_ALPHA_ENUM_EXC_LIST) and 
                                            diff_start_alpha(field1.name[i:], field2.name[i:])):
                                            field1_cname = field1.name[:i] + field1.name[(i + 1):]
                                            field2_cname = field2.name[:i] + field2.name[(i + 1):]
                                            common_name = field1.name[:i] + "x" + field1.name[(i + 1):]
                                            field1_num = ord(field1.name[i].lower()) - ord('a')
                                            field2_num = ord(field2.name[i].lower()) - ord('a')
                                            if field1_cname == field2_cname and common_name not in field_cname_xlist:
                                                if max(field1_num, field2_num) < MAX_FIELD_ENUM_LEN:
                                                    cur_common_name = common_name
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
                                                    abort(common_name)
                        if len(field_num_list) > 0:
                            if len(field_num_list) < MIN_FIELD_ENUM_LEN:
                                abort(cur_common_name)

###################################################################################################
# OUTPUT GENERATION
###################################################################################################

# Qualifiers associated with different register access types
REG_QUAL: dict[svd.parser.SVDAccessType, str] = {
    svd.parser.SVDAccessType.READ_ONLY: "RO_",
    svd.parser.SVDAccessType.WRITE_ONLY: "RW_",
    svd.parser.SVDAccessType.READ_WRITE: "RW_",
    svd.parser.SVDAccessType.WRITE_ONCE: "RW_",
    svd.parser.SVDAccessType.READ_WRITE_ONCE: "RW_"
}

if os.path.exists(OUTPUT_PATH): 
    os.remove(OUTPUT_PATH)
with open(OUTPUT_PATH, 'w') as file:   

    def write_header(txt):
        file.write(f'{INDENT}/**********************************************************************************************\n')
        file.write(f'{INDENT} * @section {txt}\n')
        file.write(f'{INDENT} **********************************************************************************************/\n')
        file.write("\n")     

    # Write includes
    file.write(f"{INDENT}#include <stdint.h>\n")
    file.write(f'{INDENT}#include <stddef.h>\n')
    file.write("\n")

    write_header("Implementation Resources")
    file.write(f'{INDENT}#define RO_ const volatile\n')
    file.write(f'{INDENT}#define RW_ volatile\n')
    file.write("\n")

    # # Write interrupt definitions
    # isr_xlist: list[str] = []
    # isr_comment_list: list[str] = []
    # isr_array_list: list[bool] = []
    # irq_decl_list: list[str] = []
    # irq_def_list: list[str] = []
    # isr_value_list: list[int] = []
    # for periph1 in device.peripherals:
    #     if periph1.interrupts:
    #         for isr in periph1.interrupts:
    #             if isr_dim_name.get(isr.value) is not None:
    #                 if isr_dim_name[isr.value] in isr_xlist: continue
    #                 isr_xlist.append(isr_dim_name[isr.value])
    #                 dim_value_list: list[str] = []
    #                 dim_comment_list: list[str] = []
    #                 for i in range(isr_dim[isr_dim_name[isr.value]]):
    #                     for periph2 in device.peripherals:
    #                         if periph2.interrupts:
    #                             for isr2 in periph2.interrupts:
    #                                 if (isr_dim_name.get(isr2.value) == isr_dim_name[isr.value] and 
    #                                     isr_dim_index[isr2.value] == i and isr2.value not in isr_value_list):
    #                                     max_dim_idx_len: int = len(str(isr_dim[isr_dim_name[isr.value]])) + 1
    #                                     dim_value_list.append(f'[{i}]{" "*(max_dim_idx_len - len(str(i)))}= {isr2.value}')
    #                                     dim_comment_list.append(f'/** @brief {isr2.description} */')
    #                                     isr_value_list.append(isr2.value)
    #                 max_index_len = max([len(x) for x in dim_value_list], default = 1) + 3
    #                 irq_decl_list.append(f'{isr_dim_name[isr.value]}_IRQ'
    #                     f'[{isr_dim[isr_dim_name[isr.value]]}]')
    #                 irq_def_list.append(f'{{\n{("".join(f'{INDENT}  {x}, {" "*(max_index_len - len(x))}{cmt}\n' 
    #                     for x, cmt in zip(dim_value_list, dim_comment_list)))}{INDENT}}}')
    #                 isr_comment_list.append("")
    #                 isr_array_list.append(True)
    #             else:
    #                 if isr.value not in isr_value_list:
    #                     isr_value_list.append(isr.value)
    #                     irq_decl_list.append(f'{isr.name}_IRQ')
    #                     irq_def_list.append(str(isr.value))
    #                     isr_array_list.append(False)
    #                     isr_comment_list.append(f'/** @brief {isr.description} */')
    # if len(isr_array_list) > 0:
    #     write_header("Interrupt Definitions")
    #     if any(not x for x in isr_array_list):
    #         file.write(f'{INDENT}/**** @subsection IRQ Interrupt Value Definitions ****/\n')
    #         file.write("\n")
    #         max_isr_decl_len = max([len(x) for x in irq_decl_list if not isr_array_list[irq_decl_list.index(x)]], default = 1)
    #         max_isr_def_len = max([len(x) for x in irq_def_list if not isr_array_list[irq_def_list.index(x)]], default = 1)
    #         for isr_decl, isr_def, isr_comment, isr_array in zip(irq_decl_list, irq_def_list, isr_comment_list, isr_array_list):
    #             if not isr_array:
    #                 isr_def_gap = (max_isr_decl_len - len(isr_decl)) + 3
    #                 isr_cmt_gap = (max_isr_def_len - len(isr_def)) + 3
    #                 file.write(f'{INDENT}static const int32_t {isr_decl}{" "*isr_def_gap}= {isr_def};{" "*isr_cmt_gap}{isr_comment}\n')
    #         file.write("\n")
    #     if any(x for x in isr_array_list):
    #         file.write(f'{INDENT}/**** @subsection IRQ Interrupt Array Definitions ****/\n')
    #         file.write("\n")
    #         for isr_decl, isr_def, isr_array in zip(irq_decl_list, irq_def_list, isr_array_list):
    #             if isr_array:
    #                 file.write(f'{INDENT}static const int32_t {isr_decl} = {isr_def};\n')
    #                 file.write("\n")

    periph_xlist: list[str] = []
    for periph1 in device.peripherals:
        if periph1.dim_name:
            if periph1.dim_name in periph_xlist: continue
            periph_xlist.append(periph1.dim_name)

        # Misc variables
        periph_name: str = periph1.dim_name if periph1.dim_name else periph1.name
        header_written: bool = False

        # Write section header
        if periph1.registers:
            write_header(f'{periph_name} Register Information')

        # # General peripheral information              
        # file.write(f'{INDENT}/**** @subsection {periph_name} General Peripheral Information ****/\n')
        # file.write("\n")
        # if periph1.dim_name:
        #     base_def_list: list[str] = []
        #     size_def_list: list[str] = []
        #     size_cmt_list: list[str] = []
        #     base_cmt_list: list[str] = []
        #     for i in range(periph_dim[periph1.dim_name]):
        #         for periph2 in device.peripherals:
        #             if periph2.dim_name == periph1.dim_name and periph2.dim_index == i:
        #                 dim_idx_gap = (len(str(periph_dim[periph1.dim_name])) - len(str(i))) + 1
        #                 base_def_list.append(f'{INDENT}  [{i}]{dim_idx_gap}= 0x{periph2.base_address:08X}U,\n')
        #                 size_def_list.append(f'{INDENT}  [{i}]{dim_idx_gap}= {periph2.size},\n')
        #                 base_cmt_list.append(f'/** @brief {periph2.name} register block base address. */')
        #                 size_cmt_list.append(f'/** @brief {periph2.name} register block base address. */')
        #     file.write(f'{INDENT}static const uint32_t {periph_name}_BASE[{periph_dim[periph1.dim_name]}] = {{\n')
        #     for x in base_def_list:
        #         file.write(x)
        #     file.write(f'{INDENT}}};\n')
        #     file.write("\n")
        #     file.write(f'{INDENT}static const int32_t {periph_name}_SIZE[{periph_dim[periph1.dim_name]}] = {{\n')
        #     for x in size_def_list:
        #         file.write(x)
        #     file.write(f'{INDENT}}};\n')
        #     file.write("\n")
        # else:
        #     file.write(f'{INDENT}static const uint32_t {periph_name}_BASE = 0x{periph1.base_address:08X}U;\n')
        #     file.write(f'{INDENT}static const int32_t {periph_name}_SIZE  = {periph1.size};\n')
        #     file.write("\n")
            
        # Write register definitions
        if periph1.registers:
            first_reg: bool = True
            reg_pre_list: list[str] = []
            reg_decl_list: list[str] = []
            reg_def_list: list[str] = []
            reg_array_list: list[bool] = []
            reg_cmt_list: list[str] = []
            reg_xlist: list[str] = []
            for reg1 in periph1.registers:
                reg_cast: str = f'({REG_QUAL[reg1.access]} uint{reg1.size}_t* const)'
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
                                                max_dim2_idx_len: int = len(str(reg_dim[f'{periph1.name}_{reg1.dim_name}'])) + 1
                                                reg_addr: int = periph2.base_address + reg2.address_offset
                                                dim2_def_list.append(f'[{j}]{" "*(max_dim2_idx_len - len(str(j)))}= {reg_cast}0x{reg_addr:08X}U')
                                                dim2_cmt_list.append(f'/** @brief {reg2.description} */')
                            if len(dim2_def_list) > 1:
                                max_dim_def_len = max([len(x) for x in dim2_def_list], default = 1) + 3
                                dim1_def_list.append(f'{{\n{("".join(f'{INDENT}    {x},{" "*(max_dim_def_len - len(x))}{cmt}\n' 
                                    for x, cmt in zip(dim2_def_list, dim2_cmt_list)))}{INDENT}  }}')
                        if len(dim1_def_list) > 1:
                            reg_decl_list.append(f'{periph_name}_{reg1.dim_name}_PTR'
                                f'[{periph_dim[periph1.dim_name]}][{reg_dim[f'{periph1.name}_{reg1.dim_name}']}]')
                            max_dim_idx_len: int = len(str(periph_dim[periph1.dim_name])) + 1
                            reg_def_list.append(f'{{\n{("".join(f'{INDENT}  [{i}]{" "*(max_dim_idx_len - len(str(i)))}= {x},\n' 
                                for x, i in zip(dim1_def_list, range(len(dim1_def_list)))))}{INDENT}}}')
                            reg_array_list.append(True)
                            reg_cmt_list.append("")
                    else:
                        dim_def_list: list[str] = []
                        dim_cmt_list: list[str] = []
                        for i in range(reg_dim[f'{periph1.name}_{reg1.dim_name}']):
                            for reg2 in periph1.registers:
                                if reg2.dim_name == reg1.dim_name and reg2.dim_index == i:
                                    reg_addr: int = periph1.base_address + reg2.address_offset
                                    max_dim_idx_len: int = len(str(reg_dim[f'{periph1.name}_{reg1.dim_name}'])) + 1
                                    dim_def_list.append(f'[{i}]{" "*(max_dim_idx_len - len(str(i)))}= {reg_cast}0x{reg_addr:08X}U')
                                    dim_cmt_list.append(f'/** @brief {reg2.description} */')
                        reg_decl_list.append(f'{periph_name}_{reg1.dim_name}_PTR'
                            f'[{reg_dim[f'{periph1.name}_{reg1.dim_name}']}]')
                        max_dim_def_len = max([len(x) for x in dim_def_list], default = 1) + 3
                        reg_def_list.append(f'{{\n{("".join(f'{INDENT}  {x},{" "*(max_dim_def_len - len(x))}{cmt}\n' 
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
                                            max_dim_idx_len: int = len(str(periph_dim[periph1.dim_name])) + 1
                                            dim_def_list.append(f'[{i}]{" "*(max_dim_idx_len - len(str(i)))}= {reg_cast}0x{reg_addr:08X}U')
                                            dim_cmt_list.append(f'/** @brief {reg2.description} */')
                                            break
                        reg_decl_list.append(f'{periph_name}_{reg1.name}_PTR'
                            f'[{periph_dim[periph1.dim_name]}]')
                        max_dim_def_len = max([len(x) for x in dim_def_list], default = 1) + 3
                        reg_def_list.append(f'{{\n{("".join(f'{INDENT}  {x},{" "*(max_dim_def_len - len(x))}{cmt}\n' 
                            for x, cmt in zip(dim_def_list, dim_cmt_list)))}{INDENT}}}')
                        reg_array_list.append(True)
                        reg_cmt_list.append("")
                    else:
                        reg_decl_list.append(f'{periph_name}_{reg1.name}_PTR')
                        reg_addr: int = periph1.base_address + reg1.address_offset
                        reg_def_list.append(f'{reg_cast}0x{reg_addr:08X}U')
                        reg_array_list.append(False)
                        reg_cmt_list.append(f'/** @brief {reg1.description} */')
                reg_pre_list.append(f'static {REG_QUAL[reg1.access]} uint{reg1.size}_t* const')
            if len(reg_decl_list) > 0:
                if any(not x for x in reg_array_list):
                    file.write(f'{INDENT}/**** @subsection {periph_name} Register Pointers ****/\n')
                    file.write("\n")
                    max_reg_pre_len = max([len(x) for x in reg_pre_list if not reg_array_list[reg_pre_list.index(x)]], default = 1)
                    max_reg_decl_len = max([len(x) for x in reg_decl_list if not reg_array_list[reg_decl_list.index(x)]], default = 1)
                    max_reg_def_len = max([len(x) for x in reg_def_list if not reg_array_list[reg_def_list.index(x)]], default = 1)
                    for reg_pre, reg_decl, reg_def, reg_cmt, reg_array in zip(reg_pre_list, reg_decl_list, reg_def_list, reg_cmt_list, reg_array_list):
                        if not reg_array:
                            reg_def_gap = ((max_reg_decl_len + max_reg_pre_len) - (len(reg_pre) + len(reg_decl))) + 3
                            reg_cmt_gap = (max_reg_def_len - len(reg_def)) + 3
                            file.write(f'{INDENT}{reg_pre} {reg_decl}{" "*reg_def_gap}= {reg_def};{" "*reg_cmt_gap}{reg_cmt}\n')
                    file.write("\n")
                if any(x for x in reg_array_list):
                    file.write(f'{INDENT}/**** @subsection Enumerated {periph_name} Register Pointers ****/\n')
                    file.write("\n")
                    for reg_pre, reg_decl, reg_def, reg_array in zip(reg_pre_list, reg_decl_list, reg_def_list, reg_array_list):
                        if reg_array:
                            file.write(f'{INDENT}{reg_pre} {reg_decl} = {reg_def};\n')
                            file.write("\n")

        # Write register reset values
        if periph1.registers:
            first_reg: bool = True
            reg_pre_list: list[str] = []
            reg_decl_list: list[str] = []
            reg_def_list: list[str] = []
            reg_array_list: list[bool] = []
            reg_cmt_list: list[str] = []
            reg_xlist: list[str] = []
            for reg1 in periph1.registers:
                reg_cast: str = f''
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
                                                max_dim2_idx_len: int = len(str(reg_dim[f'{periph1.name}_{reg1.dim_name}'])) + 1
                                                dim2_def_list.append(f'[{j}]{" "*(max_dim2_idx_len - len(str(j)))}= {reg_cast}0x{reg2.reset_value:08X}U')
                                                dim2_cmt_list.append(f'/** @brief {reg2.name} register reset value. */')
                            if len(dim2_def_list) > 1:
                                max_dim_def_len = max([len(x) for x in dim2_def_list], default = 1) + 3
                                dim1_def_list.append(f'{{\n{("".join(f'{INDENT}    {x},{" "*(max_dim_def_len - len(x))}{cmt}\n' 
                                    for x, cmt in zip(dim2_def_list, dim2_cmt_list)))}{INDENT}  }}')
                        if len(dim1_def_list) > 1:
                            reg_decl_list.append(f'{periph_name}_{reg1.dim_name}_RST'
                                f'[{periph_dim[periph1.dim_name]}][{reg_dim[f"{periph1.name}_{reg1.dim_name}"]}]')
                            max_dim_idx_len: int = len(str(periph_dim[periph1.dim_name])) + 1
                            reg_def_list.append(f'{{\n{("".join(f'{INDENT}  [{i}]{" "*(max_dim_idx_len - len(str(i)))}= {x},\n' 
                                for x, i in zip(dim1_def_list, range(len(dim1_def_list)))))}{INDENT}}}')
                            reg_array_list.append(True)
                            reg_cmt_list.append("")
                    else:
                        dim_def_list: list[str] = []
                        dim_cmt_list: list[str] = []
                        for i in range(reg_dim[f'{periph1.name}_{reg1.dim_name}']):
                            for reg2 in periph1.registers:
                                if reg2.dim_name == reg1.dim_name and reg2.dim_index == i:
                                    max_dim_idx_len: int = len(str(reg_dim[f'{periph1.name}_{reg1.dim_name}'])) + 1
                                    dim_def_list.append(f'[{i}]{" "*(max_dim_idx_len - len(str(i)))}= {reg_cast}0x{reg2.reset_value:08X}U')
                                    dim_cmt_list.append(f'/** @brief {reg2.name} register reset value. */')
                        reg_decl_list.append(f'{periph_name}_{reg1.dim_name}_RST'
                            f'[{reg_dim[f"{periph1.name}_{reg1.dim_name}"]}]')
                        max_dim_def_len = max([len(x) for x in dim_def_list], default = 1) + 3
                        reg_def_list.append(f'{{\n{("".join(f'{INDENT}  {x},{" "*(max_dim_def_len - len(x))}{cmt}\n' 
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
                                            max_dim_idx_len: int = len(str(periph_dim[periph1.dim_name])) + 1
                                            dim_def_list.append(f'[{i}]{" "*(max_dim_idx_len - len(str(i)))}= {reg_cast}0x{reg2.reset_value:08X}U')
                                            dim_cmt_list.append(f'/** @brief {reg2.name} register reset value */')
                                            break
                        reg_decl_list.append(f'{periph_name}_{reg1.name}_RST'
                            f'[{periph_dim[periph1.dim_name]}]')
                        max_dim_def_len = max([len(x) for x in dim_def_list], default = 1) + 3
                        reg_def_list.append(f'{{\n{("".join(f'{INDENT}  {x},{" "*(max_dim_def_len - len(x))}{cmt}\n' 
                            for x, cmt in zip(dim_def_list, dim_cmt_list)))}{INDENT}}}')
                        reg_array_list.append(True)
                        reg_cmt_list.append("")
                    else:
                        reg_decl_list.append(f'{periph_name}_{reg1.name}_RST')
                        reg_def_list.append(f'{reg_cast}0x{reg1.reset_value:08X}U')
                        reg_array_list.append(False)
                        reg_cmt_list.append(f'/** @brief {reg1.name} register reset value. */')
                reg_pre_list.append(f'static const uint{reg1.size}_t')
            if len(reg_decl_list) > 0:
                if any(not x for x in reg_array_list):
                    file.write(f'{INDENT}/**** @subsection {periph_name} Register Reset Values ****/\n')
                    file.write("\n")
                    max_reg_pre_len = max([len(x) for x in reg_pre_list if not reg_array_list[reg_pre_list.index(x)]], default = 1)
                    max_reg_decl_len = max([len(x) for x in reg_decl_list if not reg_array_list[reg_decl_list.index(x)]], default = 1)
                    max_reg_def_len = max([len(x) for x in reg_def_list if not reg_array_list[reg_def_list.index(x)]], default = 1)
                    for reg_pre, reg_decl, reg_def, reg_cmt, reg_array in zip(reg_pre_list, reg_decl_list, reg_def_list, reg_cmt_list, reg_array_list):
                        if not reg_array:
                            reg_def_gap = ((max_reg_decl_len + max_reg_pre_len) - (len(reg_pre) + len(reg_decl))) + 3
                            reg_cmt_gap = (max_reg_def_len - len(reg_def)) + 3
                            file.write(f'{INDENT}{reg_pre} {reg_decl}{" "*reg_def_gap}= {reg_def};{" "*reg_cmt_gap}{reg_cmt}\n')
                    file.write("\n")
                if any(x for x in reg_array_list):
                    file.write(f'{INDENT}/**** @subsection Enumerated {periph_name} Register Reset Values ****/\n')
                    file.write("\n")
                    for reg_pre, reg_decl, reg_def, reg_array in zip(reg_pre_list, reg_decl_list, reg_def_list, reg_array_list):
                        if reg_array:
                            file.write(f'{INDENT}{reg_pre} {reg_decl} = {reg_def};\n')
                            file.write("\n")

        # Write register type definitions
        reg_xlist: list[str] = []
        reg_vt_def_list: list[str] = []
        reg_pt_def_list: list[str] = []
        reg_vt_cmt_list: list[str] = []
        reg_pt_cmt_list: list[str] = []
        for reg in periph1.registers:
            if reg.dim_name:
                if reg.dim_name in reg_xlist: continue
                reg_xlist.append(reg.dim_name)
                treg_name = reg.dim_name
            else:
                treg_name = reg.name
            reg_vt_def_list.append(f'typedef uint{reg.size}_t {periph_name}_{treg_name}_t;')
            reg_pt_def_list.append(f'typedef uint{reg.size}_t* const {periph_name}_{treg_name}_PTR_t;')
            reg_vt_cmt_list.append(f'/** @brief {treg_name} register value type. */')
            reg_pt_cmt_list.append(f'/** @brief {treg_name} register pointer type. */')
        if len(reg_vt_def_list) > 0:
            file.write(f'{INDENT}/**** @subsection Enumerated {periph_name} Register Value Types ****/\n')
            file.write("\n")
            max_vt_def_len = max([len(x) for x in reg_vt_def_list], default = 1)
            for reg_vt_def, reg_vt_cmt in zip(reg_vt_def_list, reg_vt_cmt_list):
                cmt_gap: int = (max_vt_def_len - len(reg_vt_def)) + 3
                file.write(f'{INDENT}{reg_vt_def}{" "*cmt_gap}{reg_vt_cmt}\n')
            file.write("\n")
            file.write(f'{INDENT}/**** @subsection Enumerated {periph_name} Register Pointer Types ****/\n')
            file.write("\n")
            max_pt_def_len = max([len(x) for x in reg_pt_def_list], default = 1)
            for reg_pt_def, reg_pt_cmt in zip(reg_pt_def_list, reg_pt_cmt_list):
                cmt_gap: int = (max_pt_def_len - len(reg_pt_def)) + 3
                file.write(f'{INDENT}{reg_pt_def}{" "*cmt_gap}{reg_pt_cmt}\n')
            file.write("\n")
                

        # Write field mask definitions
        reg_xlist: list[str] = []
        field_xlist: list[str] = []
        field_decl_list: list[str] = []
        field_def_list: list[str] = []
        field_array_list: list[bool] = []
        field_cmt_list: list[str] = []
        for reg in periph1.registers:
            if reg.fields:
                if reg.dim_name:
                    if reg.dim_name in reg_xlist: continue
                    reg_xlist.append(reg.dim_name)
                    reg_name = reg.dim_name
                else:
                    reg_name = reg.name
                for field1 in reg.fields:
                    if field1.bit_width != reg.size:
                        if field1.dim_name:
                            if field1.dim_name in field_xlist: continue
                            field_xlist.append(field1.dim_name)
                            dim_mask_list: list[str] = []
                            dim_cmt_list: list[str] = []
                            for i in range(field_dim[f'{periph1.name}_{reg.name}_{field1.dim_name}']):
                                for field2 in reg.fields:
                                    if field2.dim_name == field1.dim_name and field2.dim_index == i:
                                        mask_value: int = ((1 << field2.bit_width) - 1) << field2.bit_offset
                                        max_dim_idx_len: int = len(str(field_dim[f'{periph1.name}_{reg.name}_{field1.dim_name}'])) + 1
                                        dim_mask_list.append(f'[{i}]{" "*(max_dim_idx_len - len(str(i)))}= 0x{mask_value:08X}U')
                                        dim_cmt_list.append(f'/** @brief {field2.description} */')
                            max_def_len: int = max([len(x) for x in dim_mask_list], default = 1) + 3
                            field_decl_list.append(f'{periph_name}_{reg_name}_{field1.dim_name}_MASK'
                                f'[{field_dim[f"{periph1.name}_{reg.name}_{field1.dim_name}"]}]')
                            field_def_list.append(f'{{\n{("".join(f'{INDENT}  {x},{" "*(max_def_len - len(x))}{cmt}\n' 
                                for x, cmt in zip(dim_mask_list, dim_cmt_list)))}{INDENT}}}')
                            field_array_list.append(True)
                            field_cmt_list.append("")
                        else:
                            mask_value: int = ((1 << field1.bit_width) - 1) << field1.bit_offset
                            field_decl_list.append(f'{periph_name}_{reg_name}_{field1.name}_MASK')
                            field_def_list.append(f'0x{mask_value:08X}U')
                            field_array_list.append(False)
                            field_cmt_list.append(f'/** @brief {field1.description} */')
        if len(field_decl_list) > 0:
            if any(not x for x in field_array_list):
                file.write(f'{INDENT}/**** @subsection {periph_name} Register Field Masks ****/\n')
                file.write("\n")
                max_field_decl_len = max([len(x) for x in field_decl_list if not field_array_list[field_decl_list.index(x)]], default = 1)
                max_field_def_len = max([len(x) for x in field_def_list if not field_array_list[field_def_list.index(x)]], default = 1)
                for field_decl, field_def, field_cmt, field_array in zip(field_decl_list, field_def_list, field_cmt_list, field_array_list):
                    if not field_array:
                        field_def_gap = (max_field_decl_len - len(field_decl)) + 3
                        field_cmt_gap = ((max_field_def_len) - len(field_def)) + 3
                        file.write(f'{INDENT}static const uint32_t {field_decl}{" "*field_def_gap}= {field_def};{" "*field_cmt_gap}{field_cmt}\n')
                file.write("\n")
            if any(x for x in field_array_list):
                file.write(f'{INDENT}/**** @subsection Enumerated {periph_name} Register Field Masks ****/\n')
                file.write("\n")
                for field_decl, field_def, field_array in zip(field_decl_list, field_def_list, field_array_list):
                    if field_array:
                        file.write(f'{INDENT}static const uint{reg.size}_t {field_decl} = {field_def};\n')
                        file.write("\n")

        # Write field position definitions
        reg_xlist: list[str] = []
        field_xlist: list[str] = []
        field_decl_list: list[str] = []
        field_array_list: list[bool] = []
        field_def_list: list[str] = []
        field_cmt_list: list[str] = []
        for reg in periph1.registers:
            if reg.fields:
                if reg.dim_name:
                    if reg.dim_name in reg_xlist: continue
                    reg_xlist.append(reg.dim_name)
                    reg_name = reg.dim_name
                else:
                    reg_name = reg.name
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
                                        max_dim_idx_len: int = len(str(field_dim[f'{periph1.name}_{reg.name}_{field1.dim_name}'])) + 1
                                        dim_pos_list.append(f'[{i}]{" "*(max_dim_idx_len - len(str(i)))}= {field2.bit_offset}')
                                        dim_cmt_list.append(f'/** @brief {field2.description} */')
                            max_field_def_len = max([len(str(x)) for x in dim_pos_list], default = 1) + 3
                            field_decl_list.append(f'{periph_name}_{reg_name}_{field1.dim_name}_POS'
                                f'[{field_dim[f"{periph1.name}_{reg.name}_{field1.dim_name}"]}]')
                            field_def_list.append(f'{{\n{("".join(f'{INDENT}  {x},{" "*(max_field_def_len - len(str(x)))}{cmt}\n' 
                                for x, cmt in zip(dim_pos_list, dim_cmt_list)))}{INDENT}}}')
                            field_array_list.append(True)
                            field_cmt_list.append("")
                        else:
                            field_decl_list.append(f'{periph_name}_{reg_name}_{field1.name}_POS')
                            field_def_list.append(str(field1.bit_offset))
                            field_array_list.append(False)
                            field_cmt_list.append(f'/** @brief {field1.description} */')
        if len(field_decl_list) > 0:
            if any(not x for x in field_array_list):
                file.write(f'{INDENT}/**** @subsection {periph_name} Register Field Positions ****/\n')
                file.write("\n")
                max_field_def_len = max([len(x) for x in field_def_list if not field_array_list[field_def_list.index(x)]], default = 1)
                max_field_decl_len = max([len(x) for x in field_decl_list if not field_array_list[field_decl_list.index(x)]], default = 1)
                for field_decl, field_def, field_cmt, field_array in zip(field_decl_list, field_def_list, field_cmt_list, field_array_list):
                    if not field_array:
                        field_def_gap = (max_field_decl_len - len(field_decl)) + 3
                        field_cmt_gap = ((max_field_def_len - len(field_def))) + 3
                        file.write(f'{INDENT}static const int32_t {field_decl}{" "*field_def_gap}= {field_def};{" "*field_cmt_gap}{field_cmt}\n')
                file.write("\n")
            if any(x for x in field_array_list):
                file.write(f'{INDENT}/**** @subsection Enumerated {periph_name} Register Field Positions ****/\n')
                file.write("\n")
                for field_decl, field_def, field_array in zip(field_decl_list, field_def_list, field_array_list):
                    if field_array:
                        file.write(f'{INDENT}static const int32_t {field_decl} = {field_def};\n')
                        file.write("\n")
