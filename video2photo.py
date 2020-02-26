import pandas as pd
import cv2
import os
from os import listdir
from os.path import isfile, join
from progress.bar import Bar
import sys
#import subprocess
#import json

imageDistance = 0.01

intro = f"""
video2photo.py

version:    1.1
author:     Benjamin Milanko
updated:    2020/02/26

description:
    Takes a video file and CSV export of GPS coordinates and exports an image every {imageDistance} km
"""

if not (sys.version_info.major == 3 and sys.version_info.minor >= 5):
    print("This script requires Python 3.5 or higher!")
    print("You are using Python {}.{}.".format(sys.version_info.major, sys.version_info.minor))
    sys.exit(1)

print(intro)

#time2float
#arguments: inTime as an array of the format [hour (int), minute (int), second (float)]
#output: the time as a single foat
#note: This will only work during a single day and will not return the expected result across midnight
def time2float(inTime):

    return int(inTime[0])*3600+int(inTime[1])*60+float(inTime[2])

#float2time
#arguments: inTime as a float of the seconds passed since midnight
#output: an array in the form [hour (int), minute (int), second (float)]
#note: 
def float2time(inTime):

    hh = int(inTime/3600)
    mm = int((inTime - hh*3600)/60)
    ss = inTime-hh*3600-mm*60

    return [hh, mm, ss]

#interpolateTime
#arguments: count, the distance passed in km; time1, the later timestamp to interpolate to ; time2, the earlier timestamp to interpolate from
#output: An array of float timestamps interpolated between time1 and time2
#note: 
def interpolateTime(count, time1, time2):

    returnTime = []

    num = int(count/imageDistance)
    delta = time1-time2

    segment = delta/num

    for i in range(num):
        returnTime.append(time2+segment*i)

    return returnTime

cwd = os.getcwd()

files = [f for f in listdir(cwd) if isfile(join(cwd, f))]

for each in files:
    split = each.split(".")
    if len(split) > 1:
        if split[1] == "MP4":
            vid = each
            metaBinary = f"{split[0]}.bin"
            metaJson = f"{split[0]}.json"
            vidFile = split[0]
        elif split[1] == "csv":
            gps = each

try:
    print(f"Loaded video {vid} and GPS file {gps}")
except NameError:
    print("Video or CSV file not found")
    sys.exit()

f = open(gps, "r", encoding="utf16")

data = f.read()

data = data.split("\n")

for i in range(len(data)):
    data[i] = data[i].split(",")

data.pop()
data.pop(0)
header = data.pop(0)

time = []
distance = []
first = 0

for i in range(len(data)):
        
    timeStamp = data[i][1].split(" ")[1]
    timeStamp = timeStamp.split(":")
    timeStamp = time2float(timeStamp)
    if i == 0:
        first = timeStamp
    timeStamp = (timeStamp-first)
    time.append(timeStamp)
    distance.append(float(data[i][8]))

outputTimestamps = []

print("\nInterpolating timestamps")
bar = Bar('Processing', max=len(distance)-1)

count = 0
for i in range(1,len(distance)):
    count += (distance[i]-distance[i-1])
    if count > 0.010:
        times = interpolateTime(count, time[i], time[i-1])
        count = 0
        outputTimestamps.extend(times)
    bar.next()
bar.finish()

print("\nExtracting frames")

vidcap = cv2.VideoCapture(vid)
fps = vidcap.get(cv2.CAP_PROP_FPS)
success,image = vidcap.read()
count = 0
success = True
previous = 0
failCount = 0
saveImages = []

bar = Bar('Processing', max=len(outputTimestamps))

while failCount < 100:
    success,frame = vidcap.read()
    if not success:
        failCount += 1

    count+=1
    timestamp = count/fps

    if len(outputTimestamps) and outputTimestamps[0] >= previous and outputTimestamps[0] < timestamp:
        #print(f"Export at {timestamp}, Success: {success}")
        if success:
            saveImages.append(frame)
        outputTimestamps.pop(0)
        bar.next()

    previous = timestamp
bar.finish()

#Creating output directory if it does not exist
dirName = "output"

try:
    os.mkdir(dirName)
    #print("Directory " , dirName ,  " Created ") 
except FileExistsError:
    #print("Directory " , dirName ,  " already exists")
    pass

numImages = len(saveImages)
zeros = len(str(numImages))

print(f"\nExporting {numImages+1} images to {dirName}/")

bar = Bar('Processing', max=numImages)
for i in range(numImages):
    name = str(i).zfill(zeros)
    im = saveImages[i]
    cv2.imwrite(f"{dirName}/{name}.png", im)
    bar.next()
bar.finish()
