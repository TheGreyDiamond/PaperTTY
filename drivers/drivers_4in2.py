#     Copyright (c) 2020 Guido Kraemer
#     Copyright (c) 2018 Jouko Strömmer
#     Copyright (c) 2017 Waveshare
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.

from drivers import drivers_partial
from drivers import drivers_consts
try:
    import RPi.GPIO as GPIO
except ImportError:
    pass


from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

class EPD4in2(drivers_partial.WavesharePartial,
              drivers_consts.EPD4in2const):
    """WaveShare 4.2" """

    # code adapted from  epd_4in2.c
    # https://github.com/waveshare/e-paper/blob/8973995e53cb78bac6d1f8a66c2d398c18392f71/raspberrypi%26jetsonnano/c/lib/e-paper/epd_4in2.c

    # note: this works differently (at least in the c code): there is a memory
    # buffer, the same size as the display. we partially refresh the memory
    # buffer with the image at a position and the do self.partial_refresh with
    # the entire memory buffer and the area to be refreshed.

    # note: this code is outside of drivers_partial.py because the class has to
    # override many methdos and therefore is way to long

    def __init__(self):
        super(drivers_partial.WavesharePartial, self).__init__(name='4.2"',
                                                               width=300, height=400)

        # this is the memory buffer that will be updated!
        self.frame_buffer = [0x00] * (self.width * self.height // 8)

    # TODO: universal?
    def set_setting(self, command, data):
        self.send_command(command)
        for d in data:
            self.send_data(d)

    # TODO: universal?
    def set_resolution(self):
        self.set_setting(self.RESOLUTION_SETTING,
                         [(self.height >> 8) & 0xff,
                          self.height & 0xff,
                          (self.width >> 8) & 0xff,
                          self.width & 0xff])

    def reset(self):
        self.digital_write(self.RST_PIN, GPIO.HIGH)
        self.delay_ms(200)
        self.digital_write(self.RST_PIN, GPIO.LOW)
        self.delay_ms(200)
        self.digital_write(self.RST_PIN, GPIO.HIGH)
        self.delay_ms(200)

    def send_command(self, command):
        self.digital_write(self.DC_PIN, GPIO.LOW)
        self.digital_write(self.CS_PIN, GPIO.LOW)
        self.spi_transfer([command])
        self.digital_write(self.CS_PIN, GPIO.HIGH)

    def send_data(self, data):
        self.digital_write(self.DC_PIN, GPIO.HIGH)
        self.digital_write(self.CS_PIN, GPIO.LOW)
        self.spi_transfer([data])
        self.digital_write(self.CS_PIN, GPIO.HIGH)

    def wait_until_idle(self):
        self.send_command(self.GET_STATUS)
        while self.digital_read(self.BUSY_PIN) == 0:
            self.send_command(self.GET_STATUS)
            self.delay_ms(100)

    def turn_on_display(self):
        self.send_command(self.DISPLAY_REFRESH)
        self.delay_ms(100)
        self.wait_until_idle()

    def full_set_lut(self):
        self.set_setting(self.VCOM_LUT, self.LUT_VCOM0)
        self.set_setting(self.W2W_LUT, self.LUT_WW)
        self.set_setting(self.B2W_LUT, self.LUT_BW)
        self.set_setting(self.W2B_LUT, self.LUT_WB)
        self.set_setting(self.B2B_LUT, self.LUT_BB)

    def partial_set_lut(self):
        self.set_setting(self.VCOM_LUT, self.PARTIAL_LUT_VCOM1)
        self.set_setting(self.W2W_LUT, self.PARTIAL_LUT_WW1)
        self.set_setting(self.B2W_LUT, self.PARTIAL_LUT_BW1)
        self.set_setting(self.W2B_LUT, self.PARTIAL_LUT_WB1)
        self.set_setting(self.B2B_LUT, self.PARTIAL_LUT_BB1)

    def gray_set_lut(self):
        self.set_setting(self.VCOM_LUT, self.GRAY_LUT_VCOM)
        self.set_setting(self.W2W_LUT, self.GRAY_LUT_WW)
        self.set_setting(self.B2W_LUT, self.GRAY_LUT_BW)
        self.set_setting(self.W2B_LUT, self.GRAY_LUT_WB)
        self.set_setting(self.B2B_LUT, self.GRAY_LUT_BB)

    def init_bw(self):
        self.reset()
        self.set_setting(self.POWER_SETTING, [0x03, 0x00, 0x2b, 0x2b])
        self.set_setting(self.BOOSTER_SOFT_START, [0x17, 0x17, 0x17])
        self.send_command(self.POWER_ON)
        self.wait_until_idle()
        self.set_setting(self.PANEL_SETTING, [0xbf, 0x0d]) # kw-bf kwr-af bwrotp 0f bwotp 1f
        self.set_setting(self.PLL_CONTROL, [0x3c]) # 3a 100hz   29 150hz 39 200hz	31 171hz
        self.set_resolution()
        self.set_setting(self.VCM_DC_SETTING, [0x28])
        # wbmode:vbdf 17|d7 vbdw 97 vbdb 57 wbrmode:vbdf f7 vbdw 77 vbdb 37 vbdr b7
        self.set_setting(self.VCOM_AND_DATA_INTERVAL_SETTING, [0x97])
        self.full_set_lut()

    def init_gray(self):
        self.reset()
        self.set_setting(self.POWER_SETTING, [0x03, 0x00, 0x2b, 0x2b, 0x13])
        self.set_setting(self.BOOSTER_SOFT_START, [0x17, 0x17, 0x17])
        self.send_command(self.POWER_ON)
        self.wait_until_idle()
        self.set_setting(self.PANEL_SETTING, [0x3f]) # kw-3f  kwr-2f  bwrotp 0f  bwotp 1f
        self.set_setting(self.PLL_CONTROL, [0x3c]) # 3a 100hz   29 150hz 39 200hz	31 171hz
        self.set_resolution()
        self.set_setting(self.VCM_DC_SETTING, [0x12])
        # wbmode:vbdf 17|d7 vbdw 97 vbdb 57 wbrmode:vbdf f7 vbdw 77 vbdb 37 vbdr b7
        self.set_setting(self.VCOM_AND_DATA_INTERVAL_SETTING, [0x97])

    def init(self, partial=True, gray=False):
        self.partial_refresh = partial
        self.gray = gray

        if self.epd_init() != 0:
            return -1

        if self.gray:
            self.init_gray()
        else:
            self.init_bw()

    def clear(self):
        height = int(self.height // 8
                    if self.height % 8 == 0
                    else self.height % 8 + 1)
        width = int(self.width)

        self.send_command(self.DATA_START_TRANSMISSION_1)
        for i in range(width * height):
            self.send_data(0xff)

        self.send_command(self.DATA_START_TRANSMISSION_2)
        for i in range(width * height):
            self.send_data(0xff)

        self.send_command(self.DISPLAY_REFRESH)
        self.delay_ms(10)
        self.turn_on_display()

    def display_full(self):

        height = int(self.height // 8
                     if self.height % 8 == 0
                     else self.height % 8 + 1)
        width = int(self.width)

        self.send_command(self.DATA_START_TRANSMISSION_2)
        for j in range(width):
            for i in range(height):
                self.send_data(self.frame_buffer[j * height + i])

        self.turn_on_display()

    def display_partial(self, x_start, y_start, x_end, y_end):

        # width = int(self.width)
        height = int(self.height // 8
                     if self.height % 8 == 0
                     else self.height % 8 + 1)

        x_start = int(x_start if x_start % 8 == 0 else x_start // 8 * 8 + 8)
        x_end = int(x_end if x_end % 8 == 0 else x_end // 8 * 8 + 8)

        y_start = int(y_start)
        y_end = int(y_end)

        self.set_setting(self.VCOM_AND_DATA_INTERVAL_SETTING, [0xf7])
        self.delay_ms(100)

        self.set_setting(self.VCM_DC_SETTING, [0x08])
        self.set_setting(self.VCOM_AND_DATA_INTERVAL_SETTING, [0x47])
        self.partial_set_lut()

        self.send_command(self.PARTIAL_IN)
        self.set_setting(self.PARTIAL_WINDOW,
                         [x_start//256, x_start % 256,
                          x_end // 256, x_end % 256 - 1,
                          y_start // 256, y_start % 256,
                          y_end // 256, y_end % 256 - 1,
                          0x28])

        # writes old data to sram for programming
        self.send_command(self.DATA_START_TRANSMISSION_1)
        for j in range(y_end - y_start):
            idx = (y_start + j) * height + x_start // 8
            for i in range((x_end - x_start) // 8):
                self.send_data(self.frame_buffer[idx + i])

        # writes new data to sram.
        self.send_command(self.DATA_START_TRANSMISSION_2)
        for j in range(y_end - y_start):
            idx = (y_start + j) * height + x_start // 8
            for i in range((x_end - x_start) // 8):
                self.send_data(~self.frame_buffer[idx + i])

        self.send_command(self.DISPLAY_REFRESH)   # display refresh
        self.delay_ms(10)  # the delay here is necessary, 200us at least!!!
        self.turn_on_display()

    # def display_gray(self, frame_buffer):
    #     # note: this code is currently not being called.
    #     # this is what the original source code says:

    #     # /****color display description****
    #     #       white  gray1  gray2  black
    #     # 0x10|  01     01     00     00
    #     # 0x13|  01     00     01     00
    #     # *********************************/
    #     # 	epd_4in2_sendcommand(0x10);

    #     self.send_command(0x10)

    #     for m in range(self.height):
    #         for i in range(self.width // 8):
    #             temp3 = 0
    #             for j in range(2):
    #                 temp1 = frame_buffer[(m * (self.width // 8) + i) * 2 + j]
    #                 for k in range(2):
    #                     temp2 = temp1 & 0xc0
    #                     if temp2 == 0xc0:
    #                         temp3 |= 0x01  # white
    #                     elif temp2 == 0x00:
    #                         temp3 |= 0x00  # black
    #                     elif temp2 == 0x80:
    #                         temp3 |= 0x01  # gray1
    #                     else:  # 0x40
    #                         temp3 |= 0x00  # gray2
    #                     temp3 <<= 1

    #                     temp1 <<= 2
    #                     temp2 = temp1 & 0xc0
    #                     if temp2 == 0xc0:  # white
    #                         temp3 |= 0x01
    #                     elif temp2 == 0x00:  # black
    #                         temp3 |= 0x00
    #                     elif temp2 == 0x80:
    #                         temp3 |= 0x01  # gray1
    #                     else:  # 0x40
    #                         temp3 |= 0x00  # gray2
    #                     if (j != 1) or (k != 1):
    #                         temp3 <<= 1

    #                     temp1 <<= 2
    #                 # end for k
    #             # end for j
    #             self.send_data(temp3)
    #         # end for i
    #     # end for m
    #     # new data
    #     self.send_command(0x13)

    #     for m in range(self.height):
    #         for i in range(self.width // 8):
    #             temp3 = 0
    #             for j in range(2):
    #                 temp1 = frame_buffer[(m * (self.width // 8) + i) * 2 + j]
    #                 for k in range(2):
    #                     temp2 = temp1 & 0xc0
    #                     if temp2 == 0xc0:
    #                         temp3 |= 0x01  # white
    #                     elif temp2 == 0x00:
    #                         temp3 |= 0x00  # black
    #                     elif temp2 == 0x80:
    #                         temp3 |= 0x00  # gray1
    #                     else:  # 0x40
    #                         temp3 |= 0x01  # gray2
    #                     temp3 <<= 1

    #                     temp1 <<= 2
    #                     temp2 = temp1 & 0xc0
    #                     if temp2 == 0xc0:  # white
    #                         temp3 |= 0x01
    #                     elif temp2 == 0x00:  # black
    #                         temp3 |= 0x00
    #                     elif temp2 == 0x80:
    #                         temp3 |= 0x00  # gray1
    #                     else:  # 0x40
    #                         temp3 |= 0x01  # gray2
    #                     if (j != 1) or (k != 1):
    #                         temp3 <<= 1

    #                     temp1 <<= 2
    #                 # end for k
    #             # end for j
    #             self.send_data(temp3)
    #         # end for i
    #     # end for m
    #     self.gray_set_lut()
    #     self.turn_on_display()

    def sleep(self):
        self.send_command(0x02)  # power off
        self.wait_until_idle()
        self.send_command(0x07)  # deep sleep
        self.send_data(0xa5)

    def set_frame_buffer(self, x, y, image):

        image_monocolor = image.convert('1')
        imwidth, imheight = image_monocolor.size
        pixels = image_monocolor.load()

        for j in range(y, y + imwidth):
            idxj = j * self.height // 8
            for i in range(x, x + imheight):
                idiv = i // 8
                irem = i % 8
                mask = 0x01 << (7 - irem)
                if pixels[j - y, i - x] != 0:
                    self.frame_buffer[idiv + idxj] |= mask
                else:
                    self.frame_buffer[idiv + idxj] &= ~mask

    def fill(self, color, fillsize):
        """slow fill routine"""
        image = Image.new('1', (fillsize, self.height), color)
        for y in range(0, self.width, fillsize):
            self.draw(0, y, image)

    ### The original fill method:
    # def fill(self, color, fillsize):
    #     """Slow fill routine"""
    #     image = Image.new('1', (fillsize, self.height), color)
    #     for x in range(0, self.height, fillsize):
    #         self.draw(x, 0, image)

    def draw(self, x, y, image):
        """replace a particular area on the display with an image"""

        print("=====================================")
        print("x: ", x)
        print("y: ", y)
        print("image.width:", image.width)
        print("image.height:", image.height)
        print("self.width: ", self.width)
        print("self.height:", self.height)

        if self.partial_refresh:
            self.set_frame_buffer(y, x, image)
            self.display_partial(y, x, y + image.height, x + image.width)
        else:
            self.set_frame_buffer(0, 0, image)
            self.display_full()
