#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def send_bdpu_every_sec():
    while True:
        # TODO Send BDPU every second if necessary
        time.sleep(1)

def is_unicast(mac):
    if mac == "ff:ff:ff:ff:ff:ff":
        return False
    else:
        return True

def add_vlan_tag(Frame, vlan_id):
    return Frame[0:12] + create_vlan_tag(vlan_id) + Frame[12:]

def remove_vlan_tag(Frame):
    return Frame[0:12] + Frame[16:]

def has_vlan_tag(vlan_id):
    if vlan_id == -1:
        return False
    else:
        return True

def get_vlan_from_interface(Filename):
    vlans = {}
    # open file from config directory
    with open("configs/" + Filename, "r") as f:
        lines = f.readlines()
        for line in lines:
            if line[:2] == "r-":
                vlans[line[:3]] = int(line[4])
            elif line[:2] == "rr":
                vlans[line[:6]] = -1
    return vlans

def get_interface_type(interface):
    interface_name = get_interface_name(interface)
    if interface_name[:2] == "rr":
        return "trunk"
    elif interface_name[:2] == "r-":
        return "access"
    

def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]
    mac_table = {}
    vlan_table = {}
    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)
    # Array with the vlan of each host
    vlan_of_interface = get_vlan_from_interface("switch" + switch_id + ".cfg")

    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))

    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec)
    t.start()

    # Printing interface names
    for i in interfaces:
        print(get_interface_name(i))

    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()
        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)
        vlan_id = int(vlan_id)
        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)
        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')

        print("Received frame of size {} on interface {}".format(length, interface), flush=True)
    

        mac_table[src_mac] = interface

        if get_interface_type(interface) == "access":
            vlan_table[src_mac] = int(vlan_of_interface[get_interface_name(interface)])
        elif get_interface_type(interface) == "trunk":   
            vlan_table[src_mac] = int(vlan_id)
            vlan_of_interface[get_interface_name(interface)] = vlan_table[src_mac]
        
        if has_vlan_tag(vlan_id):
            data = remove_vlan_tag(data)
            length = length - 4


        if is_unicast(dest_mac):
            if dest_mac in mac_table:
                if get_interface_type(mac_table[dest_mac]) == "trunk":
                    if not has_vlan_tag(vlan_id):
                        vlan_id = vlan_table[src_mac]
                        data = add_vlan_tag(data, vlan_id)

                if get_interface_type(mac_table[dest_mac]) == "access":
                    send_to_link(mac_table[dest_mac], data, length)
                elif get_interface_type(mac_table[dest_mac]) == "trunk":
                    send_to_link(mac_table[dest_mac], data, length + 4)
            else:
                for i in interfaces:
                    if i != interface:
                        if get_interface_type(i) == "access":
                            if int(vlan_of_interface[get_interface_name(i)]) == int(vlan_of_interface[get_interface_name(interface)]):
                                send_to_link(i, data, length)
                        elif get_interface_type(i) == "trunk":
                            if not has_vlan_tag(vlan_id):
                                vlan_id = vlan_table[src_mac]
                                data = add_vlan_tag(data, vlan_id)
                            send_to_link(i, data, length + 4)
        else:
            for i in interfaces:
                if i != interface:                        
                    if get_interface_type(i) == "access":
                        if int(vlan_of_interface[get_interface_name(i)]) == int(vlan_of_interface[get_interface_name(interface)]):
                            send_to_link(i, data, length)
                    elif get_interface_type(i) == "trunk":
                        if not has_vlan_tag(vlan_id):
                            vlan_id = vlan_table[src_mac]
                            data = add_vlan_tag(data, vlan_id)
                        send_to_link(i, data, length + 4)


        # data is of type bytes.
        # send_to_link(i, data, length)

if __name__ == "__main__":
    main()
