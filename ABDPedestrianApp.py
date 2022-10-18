############################################################################################
# ABD Pedestrian Test Application
# - VBOX Touch application to aid testing of the VBOX's ABD Pedestrian mode.
# - Simulates the ABD control system CAN input

# [requirements]
# CAN output - simulate the ABD control output of XY position
# 		RefX_pos - CAN id 647 start bit 0, length 32, Intel, Signed integer , scale 0.001
# 		RefY_pos - CAN id 647 start bit 32, length 32, Intel, Signed integer , scale 0.001

# CAN input - handle the VBOX CAN output
# 	Log an ASC file
# 	Parse; 
# 		Latitude - CAN id 308
# 		Longitude - CAN id 309
# 		Satellites - CAN id 314
# 		Time - CAN id 314

# CAN bus config control
# 	Baud rate 500, 1000 (500 default)
# 	termination on/off (on default)
# 	output rate 10,20,50,100 Hz 

# GUI requirements
# 	CAN output controls
# 		- User should be able to control the signals on id 647
# 			- Values of +/- 10 at 0.01 resolution
# 			- Slider?
# 	CAN input display
# 		Latitude - CAN id 308
# 		Longitude - CAN id 309
# 		Satellites - CAN id 314
# 		Time - CAN id 314
# Author: Drihan du Preez
############################################################################################

import ustruct as us
import can
import gui
import vts
from image import Image_Bank
from picture_button import Picture_Button
from button_utils import LoopingButton
from micropython import const
import backlight
import os

# Variables being created before assigning
WHITE = const(0xFFFFFF)
RED = const(0xFF0000)
baudrate500 = const(0)
baudrate1000 = const(1)
baudrate = 500000
log_toggle_display = [0]
lat_can = ['']
long_can = ['']
sats_can = ['']
time_can = ['']
actual_time = ['']
settings = False
baudrate_dir = {
    baudrate500: ("500 kbit/s", 500000),
    baudrate1000: ("1 Mbit/s", 1000000)
}
rate100 = const(0)
rate50 = const(1)
rate20 = const(2)
rate10 = const(3)
outputrate_dir = {
    rate100: ("100Hz", 100),
    rate50: ("50Hz", 50),
    rate20: ("20Hz", 20),
    rate10: ("10Hz", 10),
}
outputrate = 100
toggle_val = [0]
can_term = True
xpos_val_num = ['0.0']
ypos_val_num = ['0.0']
xpos_val = [1000]
ypos_val = [1000]
refx_pos_val = [0, 0, 0, 0]
refy_pos_val = [0, 0, 0, 0]
log_on = False
file_num = 1
timer = None
counter = 0

# Remove auto screen brightness
backlight.set(5000)

def tod_to_hmsm(ms):
    # converts time in ms to hh:mm:ss:ms format
    global actual_time
    hmsm = 4 * [None]
    hmsm[0] = ms // 3600
    ms -= (hmsm[0] * 3600)
    hmsm[1] = ms // 60
    ms -= (hmsm[1] * 60)
    hmsm[2] = ms // 1
    ms -= (hmsm[2] * 1)
    hmsm[3] = ms
    actual_time[0] = "{:02d}:{:02d}:{:02d}".format(hmsm[0], hmsm[1], hmsm[2])
    return hmsm


def bytes_to_int(bytes):
    # Converts bytes to ints
    result = 0
    for b in bytes:
        result = result * 256 +int(b)
    return result


