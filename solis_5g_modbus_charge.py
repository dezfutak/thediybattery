##
# Based off Mark Gardiner's script here: 
# https://gist.github.com/markgdev/ce2dbf9002385cbe5a35b81985f9c84a
# I've added some tweaks to get additional information out of the inverter. 
# Note: the InverterStatus gathering (for fault reporting) is wrong, I'm pretty sure I've got my hex conversion wrong
# I know the last two batter statuses are correct as that's what the system reported when I had a battery fault :-)
##


import minimalmodbus
import time
import paho.mqtt.publish as publish

instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1, debug = False)
instrument.serial.baudrate = 9600
# This probably doesn't need setting but I was getting timeout failures 
# rather than wrong data address when I had the registers wrong
instrument.serial.timeout = 2
# An example read for long
# instrument.read_long(33004, functioncode=4, signed=False)

# MQTT
# mqtt                = os.environ['USE_MQTT']
#mqtt_client         = "solisinverter"
mqtt_client         = "homeassistant"
mqtt_server         = "localhost"
mqtt_username       = "USERNAME"
mqtt_password       = "PASSWORD"
debug               = False

InverterStatusDict = {
    0: 'Waiting',
    1: 'Open Loop',
    2: 'SoftRun',
    3: 'Normal/Generating',
    4100: 'Off-Grid ',
    4112: 'Grid overvoltage OV-G-V',
    4113: 'Grid undervoltage UN-G-V',
    4114: 'Grid overfrequency OV-G-F',
    4115: 'Grid underfrequency UN-G-F',
    4116: 'Grid impedance is too large G-IMP',
    4117: 'No Grid',
    4118: 'Grid imbalance G-PHASE',
    4119: 'Grid frequency jitter G-F-FLU',
    4120: 'Grid overcurrent OV-G-I',
    4121: 'Grid current tracking fault IGFOL-F',
    4122: 'DC overvoltage OV-DC',
    4129: 'DC bus overvoltage OV-BUS',
    4130: 'DC busbar uneven voltage UNB-BUS',
    4131: 'DC bus undervoltage UN-BUS',
    4132: 'DC busbar uneven voltage 2 UNB2-BUS',
    4133: 'DC A way overcurrent OV-DCA-I',
    4134: 'DC B path overcurrent OV-DCB-I',
    4135: 'DC input disturbance DC-INTF',
    4144: 'Grid disturbance GRID-INTF',
    4145: 'DSP initialization protection INI-Fault',
    4146: 'Overtemperature protection OV-TEM',
    4147: 'PV insulation fault PV ISO-PRO',
    4148: 'Leakage current protection ILeak-PRO',
    4149: 'Relay detection protection RelayChk-FAIL',
    4150: 'DSP_B protection DSP-B-FAULT',
    4151: 'DC component is too large DCInj-FAULT',
    4152: '12V undervoltage protection 12Power-FAULT',
    4153: 'Leakage current self-test protection ILeak-Check',
    4154: 'Under temperature protection UN-TEM',
    4160: 'Arc self-test protection AFCI-Check',
    4161: 'Arc protection ARC-FAULT',
    4162: 'DSP on-chip SRAM exception RAM-FAULT',
    4163: 'DSP on-chip FLASH exception FLASH-FAULT',
    4164: 'DSP on-chip PC pointer is abnormal PC-FAULT',
    4165: 'DSP key register exception REG-FAULT',
    4166: 'Grid disturbance 02 GRID-INTF02',
    4167: 'Grid current sampling abnormality IG-AD',
    4168: 'IGBT overcurrent IGBT-OV-I',
    4176: 'Network side current transient overcurrent OV-IgTr',
    4177: 'Battery overvoltage hardware failure OV-Vbatt-H',
    4178: 'LLC hardware overcurrent OV-ILLC',
    4179: 'Battery overvoltage detection OV-Vbatt',
    4180: 'Battery undervoltage detection UN-Vbatt',
    4181: 'Battery no connected NO-Battery',
    4182: 'Bypass overvoltage fault OV-VBackup',
    4183: 'Bypass overload fault Over-Load',
    8210: 'No Battery',
    8213: 'Battery Alarm'
}

