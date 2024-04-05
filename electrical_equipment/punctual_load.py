# -*- coding: utf-8 -*-
"""
Created on Sun Feb 25 17:35:54 2024

@author: Superviseur
"""
import numpy as np

def punctual_load_fun(P_n, dt, *args):
    # Determine the number of steps based on the step time (dt)
    num_steps = int(24 * 3600 / dt)
    P_consumption = np.zeros(num_steps)

    for arg in args:
        start_hour, duration_min = arg
        # Convert start hour and duration to seconds
        start_time = start_hour * 3600
        duration = duration_min * 60
        
        # Calculate start and end indices for the operation
        start_index = int(start_time / dt)
        end_index = int((start_time + duration) / dt)
        
        # Set power consumption for the given period
        P_consumption[start_index:end_index] = P_n

    return P_consumption



