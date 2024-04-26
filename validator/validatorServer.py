import grpc
import data_pb2
import data_pb2_grpc
from concurrent import futures
import logging
import time
from threading import Thread, Event, Lock
from libCommon import *

class ValidatorServer(data_pb2_grpc.validator):

    def __init__(self,validatorInstance,validatorLock) -> None:
        super().__init__()
        self.validatorInstance = validatorInstance
        self.validatorLock = validatorLock


    def AcGetList(self, request, context):
        serializedAcList = []
        with self.validatorLock:
            for ac in self.validatorInstance.aircraftDict.values():
                # acPosPb = data_pb2.position(xPos=ac.xy.pos[0],yPos=ac.xy.pos[1],zPos=ac.zPos)
                # acVelPb = data_pb2.velocity(xVel=ac.velocity[0],yVel=ac.velocity[1],zVel=ac.velocity[2])
                # acPb = data_pb2.ACData(name=ac.name,acPos=acPosPb,acVel=acVelPb,acRad=ac.xy.radius)
                acPb = ac.toGrpcAcdata()
                # print(acPb)
                serializedAcList.append(acPb)
        return data_pb2.AcListResp(aircraftList=serializedAcList)

    def AcAdd(self, request, context):
        newAc = Aircraft.initFromGrpcAcData(request)
        respStr = validatorInstance.addAC(newAc)
        return data_pb2.AcAddResp(status=respStr)

    def AcUpdateVel(self, request, context):
        if request.name not in self.validatorInstance.aircraftDict.keys():
            return data_pb2.AcUpdateResp(status="Error: Aircraft does not exist")

        acObj = self.validatorInstance.aircraftDict[request.name]
        acObj.velocity = [request.newAcVel.xVel,request.newAcVel.yVel,request.newAcVel.zVel]

        return data_pb2.AcUpdateResp(status="Success")
    
    def VisiblityGet(self, request, context):
        # position = request.reqPos

        if (request.HasField("name")):
            if request.name not in self.validatorInstance.aircraftDict.keys():
                return data_pb2.AcUpdateResp(status="Error: Aircraft does not exist")
            if (request.HasField("reqRange")):
                acVisList = self.validatorInstance.getACVisibilityListRange(request.name,request.reqRange)
                serializedAcList = []
                for ac in acVisList:
                    serializedAcList.append(ac.toGrpcAcdata())
                return data_pb2.VisiblityGetResp(status="Success",aircraftList=serializedAcList)
        elif (request.HasField("reqPos")):
            if (request.HasField("reqRange")):
                acVisList = self.validatorInstance.getVisibilityListPosRange(request.reqPos,request.reqRange)
                serializedAcList = []
                for ac in acVisList:
                    serializedAcList.append(ac.toGrpcAcdata())
                return data_pb2.VisiblityGetResp(status="Success",aircraftList=serializedAcList)
        return data_pb2.AcUpdateResp(status="Error: Not implemented")

    def AcGet(self,request,context):
        # if request.name not in self.validatorInstance.aircraftDict.keys():
            # return data_pb2.ACData(name="Error: Aircraft does not exist")

        return self.validatorInstance.aircraftDict[request.name].toGrpcAcdata()


    def serve(validatorInstance, validatorLock):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        data_pb2_grpc.add_validatorServicer_to_server(ValidatorServer(validatorInstance, validatorLock),server)
        server.add_insecure_port('[::]:50051')
        server.start()
        try:
            server.wait_for_termination()
        except KeyboardInterrupt as ke:
            print(f"\nKeyboard Interrupt {ke}, stopping server.. ")
if __name__ == '__main__':
    print("Validator Server and Update Thread Started")
    logging.basicConfig()
    updatePeriod = 0.5
    validatorLock = Lock()
    validatorInstance = Validator(validatorLock)
    exitEvent = Event()
    validatorThread = Thread(group=None,target=validatorInstance.loop,args=(0.3,exitEvent,))
    validatorThread.start()
    validatorInstance.addAC(Aircraft("ac1",0,0,0,10,[1,0,0]))
    validatorInstance.addAC(Aircraft("ac2",5,5,100,10,[1,1,0]))
    ValidatorServer.serve(validatorInstance, validatorLock)
    exitEvent.set()