def get_status():
    # Inverter Temp
    inverter_temp = instrument.read_register(33093, functioncode=4, number_of_decimals=1, signed=False)
    
    #write to inverter iff chargetime has change - this variable tells us if the "chargeovernight" script has recently
    #been run, or not 
    with open("/home/pi/code/battery/writetoinverter", "r") as file:
        writetoinverter = file.read()
        writetoinverter = writetoinverter.rstrip('\n')
        writetoinverter = int(writetoinverter)
    
    # Inverter Time
    inverter_time_hour = instrument.read_register(33025, functioncode=4, signed=False)
    inverter_time_min = instrument.read_register(33026, functioncode=4, signed=False)
    inverter_time_sec = instrument.read_register(33027, functioncode=4, signed=False)
    inverter_time_all = str(inverter_time_hour).zfill(2)+":"+str(inverter_time_min).zfill(2)+":"+str(inverter_time_sec).zfill(2)
    #print("Inverter Time=",inverter_time_all)

    # Battery Status, 0=Charge, 1=Discharge
    battery_status = instrument.read_register(33135, functioncode=4, signed=False)

    # Battery SOC
    battery_soc = instrument.read_register(33139, functioncode=4, signed=False)

    # Grid Power (w), Positive=Export, Negative=Import
    grid_power = instrument.read_long(33130, functioncode=4, signed=True)


    # House load power (w)
    house_power = instrument.read_register(33147, functioncode=4, signed=False)

    # Battery Power (w)
    battery_power = instrument.read_long(33149, functioncode=4, signed=True)

    if battery_status == 0:
        battery_abs = battery_power
    else:
        battery_abs = -battery_power

    # Current generation (Active power) (w), need to confirm when generating
    current_generation =  instrument.read_long(33057, functioncode=4, signed=False)
    total_active_power =  instrument.read_long(33263, functioncode=4, signed=True)
    # instrument.read_long(33079, functioncode=4, signed=True)
    # possibly this too 33263? "Meter total active power"

    inverter_status = instrument.read_register(33095, functioncode=4, signed=False)

    # Total generation today (kWh)
    generation_today = instrument.read_register(33035, functioncode=4, number_of_decimals=1, signed=False)

    # Total generation yesterday (kWh)
    generation_yesterday = instrument.read_register(33036, functioncode=4, number_of_decimals=1, signed=False)
    # Grid import power yesterday (kWh)
    grid_import_yesterday = instrument.read_register(33172, functioncode=4, number_of_decimals=1, signed=False)
    grid_import_yesterday = grid_import_yesterday / 10
    # Grid import power today (kWh)
    grid_import_today = instrument.read_register(33171, functioncode=4, number_of_decimals=1, signed=False)
    grid_import_today = grid_import_today /10
    # Grid export power yesterday (kWh)
    grid_export_yesterday = instrument.read_register(33176, functioncode=4, number_of_decimals=1, signed=False)
    # Grid export power yesterday (kWh)
    house_load_yesterday = instrument.read_register(33180, functioncode=4, number_of_decimals=1, signed=False)
    
    #Grid Power
    gridvoltage = (instrument.read_register(33128, functioncode=4, signed=False))/10
    gridcurrent = (instrument.read_register(33129, functioncode=4, signed=False))/100
    gridpower = gridvoltage*gridcurrent


    #String 1 Current
    string1current = instrument.read_register(33050, functioncode=4, signed=False)
    string1current = string1current/10
    #String 2 Current
    string2current = instrument.read_register(33052, functioncode=4, signed=False)
    string2current = string2current/10
    #String 1 Voltage
    string1voltage = instrument.read_register(33049, functioncode=4, signed=False)
    string1voltage = string1voltage/10
    #String 2 Voltage
    string2voltage = instrument.read_register(33051, functioncode=4, signed=False)
    string2voltage = string2voltage/10
    string1power = round(string1voltage*string1current,3)
    string2power = round(string2voltage*string2current,3)
    # Total PV Power
    #total_pv_power = instrument.read_register(33058, functioncode=4, signed=False)
    totalpvpower = string1power+string2power
    
    #kWh this month
    thismonthkwh = instrument.read_register(33032, functioncode=4, signed=False)
    
    #kWh last month
    lastmonthkwh = instrument.read_register(33034, functioncode=4, signed=False)

    # Battery storage mode, 33=self use, 35=timed charge
    storage_mode = instrument.read_register(43110, functioncode=3, signed=False)
    
    with open("/home/pi/code/battery/chargehourstart", "r") as file:
        chargehourstart = file.read()
        chargehourstart = int(chargehourstart.rstrip('\n'))
    #    print(str(chargehourstart))
    with open("/home/pi/code/battery/chargeminutestart", "r") as file: 
        chargeminutestart = file.read()
        chargeminutestart = int(chargeminutestart.rstrip('\n'))
    #    print(str(chargeminutestart))
    
    

    #####################
    # Timed charge start
    #####################
    # doesn't work: instrument.write_registers(43143, number_of_registers=8, functioncode=6)
    
    #instrument.write_registers(43143, [3, 44, 7, 34, 0, 0, 0, 0])    
    
    if writetoinverter == 1:
        #Start Hour
        instrument.write_register(43143, functioncode=6, signed=False, value=chargehourstart)
        #Start Min
        instrument.write_register(43144, functioncode=6, signed=False, value=chargeminutestart)
    
        #End Hour
        instrument.write_register(43145, functioncode=6, signed=False, value=7)
        #End Min
        instrument.write_register(43146, functioncode=6, signed=False, value=30)
 
    instrument.read_registers(43143, number_of_registers=8, functioncode=3)
    # Hour
    charge_start_hour = instrument.read_register(43143, functioncode=3, signed=False)
    # Minute
    charge_start_min = instrument.read_register(43144, functioncode=3, signed=False)
    # Timed charge end
    # Hour
    charge_end_hour = instrument.read_register(43145, functioncode=3, signed=False)
    # Minute
    charge_end_min = instrument.read_register(43146, functioncode=3, signed=False)

    charge_start_time = str(charge_start_hour).zfill(2)+":"+str(charge_start_min).zfill(2)
    charge_end_time = str(charge_end_hour).zfill(2)+":"+str(charge_end_min).zfill(2)

    if debug:
        print(f"Inverter time: {str(inverter_time_hour).zfill(2)}:{str(inverter_time_min).zfill(2)}:{str(inverter_time_sec).zfill(2)}")
        print(f"Inverter Temperature: {inverter_temp}")
        print(f"Battery Status: {battery_status}")
        print(f"Inverter Status: {inverter_status}")
        print(f"Battery SOC: {battery_soc}")
        print(f"Grid Power: {grid_power}")
        print(f"House Power: {house_power}")
        print(f"Battery Power: {battery_power}")
        print(f"Current Generation: {current_generation}")
        print(f"Total Active Power: {total_active_power}")
        print(f"Generation Today: {generation_today}")
        print(f"Generation Yesterday: {generation_yesterday}")
        print(f"Grid Import Yesterday: {grid_import_yesterday}")
        print(f"Grid Export Yesterday: {grid_export_yesterday}")
        print(f"House Load Yesterday: {house_load_yesterday}")
        print(f"Battery Storage Mode: {storage_mode}")




    # Push to MQTT
    msgs = []

    mqtt_topic = ''.join([mqtt_client, "/" ])   # Create the topic base using the client_id and serial number
    
    if (mqtt_username != "" and mqtt_password != ""):
        auth_settings = {'username':mqtt_username, 'password':mqtt_password}
    else:
        auth_settings = None
    
    msgs.append((mqtt_topic + "Battery_Charge_Percent", battery_soc, 0, False))
    msgs.append((mqtt_topic + "Battery_Power", battery_power, 0, False))
    msgs.append((mqtt_topic + "Battery_Abs", battery_abs, 0, False))
    msgs.append((mqtt_topic + "Battery_Status", battery_status, 0, False))
    if inverter_status in InverterStatusDict:
        msgs.append((mqtt_topic + "Inverter_Status", InverterStatusDict[inverter_status], 0, False))
    else:
        msgs.append((mqtt_topic + "Inverter_Status", inverter_status, 0, False))
    msgs.append((mqtt_topic + "Power_Grid_Total_Power", grid_power, 0, False))
    # Fix to match what we get from m.ginlong.com while we're switching between the two
    Power_Grid_Status = 2.0 # Default to importing
    if grid_power > 0:
        Power_Grid_Status = 1.0
    msgs.append((mqtt_topic + "Power_Grid_Status", Power_Grid_Status, 0, False))
    msgs.append((mqtt_topic + "Consumption_Power", house_power, 0, False))
    msgs.append((mqtt_topic + "AC_Power", current_generation, 0, False))
    msgs.append((mqtt_topic + "Total_Active_Power", total_active_power, 0, False))
    msgs.append((mqtt_topic + "generation_today", generation_today, 0, False))
    msgs.append((mqtt_topic + "generation_yesterday", generation_yesterday, 0, False))
    msgs.append((mqtt_topic + "generation_thismonth", thismonthkwh, 0, False))
    msgs.append((mqtt_topic + "generation_lastmonth", lastmonthkwh, 0, False))
    msgs.append((mqtt_topic + "grid_import_yesterday", grid_import_yesterday, 0, False))
    msgs.append((mqtt_topic + "grid_import_today", grid_import_today, 0, False))
    msgs.append((mqtt_topic + "grid_export_yesterday", grid_export_yesterday, 0, False))
    msgs.append((mqtt_topic + "gridpower", gridpower, 0, False))
    msgs.append((mqtt_topic + "house_load_yesterday", house_load_yesterday, 0, False))
    msgs.append((mqtt_topic + "inverter_temp", inverter_temp, 0, False))
    msgs.append((mqtt_topic + "storage_mode", storage_mode, 0, False))
    msgs.append((mqtt_topic + "string1_current", string1current, 0, False))
    msgs.append((mqtt_topic + "string2_current", string2current, 0, False))
    msgs.append((mqtt_topic + "string1_voltage", string1voltage, 0, False))
    msgs.append((mqtt_topic + "string2_voltage", string2voltage, 0, False))
    msgs.append((mqtt_topic + "string1_power", string1power, 0, False))
    msgs.append((mqtt_topic + "string2_power", string2power, 0, False))
    msgs.append((mqtt_topic + "totalpvpower", totalpvpower, 0, False))
    msgs.append((mqtt_topic + "inverter_time_all", inverter_time_all, 0, False))
    msgs.append((mqtt_topic + "inverter_time_hour", inverter_time_hour, 0, False))
    msgs.append((mqtt_topic + "inverter_time_min", inverter_time_min, 0, False))
    msgs.append((mqtt_topic + "inverter_time_sec", inverter_time_sec, 0, False))
    msgs.append((mqtt_topic + "charge_start_hour", charge_start_hour, 0, False))
    msgs.append((mqtt_topic + "charge_start_min", charge_start_min, 0, False))
    msgs.append((mqtt_topic + "charge_end_hour", charge_end_hour, 0, False))
    msgs.append((mqtt_topic + "charge_end_min", charge_end_min, 0, False))
    msgs.append((mqtt_topic + "charge_start_time", charge_start_time, 0, False))
    msgs.append((mqtt_topic + "charge_end_time", charge_end_time, 0, False))
    
    publish.multiple(msgs, hostname=mqtt_server, auth=auth_settings)

