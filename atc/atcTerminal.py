import pygame as pg
from pygame.locals import *
import sys
from libCommon import *

import grpc
import data_pb2
import data_pb2_grpc

from tkinter import *
from tkinter import ttk

# Custom setup
camera = {
    "x": 200,
    "y": 63,
    "sf": 0.1
}
dragState = False
prev = [0,0]
tkAcLen = 0


# Pygame setup
pg.init()
WIDTH = 500
SCREENSIZE = (WIDTH,WIDTH)
screen = pg.display.set_mode(SCREENSIZE, pg.DOUBLEBUF|pg.HWACCEL)
WHITE = (255,255,255)
RED = (255,0,0)

clock = pg.time.Clock()
toolTipFontSize = 24
font = pg.font.SysFont(None, toolTipFontSize)
pg.display.set_caption('ATC Terminal')

def handleZoom(camera):
    # Test Zoom Implementation
    if pg.key.get_pressed()[pg.K_UP]:
        camera["sf"] += 0.05*camera["sf"]
        print(f"zoom {camera}")
    if pg.key.get_pressed()[pg.K_DOWN]:
        camera["sf"] -= 0.05*camera["sf"]
    if camera["sf"] == 0:
        camera["sf"] = 0.001

# Tkinter Tracker Setup
root = Tk()
frm = ttk.Frame(root, padding=10)
acTrack = StringVar()
frm.grid()
ttk.Radiobutton(frm, text=f"Track off", variable=acTrack, value="").grid(column=1, row=1)    
ttk.Radiobutton(frm, text=f"Track Airport", variable=acTrack, value="AIRPORT").grid(column=1, row=2)
ttk.Radiobutton(frm, text=f"Track VOR1", variable=acTrack, value="VOR1").grid(column=1, row=3)



# ATC Logic Setup
circles = [vor1]
rectangles = [rwShape_1836,rwShape_0627,twShape_a,twShape_b]


def calcPos(coord,camera,axis):
    return (coord+camera[axis])*camera["sf"]

def calcTrack(coord,camera):
    return -coord + (WIDTH/2)/camera["sf"]

gRPCAddr = 'localhost:50051'
if(len(sys.argv) == 2):
    gRPCAddr = sys.argv[1]


