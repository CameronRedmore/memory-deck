import asyncio
import os
from re import I
import subprocess
import sys

from ctypes import *

'''
    Python3 bindings for scanmem
    Copyright (C) 2018 Justas Dabrila <justasdabrila@gmail.com>
    This library is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published
    by the Free Software Foundation; either version 3 of the License, or
    (at your option) any later version.
    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.
    You should have received a copy of the GNU Lesser General Public License
    along with this library.  If not, see <http://www.gnu.org/licenses/>.
'''


absolute_path = os.path.dirname(__file__)
libfile = os.path.join(absolute_path, "bin", "libscanmem.so.1.0.0")

if libfile is None:
    raise OSError("Failed to find scanmem shared object.")

# backend initialization
backend = CDLL(libfile)

c_pid_t = c_int
c_match_flags = c_uint16
c_wildcard_t = c_uint16
c_scan_match_type = c_uint32
c_list_t_ptr = c_void_p
c_region_scan_level_t = c_uint32
c_scan_data_type_t = c_uint32

''' 
    maps.h: region_scan_level_t
        determine which regions we need
'''
class RegionScanLevel():
    REGION_ALL = 0 # each of them 
    REGION_HEAP_STACK_EXECUTABLE = 1 # heap, stack, executable 
    REGION_HEAP_STACK_EXECUTABLE_BSS = 2 # heap, stack, executable, bss

'''
    value.h: match_flags
        match_flags: they MUST be implemented as an `uint16_t`, the `__packed__` ensures so.
        They are reinterpreted as a normal integer when scanning for VLT, which is
        valid for both endians, as the flags are ordered from smaller to bigger.
        NAMING: Primitive, single-bit flags are called `flag_*`, while aggregates,          
        defined for convenience, are called `flags_*`
'''
class MatchFlag():

    FLAGS_EMPTY = 0

    FLAG_U8B  = 1 << 0  # could be an unsigned  8-bit variable (e.g. unsigned char)      
    FLAG_S8B  = 1 << 1  # could be a    signed  8-bit variable (e.g. signed char)        
    FLAG_U16B = 1 << 2  # could be an unsigned 16-bit variable (e.g. unsigned short)     
    FLAG_S16B = 1 << 3  # could be a    signed 16-bit variable (e.g. short)              
    FLAG_U32B = 1 << 4  # could be an unsigned 32-bit variable (e.g. unsigned int)       
    FLAG_S32B = 1 << 5  # could be a    signed 32-bit variable (e.g. int)                
    FLAG_U64B = 1 << 6  # could be an unsigned 64-bit variable (e.g. unsigned long long) 
    FLAG_S64B = 1 << 7  # could be a    signed 64-bit variable (e.g. long long)          

    FLAG_F32B = 1 << 8  # could be a 32-bit floating point variable (i.e. float)         
    FLAG_F64B = 1 << 9  # could be a 64-bit floating point variable (i.e. double)        

    FLAGS_I8B  = FLAG_U8B  | FLAG_S8B
    FLAGS_I16B = FLAG_U16B | FLAG_S16B
    FLAGS_I32B = FLAG_U32B | FLAG_S32B
    FLAGS_I64B = FLAG_U64B | FLAG_S64B

    FLAGS_INTEGER = FLAGS_I8B | FLAGS_I16B | FLAGS_I32B | FLAGS_I64B
    FLAGS_FLOAT = FLAG_F32B | FLAG_F64B
    FLAGS_ALL = FLAGS_INTEGER | FLAGS_FLOAT

    FLAGS_8B   = FLAGS_I8B
    FLAGS_16B  = FLAGS_I16B
    FLAGS_32B  = FLAGS_I32B | FLAG_F32B
    FLAGS_64B  = FLAGS_I64B | FLAG_F64B

    FLAGS_MAX = 0XFFFF

