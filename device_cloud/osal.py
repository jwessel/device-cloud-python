'''
    Copyright (c) 2016-2017 Wind River Systems, Inc.
    
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at:
    http://www.apache.org/licenses/LICENSE-2.0
    
    Unless required by applicable law or agreed to in writing, software  distributed
    under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
    OR CONDITIONS OF ANY KIND, either express or implied.
'''

"""
Operating System Abstraction Layer (OSAL). This module provides abstractions of
functions that are different on different operating systems.
"""

import os
import platform
import subprocess
import sys

# Constants
NOT_SUPPORTED = -20
EXECUTION_FAILURE = -21
BAD_PARAMETER = -22

# Setup platform info statics
WIN32 = sys.platform.startswith('win32')
LINUX = sys.platform.startswith('linux')
MACOS = sys.platform.startswith('darwin')
POSIX = LINUX or MACOS
OTHER = not POSIX and not WIN32

# Define Functions
def execl(*args):
    """
    Replaces the current process with a new instance of the specified
    executable. This function will only return if there is an issue starting the
    new instance, in which case it will return false. Otherwise, it will not
    return.
    """
    retval = EXECUTION_FAILURE

    if POSIX:
        os.execvp(args[0], args)
    elif WIN32:
        os.execvp(sys.executable, args)
    else:
        retval = NOT_SUPPORTED

    return retval

def os_kernel():
    """
    Get the operating system's kernel version
    """
    ker = "Unknown"
    if LINUX:
        ker = platform.release()
    elif WIN32 or MACOS:
        ker = platform.version()
    return ker

def os_name():
    """
    Get the operating system name
    """
    name = "Unknown"
    if LINUX:
        distro = platform.linux_distribution()
        plat = subprocess.check_output(["uname", "-o"])[:-1].decode()
        name = "{} ({})".format(distro[0], plat)
    elif WIN32:
        name = platform.system()
    elif MACOS:
        name = "macOS"
    return name

def os_version():
    """
    Get the operating system version
    """
    ver = "Unknown"
    if LINUX:
        distro = platform.linux_distribution()
        ver = "{}-{}".format(distro[1], distro[2])
    elif WIN32:
        ver = platform.release()
    elif MACOS:
        ver = platform.mac_ver()[0]
    return ver

def system_reboot(delay=0, force=True):
    """
    Reboot the system.
    """
    return system_shutdown(delay=delay, reboot=True, force=force)

def system_shutdown(delay=0, reboot=False, force=True):
    """
    Run the system shutdown command. Can be used to reboot the system.
    """
    if POSIX:
        command = "sudo /sbin/shutdown "
        command += "-r " if reboot else "-h "
        command += "now " if delay == 0 else "+{} ".format(delay)
    elif WIN32:
        command = "shutdown "
        command += "/r " if reboot else "/s "
        command += "/t {} ".format(delay*60)
        command += "/f" if force else ""
    else:
        return NOT_SUPPORTED

    return os.system(command)
