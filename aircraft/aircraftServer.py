import time
import grpc
import data_pb2
import data_pb2_grpc
import math
import random
import requests

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
import time
import uvicorn
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse 
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from threading import Thread, Event, Lock


import queue

from libCommon import *

import sys

app = FastAPI()
origins = [
    "*",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Objects
## Aircraft Parameters
    #  
## Engine State
    # Multiple engines
## Pitch
## Roll
## Yaw
## Aircraft State
    # did it crash
## ATC Messages
    # Incoming ATC messages
    # Outgoing responses
## Simulated Pilot State
    # Off: User controls
    # On: Automatically flies based of ATC messages, visible aircraft, and goals 

# Requirements

## Be initialized with certain characteristics

## Take pitch, roll, yaw, engine and aircraft states to set velocity

## Enable / Disable Simulated pilot

## Received ATC message, determine if it is an ACK or a command

## Respond to ATC message, determine if response is ACK or information

## Respond to validator notification that aircraft has crashed and handle inputs accordingly

## 

class AircraftParametersData(BaseModel):
    acName: str | str = "test1"
    engineCount: int | int = 1
    massKg : float | float = 1000
    dragConst : float | float = 0.1
    autopilotMode : str | str = "DISABLED"
class engineStateData(BaseModel):
    engineNum: int | int = 0
    thrust: float | float = 0

class AircraftStateData(BaseModel):
    pitch: float | float = 0
    yaw: float | float = 0
    roll: float | float = 0

class AircraftConfigData(BaseModel):
    gRPCAddress: str | str = ""
    acName: str | str = "test1"
    acLoc: str | str = "Parked"
    acCommsUrl: str

acConfig = {
    "gRPCAddress" : "localhost",
    "initialized" : False,
    "acLoc": "Parked",
    "acCommsUrl":"http://127.0.0.1:8001"
}

@app.get("/config")
async def get_messageLog():
    return {"status_code":status.HTTP_200_OK, "content":acConfig}

@app.post("/config")
async def post_message(newMessage: AircraftConfigData):
    if (newMessage.gRPCAddress != ""):
        acConfig["gRPCAddress"] = newMessage.gRPCAddress
    if (newMessage.acLoc != ""):
        acConfig["acLoc"] = newMessage.acLoc
    if (newMessage.acCommsUrl != ""):
        acConfig["acCommsUrl"] = newMessage.acCommsUrl
    if (newMessage.acName != ""):
        acParams[0].acName = newMessage.acName
        acConfig["initialized"] = False
    
    return {"status_code":status.HTTP_200_OK, "content":acConfig}




acParams = {0:AircraftParametersData()}
enginesState = {0:engineStateData()}
acState = {0:AircraftStateData()}
msgLog = {}
commMessageQueue = {}
activeCommand = {}
autopilotState = {
    "state":"Airborne",
    "stateTransition":"0",
    "internalState":"",
    "navIdx":-1,
    "navRoute":""
}

app.mount("/client", StaticFiles(directory="static",html = True), name="static")

# AC Param Endpoints
@app.get("/acParams")
async def get_acParams():
    return {"status_code":status.HTTP_200_OK, "content":acParams[0]}

@app.put("/acParams")
async def get_acParams(newAcParams: AircraftParametersData):
    acParams[0] = newAcParams
    newAcRPC(acParams[0].acName,acConfig["acCommsUrl"])
    return JSONResponse(status_code=status.HTTP_200_OK)

# Engine Endpoints
@app.get("/engine")
async def get_engines():
    return {"status_code":status.HTTP_200_OK, "content":enginesState}

@app.get("/engine/{id}")
async def get_engine(id: int):
    return {"status_code":status.HTTP_200_OK, "content":enginesState[id]}

@app.patch("/engine/{id}")
async def update_engine(id: int, newEngineState: engineStateData):
    enginesState[id].thrust = newEngineState.thrust
    return {"status_code":status.HTTP_200_OK, "content":enginesState[id]}

# Aircraft State Endpoints
@app.get("/acState")
async def get_acState():
    return {"status_code":status.HTTP_200_OK, "content":acState[0]}

@app.put("/acState")
async def set_acState(newAcState: AircraftStateData):
    acState[0] = newAcState
    return {"status_code":status.HTTP_200_OK, "content":acState[0]}

# Message Log Endpoints
@app.get("/log/msg")
async def get_messageLog():
    return {"status_code":status.HTTP_200_OK, "content":msgLog}

@app.post("/log/msg")
async def post_message(newMessage: CommMessageData):
    newMessage.timeSent = time.time_ns()
    # Get comm channel from validator and send message over it
    msgLog[newMessage.timeSent] = newMessage
    return {"status_code":status.HTTP_200_OK, "content":newMessage}


# Message Queue Endpoints
@app.get("/queue/msg")
async def get_messageQueue():
    return {"status_code":status.HTTP_200_OK, "content":commMessageQueue}

@app.put("/queue/msg")
async def put_messageQueue(newMessage: CommMessageData):
    if len(commMessageQueue) == 0:
        print("no other messages in queue")
        commMessageQueue[0] = newMessage
        return {"status_code":status.HTTP_200_OK, "content":{0:newMessage}}
    else:
        msgId = max(commMessageQueue.keys())+1
        print(f"{commMessageQueue} other messages in queue, new msg id {msgId}")
        commMessageQueue[msgId] = newMessage
        return {"status_code":status.HTTP_200_OK, "content":{msgId:newMessage}}

@app.delete("/queue/msg/{id}")
async def handle_message(id: int):
    msg = commMessageQueue[id]
    msgLog[msg.timeSent] = msg
    commMessageQueue.pop(id)
    return msg


# gRPC helpers
def newAcRPC(acName,acCommsUrl,xPos=100,yPos=100,zPos=1000):
    if zPos == "Airborne":
        zPos = random.randrange(1000,10000)
    with grpc.insecure_channel(f'{acConfig["gRPCAddress"]}:50051') as channel:
        stub = data_pb2_grpc.validatorStub(channel)
        newVel = data_pb2.velocity(xVel=0,yVel=0,zVel=0)
        newPos = data_pb2.position(xPos=xPos,yPos=yPos,zPos=zPos)
        newRad = 50
        newAcData = data_pb2.ACData(name=acName,acPos=newPos,acVel=newVel, acRad=newRad, commsUrl=acCommsUrl)
        response = stub.AcAdd(newAcData)
        # print(response.status)

def setVelocityRPC(xVel,yVel,zVel,acName):
    with grpc.insecure_channel(f'{acConfig["gRPCAddress"]}:50051') as channel:
        stub = data_pb2_grpc.validatorStub(channel)
        dir = data_pb2.velocity(xVel=xVel,yVel=yVel,zVel=zVel)
        newVel = data_pb2.AcUpdateReq(name=acName,newAcVel=dir)
        resp = stub.AcUpdateVel(newVel)
        # print(resp.status)

def getVisibleAcRPC(range):
    with grpc.insecure_channel(f'{acConfig["gRPCAddress"]}:50051') as channel:
        stub = data_pb2_grpc.validatorStub(channel)
        visibReq = data_pb2.VisiblityGetReq(name=acName,reqRange=range)
        print(stub.VisiblityGet(visibReq))


class Vector():
    x = 0
    y = 0
    z = 0
    def __init__(self,x=0,y=0,z=0):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self) -> str:
        return f"X:{self.x} Y:{self.y} Z:{self.z}"