def handle_can(bus):
    # Handles the incoming CAN messages, sorts the CAN data, and formats into a display value
    global can_msg, ID_308_data, ID_309_data, ID_314_data
    while True:
        can_msg = can.get_msg(bus)
        if can_msg is None:
            return
        if can_msg.id == 0x308:
            ID_308_data = can_msg.data
            # Takes a 48 bit value, shifts it by 16 bits and then converts
            lat_can[0] = "{:09.3f}".format((us.unpack('>q', bytes(can_msg.data))[0]>> 16)/10000000)
        elif can_msg.id == 0x309:
            ID_309_data = can_msg.data
            # Takes a 48 bit value, shifts it by 16 bits and then converts
            long_can[0] = "{:09.3f}".format((us.unpack('>q', bytes(can_msg.data))[0]>> 16)/10000000)
        elif can_msg.id == 0x314:
            ID_314_data = can_msg.data
            sats_can[0] = "{:02}".format(can_msg.data[2])
            time_can[0] = "{:08.1f}".format(bytes_to_int(can_msg.data[3:6])* 0.01)
            tod_to_hmsm(int(float(time_can[0])))


def wrap_callback(callback):
    def cb(*args, **kwargs):
        callback(*args, **kwargs)
    return cb


def create_buttons(*args):
    # Creates buttons and assigns callback
    global buttons
    buttons = []
    if 'Settings' in args:
        buttons.append(Picture_Button(700, -5, bank.get('Settings'), 'Settings', settings_page))
    if 'Exit' in args:
        buttons.append(Picture_Button(700, -5, bank.get('Exit'), 'Exit', rerun_main))
    if 'Reset' in args:
        buttons.append(Picture_Button(0, -8, bank.get('Reset'), 'Reset', reset_pos))
    if 'Record' in args:
        buttons.append(Picture_Button(625, -18, bank.get('Record'), 'Record', toggle_logging))

    button_cbs_l = []
    button_icons_l = [gui.DL_BEGIN(gui.PRIM_BITMAPS)]
    for i, button in enumerate(buttons):
        button_cb_l = [
            gui.PARAM_TAG_REGISTER,
            wrap_callback(button.get_callback()),
        ]
        button_cb_l.append(button.name)
        button_cbs_l.append(button_cb_l)
        button.set_gui_l_index(len(button_icons_l))
        button_icons_l.extend(button.generate_gui_l(i + 1))
    return button_cbs_l, button_icons_l


def init_buttons():
    # creates the buttons depending on the layout
    global button_layouts
    button_layouts = {}
    button_layouts['settings'] = create_buttons('Exit')
    button_layouts['main'] = create_buttons('Settings', 'Reset', 'Record')


def button_options():
    # Creates the button list depending on the screen being called
    global button_layouts
    gui_buttons = []
    if settings == False:
        gui_buttons.extend(button_layouts['main'][0])
        gui_buttons.append(button_layouts['main'][1])
    elif settings == True:
        gui_buttons.extend(button_layouts['settings'][0])
        gui_buttons.append(button_layouts['settings'][1])

    return gui_buttons


def rerun_main(l):
    # reruns the main screen
    global settings
    settings = False
    setup_can()
    main_screen()


def get_picture_button(name):
    # gets picture button name
    try:
        pb = next(pb for pb in buttons if pb.name == name)
    except:
        pb = None
    return pb


def set_logging_status():
    # sets logging colour of the picture button
    global log_on
    if log_on == False:
        get_picture_button('Record').set_colour((255, 255, 255))
    else:
        get_picture_button('Record').set_colour((255, 0, 0))


def abc(l=None):
    pass


