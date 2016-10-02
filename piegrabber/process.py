import cv2
import numpy
from time import time, sleep


def process(uv, lowerO=(60, 160), upperO=(90, 255)):            
    start = time()
    blurred_uv = uv        
    blurred_uv = cv2.blur(uv, (4,4))  # kills perf but smooths the picture

    radius, center = None, None

    for i in range(3):    
        mask = cv2.inRange(blurred_uv, lowerO, upperO)  ## FILTER THE COLORS!!
        mask = cv2.dilate(mask, None, iterations=2)

        # cnts = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2] 

        # if cnts:
        #     contour = max(cnts, key=cv2.contourArea)
        #     center, radius = cv2.minEnclosingCircle(contour)
        #     radius = round(radius)
            
    result = {
        'radius': radius,
        'center': center,
        'ms': time()-start,
        'masks': [mask],
    }
    return result