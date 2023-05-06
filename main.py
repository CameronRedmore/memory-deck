import os
import sys
import subprocess
import logging
# Little hack to allow importing of files after Decky has loaded the plugin.
sys.path.append(os.path.dirname(__file__))

from scanmem import Scanmem, parse_uservalue, UserValue, MatchFlag, ScanMatchType, ScanDataType
from threading import Thread
from ctypes import *

# initiate list that will store values we want to freeze
freeze_subprocess_list = []

class Plugin:
    search_type = "auto"

    # Method to return list of process names and PIDs on the system.
    async def get_processes(self):
        logging.info("Getting processes")

        process_list = []

        # Get a list of processes using ps for the current user, we need the PID and the untruncated process name.
        ps = subprocess.Popen(
            ["ps", "-u", "1000", "-o", "pid,command"], stdout=subprocess.PIPE)

        output = subprocess.check_output(
            ('grep', '-v', 'grep'), stdin=ps.stdout)
        ps.wait()

        # Blacklist some processes
        blacklist = ["ps ", "systemd", "reaper ", "pressure-vessel", "proton ", "power-button-handler", "ibus", "xbindkeys", "COMMAND", "wineserver", "system32", "socat", "sd-pam", "gamemoded", 
        "sdgyrodsu", "dbus-daemon", "kwalletd5", "gamescope-session", "gamescope", "PluginLoader", "pipewire", "Xwayland", "wireplumber", "ibus-daemon", "sshd", "mangoapp", "steamwebhelper", "steam ", 
        "xdg-desktop-portal", "xdg-document-portal", "xdg-permission-store", "bash", "steamos-devkit-service", "dconf-service", "CrashHandler", "ControllerTools"]

        # Parse output
        for line in output.splitlines():
            pid, name = line.decode().split(None, 1)

            # If the name doesn't contain any string from the blacklist, append it
            if not any(x in name for x in blacklist):
                process_list.append({"pid": pid, "name": name})

        # Remove blacklisted processes#
        for process in process_list:
            for blacklist_item in blacklist:
                # Check if blacklist item is contained in the process name
                if blacklist_item in process["name"]:
                    process_list.remove(process)

        return process_list

    # Asyncio-compatible long-running code, executed in a task when the plugin is loaded
    async def _main(self):
        logging.basicConfig(filename='/tmp/memory-deck.log', 
                            level= logging.DEBUG,
                            filemode='a', 
                            format='%(name)s - %(levelname)s - %(message)s')
        logging.info('Start New session')

        self.scanmem = Scanmem()
        self.scanmem.init()
        self.scanmem.set_backend()

        pass

    async def get_num_matches(self):
        return self.scanmem.get_num_matches()

    async def get_scan_progress(self):
        return self.scanmem.get_scan_progress()

    async def get_match_list(self):
        return self.scanmem.exec_command("list")
    
    async def get_matches(self):
        return self.scanmem.get_matches()

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
        # freeze_subprocess_list = []

        pass

    # Method to attach to a process
    async def attach(self, pid, name):
        logging.info("Attaching to process ", pid)
        self.pid = int(pid)
        self.process_name = name

        self.scanmem.globals.target = self.pid

        # self.scanmem.attach(self.pid)
        self.scanmem.reset()

        pass

    async def search_regions(self, match_type, searchValue, searchValueType):
        if searchValueType == "auto":
            val = parse_uservalue(searchValue)

            if val is None:
                logging.error("Unable to parse value [auto]: " + searchValue)
                return False
        else:
            val = UserValue()

            snum = None
            valid_sint = False
            unum = None
            valid_uint = False
            try:
                snum = int(searchValue)
                valid_sint = True
            except Exception:
                pass
            try:
                unum = int(searchValue, 0)
                valid_uint = True
            except Exception:
                pass
            if not valid_sint and not valid_uint:
                logging.error("Unable to parse value [Int]: " + searchValue)
                return False

            match searchValueType:
                case "c_int8":
                    val.flags |= MatchFlag.FLAG_S8B
                    val.int8_value = int(searchValue)
                case "c_uint8":
                    val.flags |= MatchFlag.FLAG_U8B
                    val.uint8_value = int(searchValue, 0)
                case "c_int16":
                    val.flags |= MatchFlag.FLAG_S16B
                    val.int16_value = int(searchValue)
                case "c_uint16":
                    val.flags |= MatchFlag.FLAG_U16B
                    val.uint16_value = int(searchValue, 0)
                case "c_int32":
                    val.flags |= MatchFlag.FLAG_S32B
                    val.int32_value = int(searchValue)
                case "c_uint32":
                    val.flags |= MatchFlag.FLAG_U32B
                    val.uint32_value = int(searchValue, 0)
                case "c_int64":
                    val.flags |= MatchFlag.FLAG_S64B
                    val.int64_value = int(searchValue)
                case "c_uint64":
                    val.flags |= MatchFlag.FLAG_U64B
                    val.uint64_value = int(searchValue, 0)
                case "c_float":
                    val.flags |= MatchFlag.FLAG_F32B
                    val.float32_value = float(searchValue)
                case "c_double":
                    val.flags |= MatchFlag.FLAG_F64B
                    val.float64_value = float(searchValue)
                case _:
                    logging.error("Unable to apply flags to value: " + searchValue)
                    return False
                
        if val.flags & MatchFlag.FLAG_F32B or val.flags & MatchFlag.FLAG_F64B:
            self.scanmem.globals.options.scan_data_type = ScanDataType.ANYFLOAT
        else:
            self.scanmem.globals.options.scan_data_type = ScanDataType.ANYINTEGER
        
        

        logging.info("Valid value: " + searchValue + ", type: " + searchValueType)

        if self.scanmem.globals.matches is None:
            logging.info("No matches, scanning all regions")
            self.scanmem.search_regions(match_type, val)
        else:
            logging.info("Matches found, scanning only those regions")
            self.scanmem.check_matches(match_type, val)

        print("Finding matches")
        return self.scanmem.get_num_matches()

    async def search(self, operator, value):
        return self.scanmem.exec_command(operator + " " + value)

    async def set_value(self, address, match_index, value):
        if match_index != 999:
            logging.info('setting memory address ' + str(address) + ' with index of ' + str(match_index) + ' to ' + str(value))
            return self.scanmem.exec_command("set " + str(match_index) + "=" + value)
        else:
            
            logging.info('setting all matched memory addresses to ' + str(value) + ' because index ' + str(match_index) + ' was received.')
            return self.scanmem.exec_command("set " + value)
        

    async def freeze(self, address, value):
        #TODO add ability to freeze new values. Probably create subprocess that continuously sets value. Or use the "set" scanmem command with args to keep setting it.
        pass

