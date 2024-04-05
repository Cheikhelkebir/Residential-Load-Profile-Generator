# -*- coding: utf-8 -*-
"""
Created on Wed Mar 20 16:14:00 2024

@author: Superviseur
"""
import numpy as np


def WashingMachine_fun(T_in, T_heating, start_hour, dt):
    # Parameters
    P_heating = 2400
    V_WM = 0.02  
    rho = 1000  
    C_p = 4186  
    C_wm = rho * C_p * V_WM  # Total heat capacity

    # Convert start hour to seconds
    start_time = start_hour * 3600

    # Calculate heating time
    time_heating = (T_heating - T_in) * C_wm / P_heating

    # Define phase durations
    time_washing = 40 * 60  # Washing duration
    time_spinning = 15 * 60  # Spinning duration
    
    num_steps = int(24 * 3600 / dt)

    # Initialize the power array
    P_WM = np.zeros(num_steps)
    
    for i in range(num_steps):
        current_time = i * dt  
        if start_time <= current_time < start_time + time_heating:
            # Heating phase
            P_WM[i] = P_heating
        elif start_time + time_heating <= current_time < start_time + time_heating + time_washing:
            # Washing phase
            P_WM[i] = 80
        elif start_time + time_heating + time_washing <= current_time < start_time + time_heating + time_washing + time_spinning:
            # Spinning phase
            P_WM[i] = 150
    
    return P_WM