def ackMessage(msg,newMsgText):
    msgUrl = msg.senderChannel
    msgData = {
        "sender" :  acParams[0].acName,
        "recipient" : msg.sender ,
        "message" : newMsgText,
        "msgType" : "ACK",
        "handled" : "True",
        "recipientChannel" : msg.senderChannel,
        "senderChannel" : msg.recipientChannel ,
        "timeSent" : int(time.time())
    }
    resp = requests.put(url=msgUrl,json=msgData)
    print(resp.status_code)
    print(resp.content)


def apHoldVor(acData, commandList):
    if autopilotState["stateTransition"] != "0":
        # print(f"Autopilot State Transition: Active command {commandList}")
        autopilotState["stateTransition"] = "0"
    newVel = [0,0,0]
    # Calculate vertical rate
    newVel[2] = velToPoint1D(acData.acPos.zPos,float(commandList[2]),25)

    # Calculate Heading
    vorDict = {
        "VOR1" : vor1
    }
    vor_location = vorDict[commandList[1]]
    ac_location = (acData.acPos.xPos,acData.acPos.yPos)
    hold_radius = 2000
    speed = 100
    vec_toCenter = [0,0]   
    vec_perp = [0,0]
    vec_toCenter[0] = (-ac_location[0]+vor_location[0]) / math.hypot(ac_location[0],vor_location[0])       
    vec_toCenter[1] = (-ac_location[1]+vor_location[1]) / math.hypot(ac_location[1],vor_location[1])
    vec_perp[0] = vec_toCenter[1]
    vec_perp[1] = -vec_toCenter[0]
    newVel[0] = (vec_toCenter[0]+vec_perp[0])*speed
    newVel[1] = (vec_toCenter[1]+vec_perp[1])*speed    
    return newVel

