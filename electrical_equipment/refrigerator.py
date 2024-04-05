# -*- coding: utf-8 -*-
"""
Created on Fri Feb 16 13:07:03 2024

@author: Superviseur
"""

import numpy as np

def refrigerator_fn(L, l, H, d, N_drawer, N_shelf, T_a, P_n,dt):
    # Coefficient of performance
    COP = 0.7

    # Air thermal mass
    Cv_air = 1297
    C_air = H * L * l * Cv_air
    # print(C_air)
    
    # Plastic thermal mass
    Cv_plastic = 1670
    Rho_plastic = 910
    V_drawer = 0.004 * l * L
    C_plastic = Rho_plastic * Cv_plastic * V_drawer * N_drawer
    # print(C_plastic)
    
    # Glass thermal mass
    Cm_glass = 840
    Rho_glass = 2500
    V_shelf = 0.004 * l * L
    C_glass = Cm_glass * Rho_glass * V_shelf * N_shelf
    # print(C_glass)
    
    
    # Total thermal mass
    C_r = (C_air + C_plastic + C_glass)*2
    # print(C_r)
    
    # Total thermal resistance
    Lam_polystyrene = 0.033
    S_envelop = 2 * (L * H + L * l + H * L)
    R_r = (1 / Lam_polystyrene) * (d / S_envelop)
    # print(R_r)

    # Time parameters
    num_steps = int(24 * 3600/dt)

    # Initialize arrays to store temperature and power values
    T_r_values = np.zeros(num_steps)
    P_r_values = np.zeros(num_steps)

    # Initial condition
    T_r = 2 + 273  # Initial temperature

    ## Integrate the differential equation using Euler's method
    for i in range(num_steps):
        # Update compressor state based on current temperature
        # Turn on compressor
        if T_r >= (5 + 273):
            P_r = P_n  
            # Turn off compressor
        elif T_r <= (2 + 273):
            P_r = 0  
       # Keep previous power if temperature is between 2°C and 5°C
        else:
            P_r = P_r_values[i-1]  

        # Model for indoor temperature 
        dT_r_dt = (1 / C_r) * ((T_a[i] + 273) - T_r) / R_r - COP * P_r / C_r

        # Update temperature using Euler's method
        T_r += dT_r_dt * dt

        # Store temperature and power values
        T_r_values[i] = T_r
        P_r_values[i] = P_r
   ## end of it 
   
    # Convert temperature values to Celsius
    T_r_values -= 273

    return T_r_values, P_r_values


