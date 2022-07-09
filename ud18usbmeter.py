#!/usr/bin/env python3

"""
this code will use BLE to connect to a UD18 USB power meter, and obtain data from it
"""

import asyncio
import datetime

# requires Bleak
# https://bleak.readthedocs.io/en/latest/
# https://github.com/hbldh/bleak
from bleak import BleakScanner, BleakClient

# this class can be imported into another script if you wish
class UD18UsbMeter:
    # the device name and UUID were found using a BLE scanning utility
    # use the callback parameter to register a callback function, useful for logging and such
    def __init__(self, dev_name="UD18_BLE", dev_mac_addr=None, data_char_uuid="0000ffe1-0000-1000-8000-00805f9b34fb", callback=None):
        self.dev_name = dev_name
        self.data_char_uuid = data_char_uuid
        self.dev_mac_addr = dev_mac_addr # optional, should be a string like "27:4B:B0:47:69:84"
        self.callback = callback
        self.device = None
        self.client = None

    async def find_device(self):
        devices = await BleakScanner.discover()
        for d in devices:
            if d.name == self.dev_name: # name match comparison is the only way to automatically find the USB meter
                self.device = d
                return self.device
            if self.dev_mac_addr is not None and self.device.address.lower() == self.dev_mac_addr.lower(): # user is allowed to specify a MAC address manually
                self.device = d
                return self.device
        return None

    async def connect(self, keep_trying=True):
        # look for the device
        while self.device is None:
            await self.find_device()
            if self.device is not None:
                print("device \"%s\" found, MAC-addr: %s" % (self.device.name, self.device.address))
                break
            else:
                print("device not found", end="")
                if keep_trying:
                    print(", retrying...")
                else:
                    return False
        # device found
        self.client = BleakClient(self.device.address)
        res = await self.client.connect()
        if res: # if connection successful
            print("connected")
            # register the notification callback function
            await self.client.start_notify(self.data_char_uuid.lower(), self.handle_data)
            print("notifications started")
            # note: expect a notification once per second
            return True
        else:
            return False

    async def handle_data(self, ender: int, data: bytearray):
        if self.callback is None:
            # if no function to call, then just print the raw data in hex format
            s = ""
            for d in data:
                s += "%02X " % d
            print("data: %s" % s.strip())
        else:
            if len(data) == 36:
                # parse the packet into human readable format
                v   = float(int( (data[ 5] <<  8) + data[6] )) / 100.0
                a   = float(int( (data[ 8] <<  8) + data[9] )) / 100.0
                mah =       int( (data[10] << 16) + (data[11] << 8) + data[12] )
                wh  = float(int( (data[13] << 24) + (data[14] << 16) + (data[15] << 8) + data[16] )) / 100.0
                self.callback(v, a, mah, wh)
            else:
                # a firmware bug on the UD18, I think it's sending AT commands but it's showing up here as ASCII bytes
                pass

def log_data(voltage: float, amperage: float, milliamphour: int, watthour: float):
    s = "%s,\t%0.2f,\t%0.2f,\t%0.1f,\t%0.2f" % (datetime.datetime.now().strftime("%H:%M:%S.%f"), voltage, amperage, milliamphour, watthour)
    print(s)

async def demo_raw_dump():
    meter = UD18UsbMeter(callback=None)
    while await meter.connect() == False:
        pass
    while True:
        await asyncio.sleep(1)

async def demo_show_data():
    meter = UD18UsbMeter(callback=log_data)
    while await meter.connect() == False:
        pass
    while True:
        await asyncio.sleep(1)

def main():
    asyncio.run(demo_show_data())

if __name__ == "__main__":
    main()