def write_asc():
    # get the data from can_handle and formats into .asc format and writes to the SD card
    global counter
    # log rate counter
    counter += ((log_rate_time / 10) / 3)
    list_308 = []
    bitStr308 = ""
    # unpacks the tuple of ints, converts to hex, and then formatted to the correct style before adding it into a list
    for i in ID_308_data:
        j = hex(i).replace("0x", "").upper()
        if len(j) == 1:
            j = "0" + j
        list_308.append(j)
    bitStr308 = " ".join(list_308)
    ID_308 = "{:04.6f} 1  {}             Rx   d 8 {}\r\n".format(counter, "308", bitStr308) 
    counter += ((log_rate_time / 100) / 3)
    list_309 = []
    bitStr309 = ""
    for i in ID_309_data:
        j = hex(i).replace("0x", "").upper()
        if len(j) == 1:
            j = "0" + j
        list_309.append(j)
    bitStr309 = " ".join(list_309)
    ID_309 = "{:04.6f} 1  {}             Rx   d 8 {}\r\n".format(counter, "309", bitStr309)
    counter += ((log_rate_time / 100) / 3)
    list_314 = []
    bitStr314 = ""
    for i in ID_314_data:
        j = hex(i).replace("0x", "").upper()
        if len(j) == 1:
            j = "0" + j
        list_314.append(j)
    bitStr314 = " ".join(list_314)
    ID_314 = "{:04.6f} 1  {}             Rx   d 8 {}\r\n".format(counter, "314", bitStr314)
    f.write(ID_308)
    f.write(ID_309)
    f.write(ID_314)


def set_file_name():
    # determines the last log file number and increments by 1 to get the new number
    global file_num
    file_list = [x for x in os.listdir() if x[0:4] == "Log_"]
    num_list = [int(x[4:].strip(".asc")) for x in file_list]
    num_list.sort(reverse=True)
    if len(file_list) == 0:
        file_num = 1
    else:
        last_file = num_list[0]
        file_num = last_file + 1

def timer_func():
    # starts the timer at the correct output rate and creates the callback
    global log_rate_time, timer
    if log_on == True:
        timer = vts.Timer(outputrate, True)
        log_rate_time = outputrate / 1000
        timer.set_callback(write_asc)

def toggle_logging(l):
    # checks if the SD is present and start logging the asc file if it is
    global log_on, file_num, counter, timer, f
    if vts.sd_present() == True:
        log_toggle_display[0] = 0 if log_toggle_display[0] else 0xffff
        if log_toggle_display[0] == 65535:
            log_on = True
            set_file_name()
            timer_func()
            file_name = "/sd/Log_{}.asc".format(file_num)
            f = open(file_name, 'w')
            f.write("base hex  timestamps absolute\r\n")
            f.write("no internal events logged\r\n")
            f.write("// version 7.0.0\r\n")
        else:
            log_on = False
            file_num += 1
            counter = 0
            timer.destroy()
            f.close()
    else:
        print("not present")


def set_baudrate(btn):
    # sets the baudrate
    global baudrate
    if btn.current == '500 kbit/s':
        baudrate = 500000
    else:
        baudrate = 1000000


def set_outputrate(btn):
    # sets the output rate
    global outputrate
    if btn.current == "100Hz":
        outputrate = 10
    elif btn.current == "50Hz":
        outputrate = 50
    elif btn.current == "20Hz":
        outputrate = 80
    else:
        outputrate = 100


def reset_pos(l):
    # resets xpos and ypos to 0 and the slider values as well and sends a CAN message
    global xpos_val_num, ypos_val, ypos_val_num, xpos_val, refx_pos_val, refy_pos_val
    xpos_val_num[0] = '0.0'
    ypos_val_num[0] = '0.0'
    xpos_val = [1000]
    ypos_val = [1000]
    refx_pos_val = [0, 0, 0, 0]
    refy_pos_val = [0, 0, 0, 0]
    can.send_msg(can.CAN1, [0x647, 0, [0]*8])
    main_screen()


def toggle_termination(l):
    # toggles can termination
    global can_term, toggle_val
    can_term = not can_term
    toggle_val[0] = 0 if can_term else 65535


def redraw_cb(b):
    # redraw callback for vsync
    xpos_slider_cb()
    ypos_slider_cb()
    set_logging_status()


