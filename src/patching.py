"""Strict Mach-O patching by instruction shape. No vendor code is shipped here."""
import hashlib
import re
import struct


def require(condition, message):
    if not condition:
        raise ValueError(message)


def shape_mask(word):
    """Keep opcodes and constants; ignore registers, memory offsets and branch targets."""
    if (word & 0x7C000000) == 0x14000000:                   # B, BL
        return 0xFC000000
    if (word & 0xFF000010) == 0x54000000:                   # B.cond
        return 0xFF00001F
    if (word & 0x7E000000) == 0x34000000:                   # CBZ, CBNZ
        return 0xFF000000
    if (word & 0x7E000000) == 0x36000000:                   # TBZ, TBNZ
        return 0xFFF80000
    if (word & 0x1F000000) == 0x10000000:                   # ADR, ADRP
        return 0x9F000000
    if (word & 0x1F800000) == 0x12800000:                   # MOVN, MOVZ, MOVK
        return 0xFFFFFFE0
    if (word & 0x1F000000) == 0x11000000:                   # ADD/SUB immediate
        # Frame and stack offsets move between builds; other immediates are kept.
        return 0xFFC003E0 if (word >> 5) & 31 in (29, 31) else 0xFFFFFC00
    if (word & 0x1F000000) in (0x12000000, 0x13000000):     # logical immediate, bitfield
        return 0xFFFFFC00
    if (word & 0x1F000000) in (0x0A000000, 0x0B000000):     # logical/arithmetic register
        return 0xFFE0FC00
    if (word & 0x1FE00000) == 0x1A800000:                   # conditional select
        return 0xFFE0FC00
    if (word & 0x1F000000) == 0x1B000000:                   # multiply
        return 0xFFE08000
    if (word & 0xFE1FFC1F) == 0xD61F0000:                   # BR, BLR, RET
        return 0xFFFFFC1F
    if (word & 0x3B000000) == 0x39000000:                   # load/store unsigned offset
        return 0xFFC00000
    if (word & 0x3B200000) == 0x38000000:                   # load/store unscaled, pre/post-index
        return 0xFFE00C00
    if (word & 0x3A000000) == 0x28000000:                   # load/store pair
        return 0xFFC00000
    if (word & 0x3B000000) == 0x18000000:                   # load literal
        return 0xFF000000
    return 0xFFFFFFFF


def pattern_regex(words):
    masks = [shape_mask(w) for w in words]
    pages = {}
    for i, word in enumerate(words):
        if (word & 0x9F000000) == 0x90000000:
            pages[word & 31] = i
        elif (word & 0x1F000000) == 0x11000000 and i - pages.get((word >> 5) & 31, -9) <= 4:
            masks[i] = 0xFFC00000                           # page offset paired with ADRP
    regex = b''
    for word, mask in zip(words, masks):
        for value, keep in zip(word.to_bytes(4, 'little'), mask.to_bytes(4, 'little')):
            if keep == 0xFF:
                regex += re.escape(bytes([value]))
            elif keep == 0:
                regex += b'.'
            else:
                regex += b'[' + b''.join(re.escape(bytes([b])) for b in range(256) if b & keep == value & keep) + b']'
    return re.compile(b'(?=' + regex + b')', re.DOTALL)


def patch_executable(original, manifest):
    # Reviewed versions pin the exact executable; newer ones rely on Meta's signature and unique patterns.
    if 'executable_sha256' in manifest:
        require(hashlib.sha256(original).hexdigest() == manifest['executable_sha256'],
                'Unsupported executable hash; refusing to patch (including already patched apps).')
    require(len(original) >= 8 and original[:4] == b'\xca\xfe\xba\xbe', 'Expected universal Mach-O')
    count = struct.unpack_from('>I', original, 4)[0]
    require(0 < count <= 16 and 8 + count * 20 <= len(original), 'Invalid architecture table')
    slices = [struct.unpack_from('>IIIII', original, 8 + i * 20) for i in range(count)]
    arms = [s for s in slices if s[0] == 0x0100000c]
    require(len(arms) == 1, 'Expected exactly one arm64 slice')
    base, length = arms[0][2:4]
    require(base >= 8 + count * 20 and length >= 32 and base + length <= len(original), 'Invalid slice')
    thin = original[base:base + length]
    require(thin[:4] == b'\xcf\xfa\xed\xfe', 'Expected 64-bit little-endian Mach-O')
    commands, command_bytes = struct.unpack_from('<II', thin, 16)
    end = 32 + command_bytes
    require(end <= length and commands <= command_bytes // 8, 'Invalid load command table')
    texts, first_section, pos = [], length, 32
    for _ in range(commands):
        require(pos + 8 <= end, 'Truncated load command')
        cmd, size = struct.unpack_from('<II', thin, pos)
        require(size >= 8 and size % 8 == 0 and pos + size <= end, 'Invalid load command size')
        if cmd == 0x19:
            require(size >= 72, 'Truncated segment')
            va, vs, fo, fs = struct.unpack_from('<QQQQ', thin, pos + 24)
            require(fo + fs <= length, 'Segment outside slice')
            nsections = struct.unpack_from('<I', thin, pos + 64)[0]
            require(72 + nsections * 80 <= size, 'Truncated section table')
            for i in range(nsections):
                section = pos + 72 + i * 80
                address, section_size = struct.unpack_from('<QQ', thin, section + 32)
                section_offset = struct.unpack_from('<I', thin, section + 48)[0]
                if section_offset:
                    first_section = min(first_section, section_offset)
                if thin[section:section + 32] == b'__text'.ljust(16, b'\0') + b'__TEXT'.ljust(16, b'\0'):
                    require(fo <= section_offset and section_offset + section_size <= fo + fs, 'Code section outside segment')
                    texts.append((address, section_offset, section_size))
        pos += size
    require(pos == end, 'Load command size mismatch')
    require(len(texts) == 1, 'Expected exactly one code section')
    code_address, code_offset, code_size = texts[0]
    code = memoryview(thin)[code_offset:code_offset + code_size]
    patched, report = bytearray(original), []
    for patch in manifest['patches']:
        words = [int(line.split()[0], 16) for line in patch['pattern']]
        index, after = patch['index'], int(patch['after'], 16)
        require(0 <= index < len(words) and after & 31 == 0, 'Invalid patch definition')
        hits = [m.start() for m in pattern_regex(words).finditer(code) if m.start() % 4 == 0]
        require(len(hits) == 1, f"{patch['purpose']}: expected one code match, found {len(hits)}; "
                                'this Meta build needs a patch review')
        target = code_offset + hits[0] + index * 4
        before = struct.unpack_from('<I', thin, target)[0]
        value = after | (before & 31)  # keep the matched destination register
        struct.pack_into('<I', patched, base + target, value)
        report.append({'purpose': patch['purpose'], 'address': hex(code_address + target - code_offset),
                       'file_offset': hex(base + target), 'before': f'{before:08x}', 'after': f'{value:08x}'})
    require(len({r['file_offset'] for r in report}) == len(report), 'Patches overlap')
    name = b'@executable_path/libQuestVDUSB.dylib\0'
    size = (24 + len(name) + 7) // 8 * 8
    require(end + size <= first_section <= length, 'Insufficient header padding')
    require(thin[end:end + size] == bytes(size), 'Nonzero header padding')
    command = (struct.pack('<IIIIII', 0xc, size, 24, 0, 0, 0) + name).ljust(size, b'\0')
    patched[base + end:base + end + size] = command
    struct.pack_into('<II', patched, base + 16, commands + 1, command_bytes + size)
    return bytes(patched), report
