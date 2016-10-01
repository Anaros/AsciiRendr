import numpy
import math

global displayableChars, displayableCharLen, brightnessPerStep
displayableChars = " .\'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
displayableCharLen = len(displayableChars)
brightnessPerStep = 765 / displayableCharLen

def getBrightnessMap2(imageArr, width, height):
    xGroups = math.floor(len(imageArr[0]) / width)
    yGroups = math.floor(len(imageArr) / height)
    width = math.floor(width)
    height = math.floor(height)
    subgroups = numpy.zeros(shape=(yGroups, xGroups))
    for y in range(yGroups):
        for x in range(xGroups):
            tempSum = 0
            for h in range(height):
                for w in range(width):
                    tempSum += sum(imageArr[y * height + h][x * width + w])

            subgroups[y][x] = tempSum / (width * height)

    return subgroups

def getCharMap(data, width, height):
    widthPerSquare = len(data[0]) / width
    heightPerSquare = len(data) / height
    brightness = getBrightnessMap2(data, widthPerSquare, heightPerSquare)
    result = []
    for r in range(height):
        row = ""
        for c in range(width):
            index = min(displayableCharLen - 1, int(brightness[r][c] / brightnessPerStep))
            row += displayableChars[index]
        result.append(row)
    return result
