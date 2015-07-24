#!/usr/bin/env python

"""
trying out the xwiimote pointer thingie.
"""

import rospy
# from sensor_msgs.msg import Joy, JoyFeedback #no idea what this actually is; doesn't seem to get used, but anyways.
# import errno # ditto
from select import poll, POLLIN
import math
import xwiimote
import time
from std_msgs.msg import Int32, Int32MultiArray, Bool #might not use header or the floats actually, we'll see.
from tango_tracker import Tango_tracker
import numpy as np
import threading


class Wii_pointer():
    def __init__(self, tracker):
        # ------------ Connecting to wii remote.
        self.mote = None
        self.tracker = tracker
        self.monitor = xwiimote.monitor(True, True)
        while self.mote == None:
            self.mote = self.monitor.poll()
            rospy.sleep(1)


        # ------------ Setting up wii remote.
        self.mote = xwiimote.iface(self.mote)
        self.mote.open(self.mote.available() | xwiimote.IFACE_WRITABLE)
        self.mote.open(self.mote.available() | xwiimote.IFACE_ACCEL)
        self.mote.open(self.mote.available() | xwiimote.IFACE_MOTION_PLUS)
        self.poller = poll()
        self.poller.register(self.mote.get_fd(), POLLIN)
        self.event = xwiimote.event()

        # ------------ Parameters, data, etc.
        self.current = [0,0,0]
        self.resting = [0,0,0]
        self.last_reading = rospy.Time.now()
        self.target = [0, 0, 0] # just for testing purposes
        self.index = 0 # ditto
        self.autoCheck = True
        self.rumble_proportion = 0

        # ----------- ROS Publishers/subscribers.
        self.button_pub = rospy.Publisher("/wii_buttons", Int32, queue_size=10)
        self.orientation_pub = rospy.Publisher("/wii_orientation", Int32MultiArray, queue_size=10)
        rospy.Subscriber("/wii_rumble", Bool, self.set_rumble)

        self.tc = 0 # can be deleted at some point, just using it to keep track of something.

    def run(self):
        if self.tracker != None:
            self.tracker.refresh_all()
            self.get_target_from_tracker()
        self.poller.poll()
        try:
            self.mote.dispatch(self.event)
        except IOError:
            self.tc += 1
            print "ioer in run", self.tc
            pass

        if self.event.type == xwiimote.EVENT_MOTION_PLUS:
            self.handle_motion()
            if self.autoCheck:
                self.check_if_close()
                # self.rumble_by_proportion() # look into running this in parallel, b/c otherwise it's a bit irregular... :|


        elif self.event.type == xwiimote.EVENT_KEY:
            self.handle_buttons()
            (code, state) = self.event.get_key()
            if True: # right now using A and B buttons as a control thingie.
                if code == 5:
                    self.set_resting()
                    self.set_zero()
            #Keys: 0 = left, 1: right, 2: up, 3 = down, 4 = A, 5 = B, 6 = +, 7 = -, 8 = home, 9 = 1, 10 = 2.


    def get_target_from_tracker(self):
        """
        sets self.target based on values from self.tracker.
        """
        if self.tracker.z_distance == None or self.tracker.xy_distance == None or self.tracker.angle_to_go == None:
            return
        pitch = math.atan2(self.tracker.z_distance, self.tracker.xy_distance)
        yaw = self.tracker.angle_to_go # TODO: incorporate offset.
        self.target = [-1*yaw, 0, math.degrees(pitch)]


    def handle_motion(self):
        """
        handles motion plus events. basically, integrates the angular velocities into a current pose.
        then, publishes to the motion topic.
        still working on the roll thingie, the ros transforms I tried earlier didn't work quite right. probably gonna muck around with cosines &c tomorrow.
        """
        non_zeroed_change = self.event.get_abs(0)
        change = [non_zeroed_change[i] - self.resting[i] for i in range(3)]
        now = rospy.Time.now()
        dt = now - self.last_reading
        self.last_reading = now

        self.current[0] += (change[0] * math.cos(math.radians(self.current[1])) + change[2] * math.sin(math.radians(self.current[1])))*(dt.nsecs/1000000000.0)*(1.492/20.0)**2
        self.current[2] += (change[2] * math.cos(math.radians(self.current[1])) + change[0] * math.sin(math.radians(self.current[1])))*(dt.nsecs/1000000000.0)*(1.492/20.0)**2
        self.current[1] += change[1]*(dt.nsecs/1000000000.0)*(1.492/20.0)**2

        a = np.array([int(i) for i in self.current], dtype=np.int32)
        b = Int32MultiArray(data=a)
        self.orientation_pub.publish(b)

    def handle_buttons(self):
        (code, state) = self.event.get_key()
        self.button_pub.publish(code)

    def set_rumble(self, msg):
        try:
            self.mote.rumble(msg.data)
        except IOError:
            pass


    def check_if_close(self):
        """
        if within some [pretty much arbitrary right now] distance of the target, rumbles. else, no rumble.
        """    
        distance = math.sqrt((self.target[0]-self.current[0])**2 + (self.target[2]-self.current[2])**2)
        # print self.target
        try:
            # return
            if distance < 4:
                self.rumble_proportion = 1
                # self.rumble_by_proportion()
            elif distance < 10:
                # self.rumble_proportion = 0.5
                self.rumble_proportion = (.50 - distance*.03)
                # self.rumble_by_proportion()
            else:
                self.rumble_proportion = 0
        except IOError:
            print "ioer in check_if_close"
            pass

    def rumble_by_proportion(self):
        """
        rumbles for c seconds - right now, 0.02. self.rumble_proportion determines how much is spent actually rumbling vs. on 'downtime.' Might also need to make this whole thing a try-except on account of the occasional IOError when setting the wii remmote's rumble.
        """
        p = self.rumble_proportion
        c = .02 # tradeoff between responsive-ness of buzz and how feel-able it is.
        try:
            if p == 0: # including zero. the .3 is based on a personal judgment call for what does v. doesn't actually buzz well.
                self.mote.rumble(False)
                rospy.sleep(c)
            elif p == 1:
                self.mote.rumble(True)
                rospy.sleep(c)
            else:
                self.mote.rumble(True)
                rospy.sleep(c*p)
                self.mote.rumble(False)
                rospy.sleep(c*(1-p))
        except IOError:
            print "ioerror in rumble_by_proportion D:"
            pass

    def rumbler_loop(self):
        while not rospy.is_shutdown():
            self.rumble_by_proportion()

    def run_loop(self):
        while not rospy.is_shutdown():
            self.run()

    def set_zero(self):
        self.current = [0,0,0]

    def set_resting(self):
        self.index = 0
        drifts = []

        while self.index < 400: #...first handful of signals are always wacky; this gets it to ignore them.
            try:
                self.poller.poll()
                self.mote.dispatch(self.event)
                self.index += 1
            except IOError:
                print "ioe in set_resting pt1"
                pass

        while self.index < 800:
            try:
                self.poller.poll()
                self.mote.dispatch(self.event)
                reading = self.event.get_abs(0)
                if self.event.type == xwiimote.EVENT_MOTION_PLUS:
                    drifts.append(reading)
                    self.index += 1
            except IOError:
                print "ioe in set_resting pt2"
                pass
        avg_reading = [(sum(i[j] for i in drifts)/len(drifts)) for j in range(3)]
        self.resting = avg_reading
        print "resting: \t", self.resting


if __name__ == "__main__":
    tt = Tango_tracker()
    wm = Wii_pointer(None)
    start_time = rospy.Time.now()
    wm.set_resting()
    run_thread = threading.Thread(target=wm.run_loop)
    rumble_thread = threading.Thread(target=wm.rumbler_loop)
    run_thread.start()
    rumble_thread.start()

    # while not rospy.is_shutdown():
    #     wm.run()

    #     if rospy.Time.now() - start_time > rospy.Duration(1200):
    #         print wm.index, '\t', wm.current
    #         exit()