'''
    value.h: mem64_t
        This union describes 8 bytes retrieved from target memory.
        Pointers to this union are the only ones that are allowed to be unaligned:                     
        to avoid performance degradation/crashes on arches that don't support unaligned access /* 
        (e.g. ARM) we access unaligned memory only through the attributes of this packed union. * 
        As described in http://www.alfonsobeato.net/arm/how-to-access-safely-unaligned-data/ ,  * 
        a packed structure forces the compiler to write general access methods to its members   * 
        that don't depend on alignment.                                                         * 
        So NEVER EVER dereference a mem64_t*, but use its accessors to obtain the needed type.  * 
'''
class Mem64(Union):
    _fields_ = [
        ("int8_value",              c_int8), 
        ("uint8_value",             c_uint8), 
        ("int16_value",             c_int16), 
        ("uint16_value",            c_uint16), 
        ("int32_value",             c_int32), 
        ("uint32_value",            c_uint32), 
        ("int64_value",             c_int64), 
        ("uint64_value",            c_uint64), 
        ("float32_value",           c_float), 
        ("float64_value",           c_double), 
        ("bytes[sizeof(int64_t)]",  c_uint8 * sizeof(c_int64)),
        ("chars[sizeof(int64_t)]",  c_char * sizeof(c_int64))   
    ]

'''
    value.h: wildcard_t
        bytearray wildcards: they must be uint8_t. They are ANDed with the incoming
        memory before the comparison, so that '??' wildcards always return true
        It's possible to extend them to fully granular wildcard-ing, if needed
'''
class ValueWildcard():
    FIXED = 0xff
    WILDCARD = 0x00

'''
    value.h: uservalue_t
        this struct describes values provided by users
'''
# typedef struct {
#     int8_t int8_value;
#     uint8_t uint8_value;
#     int16_t int16_value;
#     uint16_t uint16_value;
#     int32_t int32_value;
#     uint32_t uint32_value;
#     int64_t int64_value;
#     uint64_t uint64_value;
#     float float32_value;
#     double float64_value;

#     const uint8_t *bytearray_value;
#     const wildcard_t *wildcard_value;

#     const char *string_value;

#     match_flags flags;
# } uservalue_t;

class UserValue(Structure):
    _fields_ = [
        ("int8_value",      c_int8),
        ("uint8_value",     c_uint8),
        ("int16_value",     c_int16),
        ("uint16_value",    c_uint16),
        ("int32_value",     c_int32),
        ("uint32_value",    c_uint32),
        ("int64_value",     c_int64),
        ("uint64_value",    c_uint64),
        ("float32_value",   c_float),    
        ("float64_value",   c_double),
        ("bytearray_value", POINTER(c_uint8)),
        ("wildcard_value",  POINTER(c_wildcard_t)),
        ("string_value",    c_char_p),
        ("flags",     c_match_flags)
    ]

''' 
    value.h: value_t 
        this struct describes matched values
'''
class SetValue(Structure):

    class SetValueUnion(Union):
        _fields_ = [
            ("int8_value",              c_int8), 
            ("uint8_value",             c_uint8), 
            ("int16_value",             c_int16), 
            ("uint16_value",            c_uint16), 
            ("int32_value",             c_int32), 
            ("uint32_value",            c_uint32), 
            ("int64_value",             c_int64), 
            ("uint64_value",            c_uint64), 
            ("float32_value",           c_float), 
            ("float64_value",           c_double), 
            ("bytes[sizeof(int64_t)]",  c_uint8 * sizeof(c_int64)),
            ("chars[sizeof(int64_t)]",  c_char * sizeof(c_int64))
    ]

    _fields_ = [
        ("value", SetValueUnion),
        ("flags", c_match_flags)
    ]


''' scanroutines.h: scan_data_type_t '''
class ScanDataType():
    ANYNUMBER = 0 # ANYINTEGER or ANYFLOAT
    ANYINTEGER = 1 # INTEGER of whatever width
    ANYFLOAT = 2 # FLOAT of whatever width
    INTEGER8 = 3
    INTEGER16 = 4
    INTEGER32 = 5
    INTEGER64 = 6
    FLOAT32 = 7
    FLOAT64 = 8
    BYTEARRAY = 9
    STRING = 10


