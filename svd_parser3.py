###################################################################################################
# IMPORTS
###################################################################################################

# Requires "cmsis_svd" library -> pip install -U cmsis-svd
import cmsis_svd as svd

# Standard libraries
from dataclasses import dataclass
import typing as tp
import re
import os

###################################################################################################
# CONFIGURATION
###################################################################################################

# Output file path
OUTPUT_PATH: str = "D:\\main\\projects\\sarp\\svd_parser\\output2.h"

# Path to SVD data directory -> git clone --depth=1 -b main https://github.com/cmsis-svd/cmsis-svd-data.git
SVD_PKG_PATH: str = "D:\\main\\projects\\sarp\\svd_parser\\cmsis-svd-data\\data"

# Target device vendor name
VENDOR_NAME: str = "STMicro"

# Core 1 SVD file name
SVD_NAME: str = "STM32H7x5_CM7.svd"

###################################################################################################
# IMPLEMENTATION RESOURCES
###################################################################################################

@dataclass
class field_t:
    offset: int
    width: int
    size: int
    desc: str

@dataclass
class register_t:
    address: int
    access: svd.parser.SVDAccessType
    size: int
    desc: str
    reset: int

def get_digit_diff(obj1, obj2, delim):
    for i in range(min(len(obj1.name), len(obj2.name))):
        if obj1.name[i] != obj2.name[i]:
            if obj1.name[i].isdigit() and obj2.name[i].isdigit():
                for j in range(max(len(obj1.name[i:]), len(obj2.name[i:]))):
                    if (((j + i) < len(obj1.name) and obj1.name[j + i].isdigit()) or 
                        ((j + i) < len(obj2.name) and obj2.name[j + i].isdigit())):
                        if ((j + i) >= len(obj1.name) or 
                            (j + i) >= len(obj2.name) or 
                            obj1.name[j + i] != obj2.name[j + i]):
                            cname_1 = obj1.name[:i] + obj1.name[i:].lstrip('0123456789')
                            cname_2 = obj2.name[:i] + obj2.name[i:].lstrip('0123456789')
                            if cname_1 == cname_2:
                                common_name = obj1.name[:i] + delim + obj1.name[i:].lstrip('0123456789')
                                field1_num = int(re.search('[0-9]+', obj1.name[i:]).group())
                                field2_num = int(re.search('[0-9]+', obj2.name[i:]).group())
                                return (common_name, field1_num, field2_num)
                    else:
                        return None
            else:
                return None
    return None

def get_alpha_diff(obj1, obj2, delim):
    for i, (c1, c2) in enumerate(zip(obj1.name, obj2.name)):
        if c1 != c2:
            if c1.isalpha() and c2.isalpha():
                cname_1 = obj1.name[:i] + obj1.name[(i + 1):]
                cname_2 = obj2.name[:i] + obj2.name[(i + 1):]
                if cname_1 == cname_2:
                    common_name = obj1.name[:i] + delim + obj1.name[(i + 1):]
                    return (common_name, c1, c2)
            else:
                return None
    return None

def get_l_d(obj):
    c_obj = obj
    while (type(c_obj) == dict):
        c_list = list(c_obj.values())
        if len(c_list) == 0:
            return None
        c_obj = c_list[0]
    return c_obj

def get_a_d(obj0):
    if type(obj0) != dict: return obj0
    if len(obj0) > 0:
        for obj1 in obj0.values():
            if type(obj1) != dict: return obj1
            if len(obj1) > 0:
                for obj2 in obj1.values():
                    if type(obj2) != dict: return obj2
                    if len(obj2) > 0:
                        for obj3 in obj2.values():
                            if type(obj3) != dict: return obj3
                            if len(obj3) > 0:
                                for obj4 in obj3.values():
                                    if type(obj4) != dict: return obj4
                                    raise(RecursionError, "Maximum depth exceeded")
    return None
    



def get_qual(access):
    if access == svd.parser.SVDAccessType.READ_ONLY: return "RO_"
    if access == svd.parser.SVDAccessType.WRITE_ONLY: return "RW_"
    if access == svd.parser.SVDAccessType.READ_WRITE: return "RW_"
    if access == svd.parser.SVDAccessType.WRITE_ONCE: return "RW_"
    if access == svd.parser.SVDAccessType.READ_WRITE_ONCE: return "RW_"
      
