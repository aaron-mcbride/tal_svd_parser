

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
OUTPUT_PATH: str = "D:\\main\\projects\\sarp\\svd_parser\\output.h"

# Path to SVD data directory -> git clone --depth=1 -b main https://github.com/cmsis-svd/cmsis-svd-data.git
SVD_PKG_PATH: str = "D:\\main\\projects\\sarp\\svd_parser\\cmsis-svd-data\\data"

# Target device vendor name
VENDOR_NAME: str = "STMicro"

# Core 1 SVD file name
SVD_NAME: str = "STM32H7x5_CM7.svd"

###################################################################################################
# PARSER
###################################################################################################

parser = svd.SVDParser.for_packaged_svd(package_root = SVD_PKG_PATH, vendor = VENDOR_NAME, filename = SVD_NAME)
device = parser.get_device(xml_validation = False)
new_device: svd.parser.SVDDevice = svd.parser.SVDDevice()

###################################################################################################
# IMPLEMENTATION
###################################################################################################

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

def get_qual(reg):
    if reg.access == svd.parser.SVDAccessType.READ_ONLY: return "RO_"
    if reg.access == svd.parser.SVDAccessType.WRITE_ONLY: return "RW_"
    if reg.access == svd.parser.SVDAccessType.READ_WRITE: return "RW_"
    if reg.access == svd.parser.SVDAccessType.WRITE_ONCE: return "RW_"
    if reg.access == svd.parser.SVDAccessType.READ_WRITE_ONCE: return "RW_"

@dataclass
class field_t:
    offset: int
    width: int
    size: int

@dataclass
class register_t:
    address: int
    access: svd.parser.SVDAccessType
    size: int
    desc: str
    reset: int
      
