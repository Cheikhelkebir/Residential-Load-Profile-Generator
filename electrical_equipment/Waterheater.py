# -*- coding: utf-8 -*-
"""


@author: Superviseur
"""

import numpy as np

def Waterheater_fun(P_n, V, T_a, T_in, W_user,dt):
    
    # Users desired temperature
    T = 40 + 273  
    # Thermal capacity of water in the tank
    C_p = 4181  
    Rho = 998  
    C_wh = C_p * Rho * V
    # Thermal conductance of the tank
    A_wh = 2  
    # Initial temperature inside the tank
    T_WH = 40 + 273 
    
    # Time parameters 
    # Number of time steps in 24 hours
    num_steps = int(24 * 3600/dt)  

    # Initialize arrays to store temperature and power values
    T_WH_values = np.zeros(num_steps)
    P_WH_values = np.zeros(num_steps)
    
    
    # Iterate over 24 hours
    for i in range(num_steps):
        # Check tariff period
        if i // (3600*dt) < 8:
            tariff_period = 'Low tariff'
        else:
            tariff_period = 'High tariff'
        
        # Temperature settings based on electricity tariff
        if tariff_period == 'High tariff':
            if T_WH >= (45 + 273):
                P_WH = 0
            elif T_WH <= (40 + 273):
                P_WH = P_n
            else:
                P_WH = P_WH_values[i - 1]
        elif tariff_period == 'Low tariff':
            if T_WH >= (60 + 273):
                P_WH = 0
            elif T_WH <= (55 + 273):
                P_WH = P_n
            else:
                P_WH = P_WH_values[i - 1]
        
        # Model for indoor temperature 
        W_d = W_user[i] * (T - (T_in + 273)) / (T_WH - (T_in + 273))
        # Limit hot water consumption to between 0 and 7 L/min
        W_d_limited = max(0, min(W_d, 7))
        # Calculate rate of change of water temperature in the tank
        dT_WH_dt = (1 / C_wh) * ((T_a[i] + 273) - T_WH) * A_wh + (1 / C_wh) * (W_d_limited * (0.001 / 60) * Rho * C_p) * ((T_in + 273) - T_WH) +  P_WH / C_wh
                   
        # Update temperature using Euler's method
        T_WH += dT_WH_dt * dt

        # Store temperature and power values
        T_WH_values[i] = T_WH
        P_WH_values[i] = P_WH
        
    # Convert temperature values to Celsius
    T_WH_values -= 273

    return T_WH_values, P_WH_values