def timed_charge():
    # We can use read_registers to grab all the values in one call:
    # instrument.read_registers(43143, number_of_registers=8, functioncode=3)
    # Not going to check charge/discharge for now, we haven't implemented it yet.
    # Timed charge start
    # Hour
    charge_start_hour = instrument.read_register(43143, functioncode=3, signed=False)
    # Minute
    charge_start_min = instrument.read_register(43144, functioncode=3, signed=False)
    # Timed charge end
    # Hour
    charge_end_hour = instrument.read_register(43145, functioncode=3, signed=False)
    # Minute
    charge_end_min = instrument.read_register(43146, functioncode=3, signed=False)
    # Timed discharge start
    # Hour
    discharge_start_hour = instrument.read_register(43147, functioncode=3, signed=False)
    # Minute
    discharge_start_min = instrument.read_register(43148, functioncode=3, signed=False)
    # Timed discharge end
    # Hour
    discharge_end_hour = instrument.read_register(43149, functioncode=3, signed=False)
    # Minute
    discharge_end_min = instrument.read_register(43150, functioncode=3, signed=False)
    print(f"Charge Start: {charge_start_hour}:{charge_start_min}")
    print(f"Charge End: {charge_end_hour}:{charge_end_min}")
    print(f"Discharge Start: {discharge_start_hour}:{discharge_start_min}")
    print(f"Discharge End: {discharge_end_hour}:{discharge_end_min}")

    # Change charge start time minute, will work the same for the othe values.
    # instrument.write_register(43144, functioncode=6, signed=False, value=54)
    # We can write all the times in one call with write_registers:
    # instrument.write_registers(43143, [18, 00, 8, 0, 8, 0, 18, 0])
    # Storage control switch
    # 33 = Self use mode
    # 35 = Timed charge mode
    # Read/Write register
    # instrument.read_register(43110, functioncode=3, signed=False)
    # instrument.write_register(43110, functioncode=6, signed=False, value=33)
    # instrument.write_register(43110, functioncode=6, signed=False, value=35)
    # Read only register
    # instrument.read_register(33132, functioncode=4, signed=False)
while True:
    try:
        get_status()
    except Exception as e:
        print(e)
        print("Failed to query inverter, backing off for 30 seconds")
        time.sleep(30)
    if debug:
        print("-------------------------------")
    time.sleep(1)