while 1:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            sys.exit()
    pg.display.flip()
    clock.tick(30)
    screen.fill((0,0,0))

    # Call gRPC for planes in range
    acDict= {}
    with grpc.insecure_channel(gRPCAddr) as channel:
        stub = data_pb2_grpc.validatorStub(channel)
        towerPos = data_pb2.position(xPos=rwShape_1836[0],yPos=rwShape_0627[1],zPos=50)
        reqData = data_pb2.VisiblityGetReq(reqPos=towerPos, reqRange=60000)
        response = stub.VisiblityGet(reqData)
        for ac in response.aircraftList:
            acDict[ac.name] = (Aircraft.initFromGrpcAcData(ac))

    # Info tooltips
    mousePos = pg.mouse.get_pos()
    for ac in acDict.values():
        actualX = (ac.xy.pos[0]+camera["x"])*camera["sf"]
        actualY = (ac.xy.pos[1]+camera["y"])*camera["sf"]
        radius = ac.xy.radius*camera["sf"]
        if (abs(actualX-mousePos[0]) < radius) and (abs(actualY-mousePos[1]) < radius):
            line1 = f"Name:{ac.name}"
            line2 = f"Velocity: X:{ac.velocity[0]} Y:{ac.velocity[1]} Z:{ac.velocity[2]}"
            line3 = f"Position: X:{ac.xy.pos[0]} Y:{ac.xy.pos[1]} Z:{ac.zPos}"
            img = font.render(line1, True, (255,255,255))
            img2 = font.render(line2, True, (255,255,255))
            img3 = font.render(line3, True, (255,255,255))
            screen.blit(img, pg.mouse.get_pos())
            line2Pos = (pg.mouse.get_pos()[0],pg.mouse.get_pos()[1]+toolTipFontSize)
            screen.blit(img2, line2Pos)
            line3Pos = (pg.mouse.get_pos()[0],pg.mouse.get_pos()[1]+toolTipFontSize*2)
            screen.blit(img3, line3Pos)
            break

    # View Drag
    if dragState:
        if not pg.mouse.get_pressed()[0]:
            dragState = False
            print(f"drag {camera}")
        camera["x"] -= (prev[0]-pg.mouse.get_pos()[0])/camera["sf"]
        camera["y"] -= (prev[1]-pg.mouse.get_pos()[1])/camera["sf"]
        prev[0] = pg.mouse.get_pos()[0]
        prev[1] = pg.mouse.get_pos()[1]
    elif pg.mouse.get_pressed()[0]:
        dragState = True
        prev = [0,0]
        prev[0] = pg.mouse.get_pos()[0]
        prev[1] = pg.mouse.get_pos()[1]
        print(prev)

    # View Zoom
    handleZoom(camera)
    

    # Handle tKinter Dialog
    if tkAcLen != len(acDict):
        for widget in frm.winfo_children():
            widget.destroy()
        frm.grid()
        ttk.Radiobutton(frm, text=f"Track off", variable=acTrack, value="").grid(column=1, row=1)    
        ttk.Radiobutton(frm, text=f"Track Airport", variable=acTrack, value="AIRPORT").grid(column=1, row=2)
        ttk.Radiobutton(frm, text=f"Track VOR1", variable=acTrack, value="VOR1").grid(column=1, row=3)
        for idx,ac in enumerate(acDict.values()):
            ttk.Radiobutton(frm, text=f"Track {ac.name}", variable=acTrack, value=ac.name).grid(column=1, row=idx+4)
        tkAcLen = len(acDict)

    root.update()
    if acTrack.get() == "VOR1":
        print(f"tracking {acTrack.get()}")
        camera["x"] = calcTrack(vor1[0],camera)
        camera["y"] = calcTrack(vor1[1],camera)
    elif acTrack.get() == "AIRPORT":
        print(f"tracking {acTrack.get()}")
        camera["x"] = calcTrack(rwShape_1836[0],camera)
        camera["y"] = calcTrack(rwShape_0627[1],camera)
    elif acTrack.get() != "":
        print(f"tracking {acTrack.get()}")
        camera["x"] = calcTrack(acDict[acTrack.get()].xy.pos[0],camera)
        camera["y"] = calcTrack(acDict[acTrack.get()].xy.pos[1],camera)
    

    # Render Rectangles
    for rw in rectangles:
        pg.draw.rect(screen,WHITE,Rect(calcPos(rw[0],camera,"x"), calcPos(rw[1],camera,"y"), rw[2]*camera["sf"],rw[3]*camera["sf"]))

    # Render Circles
    for ac in circles:
        center = (calcPos(ac[0],camera,"x"), calcPos(ac[1],camera,"y"),)
        radius = ac[2]*camera["sf"]
        pg.draw.circle(screen,WHITE,center,radius,width=5)
    
    # Render Aircraft
    for ac in acDict.values():
        center = ((ac.xy.pos[0]+camera["x"])*camera["sf"],(ac.xy.pos[1]+camera["y"])*camera["sf"])
        radius = ac.xy.radius*camera["sf"]
        pg.draw.circle(screen,WHITE,center,radius,width=5)
        vMag = math.hypot(ac.velocity[0],ac.velocity[1])
        xDir = (ac.velocity[0]/vMag) if ac.velocity[0]!=0 else 0
        yDir = (ac.velocity[1]/vMag) if ac.velocity[1]!=0 else 0
        if ac.name == "test1":
            print(f"line dir {xDir},{yDir}")
        endPos = ((center[0]+xDir*radius), (center[1]+yDir*radius))
        pg.draw.line(screen,WHITE,center,end_pos=endPos)


