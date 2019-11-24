## MicroPython Gif Viewer

Reads in a 128x64 2 color GIF, displays each of the frames on an OLED display of a [Heltec WiFi Kit 32](https://heltec.org/project/wifi-kit-32/) microcontroller running MicroPython.

------

### Usage

```python
import gifviewer
gifviewer.run('fuzzy')
```

The first time you execute the gifviewer, it will read in a gif file, parse it, and write out a compressed form of each frame to microcontroller's local disk (under a directory named 'cache_<image_name>').  Once this is completed, the microcontroller will perform a `machine.restart()` to free up memory and move on to the second phase (displaying the gif).

The second time you execute the gif viewer, it  will read in each of the frames from disk, display them on the OLED display.

------

### Notes

* If you want to run gifviewer from your pc, you will need to comment out the `@micropython.native` lines in `gifviewer.py` and `gipyf.py`.  Also, the `set_pixel` function in `gifviewer.py` will need to be uncommented as well
* This utility will run under python 2.7
* Gif parsing library used is GiPyF (https://github.com/pyatka/gipyf) and was modified with the following changes:
  * Added support for Python 2.7
  * Reduce the overall memory usage by using callbacks, removed the generator, optimized the LZW tables
* There are sprinkels of `gc.collect()` throughout the code when initially parsing the gif image.  Without these, the applicaiton will crash by running out of memory
* I have not tested any other GIF images other than the `fuzzy.gif` that I have provided in this example.  The `fuzzy.gif` was handmade by me to specifically fit the `64x128` image constraints of the OLED
* Using more than 2 colors will most likely crash the app.  It uses the `0` and `1` for the colors to compress the images into binary

------

### Why I did this

Once I received the the Heltec microprocessor with the OLED display, I created some [libraries](https://github.com/carledwards/wifi-kit-32) to understand it more.  I then created a GIF image of what my family calls "fuzzy guy".  I started drawing this image back in 6th grade and continue to draw it on all of the celebration cards I give to the family.  Recently, my daughter surprised me by tatooing the the "fuzzy guy" on her arm.

------

### What I learned

* Memory on this device is very limited.  My first try and processing the first frame I ran out of memory.
* Memory becomes very fragmented, running `gc.collect()` has really helped.
* Using the local disk has made this project actually possible.  There just wasn't enough available memory to do both parsing and displaying within the same pass.
* Using the decorator `@micropython.native` has been helpful in making the app go faster, but found that it can cause the entire Micropython VM to crash.
* I was unable to find a way to have the `@micropython.native` decorator to be conditional (so that I could just use the same source files on the MicroPython board and the pc at the same time)
* I'm sure there are many more things I can do to speed this up, but the goal was to "get it working".  This documentation was very helpful in giving me ideas and things to try: [Maximizing MicroPython Speed](http://docs.micropython.org/en/v1.9.3/pyboard/reference/speed_python.html)

------

###Reference Docs

* GiPyF (https://github.com/pyatka/gipyf)
* [Maximizing MicroPython Speed](http://docs.micropython.org/en/v1.9.3/pyboard/reference/speed_python.html)
* [Getting started with MicroPython on the ESP32](https://docs.micropython.org/en/latest/esp32/tutorial/intro.html)
* [WiFi Kit 32](https://github.com/carledwards/wifi-kit-32)
* [Adafruit's Ampy Tool](https://learn.adafruit.com/micropython-basics-load-files-and-run-code/install-ampy)

------

###Development Shortcuts/Tips

#### Install some files and connect using Screen to the board

```shell
ampy --port /dev/tty.SLAB_USBtoUART put gifviewer.py && ampy --port /dev/tty.SLAB_USBtoUART put gipyf.py&& screen /dev/tty.SLAB_USBtoUART 115200
```

#### Disconnect and exit Screen mode keystrokes

```
ctrl-a
k
y
```



####Soft boot MicroPython when connected with Screen

```
ctrl-d
```

#### Machine reset MicroPython when connected with Screen

```python
import machine
machine.reset()
```

####Remove image`cache` directory

```shell
ampy --port /dev/tty.SLAB_USBtoUART rmdir cache_fuzzy
```

#### List files on the MicroPython board

```shell
ampy --port /dev/tty.SLAB_USBtoUART ls
```

------

###Source GIF File

![fuzzy](/Users/carl/dev/github/carledwards/micropython-gif-viewer/fuzzy.gif)



### Initialization (first pass)

![fuzzy_init_oled](/Users/carl/dev/github/carledwards/micropython-gif-viewer/images/fuzzy_init_oled.png)



### GIF Displayed on OLED

![fuzzy_oled](/Users/carl/dev/github/carledwards/micropython-gif-viewer/images/fuzzy_oled.png)