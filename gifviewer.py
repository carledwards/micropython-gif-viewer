
from gipyf import GiPyF
from gipyf import Image
import os
import json
import utime
import sys
import os
import stat
import machine

_play_delay = None 
_oled = None

class ImageProcessingCallbacks:
    def __init__(self, cache_dir, image_name, gif):
        self.cache_dir = cache_dir
        self.image_name = image_name
        self.gif = gif

    def gce_cb(self, color_alpha_index, play_delay):
        global _play_delay
        print('gce_cb, delay:', play_delay)
        # holds the frame delay as it is set before the frame is processed, e.g.:
        #     -> Global Color Table #1
        #     -> Image Frame #1
        #     -> Global Color Table #2
        #     -> Image Frame #2
        #     -> Global Color Table ...
        #     -> Image Frame ...
        _play_delay = play_delay

    def frame_cb(self, frame_number, image):
        global _start_time, _play_delay

        global _oled
        _oled.fill(0)
        _oled.text("Initializing", 1, 1)
        _oled.text("processsing", 1, 10)
        _oled.text("frame: %d" % frame_number, 1, 20)
        _oled.show()

        print("writing frame cache:", frame_number)
        # write the frame details to a local JSON file on the microcontroller
        f = open("%s_%d.bin" % ("/".join((self.cache_dir, self.image_name)), frame_number), "w")
        json.dump((_play_delay, image.width, image.height, image.top_left_x, image.top_left_y, image.image_data), f)
        f.flush()
        f.close()
        _play_delay = None


def create_gif_image_files(cache_dir, image_name):
    gif = GiPyF()
    cbHandler = ImageProcessingCallbacks(cache_dir, image_name, gif)
    # write each frame first
    gif.parse("%s.gif" % image_name, cbHandler.frame_cb, cbHandler.gce_cb)
    # write the image map last as this is the trigger on startup to determine
    # which mode we are in
    f  = open("%s.map" % ("/".join((cache_dir, image_name))), "w")
    json.dump(gif.image_map_list,f)
    f.flush()
    f.close

def sleep_remaining_frame_delay_time(start_time_ms, frame_delay):
    if start_time_ms and frame_delay:
        delay_in_ms = frame_delay[0] * 10  # play_delay is defined in 1/100th second
        delta_in_ms = utime.ticks_diff(utime.ticks_ms(), start_time_ms)
        delay_in_ms = delay_in_ms - delta_in_ms
        if delay_in_ms > 0:
            utime.sleep(delay_in_ms/1000)
        else:
            print("frame parsing took too long, delta: ", delta_in_ms, "delay: ", delay_in_ms)

@micropython.native
def show_gif_frames(image_map, cache_dir, image_name):
    global _oled

    pixel = _oled.framebuf.pixel

    play_delay = None
    prev_play_delay = None
    frame_start_time = None

    image_frame_index = 1
    while True:
        image_file_name = "%s_%d.bin" % ("/".join((cache_dir, image_name)), image_frame_index)
        try:
            # see if the file exists
            mode = os.stat(image_file_name)[0]
        except OSError:
            # there are no more *_n.bin files left, reset and start from the beginning
            image_frame_index = 1
            sleep_remaining_frame_delay_time(frame_start_time, play_delay)
            continue

        prev_play_delay = play_delay

        f = open(image_file_name, "r")
        play_delay, width, height, top_left_x, top_left_y, image_data = json.load(f)
        f.close()

        current_x = top_left_x
        current_y = top_left_y

        max_x = top_left_x + width

        # decompress the image data into a 0-based buffer
        for data_index in image_data:
            for entry in image_map[data_index]:
                if isinstance(entry, int):
                    pixel(127-current_y, current_x, (entry & 0x80)>>7)
                    current_x += 1
                    if current_x >= max_x:
                        current_x = top_left_x
                        current_y += 1

                    pixel(127-current_y, current_x, (entry & 0x40)>>6)
                    current_x += 1
                    if current_x >= max_x:
                        current_x = top_left_x
                        current_y += 1

                    pixel(127-current_y, current_x, (entry & 0x20)>>5)
                    current_x += 1
                    if current_x >= max_x:
                        current_x = top_left_x
                        current_y += 1

                    pixel(127-current_y, current_x, (entry & 0x10)>>4)
                    current_x += 1
                    if current_x >= max_x:
                        current_x = top_left_x
                        current_y += 1

                    pixel(127-current_y, current_x, (entry & 0x08)>>3)
                    current_x += 1
                    if current_x >= max_x:
                        current_x = top_left_x
                        current_y += 1

                    pixel(127-current_y, current_x, (entry & 0x04)>>2)
                    current_x += 1
                    if current_x >= max_x:
                        current_x = top_left_x
                        current_y += 1

                    pixel(127-current_y, current_x, (entry & 0x02)>>1)
                    current_x += 1
                    if current_x >= max_x:
                        current_x = top_left_x
                        current_y += 1

                    pixel(127-current_y, current_x, (entry & 0x01))
                    current_x += 1
                    if current_x >= max_x:
                        current_x = top_left_x
                        current_y += 1
                else:
                    for item in entry:
                        pixel(127-current_y, current_x, 1 if item else 0)
                        current_x += 1
                        if current_x >= max_x:
                            current_x = top_left_x
                            current_y += 1

        sleep_remaining_frame_delay_time(frame_start_time, prev_play_delay)
        prev_Play_delay = None
        frame_start_time = utime.ticks_ms()

        _oled.show() # this takes ~40ms to complete

        image_frame_index += 1


def load_gif_image_map(cache_dir, image_name):
    try:
        f = open("%s.map" % ("/".join((cache_dir, image_name))), "r")
        image_map = json.load(f)
        f.close()
        return image_map
    except:
        print("%s gif image map not found:", image_name, "(expected on first run)")
        return None

def init_display():
    global _oled
    import machine, ssd1306
    from machine import Pin
    oled_rst = Pin(16, Pin.OUT)
    oled_rst.value(1)
    i2c = machine.I2C(scl=machine.Pin(15), sda=machine.Pin(4))
    _oled = ssd1306.SSD1306_I2C(128, 64, i2c)


def run(image_name):
    base_cache_dir = 'cache'
    cache_dir = "_".join((base_cache_dir, image_name))

    init_display()

    try:
        mode = os.stat(cache_dir)[0]
        if stat.S_ISDIR(mode):
            try:
                _image_map = load_gif_image_map(cache_dir, image_name)
                show_gif_frames(_image_map, cache_dir, image_name)
            except:
                print("fatal error loading image cache files")
                raise
        else:
            print("fatal error: cache dir was found, but is not a directory")
    except:
        # cache directory doesn't exist, create it and generate the pre-parsed frame files
        os.mkdir(cache_dir)
        create_gif_image_files(cache_dir, image_name)
        # let the OS finish writing files
        utime.sleep(1)
        # at this point, the cache directory should be fully populated
        # time to move on to displaying the frames
        # reset the device to reset the memory, which will restart the main app
        machine.reset()

