import os
import re
import sys


class OSInfo:
    def __init__(self):
        os_types = [
            {'name': 'windows', 'sysname': 'win32'},
            {'name': 'macos', 'sysname': 'darwin'},
            {'name': 'linux', 'sysname': 'linux'},
        ]

        for os_type in os_types:
            if os_type['sysname'] == sys.platform:
                self.operating_system = os_type['name']
                self.operating_sysname = os_type['sysname']

        self.environment_terminal = os.environ.get('TERM')

    def display_info(self):
        xterm_pattern = re.compile('xterm.*')

        if self.operating_system == 'linux':
            if self.environment_terminal is None:
                is_xterm = False
                return is_xterm
            try:
                is_xterm = bool(xterm_pattern.match(self.environment_terminal))
            except ValueError:
                is_xterm = False
        else:
            is_xterm = False
        return is_xterm

    def which_os(self):
        return self.operating_system

    def which_os_type(self):
        return self.operating_sysname


    def which_term(self):
        return self.environment_terminal

