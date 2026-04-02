"""SMS target: foreign dependencies in a web application module."""

import ctypes
import mmap
import struct


def read_shared_memory(name, size=4096):
    """Read from shared memory — unusual for a web app."""
    buf = mmap.mmap(-1, size, tagname=name)
    raw = buf.read(size)
    buf.close()
    return struct.unpack(f"{size}s", raw)[0]


def call_native_lib(lib_path, func_name, *args):
    """Call a native C library function — unusual for a web app."""
    lib = ctypes.cdll.LoadLibrary(lib_path)
    func = getattr(lib, func_name)
    return func(*args)


def process_binary_data(data):
    """Parse binary protocol — unusual for a web app."""
    header = struct.unpack("!HHI", data[:8])
    version, flags, length = header
    payload = data[8 : 8 + length]
    return {"version": version, "flags": flags, "payload": payload}
