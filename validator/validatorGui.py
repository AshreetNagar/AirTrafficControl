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
    "x": 0,
    "y": 0,
    "sf": 1
}
dragState = False
prev = [0,0]
tkAcLen = 0


# Pygame setup
pg.init()
HEIGHT = 500
WIDTH = 500
SCREENSIZE = (HEIGHT,WIDTH)
screen = pg.display.set_mode(SCREENSIZE, pg.DOUBLEBUF|pg.HWACCEL)
WHITE = (255,255,255)
clock = pg.time.Clock()
toolTipFontSize = 24
font = pg.font.SysFont(None, toolTipFontSize)
pg.display.set_caption('Validator GUI')

# Tkinter Setup
root = Tk()
frm = ttk.Frame(root, padding=10)
acTrack = StringVar()

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


    # Get Aircraft from gRPC
    acDict= {}
    with grpc.insecure_channel(gRPCAddr) as channel:
        stub = data_pb2_grpc.validatorStub(channel)
        response = stub.AcGetList(data_pb2.ACListReq())
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


    # Test drag implementation
    if dragState:
        if not pg.mouse.get_pressed()[0]:
            dragState = False
        camera["x"] -= prev[0]-pg.mouse.get_pos()[0]
        camera["y"] -= prev[1]-pg.mouse.get_pos()[1]
        prev[0] = pg.mouse.get_pos()[0]
        prev[1] = pg.mouse.get_pos()[1]
    elif pg.mouse.get_pressed()[0]:
        dragState = True
        prev = [0,0]
        prev[0] = pg.mouse.get_pos()[0]
        prev[1] = pg.mouse.get_pos()[1]

    

    # Test Zoom Implementation
    if pg.key.get_pressed()[pg.K_UP]:
        camera["sf"] += 0.05
    if pg.key.get_pressed()[pg.K_DOWN]:
        camera["sf"] -= 0.05


    # Window for aircraft tracking
    if tkAcLen != len(acDict):
        for widget in frm.winfo_children():
            widget.destroy()
        frm.grid()
        for idx,ac in enumerate(acDict.values()):
            ttk.Radiobutton(frm, text=f"Track {ac.name}", variable=acTrack, value=ac.name).grid(column=1, row=idx)
        ttk.Radiobutton(frm, text=f"Track off", variable=acTrack, value="").grid(column=1, row=idx+1)    
        tkAcLen = len(acDict)
    root.update()


    if acTrack.get() != "":
        print(f"tracking {acTrack.get()}")
        camera["x"] = -acDict[acTrack.get()].xy.pos[0] + WIDTH/2
        camera["y"] = -acDict[acTrack.get()].xy.pos[1] + HEIGHT/2
    
    

    # Render circles
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