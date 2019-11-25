import binascii
import os
import struct
import copy
from gc import collect


class Table:
    """
    Table for LZW codes
    """

    def __init__(self, size):
        self.table = [[i] for i in range(size)]
        self.clear_value = size
        self.table.append([size])
        self.end_value = size + 1
        self.table.append([size + 1])

    @micropython.native
    def add(self, value):
        """
            Add value to table if it's not exists
        :param value:
        :return:
        """
        #print("!!! Table.add - value: ", value)
        compressed_value = []
        compressed_index = 0
        for i in range(0,int(len(value) / 8)):
            offset = i * 8
            byte = (
                0x80 * value[offset] + 
                0x40 * value[offset+1] + 0x20 * value[offset+2] + 0x10 * value[offset+3] + 
                0x08 * value[offset+4] + 0x04 * value[offset+5] + 
                0x02 * value[offset+6] + value[offset+7])
            compressed_value.append(byte)
        if len(value) % 8 > 0:
            compressed_value.append(value[-(len(value) % 8):])

        #print("!!! Table.add - compressed value: ", compressed_value)

        found = False
        for i in range(self.end_value + 1, len(self.table)):
            entry = self.table[i]
            if entry == compressed_value:
                found = True
                break

        if not found:
            self.table.append(compressed_value)

    @micropython.native
    def get_value(self, index):
        if index <= self.end_value:
            return self.table[index]

        value = []
        for entry in self.table[index]:
            if isinstance(entry, int):
                value.append((entry & 0x80)>> 7)
                value.append((entry & 0x40)>> 6)
                value.append((entry & 0x20)>> 5)
                value.append((entry & 0x10)>> 4)
                value.append((entry & 0x08)>> 3)
                value.append((entry & 0x04)>> 2)
                value.append((entry & 0x02)>> 1)
                value.append((entry & 0x01))
            else:
                value = value + entry
        return value

    def get_raw_value(self, index):
        return self.table[index]

    def get_size(self):
        return len(self.table)

    def is_clear(self, value):
        return value == self.clear_value

    def is_end(self, value):
        return value == self.end_value



class Color:
    def __init__(self, r, g, b):
        #super(Color, self).__init__()
        self.r = r
        self.g = g
        self.b = b

    def rgb(self):
        return (self.r, self.g, self.b)


class Palete:
    colors = []

    def __init__(self):
        pass

    def get_size(self):
        return len(self.colors)

    def get_colors(self):
        return self.colors

    def get_color(self, index):
        return self.colors[index]

    def add_color(self, color):
        self.colors.append(color)


@micropython.native
def byte_to_bits(b):
    fstr = bin(ord(b))[2:]
    return "%s%s" % ("0" * (8 - len(fstr)), fstr)

class GiPyF:
    def __init__(self):
        # Gif standart version GIF89a or GIF87a
        self.version = None

        # Headers image width and height in pixels
        self.width = 0
        self.height = 0

        # Bool value is there global color table
        self.is_global_color_table = True

        self.color_resolution = 0

        # If True it means that colors in table sorted by quantity
        self.is_color_sorted = False

        self.table_colors_count = 0

        self.global_palete = None
        self.background = b'00'
        self.width_to_height = b'00'

        self.image_map_list = []

        self.frames_count = 0

    def parse(self, source, image_callback, gce_callback):
        """
        Prepare GiPyF object from gif's binary data
        :param source: string path to file
        :return:
        """
        stream = source
        if type(source) == str:
            stream = open(source, 'rb')

        self.version = stream.read(6).decode()
        self.width = struct.unpack('<BB', stream.read(2))[0]
        self.height = struct.unpack('<BB', stream.read(2))[0]

        header_bit_data = byte_to_bits(stream.read(1))
        self.is_global_color_table = int(header_bit_data[0]) == 1
        self.color_resolution = pow(2, int(header_bit_data[1:4], 2) + 1)
        self.is_color_sorted = int(header_bit_data[5]) == 1
        self.table_colors_count = pow(2, int(header_bit_data[5:], 2) + 1)

        self.background = binascii.hexlify(stream.read(1))
        self.width_to_height = binascii.hexlify(stream.read(1))

        self.global_palete = Palete()
        pos = 0
        palete_bytes = stream.read(self.table_colors_count * 3)
        while pos < len(palete_bytes) - 2:
            self.global_palete.add_color(Color(palete_bytes[pos], palete_bytes[pos + 1], palete_bytes[pos + 2]))
            pos += 3

        # performance for micropython - use local variable
        image_map_list = self.image_map_list

        part_marker = stream.read(1)
        while ord(part_marker) != 0x3b:  # End of blocks
            if ord(part_marker) == 0x21:  # Extension block
                extension_type = ord(stream.read(1))
                if extension_type == 0xf9:  # Graphics control extension
                    data = stream.read(struct.unpack('<B', stream.read(1))[0])
                    color_alpha_index = struct.unpack('<B', data[-1:])[0]
                    play_delay = (
                        struct.unpack('<B', data[-3:-2])[0],
                        struct.unpack('<B', data[-2:-1])[0])
                    binascii.hexlify(stream.read(1))

                    gce_callback(color_alpha_index, play_delay)
                else:
                    # Skip unsupported blocks
                    block_length = struct.unpack('<B', stream.read(1))[0]
                    while block_length != 0:
                        stream.read(block_length)
                        block_length = struct.unpack('<B', stream.read(1))[0]
            elif ord(part_marker) == 0x2c:  # Image block
                top_left_x = struct.unpack('<BB', stream.read(2))[0]
                top_left_y = struct.unpack('<BB', stream.read(2))[0]

                width = struct.unpack('<BB', stream.read(2))[0]
                height = struct.unpack('<BB', stream.read(2))[0]

                local_color_table = stream.read(1)

                lzw_length = struct.unpack('<B', stream.read(1))[0] + 1

                image = Image(width, height, lzw_length, self.global_palete, top_left_x=top_left_x,
                              top_left_y=top_left_y,
                              local_color_table=local_color_table, debug=False)

                # Collect all image binary in one
                parts = b''
                length = struct.unpack('<B', stream.read(1))[0]
                while length != 0:
                    parts += stream.read(length)
                    length = struct.unpack('<B', stream.read(1))[0]

                image.set_binary_data(parts)
                image.unpack_binary_data(image_map_list)

                self.frames_count += 1

                image_callback(self.frames_count, image)
                del image

            part_marker = stream.read(1)