def can_handle():
    # packs the CAN data into 4 bytes in int form and then appends to a list
    global send_list, xpos_val_num, refx_pos_val, refy_pos_val, ypos_val_num
    refx_pos_val = us.unpack("4B", us.pack('>f', (float(xpos_val_num[0]) * 0.001)))
    refy_pos_val = us.unpack("4B", us.pack('>f', (float(ypos_val_num[0]) * 0.001)))
    send_list = []
    for x in refx_pos_val:
        send_list.append(x)
    for x in refy_pos_val:
        send_list.append(x)


def xpos_slider_cb():
    # xpos slider callback updating values and position
    global xpos_val_num, refx_pos_val, refy_pos_val
    slide_num = xpos_val[0]
    actual_num = (slide_num - 1000) / 100
    format_num = round(actual_num, 2)
    xpos_val_num[0] = "{:.2f}".format(format_num)
    can_handle()


def ypos_slider_cb():
    # ypos slider callback updating values and position
    global ypos_val_num, refy_pos_val, refx_pos_val
    slide_num = ypos_val[0]
    actual_num = (slide_num - 1000) / 100
    format_num = round(actual_num, 2)
    ypos_val_num[0] = "{:.2f}".format(format_num)
    can_handle()


def can_send(l):
    # sends the xpos and ypos can message
    can.send_msg(can.CAN1, [0x647, 0, send_list])


def vsync_cb(l):
    gui.redraw()


def settings_page(l):
    # settings page gui list
    global settings, settings_gui, baudrate_button
    settings = True
    settings_gui = [
        [gui.PARAM_CLRCOLOR, gui.RGB(255, 255, 255)],
        [gui.DL_COLOR_RGB(0, 36, 64)],
        [gui.PRIM_RECTS, [
            gui.DL_VERTEX2F(0, 0),
            gui.DL_VERTEX2F(800, 60),
        ]],
        [gui.DL_COLOR_RGB(255, 255, 255)],
        [gui.CTRL_TEXT, 400, 5, 31, gui.OPT_CENTERX, "Settings"],
        [gui.DL_COLOR_RGB(0, 0, 0)],
        [gui.PRIM_LINE_STRIP, [
            gui.DL_LINE_WIDTH(1.5),
            gui.DL_VERTEX2F(0, 60),
            gui.DL_VERTEX2F(800, 60),
        ]],
        [gui.CTRL_TEXT, 120, 120, 31, 0, "Baud Rate"],
        [gui.CTRL_TEXT, 120, 240, 31, 0, "Termination"],
        [gui.CTRL_TEXT, 120, 360, 31, 0, "Output rate"],
    ]
    settings_gui.extend(button_options())
    settings_gui.extend([
        baudrate_button(),
        refreshrate_button(),
        [gui.CTRL_TOGGLE, 540, 250, 80, 30, toggle_val, b'on\xffoff', toggle_termination],
    ],)
    gui.show(settings_gui)


def can0_cb():
    # allows to use port 1
    handle_can(can.CAN0)


def can1_cb():
    # allows to use port 2
    handle_can(can.CAN1)


