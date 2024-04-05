# -*- coding: utf-8 -*-
"""


@author: Superviseur
"""

import numpy as np

def heatpump_fun(Standard, S, H, pitch_angle,Nwi,S_wi,T_out, P_n,season,T_hp0, occupency,dt):
   
   
   # Coefficient of performance 
    if season == 'Winter':
        COP = 4
        T_set= 22+273
    elif season == 'Summer':
        COP = 3.5
        T_set= 24+273
    # House Geomerty
    # House Volume approximation
    V_h=H * S + 0.25*np.sqrt(S)*np.tan(np.radians(pitch_angle))
    S_Windows= Nwi*S_wi
    S_Wall=(np.sqrt(S)*H+np.sqrt(S)*H)*2-S_Windows
    S_roof=S/np.cos(pitch_angle)
    print(S_roof)
    # Air thermal mass
    C_0 = 1005
    Rho_0=1.225
    C_air = V_h *C_0*Rho_0
    
    # Type of isolation
    if Standard == 'RT 2012':
        U_Wall=1/5
        U_Windows=1.5
        U_roof=1/6
    elif Standard == 'RT 2020':
        U_Wall=1/7
        U_Windows=1.5
        U_roof=1/8
    
    # equivalent thermal transmittance
    G_eq=S_Windows*U_Windows + S_Wall*U_Wall + S_roof*U_roof
    print(G_eq)
    
    
    # Time parameters
    num_steps = int(24 * 3600 / dt)

    # Initialize arrays to store temperature and power values
    T_hp_values = np.zeros(num_steps)
    P_hp_values = np.zeros(num_steps)
    Power_cons  = np.zeros(num_steps)
    
    # Initial condition
    T_hp = T_hp0 + 273  # Initial temperature

    ## Integrate the differential equation using Euler's method
    for i in range(num_steps):
        # Update compressor state based on current temperature
        
        if season == 'Winter':
            # temperature setting based on occupency
            if occupency[i] >= 1 :
                if T_hp >= (21 + 273):
                    P_hp = 0
                    P_cons=np.abs(P_hp/COP)
                    # Turn oN compressor
                elif T_hp <= (19 + 273):
                    P_hp = P_n*(T_set-T_hp)/3
                    P_cons=np.abs(P_hp/COP)
               # Keep previous power 
                else:
                    P_hp = P_hp_values[i-1]
                    P_cons=np.abs(P_hp/COP)
            elif occupency[i] == 0 :
                if T_hp >= (17 + 273):
                    P_hp = 0
                    P_cons=np.abs(P_hp/COP)
                    # Turn oN compressor
                elif T_hp <= (16 + 273):
                    P_hp = P_n*(T_set-T_hp)/5
                    P_cons=np.abs(P_hp/COP)
               # Keep previous power 
                else:
                    P_hp = P_hp_values[i-1]
                    P_cons=np.abs(P_hp/COP)
                
        elif season == 'Summer':
            # temperature setting based on occupency
            if occupency[i] >= 1 :
                if T_hp >= (26 + 273):
                    P_hp = P_n*(T_set-T_hp)/5
                    P_cons=np.abs(P_hp/COP)
                    # Turn off compressor
                elif T_hp <= (25 + 273):
                    P_hp = 0 
                    P_cons=np.abs(P_hp/COP)
               # Keep previous power 
                else:
                    P_hp = P_hp_values[i-1]
                    P_cons=np.abs(P_hp/COP)
            elif occupency[i] == 0 :
                P_hp = 0 
                P_cons=np.abs(P_hp/COP)
                  
        # Model for indoor temperature 
        dT_HP_dt = (1 / C_air) * ((T_out[i] + 273) - T_hp) *G_eq + P_hp / C_air

        # Update temperature using Euler's method
        T_hp += dT_HP_dt * dt
        # Store temperature and power values
        T_hp_values[i] = T_hp
        P_hp_values[i] = P_hp
        Power_cons[i]  = P_cons
   # ## end of it 
    # Convert temperature values to °C
    T_hp_values -= 273
    # P_cons = np.abs(P_hp_values/COP)

    return T_hp_values, Power_cons
    
    
# # Test 
# # Parameters
# Standard = 'RT 2012'
# L = 10
# l = 8
# H = 2.5
# pitch_angle = 0
# Nwi = 5
# S_wi = 1
# # don't forget to change T_out accroding to season
# T_out = 35
# P_n = 4000
# season='Summer'
# T_hp0=27
# occupency=1
# dt=1

# # Solve the differential equation
# T_hp_values, P_hp_values = heatpump(Standard,L, l, H, pitch_angle, Nwi, S_wi, T_out, P_n,season,T_hp0,occupency,dt)
# print(T_hp_values, P_hp_values)


# import matplotlib.pyplot as plt

# # Convert time range to hour
# time_hours = np.arange(0, 24, 1/3600)

# # Create a figure with two sub-graphs
# fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# # Plot T_h on the first subgraph
# ax1.plot(time_hours, T_hp_values, label='T_h')
# ax1.set_xlabel('Time (h)')
# ax1.set_ylabel('Temperature (°C)')
# ax1.set_title('Temperature inside the house')
# ax1.grid(True)
# ax1.legend()

# # Plot P_h on the second sub-graph
# ax2.plot(time_hours, P_hp_values, color='orange')
# ax2.set_xlabel('Time (h)')
# ax2.set_ylabel('Power (W)')
# ax2.set_title('Power consumption profile of heat pump')
# ax2.grid(True)
# ax2.legend()

# # Define 24-hour x-axis limits
# ax1.set_xlim(0, 24)
# ax2.set_xlim(0, 24)

# # Axis markers to display hours
# ax1.set_xticks(np.arange(0, 25, 1))
# ax2.set_xticks(np.arange(0, 25, 1))

# # Adjust spacing between subgraphs
# plt.tight_layout()

# # Show graph
# plt.show()
    
    