import cv2
import numpy as np
from time import time, sleep

captures = []
 
for j in range(10):
  video = cv2.VideoCapture(j)
  video.set(3, 640)
  video.set(4, 480)
  success, _ = video.read()
  if not success:
    continue
  captures.append(video)
  print "camera {} initialized {}".format(j, success)

if not len(captures) == 8:
  raise Exception("you are stupid")

count, last = 0, time()

positions = [None] * 8
current_order_counter = 0
last_served = None
while True:
    now = time()
    if now-last > 2:
        print "%d fps" % (count * 1.0/ (now-last))
        last = now
        count = 0
    count+=1

    frames = [cap.read()[1] for cap in captures]

    for index,frame in enumerate(frames):
        if frame.mean() < 30: print("index:low",index)    
        if frame.mean() < 30 and index != last_served:
            positions[index] = current_order_counter % 8
            current_order_counter += 1
            last_served = index
            break     
        cv2.putText(frame,"Me is #{}".format(positions[index]), (10,40), cv2.FONT_HERSHEY_SIMPLEX, 1.2,(255,255,255),1)
    
    frames = [cv2.resize(frame, (0,0), fx=0.7, fy=0.7) for frame in frames]
    #frames = [np.rot90( frame , k=3) for frame in frames]
    
    frame_pairs = [(positions[index], index) for index,frame in enumerate(frames)]
    sorted_frames = [frames[p[1]] for p in sorted(frame_pairs)]


    stackedA = np.hstack(sorted_frames[:4])
    stackedB = np.hstack(sorted_frames[4:])
    stacked = np.vstack([stackedA,stackedB])
    
    

    cv2.imshow('justaname', stacked)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