''' scanroutines.h: scan_match_type_t '''
class ScanMatchType():
    MATCH_ANY = 0                # for snapshot
    # following: compare with a given value
    MATCH_EQUAL_TO = 1
    MATCH_NOTEQUAL_TO = 2
    MATCH_GREATER_THAN = 3
    MATCH_LESS_THAN = 4
    MATCH_RANGE = 5
    # following: compare with the old value
    MATCH_UPDATE = 6
    MATCH_NOT_CHANGED = 7
    MATCH_CHANGED = 8
    MATCH_INCREASED = 9
    MATCH_DECREASED = 10
    # following: compare with both given value and old value
    MATCH_INCREASED_BY = 11
    MATCH_DECREASED_BY = 12

# typedef struct {
#     uint8_t old_value;
#     match_flags match_info;
# } old_value_and_match_info;
class MatchInfo(Structure):
    _fields_ = [
        ("old_value", c_uint8),
        ("match_info", c_uint16)
    ]

# typedef struct __attribute__((packed,aligned(sizeof(old_value_and_match_info)))) {
#     void *first_byte_in_child;
#     size_t number_of_bytes;
#     old_value_and_match_info data[0];
# } matches_and_old_values_swath;
class MatchSwath(Structure):
    _fields_ = [
        ("first_byte_in_child", c_void_p),
        ("number_of_bytes", c_size_t),
        ("data", MatchInfo * 0)
    ]
    

# typedef struct {
#     size_t bytes_allocated;
#     size_t max_needed_bytes;
#     matches_and_old_values_swath swaths[0];
# } matches_and_old_values_array;
class MatchArray(Structure):
    _fields_ = [
        ("bytes_allocated", c_size_t),
        ("max_needed_bytes", c_size_t),
        ("swaths", MatchSwath * 0)
    ]

''' scanmem.h: globals_t::options '''
class GlobalOptions(Structure):
    _fields_ = [
            ("alignment",           c_uint16),
            ("debug",               c_uint16),
            ("backend",             c_uint16),
            ("scan_data_type",      c_scan_data_type_t), 
            ("region_scan_level",   c_region_scan_level_t),
            ("dump_with_ascii",     c_uint16),
            ("reverse_endianness",  c_uint16),
            ("no_ptrace",           c_uint16)
    ]

''' scanmem.h: globals_t '''
class Globals(Structure):
    _fields_ = [
            ("exit",            c_uint32, 1),
            ("target",          c_pid_t),
            ("matches",         c_void_p), # matches_and_old_values_array*
            ("num_matches",     c_uint64),
            ("scan_progress",   c_double),
            ("stop_flag",       c_bool),
            ("regions",         c_list_t_ptr),
            ("commands",        c_list_t_ptr), 
            ("current_cmdline", c_char_p),
            ("printversion",    c_void_p), # void (*printversion)(FILE *outfd);
            ("options",         GlobalOptions)
    ]

backend.sm_init.argtypes            = []
backend.sm_cleanup.argtypes         = []
backend.sm_set_backend.argtypes     = []
backend.sm_get_num_matches.argtypes     = []
backend.sm_get_scan_progress.argtypes      = []
backend.sm_backend_exec_cmd.argtypes= [c_char_p]
backend.sm_set_stop_flag.argtypes       = [c_bool]
# backend.sm_detach.argtypes              = [c_pid_t]
backend.sm_setaddr.argtypes             = [c_pid_t, c_void_p, POINTER(SetValue)]
backend.sm_checkmatches.argtypes        = [POINTER(Globals), c_scan_match_type, POINTER(UserValue)]
backend.sm_searchregions.argtypes       = [POINTER(Globals), c_scan_match_type, POINTER(UserValue)]
backend.sm_peekdata.argtypes            = [c_void_p, c_uint16, POINTER(POINTER(Mem64)), c_size_t]
backend.sm_attach.argtypes              = [c_pid_t]
backend.sm_read_array.argtypes          = [c_pid_t, c_void_p, c_void_p, c_size_t]
backend.sm_write_array.argtypes         = [c_pid_t, c_void_p, c_void_p, c_size_t]
backend.sm_readmaps.argtypes            = [c_pid_t, c_list_t_ptr, c_region_scan_level_t]
# backend.sm_reset.argtypes               = [POINTER(Globals)]

