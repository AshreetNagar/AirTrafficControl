import requests
import time
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
import grpc
import data_pb2
import data_pb2_grpc

from libCommon import *




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

atcSetup = {
    "gRPCAddress" : "localhost",
}
msgLog = {}
commMessageQueue = {}
atcState = {
    "acRequests": {}, # What each aircraft would like to do
    "acExpectedStates" : {}, # Where each aircraft should be
    "acActualStates" : {}, # Where each aircraft actually is
    "actualAcsAtVor" : {},
    "runwayOccupant" :{
        "rw18/twA": "",
        "rw27/twB": "",
    },
}


class ConfigData(BaseModel):
    gRPCAddress: str | str = ""

@app.get("/config")
async def get_messageLog():
    return {"status_code":status.HTTP_200_OK, "content":atcSetup}

@app.post("/config")
async def post_message(newMessage: ConfigData):
    if (newMessage.gRPCAddress != ""):
        atcSetup["gRPCAddress"] = newMessage.gRPCAddress
    return {"status_code":status.HTTP_200_OK, "content":atcSetup}


app.mount("/client", StaticFiles(directory="static",html = True), name="static")
# Message Log Endpoints
@app.get("/log/msg")
async def get_messageLog():
    return {"status_code":status.HTTP_200_OK, "content":msgLog}

@app.post("/log/msg")
async def post_message(newMessage: CommMessageData):
    newMessage.timeSent = time.time_ns()
    # Get comm channel from validator and send message over it
    acUrl = None
    try:
        with grpc.insecure_channel(f'{atcSetup["gRPCAddress"]}:50051') as channel:
            stub = data_pb2_grpc.validatorStub(channel)
            towerPos = data_pb2.position(xPos=rwShape_1836[0],yPos=rwShape_0627[1],zPos=50)
            reqData = data_pb2.VisiblityGetReq(reqPos=towerPos, reqRange=60000)
            response = stub.VisiblityGet(reqData)
            for ac in response.aircraftList:
                if ac.name == newMessage.recipient:
                    acUrl = ac.commsUrl + '/queue/msg'
    except Exception as e:
        return {"status_code":status.HTTP_500_INTERNAL_SERVER_ERROR, "content":"Unable to contact gRPC server"}
    if (acUrl == None) or (acUrl == "None"):
        return {"status_code":status.HTTP_400_BAD_REQUEST, "content":f"Unable to contact aircraft {ac.name}"}

    msgData = {
        "sender" : newMessage.sender ,
        "recipient" : newMessage.recipient ,
        "message" : newMessage.message,
        "msgType" : newMessage.msgType,
        "handled" : newMessage.handled,
        "timeSent" : newMessage.timeSent,
        "senderChannel" : newMessage.senderChannel,
        "recipientChannel" : acUrl
    }
    resp = requests.put(url=acUrl,json=msgData)
    print(resp.status_code)
    print(resp.content)
    msgLog[newMessage.timeSent] = newMessage
    return {"status_code":status.HTTP_200_OK, "content":msgData}


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



def autoATC(updatePeriod,updateLock,exitEvent):
    while not exitEvent.is_set():
        # Attempt a gRPC connection
        gRPCAvailable = False
        try:
            with grpc.insecure_channel(f'{atcSetup["gRPCAddress"]}:50051') as channel:
                stub = data_pb2_grpc.validatorStub(channel)
                towerPos = data_pb2.position(xPos=0,yPos=0,zPos=50)
                reqData = data_pb2.VisiblityGetReq(reqPos=towerPos, reqRange=0)
                response = stub.VisiblityGet(reqData)
            gRPCAvailable = True
        except Exception as e:
            gRPCAvailable = False
        if not gRPCAvailable:
            time.sleep(1)
            print(f"gRPC unavailable at {atcSetup['gRPCAddress']}")
            continue

        with updateLock:
            # Call gRPC for planes in range
            inRangeAcDict= {}
            with grpc.insecure_channel(f'{atcSetup["gRPCAddress"]}:50051') as channel:
                stub = data_pb2_grpc.validatorStub(channel)
                towerPos = data_pb2.position(xPos=rwShape_1836[0],yPos=rwShape_0627[1],zPos=50)
                reqData = data_pb2.VisiblityGetReq(reqPos=towerPos, reqRange=60000)
                response = stub.VisiblityGet(reqData)
                for ac in response.aircraftList:
                    inRangeAcDict[ac.name] = {}
                    inRangeAcDict[ac.name]["grpc"] = ac
                    inRangeAcDict[ac.name]["acClass"] = (Aircraft.initFromGrpcAcData(ac))
        
            vorOccupancy = {}
            rwOccupancies = {}


            # Update state of aircraft
            for acName in inRangeAcDict:
                ac = inRangeAcDict[acName]
                acState = getAcLogicalState(ac["grpc"])
                if (acState == "RW_1836") or (acState == "TW_A"):
                    rwOccupancies["rw18/twA"] = ac
                elif (acState == "RW_0627") or (acState == "TW_B"):
                    rwOccupancies["rw27/twB"] = ac
                
                atcState["acActualStates"][acName] = acState


            # Basic dispatcher:
            # If at VOR: dispatch to land at a runway
                # Note that aircraft is "occupying" a runway and its taxiway
            # If at runway: dispatch to corresponding taxiway
            # Once parked: remove from occupation list
            # for vorID in VORs:
                # acAtVorDict = atcState["actualAcsAtVor"][vorID]


            # Request Types and states
                # Request Land
                    # Holding VOR, Landing (airborne), Landed, Taxiing, Parked 
                # Request Takeoff

            print(atcState)

        time.sleep(updatePeriod)



@app.on_event("startup")
async def startup_event():
    
    # acParams[0].acName = "apTest1"#str(random.random())
    # acParams[0].autopilotMode = "ENABLED"
    # newAcRPC(acParams[0].acName)
    
    updatePeriod = 0.5
    updateLock = Lock()
    exitEvent = Event()
    updateThread = Thread(group=None,target=autoATC,args=(updatePeriod,updateLock,exitEvent))
    updateThread.start()
    # print(f"Aircraft {acParams[0].acName} connection established")


if __name__ == "__main__":
    uvicorn.run("atcTower:app", host="0.0.0.0", port=8000, reload=True)