# Navigating routes
# List of waypoints, navigate towards them
# When within range of a point (50m?), increment list idx
# 

def navigateWaypoints(acData,hVel=25,vVel=25):
    newVel = [0,0,0]
    curPos = Aircraft.initFromGrpcAcData(acData).getPosTuple()
    navRoute = waypoints[autopilotState["navRoute"]]
    navIdx = autopilotState["navIdx"]
    wayPt = navRoute[navIdx]
    for idx in range(0,2):
        newVel[idx] = velToPoint1D(curPos[idx],wayPt[idx],hVel)
    newVel[2] = velToPoint1D(curPos[2],wayPt[2],vVel)
    print(f"Pos{curPos} Wpt{navRoute[navIdx]} ")
    if pointNearPoint(curPos,navRoute[navIdx],100):
        navIdx+=1
        autopilotState["navIdx"] = navIdx
        print(f"Autopilot Waypoint Increment: Active Destination {wayPt[idx]}")
    return newVel

def apLand(acData, commandList):
    if autopilotState["stateTransition"] != "0":
        autopilotState["navIdx"] = 0
        autopilotState["navRoute"] = "rw"+commandList[2]
        autopilotState["stateTransition"] = "0"
        print(f"Autopilot State Transition: Active command {commandList}")

    newVel = navigateWaypoints(acData,300,1000)
    if (autopilotState["navIdx"] >= len(waypoints[autopilotState["navRoute"]])):
        activeCommand[0].message = "PARK"
        newVel = [0,0,0]
    return newVel
def apTakeoff(acData, commandList):
    if autopilotState["stateTransition"] != "0":
        autopilotState["navIdx"] = 0
        autopilotState["navRoute"] = "T/Orw"+commandList[2]
        autopilotState["stateTransition"] = "0"
        print(f"Autopilot State Transition: Active command {commandList}")

    newVel = navigateWaypoints(acData,300,1000)
    if (autopilotState["navIdx"] >= len(waypoints[autopilotState["navRoute"]])):
        activeCommand[0].message = "HOLD VOR1 10000"
        newVel = [0,0,0]
    return newVel

def apTaxiParking(acData, commandList):
    if autopilotState["stateTransition"] != "0":
        autopilotState["navIdx"] = 0
        autopilotState["navRoute"] = "tw"+commandList[3]
        autopilotState["stateTransition"] = "0"
        print(f"Autopilot State Transition: Active command {commandList}")

    newVel = navigateWaypoints(acData,300,1000)
    if (autopilotState["navIdx"] >= len(waypoints[autopilotState["navRoute"]])):
        activeCommand[0].message = "PARK"
        newVel = [0,0,0]
    return newVel
def apTaxiRunway(acData, commandList):
    if autopilotState["stateTransition"] != "0":
        autopilotState["navIdx"] = 0
        autopilotState["navRoute"] = "DEPARTtw"+commandList[3]
        autopilotState["stateTransition"] = "0"
        print(f"Autopilot State Transition: Active command {commandList}")

    newVel = navigateWaypoints(acData,300,1000)
    if (autopilotState["navIdx"] >= len(waypoints[autopilotState["navRoute"]])):
        activeCommand[0].message = "PARK"
        newVel = [0,0,0]
    return newVel