backend.sm_init.restype             = c_bool
backend.sm_backend_exec_cmd.restype = c_bool
backend.sm_get_num_matches.restype      = c_ulong
backend.sm_get_version.restype          = c_char_p
backend.sm_get_scan_progress.restype    = c_double
backend.sm_detach.restype               = c_bool 
backend.sm_setaddr.restype              = c_bool 
backend.sm_checkmatches.restype         = c_bool 
backend.sm_searchregions.restype        = c_bool 
backend.sm_peekdata.restype             = c_bool 
backend.sm_attach.restype               = c_bool 
backend.sm_read_array.restype           = c_bool 
backend.sm_write_array.restype          = c_bool 
backend.sm_readmaps.restype             = c_bool
# backend.sm_reset.restype                = c_bool


class Scanmem():
    def __init__(self):
        self.globals = Globals.in_dll(backend, "sm_globals")
        self.globals.options.debug = 1
        self.globals_ptr = pointer(self.globals)
        self.are_commands_initialized = False
        print(self.globals)

    def __del__(self):
        if self.are_commands_initialized:
            self.cleanup()

    def get_global_vars(self):
            return Globals.in_dll(backend, "sm_globals")

    ''' commands.h '''
    ''' bool sm_backend_exec_cmd(globals_t *vars, const char *commandline); '''
    def exec_command(self, strCmd):
        '''
            python strings are wchars, sm expects byte wide ascii.
            therefore, we've got to recreate the string
        '''
        backend.sm_execcommand(self.globals_ptr, strCmd.encode('ascii'))

    ''' scanmem.h '''
    ''' bool sm_init(globals_t *vars); '''
    def init(self):
        if self.are_commands_initialized: return False
        print("Initialising.")
        return backend.sm_init()

    ''' void sm_cleanup(globals_t *vars); '''
    def cleanup(self):
        if not self.are_commands_initialized: return False
        return backend.sm_cleanup()

    ''' unsigned long sm_get_num_matches(globals_t *vars); '''
    def get_num_matches(self):
        return backend.sm_get_num_matches()

    ''' const char *sm_get_version(void); '''
    def get_version(self):
        return c_char_p(backend.sm_get_version()).value

    ''' double sm_get_scan_progress(globals_t *vars); '''
    def get_scan_progress(self):
        return backend.sm_get_scan_progress()

    ''' void sm_set_stop_flag(globals_t *vars, bool stop_flag); '''
    def set_stop_flag(self, boolState):
        backend.sm_set_stop_flag(boolState)

    ''' void sm_set_backend(void); '''
    def set_backend(self):
        backend.sm_set_backend()

    def reset(self):
        self.exec_command("reset")

# TODO ptrace.c
# bool sm_detach(pid_t target);
    # def detach(self, pidTarget):
    #     return backend.sm_detach(pidTarget)

# bool sm_setaddr(pid_t target, void *addr, const value_t *to);
    def set_address(self, pidTarget, ptrAddress, userValue):
        return backend.sm_setaddr(pidTarget, ptrAddress, pointer(userValue))

    def set_address_ptr(self, pidTarget, ptrAddress, ptrUserValue):
        return backend.sm_setaddr(pidTarget, ptrAddress, ptrUserValue)

