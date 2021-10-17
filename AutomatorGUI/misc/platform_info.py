import wmi


def is_laptop() -> bool:
    # If the device has a battery, it's pretty certainly a laptop
    batteries = wmi.WMI().Win32_Battery()
    if len(batteries):
        return True

    ram_sticks = wmi.WMI().Win32_PhysicalMemory()
    for stick in ram_sticks:
        # If we have DIMM RAM, we're most likely not a laptop
        if stick.FormFactor == 8:
            return False
        # And if we have SODIMM RAM, we're most likely a laptop
        if stick.FormFactor == 12:
            return True

    if wmi.WMI().Win32_ComputerSystem()[0].PCSystemType == 2:
        return True

    return False
