import ctypes
import mmap

class SharedMemoryData(ctypes.Structure):
    _fields_ = [
        ("airIoStatus", ctypes.c_uint8 * 6),
        ("sliderIoStatus", ctypes.c_uint8 * 32),
        ("ledRgbData", ctypes.c_uint8 * 96),
        ("reserved", ctypes.c_uint8 * 4)
    ]

SHARED_MEMORY_NAME = "Local\\BROKENITHM_SHARED_BUFFER"
SHARED_MEMORY_SIZE = ctypes.sizeof(ctypes.c_uint8) * ctypes.sizeof(SharedMemoryData)

def open_sharedmem():
    try:
        shared_memory = mmap.mmap(-1, SHARED_MEMORY_SIZE, 
                                tagname=SHARED_MEMORY_NAME,
                                access=mmap.ACCESS_DEFAULT)
        return shared_memory
    except Exception:
        print("[Error] A Fatal Error occured while trying to write to the Shared Memory while initializing")
        return None
    
def write_to_airzone(air_zone_state: list, shared_memory: mmap.mmap):
    if len(air_zone_state) != 6 and all(isinstance(state, bool) for state in air_zone_state):
        raise ValueError("air_input must have exactly 6 elements")
    air_states = bytes([128 if state else 0 for state in fix_air_order(air_zone_state)])
    shared_memory.seek(0)
    shared_memory.write(bytes(air_states))
    
def fix_air_order(air_zone_state: list):
    if len(air_zone_state) != 6:
        raise ValueError("air_input must have exactly 6 elements")
    return [air_zone_state[4], air_zone_state[5], air_zone_state[2], air_zone_state[3], air_zone_state[0], air_zone_state[1]]
