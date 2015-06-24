#!/usr/bin/env python

import cv2
import numpy as np
from find_keypoints import find_kp
import object_match as om
from compare_kpd import calc_center
import rospy
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image
import threading
import Queue

"""
Python script that does object tracking in real time with webcam footage. 
Beware the current setup with global variables in the mouse callback functions - 
may or may not create an OOP version of this script for future efforts.
However remember that ultimately the object selection will be on the eye-helper webapp
and probably not on python opencv. - July 28, 2014

Keyboard controls to know once this program starts...
First, hit 's' and another window will pop up for selecting the training image.
Then, use the mouse to drag a box around the item of interest. If you mess up, simply draw a new rectangle!
Then, once you are satisfied with the selection box, hit 'enter' and object tracking will begin.
To end the demo, hit the 'q' key. - July 29, 2014
"""

frame = None

def process_frame(msg):
    global frame
    frame = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

rospy.init_node('eyehelper')
### Webcam things

rospy.Subscriber('/camera/image_raw', Image, process_frame)

#cap = cv2.VideoCapture(0)

bridge = CvBridge()

# 0 for built-in laptop webcam
# 1 for external webcam

while (frame == None):
    pass

while(True):
    # Capture frame-by-frame
    # Display the resulting frame
    cv2.imshow('frame',frame)
    if cv2.waitKey(1) & 0xFF == ord('s'): #s for selection mode...
        break

### Selecting things: Selecting the item of interest to track (i.e. the training image)
# snippets taken from mousing.py.... beware mouse callbacks and global-ish variables.

# setting state variables
drawing = False # true if mouse is pressed
mode = True # if True, draw rectangle. Press 'm' to toggle to curve
ix,iy = -1,-1
r = None

# mouse callback function
def draw_rectangle(event,x,y,flags,param):
    global ix,iy,drawing,mode,img,t_img,r

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix,iy = x,y

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing == True:
            if mode == True:
                img = np.copy(t_img)
                cv2.rectangle(img,(ix,iy),(x,y),(0,255,0))

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        if mode == True:
            cv2.rectangle(img,(ix,iy),(x,y),(0,255,0))
            r = [x,y,ix,iy]

# Obtain a copy of the current frame (so there's only one rectangle 
# seen at a time), a window and bind the function to window
img = np.copy(frame)
t_img = np.copy(frame)
cv2.namedWindow('image')
cv2.setMouseCallback('image',draw_rectangle)

# while loop for the selection things
while(1):
    cv2.imshow('image',img)
    if cv2.waitKey(20) & 0xFF == 32: #hit spacebar when done 
        break

# Get keypoints of selected area (training image)
t = find_kp(t_img, 'SIFT', live=True)
q = Queue.Queue(maxsize=1)
print 'HI HI'
threading.Thread(target=om.audio_loop, args=(q,)).start()

# OT demo loop
while True:
    # Setting up inputs for om.match_object
    previous = calc_center(r)
    current = frame
    train_img = None #since we're not specifying a training image in a subfolder somewhere else on our computer
    pos = r
    framenumber = 0

    # Now that we have the training image keypoints, commence object tracking on the video stream!
    center, current = om.match_object(previous, 
                                            current, 
                                            train_img, 
                                            pos, 
                                            framenumber, 
                                            show = True, 
                                            live = True,
                                            t = t)
#Show image
    cv2.imshow('OT demo', current)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

#Add new center to the queue, do this after showing the image so as not to slow down the object tracking
#If there is something in the queue, remove it
    if not q.empty():
        q.get(block=False)
    q.put(center)

# When everything's done, release the capture
cv2.destroyAllWindows()