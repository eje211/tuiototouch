#!/usr/bin/python
#
# tuiototouch, a bridge between TUIO and Linux input for multitouch
#
# The copyright owners for the contents of this file are:
#     Ecole Nationale de l'Aviation Civile, France (2010-2011)
#
# main and only file
#
# Contributors:
#     Simon Charvet <charvet@lii-enac.fr>
#
#
# This program is provided to you as free software;
# you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option)
# any later version.

import getopt, tuio, uinput, time, itertools

X_RES = 1000
X_OFFSET = 0
X_COMBINED = 1000

Y_RES = 1000
Y_OFFSET = 0
Y_COMBINED = 1000

# Log each touch event?
LOGGING = False

class Device(object):
    '''
    A virtual device for the specified TUIO input.
    '''
    def __init__(self, capabilities = ()):
        '''
        Register the touch, position and tracking capabilities with utouch.
        '''
        self.tuio_objects = {}
        capabilities += (uinput.BTN_TOUCH,
                        uinput.ABS_MT_POSITION_X + (0, X_COMBINED, 0, 0),
                        uinput.ABS_MT_POSITION_Y + (0, Y_COMBINED, 0, 0),
                        uinput.ABS_MT_TRACKING_ID + (0, 10, 0, 0))
        self.device = uinput.Device(capabilities, name = "TUIO-multitouch")

    def update(self, tuio_objects):
        '''
        Replace current queue of TUIO objects to process with a new one.
        '''
        self.tuio_objects = {obj.sessionid: obj for obj in tuio_objects}

    def display(self):
        '''
        Send all the currently queued event as one atomic commit.
        '''
        self.emit(uinput.BTN_TOUCH, bool(self.tuio_objects), syn = False)
        for key, tuio_object in self.tuio_objects.iteritems():
            self.treatment(tuio_object)
        self.emit((0, 0), 0, syn = False)

    def treatment(self, event):
        '''
        Add the specified touch event to the current atomic event.
        '''
        self.emit(uinput.ABS_MT_TRACKING_ID, event.sessionid, syn = False)
        self.emit(uinput.ABS_MT_POSITION_X, X_OFFSET + (event.xpos * X_RES), syn = False)
        self.emit(uinput.ABS_MT_POSITION_Y, Y_OFFSET + (event.ypos * Y_RES), syn = False)
        self.emit((0, 2), 0, syn = False)

    def emit(self, event, tuio_object, syn = True):
        '''
        Wrap the standard utouch emit function with one with different defaults and logging.
        '''
        evtype, evcode = event
        if LOGGING:
          print "type :%d code : %d tuio object : %d" % (evtype, evcode, tuio_object)
        self.device.emit(event, int(tuio_object), syn)


class DeviceWME(Device):
    '''
    In addition to emulating touch, also emulate the mouse.

    To do this, take the first cursor available and treat is a the mouse.
    '''
    def __init__(self, capabilities = ()):
        '''
        In addition to the regular Devcie class's capabilities, add the capatbility to directly assing the mouse
        position.
        '''
        capabilities = (uinput.ABS_X + (0, X_COMBINED, 0, 0),
                        uinput.ABS_Y + (0, Y_COMBINED, 0, 0))
        super(DeviceWME, self).__init__(capabilities)
        self.x_mouse, self.y_mouse = 0, 0

    def display(self):
        '''
        Grab the first TUIO cursor availalbe and treat is as the mouse.
        '''
        try:
            any_object = self.tuio_objects[next(self.tuio_objects.iterkeys())]
            new_x, new_y = X_OFFSET + any_object.xpos * X_RES, Y_OFFSET + any_object.ypos * Y_RES

            self.emit(uinput.BTN_TOUCH, 1)

            if new_x != self.x_mouse or new_y != self.y_mouse:
                if self.x_mouse != new_x:
                    self.emit(uinput.ABS_X, self.x_mouse, syn = False)
                if self.y_mouse != new_y:
                    self.emit(uinput.ABS_Y, self.y_mouse, syn = False)
                self.x_mouse, self.y_mouse = new_x,  new_y
                self.emit((0, 0), 0, syn = False)
            self.treatment(any_object)
        except StopIteration:
            self.emit(uinput.BTN_TOUCH, 0)

        # Translate the other TUIO cursors too.
        for tuio_object in self.tuio_objects.itervalues():
            self.treatment(tuio_object)

        self.emit((0, 0), 0, syn = False)


if __name__ == "__main__":
    import sys
    host = "127.0.0.1"
    port = 3333
    noWME = False

    options, remainder = getopt.getopt(sys.argv[1:], "", ['no-mouse-emu', 'host=', 'port=', 'xoffset=', 'yoffset=', 'xsize=', 'ysize=', 'xcombined=', 'ycombined='])

    for opt, arg in options:   
        if opt in ('--no-mouse-emu'):
            noWME = True
        if opt in ('--host'):
            host = arg
        if opt in ('--port'):
            port = int(arg)
        if opt in ('--xoffset'):
            X_OFFSET = int(arg)
        if opt in ('--yoffset'):
            Y_OFFSET = int(arg)
        if opt in ('--xsize'):
            X_RES = int(arg)
        if opt in ('--ysize'):
            Y_RES = int(arg)
        if opt in ('--xcombined'):
            X_COMBINED = int(arg)
        if opt in ('--ycombined'):
            Y_COMBINED = int(arg)

    device = Device() if noWME else DeviceWME()

    tracking = tuio.Tracking(host, port)    

    try:
        while True:
            tracking.update()
            device.update(itertools.chain(tracking.objects(), tracking.cursors()))
            device.display()
            time.sleep(0.01)
    except KeyboardInterrupt: tracking.stop()