async def main():
    # This is only executed when the plugin is run directly
    print("Slimmed down version of memory-deck for cli testing purposes")

    # Create an instance of the plugin
    plugin = Plugin()
    await plugin._main()
    pids = await plugin.get_processes()

    for pid in pids: print(pid)

    # Read PID from stdin
    print("Enter PID: ")
    selected_pid = int(input('> '))

    await plugin.attach(selected_pid, "Test")
    print("PID " + str(selected_pid) + " selected.")

    def help():
        print("########################################################################################################")
        print("Enter value to search for within PID, or enter one of the following commands: ")
        print("help")
        print("     prints this help menu")
        print("")
        print("type <ctype>")
        print("     example: type c_double")
        print("")
        print("setNewValue <newValue> [OPTIONAL* <memoryAddress>]")
        print("     Set a new value for a given memory address. If no memory address is provided, update all matches")
        print("")
        print("pid <newPID>")
        print("     attach to new PID")
        print("")
        print("list")
        print("     prints current matches")
        print("")
        print("set <arguments>")
        print("     set specific index to value")
        print("     example: write new value to match_index 1:")
        print("         set 1=999999")
        print("")        
        print("exit")
        print("     exits memory-deck cli")
        print("")
        print("reset")
        print("     resets current memory-deck cli progress")
        print("########################################################################################################")
        print("")

    help()

    matches = -1;

    # Until matches is exactly 1, request a new value
    while True:
        # Get the new value
        newValue = input("> ")

        if newValue == "exit":
            return

        if newValue == "reset":
            plugin.scanmem.reset()
            print("Scanmem has been reset.")
            help()
            continue

        if newValue == "list":
            # plugin.scanmem.exec_command("list")
            print(await plugin.get_match_list())
            continue

        if newValue.startswith("dump "):
            addressToDump = str(newValue.split(" ")[1])
            lengthToDump = str(newValue.split(" ")[2])
            plugin.scanmem.exec_command("dump " + addressToDump + " " + lengthToDump)
            continue

        if newValue == "help":
            help()
            continue

        if newValue.startswith("setNewValue "):
            newValueToSet = str(newValue.split(" ")[1])
            if len(newValue.split(' ')) < 3:
                print("updating all matches with new value")
                plugin.scanmem.exec_command("set " + newValueToSet)
            else:
                print('updating specified memory address with new value')
                mem_address = str(newValue.split(" ")[2])
                plugin.scanmem.exec_command("write i32 " + mem_address + " " + newValueToSet)
            print("New value set.")
            continue

        # If newValue starts with 'pid ' then we need to attach to a new process
        if newValue.startswith("pid "):
            selected_pid = int(newValue.split(" ")[1])
            await plugin.attach(selected_pid)
            help()
            continue
        
        if newValue.startswith("set "):
            print("Executing scanmem command - " + str(newValue))
            set_arguments = newValue.split("set ")[1]
            plugin.scanmem.exec_command("set " + str(set_arguments))
            continue

        if newValue.startswith("type "):
            plugin.search_type = newValue.split(" ")[1]
            print("Search type set to: "+ plugin.search_type)
            continue

        if plugin.search_type != "auto":
            matches = await plugin.search_regions(ScanMatchType.MATCH_EQUAL_TO, newValue, plugin.search_type)
        else:
            plugin.scanmem.exec_command("= " + newValue)
            matches = await plugin.get_num_matches()
            
        if matches < 50:
            matched_addresses = await plugin.get_matches()
            for matched_address in matched_addresses: print(matched_address)

        print("Finished")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
