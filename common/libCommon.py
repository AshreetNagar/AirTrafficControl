from pydantic import BaseModel
import time
from collision import *
import itertools
import math
import data_pb2
import copy

class Aircraft:
    name = ""
    xy = None
    zPos = 0
    velocity = [0,0,0]
    commsUrl = "None"
    def __init__(self,name,xPos,yPos,zPos,radius,velocity,commsUrl="None") -> None:
        self.name = name
        self.xy = Circle(Vector(xPos,yPos),radius)
        self.zPos = zPos
        self.velocity = velocity
        self.commsUrl = commsUrl

    def isCollided(self,ac2) -> bool:
        if not collide(self.xy,ac2.xy):
            return False
        elif (abs(self.xy.radius + ac2.xy.radius) < abs(self.zPos - ac2.zPos)):
            return False
        return True

    def update(self,updatePeriod):
        newX =  self.xy.pos[0] + self.velocity[0]*updatePeriod
        newY =  self.xy.pos[1] + self.velocity[1]*updatePeriod
        self.xy.pos = Vector(newX,newY)
        self.zPos = self.zPos + self.velocity[2]*updatePeriod
        # ac["pos"][i] = ac["pos"][i] + (ac["vel"][i]*updatePeriod)

    def toGrpcAcdata(self):
        acPosPb = data_pb2.position(xPos=self.xy.pos[0],yPos=self.xy.pos[1],zPos=self.zPos)
        acVelPb = data_pb2.velocity(xVel=self.velocity[0],yVel=self.velocity[1],zVel=self.velocity[2])
        acPb = data_pb2.ACData(name=self.name,acPos=acPosPb,acVel=acVelPb,acRad=self.xy.radius,commsUrl=self.commsUrl)
        return acPb
    
    def initFromGrpcAcData(acPb):
        velocity = [acPb.acVel.xVel, acPb.acVel.yVel, acPb.acVel.zVel]
        ac = Aircraft(acPb.name,acPb.acPos.xPos,acPb.acPos.yPos,acPb.acPos.zPos,acPb.acRad,velocity,acPb.commsUrl)
        return ac

    def getPosTuple(self):
        return (self.xy.pos[0],self.xy.pos[1],self.zPos)

    def __str__(self) -> str:
        return f"Aircraft '{self.name}' Position:{[self.xy.pos[0],self.xy.pos[1],self.zPos]} Radius:{self.xy.radius} Velocity:{self.velocity} commsUrl:{self.commsUrl}"

aircraftDict = {
    "p0": Aircraft("p0",0,0,0,10,[0,0,0]),
    "p1": Aircraft("p1",5,5,5,10,[0,0,0]),
}


class Validator:
    aircraftDict = {}

    def __init__(self,validatorLock) -> None:
        self.validatorLock = validatorLock
        pass

    def addAC(self,newAc):
        aircraft = copy.deepcopy(newAc)
        with self.validatorLock:
            if aircraft.name in self.aircraftDict:
                return "Error: Aircraft with same name exists"
            self.aircraftDict[aircraft.name] = aircraft
        return "Success"

    def getACVisibilityListRange(self,name,range):
        visibList = []
        thisAc = self.aircraftDict[name]
        for ac in self.aircraftDict.values():
            if ac == thisAc:
                continue
            dist = math.sqrt((thisAc.xy.pos[0]-ac.xy.pos[0])**2 + (thisAc.xy.pos[1]-ac.xy.pos[1])**2 + (thisAc.zPos-ac.zPos)**2)
            if((dist) < range):
                visibList.append(ac)
        return visibList

    def getVisibilityListPosRange(self,position,range):
        visibList = []
        thisXpos = position.xPos
        thisYpos = position.yPos
        thiszPos = position.zPos
        for ac in self.aircraftDict.values():
            dist = math.sqrt((thisXpos-ac.xy.pos[0])**2 + (thisYpos-ac.xy.pos[1])**2 + (thiszPos-ac.zPos)**2)
            if((dist) < range):
                visibList.append(ac)
        return visibList


    def update(self):
        with self.validatorLock:
            for subset in itertools.combinations(self.aircraftDict.values(), 2):
                if subset[0].isCollided(subset[1]):
                    print(f"Collision between {subset[0]} and {subset[1]}")

            for ac in self.aircraftDict.values():
                ac.update(1)

    def loop(self,updatePeriod, exitEvent):
        while not exitEvent.is_set():
            self.update()
            time.sleep(updatePeriod)
        print("Stopping validator loop ...")

