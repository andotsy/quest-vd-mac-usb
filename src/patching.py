"""Strict, version-specific Mach-O patching. No vendor code is shipped here."""
import hashlib
import struct


def require(condition, message):
    if not condition:
        raise ValueError(message)


def patch_executable(original, manifest):
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
    segments, first_section, pos = [], length, 32
    for _ in range(commands):
        require(pos + 8 <= end, 'Truncated load command')
        cmd, size = struct.unpack_from('<II', thin, pos)
        require(size >= 8 and size % 8 == 0 and pos + size <= end, 'Invalid load command size')
        if cmd == 0x19:
            require(size >= 72, 'Truncated segment')
            va, vs, fo, fs = struct.unpack_from('<QQQQ', thin, pos + 24)
            require(fo + fs <= length, 'Segment outside slice')
            segments.append((va, vs, fo, fs))
            nsections = struct.unpack_from('<I', thin, pos + 64)[0]
            require(72 + nsections * 80 <= size, 'Truncated section table')
            for i in range(nsections):
                section_offset = struct.unpack_from('<I', thin, pos + 72 + i * 80 + 48)[0]
                if section_offset:
                    first_section = min(first_section, section_offset)
        pos += size
    require(pos == end, 'Load command size mismatch')
    patched, report = bytearray(original), []
    for patch in manifest['patches']:
        address = int(patch['address'], 16)
        before, after = bytes.fromhex(patch['before']), bytes.fromhex(patch['after'])
        require(len(before) == len(after) == 4, 'Only four-byte instructions are supported')
        matches = [s for s in segments if s[0] <= address and address + 4 <= s[0] + s[3]]
        require(len(matches) == 1, 'Patch address is not uniquely file-backed')
        segment = matches[0]
        offset = base + segment[2] + address - segment[0]
        require(original[offset:offset + 4] == before, 'Unexpected instruction at ' + patch['address'])
        patched[offset:offset + 4] = after
        report.append(dict(patch, file_offset=hex(offset)))
    name = b'@executable_path/libQuestVDUSB.dylib\0'
    size = (24 + len(name) + 7) // 8 * 8
    require(end + size <= first_section <= length, 'Insufficient header padding')
    require(thin[end:end + size] == bytes(size), 'Nonzero header padding')
    command = (struct.pack('<IIIIII', 0xc, size, 24, 0, 0, 0) + name).ljust(size, b'\0')
    patched[base + end:base + end + size] = command
    struct.pack_into('<II', patched, base + 16, commands + 1, command_bytes + size)
    return bytes(patched), report