class Image:
    def __init__(self, width, height, lzw_length, global_palete, top_left_x=0, top_left_y=0, local_color_table=b'00', debug=False):
        self.global_palete = global_palete
        self.local_color_table = local_color_table

        # local image top lext coordinates
        self.top_left_y = top_left_y
        self.top_left_x = top_left_x

        self.lzw_length = lzw_length

        # local image size
        self.height = height
        self.width = width

        self.binary_data = b''
        self.image_data = []

        self.debug = debug

    def set_binary_data(self, data):
        self.binary_data = data

    def unpack_binary_data(self, image_map_list):
        """
            Unpack LZW binary
        :return:
        """
        result = []
        prev_block = None
        lzw_table = Table(self.global_palete.get_size())
        current_lzw_length = self.lzw_length

        image_data = self.image_data
        binary_data = self.binary_data

        pos = 7
        dataByte = 0
        cByte = byte_to_bits(binary_data[dataByte:dataByte + 1])
        block = None
        while dataByte < len(binary_data) - 1:
            collect()

            readbits_result = []

            if lzw_table.get_size() >= pow(2, current_lzw_length) and current_lzw_length < 12:
                current_lzw_length += 1

            for k in range(current_lzw_length):
                readbits_result.insert(0, cByte[pos])
                pos -= 1
                if pos < 0:
                    pos = 7
                    dataByte += 1
                    if len(binary_data) - dataByte == 0:
                        for ap in range(current_lzw_length - k):
                            readbits_result.insert(0, 0)

                        break
                    else:
                        cByte = byte_to_bits(binary_data[dataByte:dataByte + 1])

            block = int("".join([str(i) for i in readbits_result]), 2)

            if self.debug:
                print("unpack_binary_data, block:", block)

            if not lzw_table.is_end(block):

                if self.debug:
                    print("unpack_binary_data - 1")

                if not lzw_table.is_clear(block):
                    if block == lzw_table.get_size():
                        ref = lzw_table.get_value(result[-1])[:]
                        ref.append(ref[0])
                        lzw_table.add(ref)

                    if self.debug:
                        print("unpack_binary_data - 2")

                    result.append(block)

                    if prev_block is not None:
                        add = prev_block[:]
                        add.append(lzw_table.get_value(block)[0])
                        lzw_table.add(add)

                        if self.debug:
                            print("unpack_binary_data - 3")


                    prev_block = lzw_table.get_value(block)[:]

                    if self.debug:
                        print("unpack_binary_data - 4")

                else:
                    lzw_table = Table(self.global_palete.get_size())
                    current_lzw_length = self.lzw_length
                    prev_block = None
                    if self.debug:
                        print("unpack_binary_data - 5")

            if self.debug:
                print("unpack_binary_data - 6")

            if lzw_table.is_end(block) or lzw_table.is_clear(block) or dataByte == len(binary_data) - 1:
                if self.debug:
                    print("unpack_binary_data - 7, result: ", result)
                while result:
                    r = result.pop(0)
                    image_item = lzw_table.get_raw_value(r)
                    if r == 0:
                        image_item = [[0]]
                    elif r == 1:
                        image_item = [[1]]
                    image_found = False
                    found_index = 0
                    for i in range(0, len(image_map_list)):
                        if image_item == image_map_list[i]:
                            image_found = True
                            found_index = i
                            break
                    if not image_found:
                        image_map_list.append(image_item)
                        found_index = len(image_map_list)-1

                    image_data.append(found_index)