def write_header(file, text):
    file.write(f'{" "*4}/**********************************************************************************************\n')
    file.write(f'{" "*4} * @section {text}\n')
    file.write(f'{" "*4} **********************************************************************************************/\n')
    file.write("\n")

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

###################################################################################################
# IMPLEMENTATION
###################################################################################################

parser = svd.SVDParser.for_packaged_svd(package_root = SVD_PKG_PATH, vendor = VENDOR_NAME, filename = SVD_NAME)
device = parser.get_device(xml_validation = False)

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

if os.path.exists(OUTPUT_PATH):
    os.remove(OUTPUT_PATH)

with open(OUTPUT_PATH, "w") as f:

    f.write(f'{" "*4}#include <stdint.h>\n')
    f.write("\n")
    f.write(f"{" "*4}#define RO_ const volatile\n")
    f.write(f"{" "*4}#define RW_ volatile\n")
    f.write("\n")

    if device.peripherals:
        p_xlist: list[str] = []
        for p1 in device.peripherals:
            if p1.name not in p_xlist:
                periph_name: str = p1.name
                for p2 in device.peripherals:
                    digit_diff = get_digit_diff(p1, p2, "")
                    if digit_diff is not None:
                        periph_name = digit_diff[0]
                        p_xlist.append(p2.name)

                write_header(f, f'{periph_name} Register Definitions')

                if p1.registers:
                    r_xlist: list[str] = []
                    reg_list: list = []
                    name_list: list = []
                    for r1 in p1.registers:
                        if r1.name not in r_xlist:
                            for r2 in p1.registers:
                                if get_digit_diff(r1, r2, "") is not None:
                                    r_xlist.append(r2.name)

                            pp_name: str = p1.name
                            pr_name: str = r1.name

                            base_r1_num: int = 0
                            base_r1: tp.Any = None
                            new_r1: dict[int, tp.Any] = {}
                            if device.peripherals is not None:
                                for p2 in device.peripherals:
                                    p_diff = get_digit_diff(p1, p2, "x")
                                    if p1.name == p2.name or p_diff is not None:

                                        base_r2_num: int = 0
                                        base_r2: register_t = None
                                        new_r2: dict[int, tp.Any] = {}
                                        if p2.registers is not None:
                                            for r2 in p2.registers:
                                                r_diff = get_digit_diff(r1, r2, "x")
                                                if r_diff is not None:
                                                    pr_name = r_diff[0]
                                                    base_r2_num = r_diff[1]
                                                    new_r2[r_diff[2]] = register_t(
                                                        address = p2.base_address + r2.address_offset,
                                                        access = r2.access,
                                                        size = r2.size,
                                                        desc = r2.description,
                                                        reset = r2.reset_value)
                                                elif (r1.name == r2.name):
                                                    base_r2 = register_t(
                                                        address = p2.base_address + r2.address_offset,
                                                        access = r2.access,
                                                        size = r2.size, 
                                                        desc = r2.description,
                                                        reset = r2.reset_value)

                                        if base_r2 is not None:
                                            new_r2[base_r2_num] = base_r2
                                        if p1.name == p2.name:
                                            base_r1 = new_r2
                                        else:
                                            base_r1_num = p_diff[1]
                                            pp_name = p_diff[0]
                                            if len(new_r2) > 0:
                                                new_r1[p_diff[2]] = new_r2

                            if base_r1 is not None:
                                new_r1[base_r1_num] = base_r1

                            if len(new_r1) > 0:
                                reg_list.append(new_r1)
                                name_list.append(f'{pp_name}_{pr_name}')

                    if len(reg_list) > 0:

                        f.write(f'{" "*4}/**** @subsection {periph_name} Register Pointer Definitions ****/\n')
                        f.write('\n')

                        decl_list: list[str] = []
                        def_list: list[str] = []
                        cmt_list: list[str] = []
                        for r1, n in zip(reg_list, name_list):
                            if len(r1) == 1 and len(list(r1.values())[0]) == 1:
                                decl_list.append(f'static {get_qual(get_l_d(r1).access)} uint{get_l_d(r1).size}_t* const {n}_PTR')
                                def_list.append(f'({get_qual(get_l_d(r1).access)} uint{get_l_d(r1).size}_t*)0x{get_l_d(r1).address:08X}U')
                                cmt_list.append(f'/** @brief {get_l_d(r1).desc} */')
                        if len(decl_list) > 0:
                            max_decl_len: int = max([len(x) for x in decl_list])
                            max_def_len: int = max([len(x) for x in def_list])
                            for decl, _def, cmt in zip(decl_list, def_list, cmt_list):
                                def_gap: int = (max_decl_len - len(decl)) + 1
                                cmt_gap: int = (max_def_len - len(_def)) + 3
                                f.write(f'{" "*4}{decl}{" "*def_gap}= {_def};{" "*cmt_gap}{cmt}\n')
                            f.write('\n')

                        for r1, n in zip(reg_list, name_list):
                            max_idx: int = 0
                            size: int = get_a_d(r1).size
                            qual: str = get_qual(get_a_d(r1).access)
                            r1_decl_list: list[str] = []
                            r1_def_list: list[str] = []
                            r1_cmt_list: list[str] = []
                            if len(r1) > 1:
                                for i, r2 in r1.items():
                                    if len(r2) == 1:
                                        max_idx = max(max_idx, i)
                                        r1_decl_list.append(f'[{i}]')
                                        r1_def_list.append(f'({qual} uint{size}_t*)0x{get_l_d(r2).address:08X}U')
                                        r1_cmt_list.append(f'/** @brief {get_l_d(r2).desc} */') 
                            elif len(list(r1.values())[0]) > 1:
                                for i, r2 in list(r1.values())[0].items():
                                    max_idx = max(max_idx, i)
                                    r1_decl_list.append(f'[{i}]')
                                    r1_def_list.append(f'({qual} uint{size}_t*)0x{r2.address:08X}U')
                                    r1_cmt_list.append(f'/** @brief {r2.desc} */')
                            if len(r1_decl_list) > 0:
                                f.write(f'{" "*4}static {qual} uint{size}_t* const {n}_PTR[{max_idx + 1}] = {{\n')
                                max_r1_decl_len: int = max([len(x) for x in r1_decl_list])
                                max_r1_def_len: int = max([len(x) for x in r1_def_list])
                                for i, (decl, _def, cmt) in enumerate(zip(r1_decl_list, r1_def_list, r1_cmt_list)):
                                    def_gap: int = (max_r1_decl_len - len(decl)) + 1
                                    cmt_gap: int = (max_r1_def_len - len(_def)) + 3
                                    comma_str: str = "," if i < len(r1_decl_list) - 1 else ""
                                    f.write(f'{" "*6}{decl}{" "*def_gap}= {_def}{comma_str}{" "*cmt_gap}{cmt}\n')
                                f.write(f"{" "*4}}};\n")
                                f.write('\n')
                        
                        for r1, n in zip(reg_list, name_list):
                            r1_str: str = ""
                            max_idx_d1: int = 0
                            max_idx_d2: int = 0
                            size: int = get_a_d(r1).size
                            qual: str = get_qual(get_a_d(r1).access)
                            if len(r1) > 1:
                                for i, r2 in r1.items():
                                    r2_decl_list: list[str] = []
                                    r2_def_list: list[str] = []
                                    r2_cmt_list: list[str] = []
                                    if len(r2) > 1:
                                        for j, r3 in r2.items():
                                            max_idx_d2 = max(max_idx_d2, j)
                                            r1_decl_list.append(f'[{j}]')
                                            r1_def_list.append(f'({qual} uint{size}_t*)0x{r3.address:08X}U')
                                            r1_cmt_list.append(f'/** @brief {r3.desc} */')
                                    dim_r1_str: str = ""
                                    if len(r2_decl_list) > 0:
                                        dim_r1_str += f'{" "*6}[{i}] = {{\n'
                                        max_decl_len: int = max([len(x) for x in r2_decl_list])
                                        max_def_len: int = max([len(x) for x in r2_def_list])
                                        for i, (decl, _def, cmt) in enumerate(zip(r2_decl_list, r2_def_list, r2_cmt_list)):
                                            def_gap: int = (max_r1_decl_len - len(decl)) + 1
                                            cmt_gap: int = (max_r1_def_len - len(_def)) + 3
                                            comma_str: str = "," if i < len(r2_decl_list) - 1 else ""
                                            dim_r1_str += f'{" "*8}{decl}{" "*def_gap}= {_def}{comma_str}{" "*cmt_gap}{cmt}\n'
                                        dim_r1_str += f'{" "*6}}},\n'
                                    r1_str += dim_r1_str
                                if len(r1_str) > 0:
                                    f.write(f'{" "*4}static {qual} uint{size}_t* const {n}_PTR[{max_idx_d1 + 1}][{max_idx_d2 + 1}] = {{\n')
                                    f.write(r1_str[:-2] + "\n")
                                    f.write(f"{" "*4}}};\n")
                                    f.write('\n')
                        
                        f.write(f'{" "*4}/**** @subsection {periph_name} Register Reset Value Definitions ****/\n')
                        f.write('\n')

                        decl_list: list[str] = []
                        def_list: list[str] = []
                        cmt_list: list[str] = []
                        for r1, n in zip(reg_list, name_list):
                            if len(r1) == 1 and len(list(r1.values())[0]) == 1:
                                decl_list.append(f'static const uint{get_l_d(r1).size}_t {n}_RST')
                                def_list.append(f'0x{get_l_d(r1).reset:08X}U')
                                cmt_list.append(f'/** @brief {get_l_d(r1).desc} */')
                        if len(decl_list) > 0:
                            max_decl_len: int = max([len(x) for x in decl_list])
                            max_def_len: int = max([len(x) for x in def_list])
                            for decl, _def, cmt in zip(decl_list, def_list, cmt_list):
                                def_gap: int = (max_decl_len - len(decl)) + 1
                                cmt_gap: int = (max_def_len - len(_def)) + 3
                                f.write(f'{" "*4}{decl}{" "*def_gap}= {_def};{" "*cmt_gap}{cmt}\n')
                            f.write('\n')

                        for r1, n in zip(reg_list, name_list):
                            max_idx: int = 0
                            size: int = get_a_d(r1).size
                            qual: str = get_a_d(get_l_d(r1).access)
                            r1_decl_list: list[str] = []
                            r1_def_list: list[str] = []
                            r1_cmt_list: list[str] = []
                            if len(r1) > 1:
                                for i, r2 in r1.items():
                                    if len(r2) == 1:
                                        max_idx = max(max_idx, i)
                                        r1_decl_list.append(f'[{i}]')
                                        r1_def_list.append(f'0x{get_l_d(r2).reset:08X}U')
                                        r1_cmt_list.append(f'/** @brief {get_l_d(r2).desc} */') 
                            elif len(list(r1.values())[0]) > 1:
                                for i, r2 in list(r1.values())[0].items():
                                    max_idx = max(max_idx, i)
                                    r1_decl_list.append(f'[{i}]')
                                    r1_def_list.append(f'0x{r2.reset:08X}U')
                                    r1_cmt_list.append(f'/** @brief {r2.desc} */')
                            if len(r1_decl_list) > 0:
                                f.write(f'{" "*4}static const uint{size}_t {n}_RST[{max_idx + 1}] = {{\n')
                                max_r1_decl_len: int = max([len(x) for x in r1_decl_list])
                                max_r1_def_len: int = max([len(x) for x in r1_def_list])
                                for i, (decl, _def, cmt) in enumerate(zip(r1_decl_list, r1_def_list, r1_cmt_list)):
                                    def_gap: int = (max_r1_decl_len - len(decl)) + 1
                                    cmt_gap: int = (max_r1_def_len - len(_def)) + 3
                                    comma_str: str = "," if i < len(r1_decl_list) - 1 else ""
                                    f.write(f'{" "*6}{decl}{" "*def_gap}= {_def}{comma_str}{" "*cmt_gap}{cmt}\n')
                                f.write(f"{" "*4}}};\n")
                                f.write('\n')
                        
                        for r1, n in zip(reg_list, name_list):
                            r1_str: str = ""
                            max_idx_d1: int = 0
                            max_idx_d2: int = 0
                            size: int = get_a_d(r1).size
                            qual: str = get_a_d(get_l_d(r1).access)
                            if len(r1) > 1:
                                for i, r2 in r1.items():
                                    r2_decl_list: list[str] = []
                                    r2_def_list: list[str] = []
                                    r2_cmt_list: list[str] = []
                                    if len(r2) > 1:
                                            max_idx_d2 = max(max_idx_d2, j)
                                            r1_decl_list.append(f'[{j}]')
                                            r1_def_list.append(f'0x{r3.reset:08X}U')
                                            r1_cmt_list.append(f'/** @brief {r3.desc} */')
                                    dim_r1_str: str = ""
                                    if len(r2_decl_list) > 0:
                                        dim_r1_str += f'{" "*6}[{i}] = {{\n'
                                        max_decl_len: int = max([len(x) for x in r2_decl_list])
                                        max_def_len: int = max([len(x) for x in r2_def_list])
                                        for i, (decl, _def, cmt) in enumerate(zip(r2_decl_list, r2_def_list, r2_cmt_list)):
                                            def_gap: int = (max_r1_decl_len - len(decl)) + 1
                                            cmt_gap: int = (max_r1_def_len - len(_def)) + 3
                                            comma_str: str = "," if i < len(r2_decl_list) - 1 else ""
                                            dim_r1_str += f'{" "*8}{decl}{" "*def_gap}= {_def}{comma_str}{" "*cmt_gap}{cmt}\n'
                                        dim_r1_str += f'{" "*6}}},\n'
                                    r1_str += dim_r1_str
                                if len(r1_str) > 0:
                                    f.write(f'{" "*4}static const uint{size}_t {n}_RST[{max_idx_d1 + 1}][{max_idx_d2 + 1}] = {{\n')
                                    f.write(r1_str[:-2] + "\n")
                                    f.write(f"{" "*4}}};\n")
                                    f.write('\n')

                        max_n_len: int = max([len(x) for x in name_list])

                        f.write(f'{" "*4}/**** @subsection {periph_name} Register Value Type Definitions ****/\n')
                        f.write('\n')

                        for r1, n in zip(reg_list, name_list):
                            r_size: int = get_a_d(r1).size
                            cmt_gap: int = (max_n_len - len(n)) + 3
                            f.write(f'{" "*4}typedef uint{r_size}_t {n}_vt;{" "*cmt_gap}/** @brief {n} register value type. */\n')
                        f.write("\n")
                        
                        f.write(f'{" "*4}/**** @subsection {periph_name} Register Pointer Type Definitions ****/\n')
                        f.write('\n')

                        for r1, n in zip(reg_list, name_list):
                            r_size: int = get_a_d(r1).size
                            qual: str = get_qual(get_a_d(r1).access)
                            cmt_gap: int = (max_n_len - len(n)) + 3
                            f.write(f'{" "*4}typedef {qual} uint{r_size}_t* {n}_pt;{" "*cmt_gap}/** @brief {n} pointer register pointer type. */\n')
                        f.write("\n")
                    
                if p1.registers:
                    field_list: list = []
                    name_list: list = []
                    r_xlist: list[str] = []
                    for r1 in p1.registers:
                        if r1.name not in r_xlist:
                            for r2 in p1.registers:
                                if get_digit_diff(r1, r2, "") is not None:
                                    r_xlist.append(r2.name)

                            new_r1: dict[int, tp.Any] = {}
                            if r1.fields:
                                f_xlist: list[str] = []
                                for f1 in r1.fields:
                                    if f1.name not in f_xlist:
                                        for f2 in r1.fields:
                                            if get_digit_diff(f1, f2, "") is not None:
                                                f_xlist.append(f2.name)

                                        fp_name: str = p1.name
                                        fr_name: str = r1.name
                                        ff_name: str = f1.name

                                        base_f1_num: int = 0
                                        base_f1: tp.Any = None
                                        new_f1: dict[int, tp.Any] = {}
                                        if device.peripherals is not None:
                                            for p2 in device.peripherals:
                                                p_diff = get_digit_diff(p1, p2, "x")
                                                if p1.name == p2.name or p_diff is not None:

                                                    base_f2_num: int = 0
                                                    base_f2: tp.Any = None
                                                    new_f2: dict[int, tp.Any] = {}
                                                    if p2.registers is not None:
                                                        for r2 in p2.registers:
                                                            r_diff = get_digit_diff(r1, r2, "x")
                                                            if r1.name == r2.name or r_diff is not None:

                                                                base_f3_num: int = 0
                                                                base_f3: field_t = None
                                                                new_f3: dict[int, field_t] = {}
                                                                if r2.fields is not None:
                                                                    for f2 in r2.fields:
                                                                        f_diff = get_digit_diff(f1, f2, "x")
                                                                        if f_diff is not None:
                                                                            ff_name = f_diff[0]
                                                                            base_f3_num = f_diff[1]
                                                                            new_f3[f_diff[2]] = field_t(
                                                                                offset = f2.bit_offset, 
                                                                                width = f2.bit_width,
                                                                                size = r2.size,
                                                                                desc = f2.description)
                                                                        elif (f1.name == f2.name):
                                                                            base_f3 = field_t(
                                                                                offset = f2.bit_offset,
                                                                                width = f2.bit_width,
                                                                                size = r2.size,
                                                                                desc = f2.description)
                                                                            
                                                                if base_f3 is not None:
                                                                    new_f3[base_f3_num] = base_f3
                                                                if r1.name == r2.name:
                                                                    base_f2 = new_f3
                                                                else:
                                                                    base_f2_num = r_diff[1]
                                                                    fr_name = r_diff[0]
                                                                    if len(new_f3) > 0:
                                                                        new_f2[r_diff[2]] = new_f3

                                                    if base_f2 is not None:
                                                        new_f2[base_f2_num] = base_f2
                                                    if p1.name == p2.name:
                                                        base_f1 = new_f2
                                                    else:
                                                        base_f1_num = p_diff[1]
                                                        fp_name = p_diff[0]
                                                        if len(new_f2) > 0:
                                                            new_f1[p_diff[2]] = new_f2

                                        if base_f1 is not None:
                                            new_f1[base_f1_num] = base_f1

                            if len(new_f1) > 0:
                                field_list.append(new_f1)
                                name_list.append(f'{fp_name}_{fr_name}_{ff_name}')

                    if len(field_list) > 0:

                        f.write(f'{" "*4}/**** @subsection {periph_name} Field Mask Definitions ****/\n')
                        f.write('\n')

                        decl_list: list[str] = []
                        def_list: list[str] = []
                        cmt_list: list[str] = []
                        for f1, n in zip(field_list, name_list):
                            if (len(f1) == 1 and len(list(f1.values())[0]) == 1 and 
                                len(list(list(f1.values())[0].values())[0]) == 1):
                                decl_list.append(f'static const uint{get_l_d(f1).size}_t {n}_MASK')
                                def_list.append(f'0x{(((1 << get_l_d(f1).width) - 1) << get_l_d(f1).offset):0{get_l_d(f1).size // 4}X}U')
                                cmt_list.append(f'/** @brief {get_l_d(f1).desc} */')
                        if len(decl_list) > 0:
                            max_decl_len: int = max([len(x) for x in decl_list])
                            max_def_len: int = max([len(x) for x in def_list])
                            for decl, _def, cmt in zip(decl_list, def_list, cmt_list):
                                def_gap: int = (max_decl_len - len(decl)) + 1
                                cmt_gap: int = (max_def_len - len(_def)) + 3
                                f.write(f'{" "*4}{decl}{" "*def_gap}= {_def};{" "*cmt_gap}{cmt}\n')
                            f.write('\n')

                        for f1, n in zip(field_list, name_list):
                            name: str = n
                            max_idx: int = 0
                            size: int = get_a_d(f1).size
                            decl_list: list[str] = []
                            def_list: list[str] = []
                            cmt_list: list[str] = []
                            if len(f1) == 1:
                                if len(list(f1.values())[0]) > 1:
                                    for j, f2 in list(f1.values())[0].items():
                                        if len(f2) == 1:
                                            max_idx = max(max_idx, j)
                                            decl_list.append(f'[{j}]')
                                            def_list.append(f'0x{(((1 << get_l_d(f2).width) - 1) << get_l_d(f2).offset):0{size // 4}X}U')
                                            cmt_list.append(f'/** @brief {get_l_d(f2).desc} */')
                                elif len(list(list(f1.values())[0].values())[0]) > 1:
                                    for j, f2 in list(list(f1.values())[0].values())[0].items():
                                        max_idx = max(max_idx, j)
                                        decl_list.append(f'[{j}]')
                                        def_list.append(f'0x{(((1 << f2.width) - 1) << f2.offset):0{size // 4}X}U')
                                        cmt_list.append(f'/** @brief {f2.desc} */')
                            else:
                                for i, f2 in f1.items():
                                    if len(f2) == 1 and len(list(f2.values())[0]) == 1:
                                        max_idx = max(max_idx, i)
                                        decl_list.append(f'[{i}]')
                                        def_list.append(f'0x{(((1 << get_l_d(f2).width) - 1) << get_l_d(f2).offset):0{size // 4}X}U')
                                        cmt_list.append(f'/** @brief {get_l_d(f2).desc} */')
                            if len(decl_list) > 0:
                                f.write(f'{" "*4}static const uint{size}_t {name}_MASK[{max_idx + 1}] = {{\n')
                                max_decl_len: int = max([len(x) for x in decl_list])
                                max_def_len: int = max([len(x) for x in def_list])
                                for i, (decl, _def, cmt) in enumerate(zip(decl_list, def_list, cmt_list)):
                                    def_gap: int = (max_decl_len - len(decl)) + 1
                                    cmt_gap: int = (max_def_len - len(_def)) + 3
                                    comma_str: str = "," if i < len(decl_list) - 1 else ""
                                    f.write(f'{" "*6}{decl}{" "*def_gap}= {_def}{comma_str}{" "*cmt_gap}{cmt}\n')
                                f.write(f"{" "*4}}};\n")
                                f.write('\n')
                            
                        for f1, n in zip(field_list, name_list):
                            f1_str: str = ""
                            max_idx_d1: int = 0
                            max_idx_d2: int = 0
                            size: int = get_a_d(f1).size
                            if len(f1) > 1:
                                for i, f2 in f1.items():
                                    max_idx_d1 = max(max_idx_d1, i)
                                    f2_decl_list: list[str] = []
                                    f2_def_list: list[str] = []
                                    f2_cmt_list: list[str] = []
                                    if len(f2) > 1:
                                        for j, f3 in f2.items():
                                            if len(f3) == 1:
                                                max_idx_d2 = max(max_idx_d2, j)
                                                f2_decl_list.append(f'[{j}]')
                                                f2_def_list.append(f'0x{(((1 << get_l_d(f3).width) - 1) << get_l_d(f3).offset):0{size // 4}X}U')
                                                f2_cmt_list.append(f'/** @brief {get_l_d(f3).desc} */')
                                    elif len(list(f2.values())[0]) > 1:
                                        for j, f3 in list(f2.values())[0].items():
                                            max_idx_d2 = max(max_idx_d2, j)
                                            f2_decl_list.append(f'[{j}]')
                                            f2_def_list.append(f'0x{(((1 << f3.width) - 1) << f3.offset):0{size // 4}X}U')
                                            f2_cmt_list.append(f'/** @brief {f3.desc} */')
                                    dim_f2_str: str = ""
                                    if len(f2_decl_list) > 0:
                                        dim_f2_str += f'{" "*6}[{i}] = {{\n'
                                        max_decl_len: int = max([len(x) for x in f2_decl_list])
                                        max_def_len: int = max([len(x) for x in f2_def_list])
                                        for j, (decl, _def, cmt) in enumerate(zip(f2_decl_list, f2_def_list, f2_cmt_list)):
                                            def_gap: int = (max_decl_len - len(decl)) + 1
                                            cmt_gap: int = (max_def_len - len(_def)) + 3
                                            comma_str: str = "," if j < len(f2_decl_list) - 1 else ""
                                            dim_f2_str += f'{" "*8}{decl}{" "*def_gap}= {_def}{comma_str}{" "*cmt_gap}{cmt}\n'
                                        dim_f2_str += f'{" "*6}}},\n'
                                        f1_str += dim_f2_str
                            elif len(list(f1.values())[0]) > 1:
                                for i, f2 in list(f1.values())[0].items():
                                    max_idx_d1 = max(max_idx_d1, i)
                                    f2_decl_list: list[str] = []
                                    f2_def_list: list[str] = []
                                    f2_cmt_list: list[str] = []
                                    if len(f2) > 1:
                                        for j, f3 in f2.items():
                                            max_idx_d2 = max(max_idx_d2, j)
                                            f2_decl_list.append(f'[{j}]')
                                            f2_def_list.append(f'0x{(((1 << f3.width) - 1) << f3.offset):0{size // 4}X}U')
                                            f2_cmt_list.append(f'/** @brief {f3.desc} */')
                                    dim_f2_str: str = ""
                                    if len(f2_decl_list) > 0:
                                        dim_f2_str += f'{" "*6}[{i}] = {{\n'
                                        max_decl_len: int = max([len(x) for x in f2_decl_list])
                                        max_def_len: int = max([len(x) for x in f2_def_list])
                                        for j, (decl, _def, cmt) in enumerate(zip(f2_decl_list, f2_def_list, f2_cmt_list)):
                                            def_gap: int = (max_decl_len - len(decl)) + 1
                                            cmt_gap: int = (max_def_len - len(_def)) + 3
                                            comma_str: str = "," if j < len(f2_decl_list) - 1 else ""
                                            dim_f2_str += f'{" "*8}{decl}{" "*def_gap}= {_def}{comma_str}{" "*cmt_gap}{cmt}\n'
                                        dim_f2_str += f'{" "*6}}},\n'
                                        f1_str += dim_f2_str
                            if len(f1_str) > 0:
                                f.write(f'{" "*4}static const uint{size}_t {n}_MASK[{max_idx_d1 + 1}][{max_idx_d2 + 1}] = {{\n')
                                f.write(f1_str[:-2] + "\n")
                                f.write(f"{" "*4}}};\n")
                                f.write('\n')

                        for f1, n in zip(field_list, name_list):
                            d1_str: str = ""
                            max_idx_d1: int = 0
                            max_idx_d2: int = 0
                            max_idx_d3: int = 0
                            size: int = get_a_d(f1).size
                            if len(f1) > 1:
                                for i, f2 in f1.items():
                                    if len(f2) > 1:
                                        max_idx_d1 = max(max_idx_d1, i)
                                        d2_str: str = ""
                                        for j, f3 in f2.items():
                                            if len(f3) > 1:
                                                max_idx_d2 = max(max_idx_d2, j)
                                                d3_decl_list: list[str] = []
                                                d3_def_list: list[str] = []
                                                d3_cmt_list: list[str] = []
                                                for k, f4 in f3.items():
                                                    max_idx_d3 = max(max_idx_d3, k)
                                                    d3_decl_list.append(f'[{k}]')
                                                    d3_def_list.append(f'0x{(((1 << f4.width) - 1) << f4.offset):0{size // 4}X}U')
                                                    d3_cmt_list.append(f'/** @brief {f4.desc} */')
                                                if len(d3_decl_list) > 0:
                                                    max_decl_len: int = max([len(x) for x in d3_decl_list])
                                                    max_def_len: int = max([len(x) for x in d3_def_list])
                                                    d2_str += f'{" "*8}[{j}] = {{\n'
                                                    for l, (decl, _def, cmt) in enumerate(zip(d3_decl_list, d3_def_list, d3_cmt_list)):
                                                        def_gap: int = (max_decl_len - len(decl)) + 1
                                                        cmt_cap: int = (max_def_len - len(_def)) + 3
                                                        comma_str: str = "," if l < len(d3_decl_list) - 1 else ""
                                                        new_str = f'{" "*10}{decl}{" "*def_gap}= {_def}{comma_str}{" "*cmt_gap}{cmt}\n'
                                                        d2_str += new_str
                                                    d2_str += f'{" "*8}}},\n'
                                        if len(d2_str) > 0:
                                            d1_str += f'{" "*6}[{i}] = {{\n'
                                            d1_str += d2_str[:-2] + "\n"
                                            d1_str += f'{" "*6}}},\n'
                            if len(d1_str) > 0:
                                f.write(f'{" "*4}static uint{size}_t {n}[{max_idx_d1 + 1}][{max_idx_d2 + 1}][{max_idx_d3 + 1}] = {{\n')
                                f.write(d1_str[:-2] + "\n")
                                f.write(f'{" "*4}}};\n')
                                f.write('\n')
