#!/usr/bin/env python

import cv2
import numpy as np
import rospy
from cv_bridge import CvBridge, CvBridgeError
from image_selector import *
from object_matcher import *
from audio_player import *
from sensor_msgs.msg import Image

class EyeHelper():
    """
    The wrapper to end all wrappers.
    """

    def __init__(self):
        # yaaay class variables
        self.center = ()
        self.state = 'selecting'

        self.ims = ImageSelector()       
        self.om = ObjectMatcher() 
        self.ap = AudioPlayer()

        # Camera via the comprobo raspberry pi setup
        rospy.init_node('eyehelper')
        rospy.Subscriber('/camera/image_raw', Image, self.process_frame)
        self.bridge = CvBridge()

    def process_frame(self, msg):
        # TODO: make sure the callback works
        """
        callback for camera stuff
        """
        print 'processing'
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

        ### continuous stuff happens here ###
        if self.state == 'grocery':
            print('grocery')
            if 0xFF == ord('d'):
                # all other windows except for the raw stream should be closed
                self.state = 'no_grocery'

            elif 0xFF == ord('q'):
                # TODO: byebye
                # "quit" the rosrun ; what do people usually do with keyboard quitting in ROS setups?? (probably an odd situation to begin with)
                print 'byebye'
                return

            else:
                # runs the object matching and displays the matches/center
                self.om.run(frame, self.ims.frozen_img, self.ims.t_img_corners)

        elif self.state == 'no_grocery':
            if 0xFF == ord('s'):
                # just a transition state
                
                self.state = 'selecting'
            elif 0xFF == ord('q'):
                # TODO: byebye
                print 'byebye'
                return
            else:
                # continue showing the raw stream
                cv2.imshow('No Grocery', frame)
                print 'no_grocery else' # for debugging

        elif self.state == 'selecting':
            # TODO: ... check: Will process_frame happen over and over again while the image selection thing is frozen?
            # TODO: for selecting - only make the new window if we don't already have one up 

            # ims.run will loop through selection until spacebar is hit and execution can then go as normal
            print self.ims.t_img_corners
            self.ims.run(frame)
            # after we finish selecting, we have a grocerey, so change states
            self.state = 'grocery'
            print 'selecting else' # for debugging
            return

if __name__ == "__main__":
    eh = EyeHelper()
    r = rospy.Rate(5) # 5hz

    while not rospy.is_shutdown():
        r.sleep()