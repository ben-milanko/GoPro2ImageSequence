import pandas as pd
import cv2
import os
from os import listdir
from os.path import isfile, join
from progress.bar import Bar
import subprocess
import sys
import json
import math
#import exif
#from exif import Image
import piexif
from fractions import Fraction
from datetime import datetime


imageDistance = 0.01

intro = f"""
video2photo.py

version:    1.0
author:     Benjamin Milanko
updated:    2020/02/29

description:
    Takes a GoPro video file and extracts an image every {imageDistance} km, the program uses the internal GoPro GPS data using an external library from stilldavid
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

#rad
#arguments: x, a float value in degrees
#output: the equivalant value in radians
#note: 
def rad(x):
  return x * math.pi / 180

#dist
#arguments: p1, p2; points defined as [latitude, longitude]
#output: the distance in kilometers as a float
#note: 
def dist(p1, p2):
  R = 6378137 # Earth’s mean radius in meter
  dLat = rad(math.fabs(p2[0] - p1[0]))
  dLong = rad(math.fabs(p2[1] - p1[1]))
  a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(rad(p1[0])) * math.cos(rad(p2[0])) * math.sin(dLong / 2) * math.sin(dLong / 2)
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
  d = R * c
  return d/1000 # returns the distance in kilometers

def to_deg(value, loc):
    """convert decimal coordinates into degrees, munutes and seconds tuple
    Keyword arguments: value is float gps-value, loc is direction list ["S", "N"] or ["W", "E"]
    return: tuple like (25, 13, 48.343 ,'N')
    """
    if value < 0:
        loc_value = loc[0]
    elif value > 0:
        loc_value = loc[1]
    else:
        loc_value = ""
    abs_value = abs(value)
    deg =  int(abs_value)
    t1 = (abs_value-deg)*60
    min = int(t1)
    sec = round((t1 - min)* 60, 5)
    return (deg, min, sec, loc_value)


def change_to_rational(number):
    """convert a number to rantional
    Keyword arguments: number
    return: tuple like (1, 2), (numerator, denominator)
    """
    f = Fraction(str(number))
    return (f.numerator, f.denominator)


def set_gps_location(file_name, lat, lng, altitude, timestamp):
    """Adds GPS position as EXIF metadata
    Keyword arguments:
    file_name -- image file
    lat -- latitude (as float)
    lng -- longitude (as float)
    altitude -- altitude (as float)
    """
    lat_deg = to_deg(lat, ["S", "N"])
    lng_deg = to_deg(lng, ["W", "E"])

    exiv_lat = (change_to_rational(lat_deg[0]), change_to_rational(lat_deg[1]), change_to_rational(lat_deg[2]))
    exiv_lng = (change_to_rational(lng_deg[0]), change_to_rational(lng_deg[1]), change_to_rational(lng_deg[2]))

    #print(exiv_lat, exiv_lng)

    zeroth_ifd = {piexif.ImageIFD.Software: u"video2photo"}
                
    gps_ifd = {
        piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
        piexif.GPSIFD.GPSLatitudeRef: lat_deg[3],
        piexif.GPSIFD.GPSLatitude: exiv_lat,
        piexif.GPSIFD.GPSLongitudeRef: lng_deg[3],
        piexif.GPSIFD.GPSLongitude: exiv_lng,
        #piexif.GPSIFD.GPSAltitudeRef: 1,
        #piexif.GPSIFD.GPSAltitude: change_to_rational(round(altitude)),
    }

    #print(gps_ifd)

    dt = datetime.fromtimestamp(timestamp).strftime("%Y:%m:%d %H:%M:%S")

    dt = dt.encode("utf-8")

    exif_ifd = {piexif.ExifIFD.DateTimeOriginal: dt}

    #exif_dict = {"GPS":gps_ifd}
    exif_dict = {"0th":zeroth_ifd, "Exif":exif_ifd, "GPS":gps_ifd}

    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, file_name)

cwd = os.getcwd() #Current working directory

files = [f for f in listdir(cwd) if isfile(join(cwd, f))] #Iterates through

for each in files:
    split = each.split(".")
    if len(split) > 1:
        if split[1] == "MP4":
            vid = each
            metaBinary = f"{split[0]}.bin"
            metaJson = f"{split[0]}.json"
            vidFile = split[0]

try:
    print(f"Identified video file {vid}\n")
except NameError:
    print("Could not find video file, exiting")
    sys.exit()

subprocess.call(["ffmpeg", "-y", "-i", vid, "-codec", "copy", "-map", "0:3:handler_name:' GoPro MET'", "-f", "rawvideo", metaBinary],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print(f"Successfully extracted metadata from {vid}\n")

subprocess.call(f"go run ~/go/src/github.com/stilldavid/gopro-utils/bin/gopro2json/gopro2json.go -i {metaBinary} -o {metaJson}", shell=True)

print(f"Converted binary metadata to JSON")

with open(metaJson) as f:
  data = json.load(f)

data = data['data'] 

lat = []
lon = []
alt = []

time = []
distance = []
first = 0

for i in range(len(data)):
    
    timeStamp = data[i]['utc']/1000000

    if i == 0:
        first = timeStamp
        tempDistance = 0
    else:
        p1 = [data[i-1]['lat'],data[i-1]['lon']]
        p2 = [data[i]['lat'],data[i]['lon']]

        tempDistance = dist(p1,p2)
    
    lat.append(data[i]['lat'])
    lon.append(data[i]['lon'])
    alt.append(data[i]['alt'])

    timeStamp = (timeStamp-first)
    time.append(timeStamp)
    distance.append(tempDistance)

outputLat = []
outputLon = []
outputAlt = []

outputTimestamps = []

print("\nInterpolating timestamps")
bar = Bar('Processing', max=len(distance)-1, suffix = '%(index)d/%(max)d - %(eta)ds')

count = 0
for i in range(0,len(distance)):
    count += (distance[i])
    if count > 0.010:
        count = 0
        outputTimestamps.append(time[i])
        
        outputLat.append(lat[i])
        outputLon.append(lon[i])
        outputAlt.append(alt[i])

    bar.next()
bar.finish()


vidcap = cv2.VideoCapture(vid)
fps = vidcap.get(cv2.CAP_PROP_FPS)
success,image = vidcap.read()
count = 0
success = True
previous = 0
failCount = 0
total = 0

allImages = []

saveLat = []
saveLon = []
saveAlt = []
saveTime = []

dontBreak = 0

#Creating output directory if it does not exist
dirName = f"{vidFile}_output"

try:
    os.mkdir(dirName)
    #print("Directory " , dirName ,  " Created ") 
except FileExistsError:
    #print("Directory " , dirName ,  " already exists")
    pass

# set_gps_location(f"{dirName}/000.jpeg", outputLat[1], outputLon[1], outputAlt[1], outputTimestamps[1]+first)
# print(f"{dirName}/000.jpeg", outputLat[200], outputLon[200], outputAlt[200], outputTimestamps[200]+first)
# print(f"{dirName}/000.jpeg", outputLat[0], outputLon[0], outputAlt[0], outputTimestamps[0]+first)
# print(f"{dirName}/000.jpeg", outputLat[1], outputLon[1], outputAlt[1], outputTimestamps[1]+first)

print(f"\n{len(outputTimestamps)} Images to be extracted to {dirName}/, images are exported in batches of 100")

while(len(outputTimestamps)>0):

    saveImages = []

    if len(outputTimestamps) > 100:
        l = 100
    else:
        l = len(outputTimestamps)

    #print("Extracting frames")

    bar = Bar('Extracting frames', max=l, suffix = '%(index)d/%(max)d - %(eta)ds')

    while failCount < 100 and dontBreak < 100:
        success,frame = vidcap.read()
        if not success:
            failCount += 1

        count+=1
        timestamp = count/fps

        if len(outputTimestamps) and outputTimestamps[0] >= previous and outputTimestamps[0] < timestamp:
            #print(f"Export at {timestamp}, Success: {success}")
            if success:
                saveImages.append(frame)
                
                saveLat.append(outputLat.pop(0))
                saveLon.append(outputLon.pop(0))
                saveAlt.append(outputAlt.pop(0))
                saveTime.append(outputTimestamps[0])

                dontBreak += 1

            outputTimestamps.pop(0)
            bar.next()

        previous = timestamp
    bar.finish()


    num = len(outputTimestamps)
    numImages = len(saveImages)
    zeros = len(str(num))

    #print(f"Exporting images to {dirName}/")

    bar = Bar(f"Exporting images ", max=numImages, suffix = '%(index)d/%(max)d - %(eta)ds')
    for i in range(numImages):
        name = str(total).zfill(zeros)
        im = saveImages[i]
        file_name = f"{dirName}/{name}.jpeg"
        
        allImages.append(file_name)

        cv2.imwrite(file_name, im)

        total += 1

        #print(file_name, saveLat[0], saveLon[0], saveAlt[0], saveTime[0]+first)
        #set_gps_location(file_name, saveLat.pop(0), saveLon.pop(0), saveAlt.pop(0), saveTime.pop(0)+first)

        bar.next()
    bar.finish()

    dontBreak = 0

print(f"\nEncoding GPS and timestamp data")
bar = Bar('Processing', max=len(allImages), suffix = '%(index)d/%(max)d - %(eta)ds')

for i in range(len(allImages)):
    set_gps_location(allImages[i], saveLat[i], saveLon[i], saveAlt[i], saveTime[i]+first)

    bar.next()

bar.finish()