def main_screen():
    # main screen gui list
    main_display_list = [
        [gui.EVT_VSYNC, vsync_cb],
        [gui.EVT_REDRAW, redraw_cb],
        [gui.PARAM_CLRCOLOR, gui.RGB(255, 255, 255)],
        [gui.DL_COLOR_RGB(0, 36, 64)],
        [gui.PRIM_RECTS, [
            gui.DL_VERTEX2F(0, 0),
            gui.DL_VERTEX2F(800, 60),
        ]],
        [gui.DL_COLOR_RGB(255, 255, 255)],
        [gui.CTRL_TEXT, 400, 5, 31, gui.OPT_CENTERX, "ABD Pedestrian App"],
        [gui.DL_COLOR_RGB(0, 0, 0)],
        [gui.PRIM_LINE_STRIP, [
            gui.DL_LINE_WIDTH(1.5),
            gui.DL_VERTEX2F(0, 60),
            gui.DL_VERTEX2F(800, 60),
        ]],
        [gui.PRIM_LINE_STRIP, [
            gui.DL_LINE_WIDTH(1.5),
            gui.DL_VERTEX2F(0, 250),
            gui.DL_VERTEX2F(800, 250),
        ]],
        [gui.CTRL_TEXT, 200, 65, 30, gui.OPT_CENTERX,'Satellites'],
        [gui.CTRL_TEXT, 200, 105, 31, gui.OPT_CENTERX, sats_can],
        [gui.CTRL_TEXT, 600, 65, 30, gui.OPT_CENTERX,'Time'],
        [gui.CTRL_TEXT, 600, 105, 31, gui.OPT_CENTERX, actual_time],
        [gui.CTRL_TEXT, 200, 160, 30, gui.OPT_CENTERX,'Latitude'],
        [gui.CTRL_TEXT, 200, 200, 31, gui.OPT_CENTERX, lat_can],
        [gui.CTRL_TEXT, 600, 160, 30, gui.OPT_CENTERX,'Longitude'],
        [gui.CTRL_TEXT, 600, 200, 31, gui.OPT_CENTERX, long_can],
        [gui.CTRL_TEXT, 70, 265, 30, gui.OPT_CENTERX, 'RefX_pos'],
        [gui.CTRL_TEXT, 70, 375, 30, gui.OPT_CENTERX, 'RefY_pos'],
        [gui.CTRL_TEXT, 470, 310, 31, gui.OPT_CENTERX, xpos_val_num],
        [gui.CTRL_TEXT, 470, 420, 31, gui.OPT_CENTERX, ypos_val_num],
        [gui.DL_COLOR_RGB(255, 0, 0)],
        [gui.CTRL_TEXT, 760, 265, 30, gui.OPT_CENTERX, '10'],
        [gui.CTRL_TEXT, 170, 265, 30, gui.OPT_CENTERX, '-10'],
        [gui.CTRL_TEXT, 760, 375, 30, gui.OPT_CENTERX, '10'],
        [gui.CTRL_TEXT, 170, 375, 30, gui.OPT_CENTERX, '-10'],
    ]
    main_display_list.extend(button_options())
    main_display_list.extend([
        [gui.DL_COLOR_RGB(0, 36, 64)],
        [gui.CTRL_SLIDER, 220, 270, 500, 25, 2000, xpos_val, can_send],
        [gui.CTRL_SLIDER, 220, 380, 500, 25, 2000, ypos_val, can_send],
    ])
    gui.show(main_display_list)


def setup_can():
    # determines can setup
    can.reset(can.CAN0, baudrate)
    can.set_callback(can.CAN0, can1_cb)
    can.termination(can.CAN0, can_term)
    can.add_rx_id(can.CAN0, 0x308)
    can.add_rx_id(can.CAN0, 0x309)
    can.add_rx_id(can.CAN0, 0x314)
    can.test_mode(can.CAN0, 0)
    can.reset(can.CAN0, baudrate)
    can.set_callback(can.CAN1, can1_cb)
    can.termination(can.CAN1, can_term)
    can.add_rx_id(can.CAN1, 0x308)
    can.add_rx_id(can.CAN1, 0x309)
    can.add_rx_id(can.CAN1, 0x314)
    can.test_mode(can.CAN1, 0)


def main():
    # inital load settings
    global settings, bank, can_term, baudrate_button, refreshrate_button
    settings = False
    baudrate_button = LoopingButton(500, 120, 160, 60, [x[0] for x in baudrate_dir.values()], 30, set_baudrate)
    refreshrate_button = LoopingButton(500, 360, 160, 60, [x[0] for x in outputrate_dir.values()], 30, set_outputrate)
    bank = Image_Bank((
        ('/icon-reset.png', 'Reset'),
        ('/icon-settings.png', 'Settings'),
        ('/icon-record.png', 'Record'),
        ('/icon-exit.png', 'Exit'),
    ))
    
    init_buttons()
    setup_can()
    main_screen()

main()

