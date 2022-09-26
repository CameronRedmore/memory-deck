import os
import sys
import subprocess

from scanmem import Scanmem, parse_uservalue

# Little hack to allow importing of files after Decky has loaded the plugin.
sys.path.append(os.path.dirname(__file__))


class Plugin:
    # Method to return list of process names and PIDs on the system.
    async def get_processes(self):
        print("Getting processes")

        process_list = []

        # Get a list of processes using ps for the current user, we need the PID and the untruncated process name.
        ps = subprocess.Popen(
            ["ps", "-u", "1000", "-o", "pid,command"], stdout=subprocess.PIPE)

        output = subprocess.check_output(
            ('grep', '-v', 'grep'), stdin=ps.stdout)
        ps.wait()

        # Blacklist some processes
        blacklist = ["ps ", "systemd", "reaper ", "pressure-vessel", "proton ", "power-button-handler", "ibus", "xbindkeys", "COMMAND", "wineserver", "system32", "socat", "sd-pam", "gamemoded", "sdgyrodsu", "dbus-daemon", "kwalletd5",
                     "gamescope-session", "gamescope", "PluginLoader", "pipewire", "Xwayland", "wireplumber", "ibus-daemon", "sshd", "mangoapp", "steamwebhelper", "steam ", "xdg-desktop-portal", "xdg-document-portal", "xdg-permission-store", "bash"]

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
        print("Attaching to process ", pid)
        self.pid = int(pid)
        self.process_name = name

        self.scanmem.globals.target = self.pid

        # self.scanmem.attach(self.pid)
        self.scanmem.reset()

        pass

    async def search_regions(self, match_type, value):
        print("Searching for ", match_type, value)

        val = parse_uservalue(value)

        if val is None:
            print("Invalid value!")
            return False

        # print(self.scanmem.globals.matches)

        print("Valid value!")

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