# bool sm_checkmatches(globals_t *vars, scan_match_type_t match_type, const uservalue_t *uservalue);
    def check_matches(self, matchType, userValue):
        return backend.sm_checkmatches(self.globals_ptr, matchType, pointer(userValue))

    def check_matches_ptr(self, matchType, ptrUserValue):
        return backend.sm_checkmatches(self.globals_ptr, matchType, ptrUserValue)

# bool sm_searchregions(globals_t *vars, scan_match_type_t match_type, const uservalue_t *uservalue);
    def search_regions(self, matchType: ScanMatchType, userValue):
        return backend.sm_searchregions(self.globals_ptr, matchType, pointer(userValue))

    def search_regions_ptr(self, matchType, ptrUserValue):
        return backend.sm_searchregions(self.globals_ptr, matchType, ptrUserValue)

# bool sm_peekdata(const void *addr, uint16_t length, const mem64_t **result_ptr, size_t *memlength);
    def peek_data(self, ptrAddress, length, ptrResultArray, ptrMemLength):
        return backend.sm_peekdata(ptrAddress, length, ptrResultArray, ptrMemLength)

# bool sm_attach(pid_t target);
    def attach(self, pidTarget):
        return backend.sm_attach(pidTarget)

# bool sm_read_array(pid_t target, const void *addr, void *buf, size_t len);
    def read_array(self, pidTarget, ptrAddress, ptrBuffer, length):
        return backend.sm_read_array(pidTarget, ptrAddress, ptrBuffer, length)

# bool sm_write_array(pid_t target, void *addr, const void *data, size_t len);
    def write_array(self, pidTarget, ptrAddress, ptrData, length):
        return backend.sm_read_array(pidTarget, ptrAddress, ptrData, length)


# typedef struct {
#     uint8_t old_value;
#     match_flags match_info;
# } old_value_and_match_info;

# /* Array that contains a consecutive (in memory) sequence of matches (= swath).
#    - the first_byte_in_child pointer refers to locations in the child,
#      it cannot be followed except using ptrace()
#    - the number_of_bytes refers to the number of bytes in the child
#      process's memory that are covered, not the number of bytes the struct
#      takes up. It's the length of data. */
# typedef struct __attribute__((packed,aligned(sizeof(old_value_and_match_info)))) {
#     void *first_byte_in_child;
#     size_t number_of_bytes;
#     old_value_and_match_info data[0];
# } matches_and_old_values_swath;

# /* Master matches array, smartly resized, contains swaths.
#    Both `bytes` values refer to real struct bytes this time. */
# typedef struct {
#     size_t bytes_allocated;
#     size_t max_needed_bytes;
#     matches_and_old_values_swath swaths[0];
# } matches_and_old_values_array;

    def get_matches(self):
        num_matches = self.get_num_matches()
        matches = []
        current_address = self.globals.matches
        bytes_allocated = c_size_t.from_address(current_address)
        current_address += sizeof(bytes_allocated)
        max_needed_bytes = c_size_t.from_address(current_address)
        current_address += sizeof(max_needed_bytes)
        for i in range(0, num_matches):
            first_byte_in_child = c_void_p.from_address(current_address)
            current_address += sizeof(first_byte_in_child)
            number_of_bytes = c_size_t.from_address(current_address)

            print("first_byte_in_child: %s" % first_byte_in_child)
            print("number_of_bytes: %s" % number_of_bytes)

            if number_of_bytes.value > 64:
                continue

            current_address += sizeof(number_of_bytes)

            variable_bytes = []

            for j in range(0, number_of_bytes.value):
                old_value = c_uint8.from_address(current_address)

                current_address += sizeof(old_value)
                match_info = c_uint16.from_address(current_address)
                current_address += sizeof(match_info)

                variable_bytes.append(old_value.value)

                extra_byte = c_uint8.from_address(current_address)
                current_address += sizeof(extra_byte)

            # Turn bytes into singular integer
            variable_int = int.from_bytes(bytearray(variable_bytes), byteorder='little')

            matches.append({
                "address": hex(first_byte_in_child.value),
                "first_byte_in_child": first_byte_in_child.value,
                "value": variable_int,
                "match_info": match_info.value,
                "number_of_bytes": number_of_bytes.value,
                "variable_bytes": variable_bytes
            })

        return matches



