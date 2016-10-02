import numpy
import math

global displayableChars, displayableCharLen, brightnessPerStep
displayableChars = " .\'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
displayableCharLen = len(displayableChars)
brightnessPerStep = 255 / displayableCharLen


def getBrightnessMap2(imageArr, width, height):
    xGroups = math.floor(len(imageArr[0]) / width)
    yGroups = math.floor(len(imageArr) / height)
    width = math.floor(width)
    height = math.floor(height)
    subgroups = []
    for y in range(yGroups):
        subgroup = []
        yHeight = y * height
        for x in range(xGroups):
            tempSum = 0
            xWidth = x * width
            for h in range(yHeight, yHeight + height):
                for w in range(xWidth, xWidth + width):
                    tempSum += imageArr[h][w][0]
            subgroup.append(convertBrightnessValue(tempSum / (width * height)))
        subgroups.append("".join(subgroup))

    return subgroups


def convertBrightnessValue(bValue):
    return displayableChars[int(bValue / brightnessPerStep)]

def getCharMap(data, width, height):
    widthPerSquare = len(data[0]) / width
    heightPerSquare = len(data) / height
    brightness = getBrightnessMap2(data, widthPerSquare, heightPerSquare)
#    result = ["".join(map(convertBrightnessValue, bRow)) for bRow in brightness]
    return brightness
