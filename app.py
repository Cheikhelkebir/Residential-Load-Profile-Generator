# -*- coding: utf-8 -*-

from flask import Flask, request, render_template, jsonify
from datetime import datetime
import json
from scipy.interpolate import interp1d
import numpy as np
import pandas as pd
from electrical_equipment.heatpump import heatpump_fun
from electrical_equipment.refrigerator import refrigerator_fn
from electrical_equipment.WashingMachine import WashingMachine_fun
from electrical_equipment.Waterheater import Waterheater_fun
from electrical_equipment.punctual_load import punctual_load_fun
import os
import requests
app = Flask(__name__)

@app.route('/get-location', methods=['GET'])
def get_location():
    supervisor_token = os.getenv("SUPERVISOR_TOKEN")
    #if not supervisor_token:
    #    return jsonify({"error": "Supervisor token not found"}), 500

    api_url = "http://supervisor/core/api/config"
    headers = {"Authorization": f"Bearer {supervisor_token}"}
    print('test')
    try:
        #return jsonify({
        #    "latitude": 49.0527528,
        #    "longitude": 2.0388736
        #})
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            config = response.json()
            return jsonify({
                "latitude": config.get("latitude"),
                "longitude": config.get("longitude")
            })
        else:
            return jsonify({"error": "Failed to fetch location", "status_code": response.status_code}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#@app.route('/process_form', methods=['POST','GET'])
def process_form():

    # Household occupants
    Household_occupants = float(request.form.get('Household-occupants'))
    # End of Household occupants

    # Occupancy data
    occupancy_data = request.form.get('Occupancy')
    if occupancy_data:
        occupancy_data = json.loads(occupancy_data)
    if occupancy_data:
        occupancy_time_pairs = [{'hour': f"{i}h", 'occupancy': occupancy} for i, occupancy in enumerate(occupancy_data, start=1)]
    else:
        occupancy_time_pairs = []
    occupancy_data = [float(oc) for oc in occupancy_data]
	# End of Occupancy data

    # Simulation step time
    Simulation_StepTime = float(request.form.get('Simulation-StepTime'))
    # End of Simulation step time

    # Import Outdoor Temperature
    hidden_temperatures = request.form.get('hiddenTemperatures')
    hidden_times = request.form.get('hiddenTimes')

    # JSON data convert into Python lists
    temperatures = json.loads(hidden_temperatures)
    times = json.loads(hidden_times)

    # Create a list of dictionaries combining temperatures and times to facilitate template iteration
    temperature_time_pairs = [{'temperature': temp, 'time': time} for temp, time in zip(temperatures, times)]
    # End of Import Outdoor Temperature

    # determine the season
    # Initialization of the temperature at the starting of
    # convert all temperatures to float
    temperatures = [float(temp) for temp in temperatures]
    # times = [float(time) for time in times if time]
    # Initialization of Cold water temperature
    T_in = 12
    # Initialization of indoor temperature
    T_hp0 = temperatures[0]
    average_temp = sum(temperatures) / len(temperatures)
    if average_temp < 19:
             season = "Winter"  # Average temperature indicates Winter
             T_hp0 = 17
             T_in = 11
    elif average_temp > 26:
               season = "Summer"  # Average temperature indicates
               T_hp0 -= 2
               T_in = 20
    else:
             season = "Transition" # For temperatures between 19°C and 26°C
             T_hp0 = None
             T_in= 15
    # End of determine the season

    # determined the temperature for every hour for next day
    # Convert times into continuous hours
    hours_continuous = []
    #for time in times:
    #      hours, minutes = map(int, time.split(':'))
    #      hours_continuous.append(hours + (minutes / 60))
    for time in times:
        try:
            # Parse time to handle both AM/PM and 24-hour formats
            time_obj = datetime.strptime(time, "%I:%M %p")  # For 12-hour format
            hours = time_obj.hour
            minutes = time_obj.minute
            hours_continuous.append(hours + (minutes / 60))
        except ValueError:
            raise ValueError(f"Invalid time format: {time}")

    # Adjust continuous hours
    for i in range(1, len(hours_continuous)):
          if hours_continuous[i] < hours_continuous[i-1]:
             hours_continuous[i:] = [h + 24 for h in hours_continuous[i:]]
    # linear interpolation
    interpolation_func = interp1d(hours_continuous, temperatures, kind='linear')
    # Generate continuous hours for each hour between 00h and the maximum hour + 1 to cover the entire range
    interpolated_hours = np.arange(min(hours_continuous), max(hours_continuous) + 1, 1)
    # Calculate interpolated temperatures for each hour
    interpolated_temperatures = interpolation_func(interpolated_hours)
    # Convert continuous hours into daytime hours and associate them with their temperatures
    results = [{"time": f"{int(hour % 24):02d}:00", "temperature": temp} for hour, temp in zip(interpolated_hours, interpolated_temperatures)]
    filtered_results = {entry["time"]: entry["temperature"] for entry in results}
    # Extract temperatures in hourly order
    ordered_temperatures = [filtered_results[f"{hour:02d}:00"] for hour in range(24)]
    # End of determined the temperature for every hour for next day

    # Function to transform data according to dt
    def transform_data_for_dt(data, dt, total_seconds=24*3600):
        repeats_per_hour = int(3600 / dt)
        transformed_data = np.repeat(data, repeats_per_hour)
        expected_length = int(total_seconds / dt)
        assert len(transformed_data) == expected_length, f"La longueur transformée {len(transformed_data)} ne correspond pas à la longueur attendue {expected_length}."
        return transformed_data
    # End of Function to transform data according to dt

    # Adapting occupency and T_out with data with time step
    occupancy = transform_data_for_dt(occupancy_data, Simulation_StepTime)
    T_out = transform_data_for_dt(ordered_temperatures, Simulation_StepTime)
    presence = np.where(occupancy >= 1, 1, 0)

    # House geometry
    house_Surface = float(request.form.get('house-Surface'))
    house_height = float(request.form.get('house-height'))
    roof_pitch = float(request.form.get('roof-pitch'))
    num_windows = int(request.form.get('num-windows'))
    window_surface = float(request.form.get('window-surface'))
    # End of House geometry


    # Standard
    isolation_type = str(request.form.get('isolation-type'))
    # End of Standard

    # Heating cooling system
    heating_system_type = request.form.get('heating-system-type')
    nominal_power = None  # Initialization to None
    indoorTemperature=T_out
    heatpump_cons = np.zeros(int(3600*24/Simulation_StepTime))
    # Air/air heat pump
    if heating_system_type == "1":
        nominal_power = float(request.form.get('nominal-power'))
        indoorTemperature, heatpump_cons=heatpump_fun(isolation_type,house_Surface,house_height,roof_pitch,num_windows,window_surface,T_out,nominal_power,season,T_hp0,occupancy,Simulation_StepTime)
    # End of "Air/air heat pump"
    # return {"temperature": indoorTemperature.tolist(), "power_consumption": heatpump_cons.tolist()}
    # End of Heating cooling system

    # Water Heater
    # Cold water temperature
    # T_in = float(request.form.get('cold-water'))
    # End Cold water temperature
    water_heater_type = request.form.get('water-heater-type')
    nominal_power_water_heater = None
    water_tank_volume = None
    cold_water_temperature_estimation = None
    P_WH = np.zeros(int(3600*24/Simulation_StepTime))
    if water_heater_type == "1":
        nominal_power_water_heater = float(request.form.get('nominal-power-water-heater'))
        water_tank_volume = float(request.form.get('water-tank-volume'))
        # import hot water consumption profile
        data = pd.read_excel('Hot_water_consumption.xlsx')
        # Extract data from column W_user
        # W_user_data = data['W_user']
        # Adapt hot water consumption profile to time step
        data_length=len(data)
        # new_length = int(3600*24/Simulation_StepTime)
        # W_user_adapted = np.zeros(new_length)
        if Simulation_StepTime < 1:
            # Downsampling
            downsampled_length = int(data_length /Simulation_StepTime)
            downsampled_data = np.array([data['W_user'][int(i*Simulation_StepTime):int((i+1)*Simulation_StepTime)].mean() for i in range(downsampled_length)])
            W_user_data_adapted = downsampled_data

        else:
            # Upsampling
            original_time = np.arange(0, data_length)
            new_time = np.arange(0, data_length, Simulation_StepTime)
            interpolation_function = interp1d(original_time, data['W_user'], kind='linear')
            upsampled_data = interpolation_function(new_time)
            W_user_data_adapted = upsampled_data

        Hot_Water_Consumption = presence * W_user_data_adapted*Household_occupants/4
        WH_temperature, P_WH = Waterheater_fun(nominal_power_water_heater, water_tank_volume, indoorTemperature, T_in, Hot_Water_Consumption,Simulation_StepTime)
    # return P_WH.tolist()
    # End of Water Heater

    # Refrigerator and Freezer
    refrigerator_type = request.form.get('refrigerator-type')
    nominal_power_refrigerator = None
    dimensions_refrigerator = {}
    num_drawers_refrigerator = None
    num_shelves_refrigerator = None
    Pr_consumption = np.zeros(int(3600*24/Simulation_StepTime))
    if refrigerator_type == "1":
        nominal_power_refrigerator = float(request.form.get('nominal-power-refrigerator'))
        dimensions_refrigerator = {
            'length': float(request.form.get('length-refrigerator')),
            'width': float(request.form.get('width-refrigerator')),
            'height': float(request.form.get('height-refrigerator')),
            'thickness': float(request.form.get('thickness-refrigerator'))
        }
        num_drawers = int(request.form.get('num-drawers-refrigerator'))
        num_shelves = int(request.form.get('num-shelves-refrigerator'))
        Tr_values, Pr_consumption= refrigerator_fn(dimensions_refrigerator['length'],dimensions_refrigerator['width'], dimensions_refrigerator['height'], dimensions_refrigerator['thickness'],num_drawers,num_shelves,indoorTemperature,nominal_power_refrigerator,Simulation_StepTime)
    # End of Refrigerator and Freezer
    # return Pr_consumption.tolist()


    # Converts a string 'hh:mm' to floating hours
    def time_str_to_hours(time_str):
          hours, minutes = map(int, time_str.split(':'))
          return hours + minutes / 60.0

    # Washing devices
    # Washing Machine
    Washingmachine_enabled = request.form.get('Washingmachine_enabled') == 'true'
    if not Washingmachine_enabled:
        P_consumption_WM=np.array([0] * (int(24 * 3600 / Simulation_StepTime)))
    else :
        Washing_Temp_setting = float(request.form.get('Temperature-setting-for-washing'))
        Starting_Time = request.form.get('Starting-time')
        starting_time = time_str_to_hours(Starting_Time)
        P_consumption_WM=WashingMachine_fun(T_in,Washing_Temp_setting,starting_time,Simulation_StepTime)
    # return P_consumption_WM.tolist()
    # End of Washing Machine
    # End of Washing devices

    # ON/OFF Appliances
    # TV
    tv_enabled = request.form.get('tv_enabled') == 'true'
    if not tv_enabled:
        P_consumption_tv=np.array([0] * (int(24 * 3600 / Simulation_StepTime)))
    else :
        nominal_power_tv = float(request.form.get('tv_nominal_power', 0))
        tv_schedules = []

        i = 0
        while True:
             starting_time_str = request.form.get(f'tv_starting_time_{i}')
             duration = request.form.get(f'tv_duration_{i}')
             if not starting_time_str or not duration:
                 break  # Sortie de la boucle si l'un des champs est manquant
             starting_time = time_str_to_hours(starting_time_str)
             tv_schedules.append((starting_time, float(duration)))
             i += 1
        P_consumption_tv = punctual_load_fun(nominal_power_tv, Simulation_StepTime, *tv_schedules)
    # return P_consumption_tv.tolist()
   # End of TV

   # Microwave
    microwave_enabled = request.form.get('microwave_enabled') == 'true'
    if not microwave_enabled :
        P_consumption_microwave=np.array([0] * (int(24 * 3600 / Simulation_StepTime)))
    else :
        nominal_power_microwave = float(request.form.get('microwave_nominal_power', 0))
        microwave_schedules = []

        i = 0
        while True:
            starting_time_str = request.form.get(f'microwave_starting_time_{i}')
            duration = request.form.get(f'microwave_duration_{i}')
            if not starting_time_str or not duration:
                break
            starting_time = time_str_to_hours(starting_time_str)
            microwave_schedules.append((starting_time, float(duration)))
            i += 1
        P_consumption_microwave = punctual_load_fun(nominal_power_microwave, Simulation_StepTime, *microwave_schedules)
    # return P_consumption_microwave.tolist()
    # End of Microwave

    # Oven
    oven_enabled = request.form.get('oven_enabled') == 'true'
    if not oven_enabled :
        P_consumption_oven=np.array([0] * (int(24 * 3600 / Simulation_StepTime)))
    else :
        nominal_power_oven = float(request.form.get('oven_nominal_power', 0))
        oven_schedules = []

        i = 0
        while True:
              starting_time_str = request.form.get(f'oven_starting_time_{i}')
              duration = request.form.get(f'oven_duration_{i}')
              if not starting_time_str or not duration:
                        break
              starting_time = time_str_to_hours(starting_time_str)
              oven_schedules.append((starting_time, float(duration)))
              i += 1
        P_consumption_oven = punctual_load_fun(nominal_power_oven, Simulation_StepTime, *oven_schedules)
    # return P_consumption_oven.tolist()
    # End of Oven

    # Iron
    iron_enabled = request.form.get('iron_enabled') == 'true'
    if not iron_enabled :
        P_consumption_iron=np.array([0] * (int(24 * 3600 / Simulation_StepTime)))
    else :
        nominal_power_iron = float(request.form.get('iron_nominal_power', 0))
        iron_schedules = []

        i = 0
        while True:
              starting_time_str = request.form.get(f'iron_starting_time_{i}')
              duration = request.form.get(f'iron_duration_{i}')
              if not starting_time_str or not duration:
                    break
              starting_time = time_str_to_hours(starting_time_str)
              iron_schedules.append((starting_time, float(duration)))
              i +=1
        P_consumption_iron = punctual_load_fun(nominal_power_iron, Simulation_StepTime, *iron_schedules)
    # return P_consumption_iron.tolist()
    # End of Iron

    # Hair Dryer
    hairdryer_enabled = request.form.get('hairdryer_enabled') == 'true'
    if not hairdryer_enabled :
        P_consumption_hairdryer=np.array([0] * (int(24 * 3600 / Simulation_StepTime)))
    else:
        nominal_power_hairdryer = float(request.form.get('hairdryer_nominal_power',0))
        hairdryer_schedules = []

        i = 0
        while True:
              starting_time_str = request.form.get(f'hairdryer_starting_time_{i}')
              duration = request.form.get(f'hairdryer_duration_{i}')
              if not starting_time_str or not duration:
                    break
              starting_time = time_str_to_hours(starting_time_str)
              hairdryer_schedules.append((starting_time, float(duration)))
              i += 1
        P_consumption_hairdryer = punctual_load_fun(nominal_power_hairdryer, Simulation_StepTime, *hairdryer_schedules)
    # return P_consumption_hairdryer.tolist()
    # End of Hair Dryer

    # Fan
    fan_enabled = request.form.get('fan_enabled') == 'true'
    if not fan_enabled :
        P_consumption_fan=np.array([0] * (int(24 * 3600 / Simulation_StepTime)))
    else:
        nominal_power_fan = float(request.form.get('fan_nominal_power',0))
        fan_schedules = []

        i = 0
        while True:
              starting_time_str = request.form.get(f'fan_starting_time_{i}')
              duration = request.form.get(f'fan_duration_{i}')
              if not starting_time_str or not duration:
                   break
              starting_time = time_str_to_hours(starting_time_str)
              fan_schedules.append((starting_time, float(duration)))
              i += 1
        P_consumption_fan = punctual_load_fun(nominal_power_fan, Simulation_StepTime, *fan_schedules)
    # return P_consumption_fan.tolist()
    # End of Fan

    # Game Console
    gameconsole_enabled = request.form.get('gameconsole_enabled') == 'true'
    if not gameconsole_enabled :
        P_consumption_gameconsole = np.array([0] * (int(24 * 3600 / Simulation_StepTime)))
    else:
        nominal_power_game_console = float(request.form.get('gameconsole_nominal_power',0))
        game_console_schedules = []

        i = 0
        while True:
              starting_time_str = request.form.get(f'gameconsole_starting_time_{i}')
              duration = request.form.get(f'gameconsole_duration_{i}')
              if not starting_time_str or not duration:
                    break
              starting_time = time_str_to_hours(starting_time_str)
              game_console_schedules.append((starting_time, float(duration)))
              i += 1
        P_consumption_gameconsole = punctual_load_fun(nominal_power_game_console, Simulation_StepTime, *game_console_schedules)
    # return P_consumption_gameconsole.tolist()
    # End of Game Console

    # Lighting Section
    # Lighting1
    Lighting1_enabled = request.form.get('Lighting1_enabled') == 'true'
    if not Lighting1_enabled :
        P_consumption_Lighting1 = np.array([0] * (int(24 * 3600 / Simulation_StepTime)))
    else:
        nominal_power_Lighting1 = float(request.form.get('Lighting1_nominal_power',0))
        Lighting_schedules = []

        i = 0
        while True:
              starting_time_str = request.form.get(f'Lighting1_starting_time_{i}')
              duration = request.form.get(f'Lighting1_duration_{i}')
              if not starting_time_str or not duration:
                    break
              starting_time = time_str_to_hours(starting_time_str)
              Lighting_schedules.append((starting_time, float(duration)))
              i += 1
        P_consumption_Lighting1 = punctual_load_fun(nominal_power_Lighting1, Simulation_StepTime, *Lighting_schedules)

    # Lighting2
    Lighting2_enabled = request.form.get('Lighting2_enabled') == 'true'
    if not Lighting2_enabled :
        P_consumption_Lighting2 = np.array([0] * (int(24 * 3600 / Simulation_StepTime)))
    else:
        nominal_power_Lighting2 = float(request.form.get('Lighting2_nominal_power',0))
        Lighting2_schedules = []

        i = 0
        while True:
              starting_time_str = request.form.get(f'Lighting2_starting_time_{i}')
              duration = request.form.get(f'Lighting2_duration_{i}')
              if not starting_time_str or not duration:
                    break
              starting_time = time_str_to_hours(starting_time_str)
              Lighting2_schedules.append((starting_time, float(duration)))
              i += 1
        P_consumption_Lighting2 = punctual_load_fun(nominal_power_Lighting2, Simulation_StepTime, *Lighting2_schedules)

    # Lighting3
    Lighting3_enabled = request.form.get('Lighting3_enabled') == 'true'
    if not Lighting3_enabled :
        P_consumption_Lighting3 = np.array([0] * (int(24 * 3600 / Simulation_StepTime)))
    else:
        nominal_power_Lighting3 = float(request.form.get('Lighting3_nominal_power',0))
        Lighting3_schedules = []

        i = 0
        while True:
              starting_time_str = request.form.get(f'Lighting3_starting_time_{i}')
              duration = request.form.get(f'Lighting3_duration_{i}')
              if not starting_time_str or not duration:
                    break
              starting_time = time_str_to_hours(starting_time_str)
              Lighting3_schedules.append((starting_time, float(duration)))
              i += 1
        P_consumption_Lighting3 = punctual_load_fun(nominal_power_Lighting3, Simulation_StepTime, *Lighting3_schedules)

    # End of Lighting section

    # Total_consumption:
    P_consumption_total=heatpump_cons +P_WH+Pr_consumption+P_consumption_WM+(P_consumption_tv + P_consumption_microwave + P_consumption_oven + P_consumption_iron + P_consumption_hairdryer + P_consumption_fan + P_consumption_gameconsole+P_consumption_Lighting1+P_consumption_Lighting3+P_consumption_Lighting2)*presence
    P_consumption_total_list = P_consumption_total.tolist()
    # return P_consumption_total_list


    # Use render_template to display results
    return render_template('page_2_consumption_profile.html', Simulation_StepTime =Simulation_StepTime, house_height=house_height, roof_pitch=roof_pitch, num_windows=num_windows, window_surface=window_surface, isolation_type=isolation_type, heating_system_type=heating_system_type, nominal_power=nominal_power, water_heater_type=water_heater_type, nominal_power_water_heater=nominal_power_water_heater, water_tank_volume=water_tank_volume, cold_water_temperature_estimation=cold_water_temperature_estimation, refrigerator_type=refrigerator_type, nominal_power_refrigerator=nominal_power_refrigerator, dimensions_refrigerator=dimensions_refrigerator, num_drawers_refrigerator=num_drawers_refrigerator, num_shelves_refrigerator=num_shelves_refrigerator,
                            temperature_time_pairs=temperature_time_pairs, occupancy_time_pairs=occupancy_time_pairs,season =season, T_hp0=T_hp0, P_consumption_total_list=P_consumption_total_list)




@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('page_1_user_main.html')

    if request.method == 'POST':
        return process_form()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port="8099")
    #app.run(host='0.0.0.0')