# # bool sm_reset(globals_t* vars);
#     def reset(self):
#         return backend.sm_reset(self.globals_ptr)

INT8_MIN = -128
INT16_MIN = -32767-1
INT32_MIN = -2147483647-1
INT64_MIN = -9223372036854775807-1

INT8_MAX = 127
INT16_MAX = 32767
INT32_MAX = 2147483647
INT64_MAX = 9223372036854775807

UINT8_MAX = 255
UINT16_MAX = 65535
UINT32_MAX = 4294967295
UINT64_MAX = 18446744073709551615


def parse_uservalue(input):
    val = UserValue()
    if parse_uservalue_int(input, val):
        print("Parsed as int %s", val)
        return val
    if parse_uservalue_float(input, val):
        print("Parsed as float %s", val)
        return val
    return None

def parse_uservalue_int(input, val):
    snum = None
    valid_sint = False
    unum = None
    valid_uint = False
    try:
        snum = int(input)
        valid_sint = True
    except ValueError:
        pass
    try:
        unum = int(input, 0)
        valid_uint = True
    except ValueError:
        pass
    if not valid_sint and not valid_uint:
        return False

    if valid_uint and unum <= UINT8_MAX:
        val.flags |= MatchFlag.FLAG_U8B
        val.uint8_value = unum
    if valid_sint and snum >= INT8_MIN and snum <= INT8_MAX:
        val.flags |= MatchFlag.FLAG_S8B
        val.int8_value = snum
    if valid_uint and unum <= UINT16_MAX:
        val.flags |= MatchFlag.FLAG_U16B
        val.uint16_value = unum
    if valid_sint and snum >= INT16_MIN and snum <= INT16_MAX:
        val.flags |= MatchFlag.FLAG_S16B
        val.int16_value = snum
    if valid_uint and unum <= UINT32_MAX:
        val.flags |= MatchFlag.FLAG_U32B
        val.uint32_value = unum
    if valid_sint and snum >= INT32_MIN and snum <= INT32_MAX:
        val.flags |= MatchFlag.FLAG_S32B
        val.int32_value = snum
    if valid_uint and unum <= UINT64_MAX:
        val.flags |= MatchFlag.FLAG_U64B
        val.uint64_value = unum
    if valid_sint and snum >= INT64_MIN and snum <= INT64_MAX:
        val.flags |= MatchFlag.FLAG_S64B
        val.int64_value = snum
    return True
  
def parse_uservalue_float(input, val):
    try:
        num = float(input)
    except ValueError:
        return False
    val.flags |= MatchFlag.FLAG_FLOAT
    val.float32_value = num
    val.float64_value = num
    return True

