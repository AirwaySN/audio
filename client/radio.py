from SimConnect import *
import pymumble_py3

# 创建Mumble客户端




if __name__ == "__main__":
    try:
        # 创建SimConnect对象
        simconnect = SimConnect()
        aq = AircraftRequests(simconnect, _time=2000)

        # 获取COM1

        com1_active = aq.get("COM_ACTIVE_FREQUENCY:1")  


        def convert_ferquency(frequency):
            frequency = int(round(frequency * 1000))
            frequency = str(frequency).zfill(6)
            return frequency
 
        # print (aq.get("COM_STANDBY_FREQ_IDENT:1"))  

        print (f"COM1活动频率: {convert_ferquency(com1_active)}")

        


    except Exception as e:
        print(f"错误: {e}")
    finally:
        if 'simconnect' in locals():
            simconnect.exit()