with open(OUTPUT_PATH, "w") as f:

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

                                        base_r2_num: int = -1
                                        base_r2: register_t = None
                                        new_r2: dict[int, tp.Any] = {}
                                        if p2.registers is not None:
                                            for r2 in p2.registers:
                                                r_diff = get_digit_diff(r1, r2, "x")
                                                if r_diff is not None:
                                                    pr_name = r_diff[0]
                                                    base_r2_num = r_diff[1]
                                                    new_r2[r_diff[2]] = register_t(
                                                        address = r2.base_address + r2.address_offset,
                                                        access = r2.access,
                                                        size = r2.size,
                                                        desc = r2.description,
                                                        reset = r2.reset_value)
                                                elif r1.name == r2.name:
                                                    base_r2 = register_t(
                                                        address = r2.base_address + r2.address_offset,
                                                        access = r2.access,
                                                        size = r2.size, 
                                                        desc = r2.description,
                                                        reset = r2.reset_value)

                                        if base_r2 is not None:
                                            new_r2[base_r2_num] = base_r2
                                        if p1.name == p2.name:
                                            base_f1 = new_r2
                                        else:
                                            base_r1_num = p_diff[1]
                                            new_r1[p_diff[2]] = new_r2
                                            pp_name = p_diff[0]

                            if base_r1 is not None:
                                new_r1[base_r1_num] = base_r1
                            reg_list.append(new_r1)
                            name_list.append(f'{pp_name}_{pr_name}')

                    f.write(f'    /**** @subsection {periph_name} Register Pointer Definitions ****/')
                    f.write('\n')

                    decl_list: list[str] = []
                    def_list: list[str] = []
                    cmt_list: list[str] = []
                    for r1, n in zip(reg_list, name_list):
                        if len(r1) == 1 and len(r1[0]) == 1:
                            decl_list.append(f'static {get_qual(r1[0][0].access)} uint{r1[0][0].size}_t* const {n}_PTR')
                            def_list.append(f'({get_qual(r1[0][0].access)} uint{r1[0][0].size}_t*)0x{r1[0][0].address:08X}U')
                            cmt_list.append(f'/** @brief {r1[0][0].desc} */')
                    if len(decl_list) > 0:
                        max_decl_len: int = max([len(x) for x in decl_list])
                        max_def_len: int = max([len(x) for x in def_list])
                        for decl, _def, cmt in zip(decl_list, def_list, cmt_list):
                            def_gap: int = (max_decl_len - len(decl)) + 3
                            cmt_gap: int = (max_def_len - len(_def)) + 3
                            f.write(f'    {decl}{" "*def_gap}= {_def};{" "*cmt_gap}{cmt}\n')
                        f.write('\n')

                    for r1, n in zip(reg_list, name_list):
                        max_idx: int = 0
                        size: int = r1.values()[0][0].size
                        qual: str = get_qual(r1.values()[0][0].access)
                        r1_decl_list: list[str] = []
                        r1_def_list: list[str] = []
                        r1_cmt_list: list[str] = []
                        if len(r1) > 1:
                            for i, r2 in r1.items():
                                if len(r2) == 1:
                                    r1_decl_list.append(f'[{i}]')
                                    r1_def_list.append(f'({qual} uint{size}_t*)0x{r2[0].address:08X}U')
                                    r1_cmt_list.append(f'/** @brief {r2[0].desc} */') 
                                    max_idx = max(max_idx, i)
                        elif len(r1[0]) > 1:
                            for i, r2 in r1[0].items():
                                r1_decl_list.append(f'[{i}]')
                                r1_def_list.append(f'({qual} uint{size}_t*)0x{r2.address:08X}U')
                                r1_cmt_list.append(f'/** @brief {r2[0].desc} */')
                                max_idx = max(max_idx, i)
                        if len(r1_decl_list) > 0:
                            f.write(f'    static {qual} uint{size}_t* const {n}_PTR[{max_idx}] = {{\n')
                            max_r1_decl_len: int = max([len(x) for x in r1_decl_list])
                            max_r1_def_len: int = max([len(x) for x in r1_def_list])
                            for decl, _def, cmt in zip(r1_decl_list, r1_def_list, r1_cmt_list):
                                def_gap: int = (max_r1_decl_len - len(decl)) + 3
                                cmt_gap: int = (max_r1_def_len - len(_def)) + 3
                                f.write(f'      {decl}{" "*def_gap}= {_def},{" "*cmt_gap}{cmt}\n')
                            f.write("}};\n")
                            f.write('\n')
                    
                    for r1, n in zip(reg_list, name_list):
                        max_idx_d1: int = 0
                        max_idx_d2: int = 0
                        size: int = r1.values()[0][0].size
                        qual: str = get_qual(r1.values()[0][0].access)
                        r1_str_list: list[str] = []
                        if len(r1) > 1:
                            for i, r2 in r1.items():
                                r2_decl_list: list[str] = []
                                r2_def_list: list[str] = []
                                r2_cmt_list: list[str] = []
                                if len(r2) > 1:
                                    for j, r3 in r2.items():
                                        r1_decl_list.append(f'[{j}]')
                                        r1_def_list.append(f'({qual} uint{size}_t*)0x{r3.address:08X}U')
                                        r1_cmt_list.append(f'/** @brief {r3.desc} */')
                                        max_idx_d2 = max(max_idx_d2, j)
                                dim_r1_str: str = f'{{\n'
                                if len(r2_decl_list) > 0:
                                    max_decl_len: int = max([len(x) for x in r2_decl_list])
                                    max_def_len: int = max([len(x) for x in r2_def_list])
                                    for decl, _def, cmt in zip(r2_decl_list, r2_def_list, r2_cmt_list):
                                        def_gap: int = (max_r1_decl_len - len(decl)) + 3
                                        cmt_gap: int = (max_r1_def_len - len(_def)) + 3
                                        dim_r1_str += f'        {decl}{" "*def_gap}= {_def},{" "*cmt_gap}{cmt}\n'
                                dim_r1_str += '      },\n'
                                r1_str_list.append(dim_r1_str)
                            if len(r1_str_list) > 0:
                                f.write(f'    static {qual} uint{size}_t* const {n}_PTR[{max_idx_d1}][{max_idx_d2}] = {{\n')
                                for x in r1_str_list: f.write(x)
                                f.write("    };\n")
                                f.write('\n')
                            
                    f.write(f'    /**** @subsection {periph_name} Register Reset Value Definitions ****/')
                    f.write('\n')

                    decl_list: list[str] = []
                    def_list: list[str] = []
                    cmt_list: list[str] = []
                    for r1, n in zip(reg_list, name_list):
                        if len(r1) == 1 and len(r1[0]) == 1:
                            decl_list.append(f'static const uint{r1[0][0].size}_t {n}_RST')
                            def_list.append(f'0x{r1[0][0].reset:08X}U')
                            cmt_list.append(f'/** @brief {r1[0][0].desc} */')
                    if len(decl_list) > 0:
                        max_decl_len: int = max([len(x) for x in decl_list])
                        max_def_len: int = max([len(x) for x in def_list])
                        for decl, _def, cmt in zip(decl_list, def_list, cmt_list):
                            def_gap: int = (max_decl_len - len(decl)) + 3
                            cmt_gap: int = (max_def_len - len(_def)) + 3
                            f.write(f'    {decl}{" "*def_gap}= {_def};{" "*cmt_gap}{cmt}\n')
                        f.write('\n')

                    for r1, n in zip(reg_list, name_list):
                        max_idx: int = 0
                        size: int = r1.values()[0][0].size
                        qual: str = get_qual(r1.values()[0][0].access)
                        r1_decl_list: list[str] = []
                        r1_def_list: list[str] = []
                        r1_cmt_list: list[str] = []
                        if len(r1) > 1:
                            for i, r2 in r1.items():
                                if len(r2) == 1:
                                    r1_decl_list.append(f'[{i}]')
                                    r1_def_list.append(f'0x{r2[0].reset:08X}U')
                                    r1_cmt_list.append(f'/** @brief {r2[0].desc} */') 
                                    max_idx = max(max_idx, i)
                        elif len(r1[0]) > 1:
                            for i, r2 in r1[0].items():
                                r1_decl_list.append(f'[{i}]')
                                r1_def_list.append(f'0x{r2.reset:08X}U')
                                r1_cmt_list.append(f'/** @brief {r2[0].desc} */')
                                max_idx = max(max_idx, i)
                        if len(r1_decl_list) > 0:
                            f.write(f'    static const uint{size}_t {n}_RST[{max_idx}] = {{\n')
                            max_r1_decl_len: int = max([len(x) for x in r1_decl_list])
                            max_r1_def_len: int = max([len(x) for x in r1_def_list])
                            for decl, _def, cmt in zip(r1_decl_list, r1_def_list, r1_cmt_list):
                                def_gap: int = (max_r1_decl_len - len(decl)) + 3
                                cmt_gap: int = (max_r1_def_len - len(_def)) + 3
                                f.write(f'      {decl}{" "*def_gap}= {_def},{" "*cmt_gap}{cmt}\n')
                            f.write("}};\n")
                            f.write('\n')
                    
                    for r1, n in zip(reg_list, name_list):
                        max_idx_d1: int = 0
                        max_idx_d2: int = 0
                        size: int = r1.values()[0][0].size
                        qual: str = get_qual(r1.values()[0][0].access)
                        r1_str_list: list[str] = []
                        if len(r1) > 1:
                            for i, r2 in r1.items():
                                r2_decl_list: list[str] = []
                                r2_def_list: list[str] = []
                                r2_cmt_list: list[str] = []
                                if len(r2) > 1:
                                    for j, r3 in r2.items():
                                        r1_decl_list.append(f'[{j}]')
                                        r1_def_list.append(f'0x{r3.reset:08X}U')
                                        r1_cmt_list.append(f'/** @brief {r3.desc} */')
                                        max_idx_d2 = max(max_idx_d2, j)
                                dim_r1_str: str = f'[{i}] = {{\n'
                                if len(r2_decl_list) > 0:
                                    max_decl_len: int = max([len(x) for x in r2_decl_list])
                                    max_def_len: int = max([len(x) for x in r2_def_list])
                                    for decl, _def, cmt in zip(r2_decl_list, r2_def_list, r2_cmt_list):
                                        def_gap: int = (max_r1_decl_len - len(decl)) + 3
                                        cmt_gap: int = (max_r1_def_len - len(_def)) + 3
                                        dim_r1_str += f'        {decl}{" "*def_gap}= {_def},{" "*cmt_gap}{cmt}\n'
                                dim_r1_str += '      },\n'
                                r1_str_list.append(dim_r1_str)
                            if len(r1_str_list) > 0:
                                f.write(f'    static const uint{size}_t {n}_RST[{max_idx_d1}][{max_idx_d2}] = {{\n')
                                for x in r1_str_list: f.write(f'[]x')
                                f.write("    };\n")
                                f.write('\n')

                    f.write(f'    /**** @subsection {periph_name} Register Value Type Definitions ****/')
                    f.write('\n')

                    for r1, n in zip(reg_list, name_list):
                        r_size: int = r1.values()[0][0].size
                        f.write(f'    typedef uint{r_size}_t {n}_vt;\n')
                    f.write("\n")
                    
                    f.write(f'    /**** @subsection {periph_name} Register Pointer Type Definitions ****/')
                    f.write('\n')

                    for r1, n in zip(reg_list, name_list):
                        r_size: int = r1.values()[0][0].size
                        f.write(f'    typedef uint{r_size}_t* {n}_pt;\n')
                    
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
                                                                                size = r2.size)
                                                                        elif f1.name == f2.name:
                                                                            base_f3 = field_t(
                                                                                offset = f2.bit_offset,
                                                                                width = f2.bit_width,
                                                                                size = r2.size)
                                                                            
                                                                if base_f3 is not None:
                                                                    new_f3[base_f3_num] = base_f3
                                                                if r1.name == r2.name:
                                                                    base_f2 = new_f3
                                                                else:
                                                                    base_f2_num = r_diff[1]
                                                                    new_f2[r_diff[2]] = new_f3
                                                                    fr_name = r_diff[0]

                                                    if base_f2 is not None:
                                                        new_f2[base_f2_num] = base_f2
                                                    if p1.name == p2.name:
                                                        base_f1 = new_f2
                                                    else:
                                                        base_f1_num = p_diff[1]
                                                        new_f1[p_diff[2]] = new_f2
                                                        fp_name = p_diff[0]

                                        if base_f1 is not None:
                                            new_f1[base_f1_num] = base_f1

                            field_list.append(new_f1)
                            name_list.append(f'{fp_name}_{fr_name}_{ff_name}')

                    f.write(f'    /**** @subsection {periph_name} Field Mask Definitions ****/')
                    f.write('\n')

                    decl_list: list[str] = []
                    def_list: list[str] = []
                    cmt_list: list[str] = []
                    for f1, n in zip(field_list, name_list):
                        if len(f1) == 1 and len(f1[0]) == 1 and len(f1[0][0]) == 1:
                            decl_list.append(f'#define {n}_MASK')
                            def_list.append(f'0x{((1 << f1[0][0][0].width) - 1) << f1[0][0][0].offset:08X}U')
                            cmt_list.append(f'/** @brief {f1[0][0][0].desc} */')
                    if len(decl_list) > 0:
                        max_decl_len: int = max([len(x) for x in decl_list])
                        max_def_len: int = max([len(x) for x in def_list])
                        for decl, _def, cmt in zip(decl_list, def_list, cmt_list):
                            def_gap: int = (max_decl_len - len(decl)) + 3
                            cmt_gap: int = (max_def_len - len(_def)) + 3
                            f.write(f'    {decl}{" "*def_gap}= {_def};{" "*cmt_gap}{cmt}\n')
                        f.write('\n')

                    for f1, n in zip(field_list, name_list):
                        max_idx: int = 0
                        name: str = n
                        size: int = f1.values()[0][0].size
                        decl_list: list[str] = []
                        def_list: list[str] = []
                        cmt_list: list[str] = []
                        if len(f1) == 1:
                            for i, f2 in f1.items():
                                if len(f2) > 1:
                                    for j, f3 in f2.items():
                                        if len(f3) == 1:
                                            decl_list.append(f'[{j}]')
                                            def_list.append(f'0x{((1 << f3[0].width) - 1) << f3[0].offset:0{size // 4}X}U')
                                            cmt_list.append(f'/** @brief {f3[0].desc} */')
                                            max_idx = max(max_idx, j)                                    
                                else:
                                    for j, f3 in f2.items():
                                        if len(f3) > 1:
                                            decl_list.append(f'[{j}]')
                                            def_list.append(f'0x{((1 << f3[0].width) - 1) << f3[0].offset:0{size // 4}X}U')
                                            cmt_list.append(f'/** @brief {f3[0].desc} */')
                                            max_idx = max(max_idx, j)
                        elif len(f1[0]) == 1:
                            for i, f2 in f1[0].items():
                                if len(f2) > 1:
                                    decl_list.append(f'[{i}]')
                                    def_list.append(f'0x{((1 << f2.width) - 1) << f2.offset:0{size // 4}X}U')
                                    cmt_list.append(f'/** @brief {f2.desc} */')
                                    max_idx = max(max_idx, i)
                        if len(decl_list) > 0:
                            f.write(f'    static const uint{size} {name})_MASK[{max_idx}] = {{\n')
                            max_decl_len: int = max([len(x) for x in decl_list])
                            max_def_len: int = max([len(x) for x in def_list])
                            for decl, _def, cmt in zip(decl_list, def_list, cmt_list):
                                def_gap: int = (max_decl_len - len(decl)) + 3
                                cmt_gap: int = (max_def_len - len(_def)) + 3
                                f.write(f'      {decl}{" "*def_gap}= {_def};{" "*cmt_gap}{cmt}\n')
                            f.write("    };\n")
                            f.write('\n')
                        
                    for f1, n in zip(field_list, name_list):
                        max_idx_d1: int = 0
                        max_idx_d2: int = 0
                        size: int = f1.values()[0][0].size
                        qual: str = get_qual(f1.values()[0][0].access)
                        r1_str_list: list[str] = []
                        if len(f1) > 1:
                            for i, f2 in f1.items():
                                f2_decl_list: list[str] = []
                                f2_def_list: list[str] = []
                                f2_cmt_list: list[str] = []
                                if len(f2) > 1:
                                    for j, f3 in f2.items():
                                        if len(f3) == 1:
                                            f2_decl_list.append(f'[{j}]')
                                            f2_def_list.append(f'0x{((1 << f3.width) - 1) << f3.offset:0{size // 4}X}U')
                                            f2_cmt_list.append(f'/** @brief {f3.desc} */')
                                            max_idx_d2 = max(max_idx_d2, j)
                                else:
                                    for j, f3 in f2.items():
                                        f2_decl_list.append(f'[{j}]')
                                        f2_def_list.append(f'0x{((1 << f3.width) - 1) << f3.offset:0{size // 4}X}U')
                                        f2_cmt_list.append(f'/** @brief {f3.desc} */')
                                        max_idx_d2 = max(max_idx_d2, j)
                                    

                                dim_f2_str: str = f'[{i}] = {{\n'
                                if len(f2_decl_list) > 0:
                                    max_decl_len: int = max([len(x) for x in f2_decl_list])
                                    max_def_len: int = max([len(x) for x in f2_def_list])
                                    for decl, _def, cmt in zip(f2_decl_list, f2_def_list, f2_cmt_list):
                                        def_gap: int = (max_decl_len - len(decl)) + 3
                                        cmt_gap: int = (max_def_len - len(_def)) + 3
                                        dim_f2_str += f'        {decl}{" "*def_gap}= {_def};{" "*cmt_gap}{cmt}\n'
                                dim_f2_str += '      },\n'
                                r1_str_list.append(dim_f2_str)
                            if len(r1_str_list) > 0:
                                f.write(f'    static const uint{size}_t {n}_MASK[{max_idx_d1}][{max_idx_d2}] = {{\n')
                                for x in r1_str_list: f.write(x)
                                f.write("    };\n")
                                f.write('\n')






                                    

                                    
                                        
                                    
                        
                            

                            

                            
                            

                            






                        



  