class Plugin:
    #Method to return list of process names and PIDs on the system.
    async def get_processes(self):
        print("Getting processes")

        process_list = []

        # Get a list of processes using ps for the current user, we need the PID and the untruncated process name.
        ps = subprocess.Popen(["ps", "-u", "1000", "-o", "pid,command"], stdout=subprocess.PIPE)

        output = subprocess.check_output(('grep', '-v', 'grep'), stdin=ps.stdout)
        ps.wait()
        
        # Blacklist some processes
        blacklist = ["ps ", "systemd", "reaper ", "pressure-vessel", "proton ", "power-button-handler", "ibus", "xbindkeys", "COMMAND", "wineserver", "system32", "socat", "sd-pam", "gamemoded", "sdgyrodsu", "dbus-daemon", "kwalletd5", "gamescope-session", "gamescope", "PluginLoader", "pipewire", "Xwayland", "wireplumber", "ibus-daemon", "sshd", "mangoapp", "steamwebhelper", "steam ", "xdg-desktop-portal", "xdg-document-portal", "xdg-permission-store", "bash"]

        # Parse output
        for line in output.splitlines():
            pid, name = line.decode().split(None, 1)

            # If the name doesn't contain any string from the blacklist, append it
            if not any(x in name for x in blacklist):
                process_list.append({"pid": pid, "name": name})

        # Remove blacklisted processes#
        for process in process_list:
            for blacklist_item in blacklist:
                #Check if blacklist item is contained in the process name
                if blacklist_item in process["name"]:
                    process_list.remove(process)
        
        return process_list

    # Asyncio-compatible long-running code, executed in a task when the plugin is loaded
    async def _main(self):
        print("Hello World!")

        self.scanmem = Scanmem()

        self.scanmem.init()
        self.scanmem.set_backend()

        pass

    async def get_num_matches(self):
        return self.scanmem.get_num_matches()

    async def get_scan_progress(self):
        return self.scanmem.get_scan_progress()

    async def get_match_list(self):
        matches = self.scanmem.get_matches()

        return matches

    async def get_attached_process(self):
        # If self.pid and self.process_name exist
        if hasattr(self, 'pid') and hasattr(self, 'process_name'):
            pid = self.pid
            name = self.process_name
        # If they don't exist, return None
        else:
            return None

        return {"pid": pid, "name": name}

    async def reset_scanmem(self):
        self.scanmem.reset()

        pass


    # Method to attach to a process
    async def attach(self, pid, name):
        print("Attaching to process %s", pid)
        self.pid = int(pid)
        self.process_name = name

        self.scanmem.globals.target = self.pid

        # self.scanmem.attach(self.pid)
        self.scanmem.reset()

        pass

    async def search_regions(self, match_type, value):
        print("Searching for %s %s", match_type, value)

        val = parse_uservalue(value)

        if val is None:
            print("Invalid value!")
            return False

        # print(self.scanmem.globals.matches)

        print ("Valid value!")

        if self.scanmem.globals.matches is None:
            print("No matches, scanning all regions")
            self.scanmem.search_regions(match_type, val)
        else:
            print("Matches found, scanning only those regions")
            self.scanmem.check_matches(match_type, val)

        print("Finding matches")
        matches = self.scanmem.get_num_matches()

        return matches

    
    async def search(self, operator, value):
        return self.scanmem.exec_command(operator + " " + value)

    async def set_value(self, address, value):
        # return self.scanmem.set_address(self.pid, address, value)
        return self.scanmem.exec_command("set " + address + " " + value)

# async def main():
#     # This is only executed when the plugin is run directly
#     # Create an instance of the plugin
#     plugin = Plugin()

#     await plugin._main()

#     print(await plugin.get_processes())
    
#     # Read PID from stdin
#     print("Enter PID: ")
#     pid = int(input('> '))

#     await plugin.attach(pid, "Test")

#     matches = -1;

#     # Until matches is exactly 1, request a new value
#     while matches != 1:
#         # Get the new value
#         newValue = input("> ")

#         if newValue == "exit":
#             return
        
#         if newValue == "reset":
#             plugin.scanmem.reset()
#             continue
 
#         if newValue == "list":
#             plugin.scanmem.exec_command("list")
#             continue

#         # If newValue starts with 'pid ' then we need to attach to a new process
#         if newValue.startswith("pid "):
#             pid = int(newValue.split(" ")[1])
#             await plugin.attach(pid)
#             continue


#         # await plugin.search_regions(ScanMatchType.MATCH_EQUAL_TO, newValue)
#         plugin.scanmem.exec_command("= " + newValue)


#         matches = await plugin.get_num_matches()

#         if matches < 50:
#             print(await plugin.get_match_list())

#         print("Finished")





# if __name__ == "__main__":
#     asyncio.run(main())