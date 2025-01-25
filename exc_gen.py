###################################################################################################
# CONFIGURATION
###################################################################################################

# Path to SVD file
SVD_PATH: str = "D:\\main\\projects\\sarp\\svd_parser\\cmsis-svd-data\\data\\STMicro\\STM32H7x5_CM7.svd"

# Output file path
OUTPUT_PATH: str = "D:\\main\\projects\\sarp\\svd_parser\\exc.h"

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

# Offset for IRQ numbers
IRQ_OFFSET: int = 16

# Vector table size
VTABLE_SIZE: int = 256

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

for peripheral in device.peripherals:
    if peripheral.interrupts:
        for interrupt in peripheral.interrupts:
            if interrupt.name == "TIM8_TRG_COM_TIM14":
                interrupt.name = "TIM8_14_TRG_COM"
            if interrupt.name == "RTC_TAMP_STAMP_CSS_LSE":
                interrupt.name = "RTC_TAMP_STAMP"

if os.path.exists(OUTPUT_PATH): 
    os.remove(OUTPUT_PATH)

with open(OUTPUT_PATH, "w") as file:

    if device.peripherals:

        max_it_name_len: int = 0
        for peripheral in device.peripherals:
            if peripheral.interrupts:
                for interrupt in peripheral.interrupts:
                    max_it_name_len = max(max_it_name_len, len(interrupt.name))

        max_exc_num_len: int = 0
        for peripheral in device.peripherals:
            if peripheral.interrupts:
                for interrupt in peripheral.interrupts:
                    exc_num = interrupt.value + IRQ_OFFSET
                    max_exc_num_len = max(max_exc_num_len, len(str(exc_num)))

        file.write(f'  #include<stdint.h>\n')
        file.write(f'  #define EXC_ATTR_ __attribute__((weak, used, alias("default_handler")))\n')
        file.write(f'  #define VTABLE_SIZE {VTABLE_SIZE}')
        file.write(f'\n')
        file.write(f'  /*************************************************************************************************\n')
        file.write(f'   * @section Interrupt Handler Definitions \n')
        file.write(f'   *************************************************************************************************/\n')
        file.write(f'\n')

        for i in range(0, VTABLE_SIZE):
            for peripheral in device.peripherals:
                if peripheral.interrupts:
                    for interrupt in peripheral.interrupts:
                        if interrupt.value + IRQ_OFFSET == i:
                    
                            name: str = f'{interrupt.name.lower()}_exc_handler'
                            cmt: str = f'/** @brief {fmt_desc(interrupt.description)} */'

                            cmt_gap: int = (max_it_name_len - len(interrupt.name)) + 3
                            file.write(f'  EXC_ATTR_ void {name}();{" "*cmt_gap}{cmt}\n')

        file.write(f'\n')
        file.write(f'  /*************************************************************************************************\n')
        file.write(f'   * @section Exception Number Definitions \n')
        file.write(f'   *************************************************************************************************/\n')
        file.write(f'\n')

        for i in range(0, VTABLE_SIZE):
            for peripheral in device.peripherals:
                if peripheral.interrupts:
                    for interrupt in peripheral.interrupts:
                        if interrupt.value + IRQ_OFFSET == i:
                    
                            name: str = f'{interrupt.name.upper()}_EXC_NUM'
                            value: str = f'INT32_C({interrupt.value + IRQ_OFFSET})'
                            cmt: str = f'/** @brief {fmt_desc(interrupt.description)} */'
                            
                            value_gap: int = (max_it_name_len - len(interrupt.name)) + 3
                            cmt_gap: int = (max_exc_num_len - len(str(interrupt.value + IRQ_OFFSET))) + 3
                            file.write(f'  #define {name}{" "*value_gap}{value}{" "*cmt_gap}{cmt}\n')
                    
        file.write(f'\n')
        file.write(f'  /*************************************************************************************************\n')
        file.write(f'   * @section Vector Table Definition \n')
        file.write(f'   *************************************************************************************************/\n')
        file.write(f'\n')

        file.write(f'  __attribute__((section(".vtable")))\n')
        file.write(f'  static const uint32_t vtable[{VTABLE_SIZE}] = {{\n')

        for peripheral in device.peripherals:
            if peripheral.interrupts:
                for i in range(0, VTABLE_SIZE):
                    for interrupt in peripheral.interrupts:
                        if interrupt.value + IRQ_OFFSET == i:

                            value: str = f'(uint32_t)&{interrupt.name.lower()}_exc_handler'
                            index: str = f'[{interrupt.name.upper()}_EXC_NUM]'
                            cmt: str = f'/** @brief {fmt_desc(interrupt.description)} */'

                            index_gap: int = (max_it_name_len - len(interrupt.name)) + 1
                            cmt_gap: int = (max_it_name_len - len(interrupt.name)) + 1
                            file.write(f'    {index}{" "*index_gap}= {value},{" "*cmt_gap}{cmt}\n')
        
        file.write(f'  }};\n')
        file.write(f'\n')