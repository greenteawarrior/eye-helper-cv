#!/usr/bin/env python

import cv2
import numpy as np
import rospy
from cv_bridge import CvBridge, CvBridgeError
from image_selector import *
from object_matcher import *
from audio_player import *


class EyeHelper():
    """
    The wrapper to end all wrappers.
    """

    def __init__(self):
        # yaaay class variables
        self.center = []
        self.state = 'no_grocery'

        # initialize helper objects, yo 
        self.ims = ImageSelector()       
        self.om = ObjectMatcher()
        self.ap = AudioPlayer()

        # Camera via the comprobo raspberry pi setup
        rospy.init_node('eyehelper')
        rospy.Subscriber('/camera/image_raw', Image, process_frame)
        bridge = CvBridge()

    def process_frame(self, msg):
        # TODO: make sure the callback works
        "callback for camera stuff"
        frame = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

        ### continuous stuff happens here ###
        if self.state = 'grocery':
            if 0xFF == ord('d'):
                # all other windows except for the raw stream should be closed
                self.state = 'no_grocery'

            elif 0xFF == ord('q'):
                # TODO: byebye
                # "quit" the rosrun ; what do people usually do with keyboard quitting in ROS setups?? (probably an odd situation to begin with)
                print 'byebye'
                return

            else:
                # tracking stuff!
                # lots of helper function calling here

        elif self.state = 'no_grocery':
            if 0xFF == ord('s'):
                # just a transition state
                self.state = 'selecting'
            elif 0xFF == ord('q'):
                # TODO: byebye
                print 'byebye'
                return
            else:
                # continue showing the raw stream
                print 'no_grocery else' # for debugging

        elif self.state = 'selecting':
            if 0xFF == 32: #spacebar
                self.state = 'grocery'
            elif 0xFF == ord('q'):
                # TODO: byebye
                print 'byebye'
                return
            else:
                print 'selecting else' # for debugging

if __name__ == main:
    eh = EyeHelper()
    # eh.run()