def acLoop(updatePeriod, updateLock, exitEvent):
    while not exitEvent.is_set():
        # Attempt a gRPC connection
        gRPCWait()
        if not acConfig["initialized"]:
            gRPCWait()
            acParams[0].autopilotMode = "ENABLED"
            if acConfig["acLoc"] == "Parked":
                newAcRPC(acParams[0].acName,acConfig["acCommsUrl"],xPos=parkingCoord[0],yPos=parkingCoord[1],zPos=0)
            else:
                newAcRPC(acParams[0].acName,acConfig["acCommsUrl"], zPos="Airborne")
            acConfig["initialized"] = True
        
        with updateLock:
            acData = None
            with grpc.insecure_channel(f'{acConfig["gRPCAddress"]}:50051') as channel:
                stub = data_pb2_grpc.validatorStub(channel)
                acData = (stub.AcGet(data_pb2.AcGetReq(name=acParams[0].acName)))
            if acData == None:
                newAcRPC(acParams[0].acName,acConfig["acCommsUrl"])
                continue
            
            # Autopilot
            if acParams[0].autopilotMode == "ENABLED":
                newVel = [0,0,0]
                while (len(commMessageQueue) != 0):
                    # Load Message
                    id = min(commMessageQueue.keys())
                    msg = commMessageQueue[id]
                    msgLog[msg.timeSent] = msg
                    commMessageQueue.pop(id)
                    if msg.msgType == "ACK":
                        continue
                    
                    # Check validity
                    ## Get Aircraft state (Airborne, Landing, holding short runway, Parked)
                    autopilotState["state"] = getAcLogicalState(acData)

                    command = msg.message
                    # Respond to message
                    validCmd = True
                    if command.startswith("HOLD VOR") :
                        if (autopilotState["state"] != "Airborne"):
                            ackMessage(msg,"Unable to comply: Not Airborne")
                            validCmd = False
                        elif (command.split()[2] not in VORs):
                            ackMessage(msg,"Unable to comply: Invalid VOR")
                            validCmd = False
                    elif command.startswith("CLEAR LAND"):
                        if (autopilotState["state"] != "Airborne"):
                            ackMessage(msg,"Unable to comply: Not Airborne")
                            validCmd = False
                        elif ("rw"+command.split()[2] not in waypoints):
                            ackMessage(msg,"Unable to comply: Invalid Runway")
                            validCmd = False
                    elif command.startswith("CLEAR TAKEOFF"):
                        if (autopilotState["state"] != "Landing") and (autopilotState["state"] != "Taxiing"):
                            ackMessage(msg,"Unable to comply: Not at runway")
                            validCmd = False
                    elif command.startswith("CLEAR TAXI PARKING"):
                        if (autopilotState["state"] != "Landing"):
                            ackMessage(msg,"Unable to comply: Not Landed")
                            validCmd = False
                        elif ("tw"+command.split()[3] not in waypoints):
                            ackMessage(msg,"Unable to comply: Invalid Taxiway")
                            validCmd = False
                    elif command.startswith("CLEAR TAXI RUNWAY"):
                        if (autopilotState["state"] != "Parked"):
                            ackMessage(msg,"Unable to comply: Not Parked")
                            validCmd = False
                        elif ("tw"+command.split()[3] not in waypoints):
                            ackMessage(msg,"Unable to comply: Invalid Taxiway")
                            validCmd = False
                    else:
                        ackMessage(msg,"Unable to comply: Invalid Command")
                    if validCmd:                    
                        ackMessage(msg,f"{acParams[0].acName} {msg.message}")
                        activeCommand[0] = msg
                        autopilotState["stateTransition"] = activeCommand[0].message
                
                autopilotState["state"] = getAcLogicalState(acData)


                # Get Latest Command
                if len(activeCommand) == 0:
                    if autopilotState["state"] == "Airborne":
                        command = "HOLD VOR1 10000"      
                        autopilotState["stateTransition"] = command                  
                    elif autopilotState["state"] == "Parked":
                        command = "PARK"
                        autopilotState["stateTransition"] = command                  
                    elif autopilotState["state"] == "Landing":
                        command = "PARK"
                        autopilotState["stateTransition"] = command                  
                    elif autopilotState["state"] == "Taxiing":                
                        command = "PARK"
                        autopilotState["stateTransition"] = command                  

                else:
                    command = activeCommand[0].message
                commandList =  command.split()
                if command.startswith("HOLD VOR"):
                    newVel = apHoldVor(acData, commandList)
                elif command.startswith("CLEAR LAND"):
                    newVel = apLand(acData,commandList)
                elif command.startswith("CLEAR TAKEOFF"):
                    newVel = apTakeoff(acData,commandList)
                elif command.startswith("CLEAR TAXI PARKING"):
                    newVel = apTaxiParking(acData,commandList)
                elif command.startswith("CLEAR TAXI RUNWAY"):
                    newVel = apTaxiRunway(acData,commandList)
                elif command == "PARK":
                    if autopilotState["stateTransition"] != "0":
                        print(f"Autopilot State Transition: Active command {commandList}")
                        autopilotState["stateTransition"] = "0"
                    newVel = [0,0,0]
                setVelocityRPC(newVel[0],newVel[1],newVel[2] ,acParams[0].acName)

            if acParams[0].autopilotMode == "DISABLED":
                vectors = []
                velVector = Vector(acData.acVel.xVel,acData.acVel.yVel,acData.acVel.zVel)
                print(f"original velocity {velVector}")
                vectors.append(velVector)
                
                # Gravity
                if acData.acPos.zPos > 0:
                    vectors.append(Vector(0,0,(9.8*updatePeriod)))

                # Drag
                vectors.append(Vector(-(velVector.x*acParams[0].dragConst),-(velVector.y*acParams[0].dragConst),-(velVector.z*acParams[0].dragConst)))

                # Thrust
                thrust = 0
                for engine in enginesState.values():
                    thrust += engine.thrust/2
                t_magnitude = thrust*0.5
                zThrustVel = t_magnitude*math.sin(acState[0].pitch)
                yThrustVel = t_magnitude*math.cos(acState[0].pitch)*math.sin(acState[0].yaw)
                xThrustVel = t_magnitude*math.cos(acState[0].pitch)*math.cos(acState[0].yaw)
                thrustVec = Vector(xThrustVel,yThrustVel,zThrustVel)
                vectors.append(thrustVec)

                newVel = Vector() 
                for vec in vectors:
                    newVel.x += vec.x
                    newVel.y += vec.y
                    newVel.z += vec.z                

                newVel.x = max(-55,min(newVel.x,55))
                newVel.y = max(-55,min(newVel.y,55))
                newVel.z = max(-55,min(newVel.z,55))                


                print(f"new vel {newVel}")
                setVelocityRPC(newVel.x,newVel.y,newVel.z,acParams[0].acName)
            # with grpc.insecure_channel(f'{acConfig["gRPCAddress"]}:50051') as channel:
            #     newVel = data_pb2.velocity(xVel=newVel.x,yVel=newVel.y,zVel=newVel.z)
            #     acUpdate = data_pb2.AcUpdateReq(name=acParams[0].acName, newAcVel=newVel)
            #     stub = data_pb2_grpc.validatorStub(channel)
            #     acData = (stub.AcGet(acUpdate))            


        time.sleep(updatePeriod)

def gRPCWait():
    gRPCAvailable = False
    while not gRPCAvailable:
        try:
            with grpc.insecure_channel(f'{acConfig["gRPCAddress"]}:50051') as channel:
                stub = data_pb2_grpc.validatorStub(channel)
                towerPos = data_pb2.position(xPos=0,yPos=0,zPos=50)
                reqData = data_pb2.VisiblityGetReq(reqPos=towerPos, reqRange=0)
                response = stub.VisiblityGet(reqData)
            gRPCAvailable = True
        except Exception as e:
            gRPCAvailable = False
        if not gRPCAvailable:
            time.sleep(1)

@app.on_event("startup")
async def startup_event():
        
    updatePeriod = 0.5
    updateLock = Lock()
    exitEvent = Event()
    print("startup here",file=sys.stderr)
    updateThread = Thread(group=None,target=acLoop,args=(updatePeriod,updateLock,exitEvent))
    updateThread.start()
    print(f"Aircraft {acParams[0].acName} connection established")

if __name__ == "__main__":
    # if len(sys.argv) == 2:
        # acName = sys.argv[1]
    # print(f"acname {acName}")
    uvicorn.run("aircraftServer:app", host="0.0.0.0", port=8001, reload=True)
    # exitEvent.set()
    