#!/usr/bin/env python3
"""反汇编 cmvs32.exe 里出错地址附近的一段"""
import sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Users\DMS\Desktop\Hapymaher\ハピメア フルHD版\cmvs32.exe"
VA = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0x42FFA8
BEFORE = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x180
AFTER = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x40

pe = pefile.PE(EXE, fast_load=True)
image_base = pe.OPTIONAL_HEADER.ImageBase


def va_to_off(va):
    rva = va - image_base
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (rva - s.VirtualAddress)
    return None


data = open(EXE, "rb").read()
off = va_to_off(VA)
print(f"VA {VA:#x} -> 文件偏移 {off:#x}  (image base {image_base:#x})")

start = off - BEFORE
buf = data[start:off + AFTER]
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

for ins in md.disasm(buf, VA - BEFORE):
    mark = "   <<<<< 出错点" if ins.address == VA else ""
    print(f"{ins.address:#010x}  {ins.bytes.hex(' '):<24} {ins.mnemonic:<8} {ins.op_str}{mark}")
