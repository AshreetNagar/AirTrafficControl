


# Update v2
# # Calculate old velocity vector
# v_Hmagnitude = math.hypot(acData.acVel.xVel,acData.acVel.yVel)
# if v_Hmagnitude != 0:
#     v_Hangle = math.acos(acData.acVel.xVel/ v_Hmagnitude) 
# else:
#     v_Hangle = acState.yaw
# v_Vmagnitude = acData.acVel.zVel
# v_Vangle = (3*math.pi)/2 
# v_magnitude = math.hypot(v_Hmagnitude,v_Vmagnitude)


# # Calculate gravity vector: only affects Z velocity
# g_Hmagnitude = 0
# g_Hangle = 0            
# g_Vangle = math.pi/2
# if acData.zPos == 0:
#     g_Vmagnitude = 0
# else:
#     g_Vmagnitude = 9.8*updatePeriod*acParams.mass

# # Calculate drag vector: opposite direction of original velocity
# d_magnitude = v_magnitude*acParams.dragConst
# d_Hangle = v_Hangle + math.pi
# d_Vangle = v_Vangle + math.pi


# # Calculate thrust vector: direction of plane
# thrust = 0
# for engine in enginesState.values():
#     thrust += engine.thrust/2
# t_magnitude = thrust*0.5
# t_Hangle = acState.yaw
# t_Vangle = acState.pitch

# # Calculate new vel
# newV_HMag = 0
# newV_VMag = v_Vmagnitude
# newV_Hangle = 0
# newV_Vangle = 0


# Update v1
# drag = 0.05
# thrust = 0
# mass = 1000
# for engine in enginesState.values():
#     thrust += engine.thrust/2

# print(f"thrust:{thrust} pitch:{acState.pitch} yaw:{acState.yaw}")

# h_magnitude = math.hypot(acData.acVel.xVel,acData.acVel.yVel)
# if h_magnitude != 0:
#     h_angle = math.acos(acData.acVel.xVel/ h_magnitude) 
#     hThrustFactor = (acState.yaw+h_angle)/math.pi - 1.5
#     h_newMagnitude = h_magnitude + (thrust-drag*h_magnitude)*updatePeriod*hThrustFactor
# else:
#     h_angle = acState.yaw
#     h_newMagnitude = (thrust)*updatePeriod

# v_magnitude = math.hypot(acData.acVel.zVel,h_magnitude)
# if v_magnitude != 0:
#     v_angle = math.acos(acData.acVel.zVel/ v_magnitude) 
#     vThrustFactor = (acState.pitch+v_angle)/math.pi - 1.5
#     v_newMagnitude = v_magnitude + (thrust-drag)*updatePeriod*vThrustFactor - 9.8*updatePeriod
# else:
#     v_angle = 0
#     vThrustFactor = ((acState.pitch+v_angle)/math.pi - 1.5)
#     v_newMagnitude = (thrust)*updatePeriod*vThrustFactor - 9.8*updatePeriod


# if h_newMagnitude == 0:
#     newX = 0
#     newY = 0
# else:
#     h_turningPerf = 0.5
#     h_newAngle = h_angle + (acState.yaw-h_angle)*h_turningPerf
#     newX = math.cos(h_newAngle)*h_newMagnitude
#     newY = math.sin(h_newAngle)*h_newMagnitude

# if v_newMagnitude == 0:    
#     newZ = 0
# else:
#     v_turningPerf = 0.25
#     v_newAngle = v_angle + (acState.pitch-v_angle)*v_turningPerf
#     newZ = math.cos(v_newAngle)*v_newMagnitude