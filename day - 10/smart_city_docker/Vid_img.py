import cv2
import os
# direcory path
os.chdir(r"D:\\smart city\\frames")
#import datetime
# video path
cap = cv2.VideoCapture(
    r"D:\\smart city\\videos\\v4.mp4")
# ret,frame = cap.read()
framerate = int(cap.get(cv2.CAP_PROP_FPS))
framecount = 0
count = 0
while True:
    success, frame = cap.read()
    frame = cv2.resize(frame, (1280, 720))
    framecount += 1

    if framecount == 3:
        print('hi', count)
        framecount = 0
        cv2.imwrite('v4_%d.jpg' % count, frame)
        count += 1
        
    if success == 0:
        break

        # show the output frame
    #cv2.imshow("Frame", cv2.resize(frame, (1000, 800)))
    key = cv2.waitKey(1) & 0xFF

    # if the `q` key was pressed, break from the loop
    if key == ord("q"):
        break