class CommMessageData(BaseModel):
    sender : str 
    recipient : str
    senderChannel : str
    recipientChannel : str
    message : str 
    msgType : str | str = "ACK"
    handled : bool | bool = "False"
    timeSent : int 

class crashMsgData(BaseModel):
    location : str | str = ""



# coordinate system:
# x increases to the right
# y increases going down

parkingCoord = (-2700,3500,0)
rwShape_1836 = (0,0,50,3400)
rwShape_0627 = (-3000,2500,3400,50)
twShape_a = (-2700,3100,2800,25) # connected to 1836
twShape_b = (-2700,2500,25,1000) # connected to 0627
vor1 = (5000,5000,50)

VORs = {
    "1": vor1
}
waypoints = {
    # Land/Takeoff parameters: Line up at z=2500m, Touchdown 300m after field begins , Park at taxiway entrance
    "rw18": [(5000,-1500,2500),(25,-1500,2500),(25,300,0),(25,3125,0)],
    "rw27": [(5000,2525,2500), (100,2525,0), (-2700,2525,0)],
    "twA": [(25,3125,0),(-2700,2500,0),parkingCoord],
    "twB": [(-2700,2525,0),(-2700,2500,0),parkingCoord],
}
waypoints["T/Orw18"] = list(reversed(waypoints["rw18"]))
waypoints["T/Orw27"] = list(reversed(waypoints["rw27"]))
waypoints["DEPARTtwA"] = list(reversed(waypoints["twA"]))
waypoints["DEPARTtwB"] = list(reversed(waypoints["twB"]))




def getAcLogicalState(acData):
    acXYPos = [acData.acPos.xPos, acData.acPos.yPos, acData.acPos.zPos]
    airborne = (acData.acPos.zPos > 0)
    parked = (pointNearPoint(acXYPos,parkingCoord,150))
    atVOR = ""
    for vorID in VORs:
        vor = VORs[vorID]
        if pointNearPoint(vor,acXYPos,range=500,disableZ=True):
            atVOR = f"{vorID}:{acData.acPos.zPos}"

    if airborne:
        if (atVOR != ""):
            return atVOR
        return "Airborne"
    elif parked:
        return "Parked"
    elif pointInBound(acXYPos,rwShape_1836):
        return "RW_1836"
    elif pointInBound(acXYPos,rwShape_0627):
        return "RW_0627"
    elif pointInBound(acXYPos,twShape_a):                
        return "TW_A"
    elif pointInBound(acXYPos,twShape_b):                
        return "TW_B"
    else:
        return "Grounded"


def getAcLogicalStateATC(acData):
    acXYPos = [acData.acPos.xPos, acData.acPos.yPos, acData.acPos.zPos]
    airborne = (acData.acPos.zPos > 0)
    parked = (pointNearPoint(acXYPos,parkingCoord,150))
    landing = pointInBound(acXYPos,rwShape_1836) or pointInBound(acXYPos,rwShape_0627)
    taxiing = pointInBound(acXYPos,twShape_a) or pointInBound(acXYPos,twShape_b)
    if airborne:
        return "Airborne"
    elif parked:
        return "Parked"
    elif landing:
        return "Landing"
    elif taxiing:                
        return "Taxiing"
    else:
        return "Grounded"

def velToPoint1D(pos,pt, rate):
    altitude = pt
    curZ = pos
    deltaZ = altitude - curZ
    if deltaZ == 0:
        return 0
    else:
        direction = deltaZ/abs(deltaZ)
        if abs(deltaZ) > rate:
            return direction*(rate)
        else:
            # return direction*(0.25*(deltaZ**2))
            return direction*(0.25*deltaZ)

def pointNearPoint(pt1, pt2, range, disableZ=False):
    xDist = pt1[0]-pt2[0]
    yDist = pt1[1]-pt2[1]
    if not disableZ:
        zDist = pt1[2]-pt2[2]
    else:
        zDist = 0
    dist = math.hypot(xDist,yDist,zDist)
    if (dist < range):
        return True
    else:
        return False

def pointInBound(point, bound):
    # bound: left, top, width, height
    # pointx: greater than left, less than left+width, 
    # pointy: greater than top, less than top+height
    # print(f"bound conditions {(point[0]>=bound[0])} {(point[0]<=(bound[0]+bound[2]))} {(point[1]>=bound[1])} {(point[1]<=(bound[1]+bound[3]))}")
    if ((point[0]>=bound[0]) and (point[0]<=(bound[0]+bound[2])) and (point[1]>=bound[1]) and (point[1]<=(bound[1]+bound[3]))):
        return True
    else:
        return False
