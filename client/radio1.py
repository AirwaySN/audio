from SimConnect import *
import pymumble_py3 as pymumble
import threading
import time
import keyboard
import pyaudio
import wave
import numpy as np


# 配置服务器信息
SERVER_HOST = "hjdczy.top"  # Mumble服务器地址
USERNAME = "1005"    # 用户名
PASSWORD = "yoyo14185721"             # 密码（如果需要）

class MumbleRadioClient:
    def __init__(self, server_host, username, password=""):
        # SimConnect 初始化
        self.simconnect = SimConnect()
        self.aq = AircraftRequests(self.simconnect, _time=2000)
        
        # 音频配置
        self.CHUNK = 960  # 20ms @ 48000Hz
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 48000
        self.is_talking = False
        
        # PyAudio 初始化
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        # Mumble 客户端配置
        self.mumble = pymumble.Mumble(
            server_host, 
            username,
            password=password,
            reconnect=True
        )
        self.mumble.set_receive_sound(True)
        self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, self.handle_incoming_audio)
        self.current_channel = None

        # 添加音频输出流
        self.output_stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True,
            frames_per_buffer=self.CHUNK
        )
        

    def convert_frequency(self, frequency):
        """将频率转换为标准格式"""
        return int(round(frequency * 1000))
    
    def get_channel_name(self, frequency):
        """根据频率生成频道名称"""
        freq = self.convert_frequency(frequency)
        return f"FREQ_{str(freq).zfill(6)}"
    
    def switch_channel(self, frequency):
        """切换到对应频率的频道"""
        channel_name = self.get_channel_name(frequency)
        try:
            channel = self.mumble.channels.find_by_name(channel_name)
        except pymumble.errors.UnknownChannelError:
            # 如果频道不存在则创建
            self.mumble.channels.new_channel(0, channel_name,temporary=True)
            channel = self.mumble.channels.find_by_name(channel_name)
        
        if channel and self.current_channel != channel["channel_id"]:
            self.mumble.users.myself.move_in(channel["channel_id"])
            self.current_channel = channel["channel_id"]
            print(f"已切换到频率: {frequency:.3f} MHz")
    
    def monitor_frequency(self):
        """监控COM1频率变化"""
        last_frequency = None
        while True:
            try:
                com1_active = self.aq.get("COM_ACTIVE_FREQUENCY:1")
                if com1_active != last_frequency:
                    self.switch_channel(com1_active)
                    last_frequency = com1_active
            except Exception as e:
                print(f"频率监控错误: {e}")
            time.sleep(0.5)
    
    def handle_voice(self):
        """处理按键说话功能"""
        while True:
            if keyboard.is_pressed('v'):  # 按住V键说话
                if not self.is_talking:
                    self.is_talking = True
                    print("开始说话...")
                
                # 读取音频数据
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                self.mumble.sound_output.add_sound(data)
            else:
                if self.is_talking:
                    self.is_talking = False
                    print("停止说话")
            time.sleep(0.01)

    def handle_incoming_audio(self, user, soundchunk):
        """处理接收到的音频"""
        if user["name"] != self.mumble.users.myself["name"]:  # 不播放自己的声音
            self.output_stream.write(soundchunk.pcm)

    def run(self):
        """启动客户端"""
        try:
            # 连接到Mumble服务器
            self.mumble.start()
            self.mumble.is_ready()
            print("已连接到Mumble服务器")
            
            # 启动频率监控
            monitor_thread = threading.Thread(target=self.monitor_frequency)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # 启动语音处理
            voice_thread = threading.Thread(target=self.handle_voice)
            voice_thread.daemon = True
            voice_thread.start()
            
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("正在关闭客户端...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'output_stream'):
            self.output_stream.stop_stream()
            self.output_stream.close()
        if hasattr(self, 'audio'):
            self.audio.terminate()
        if hasattr(self, 'mumble'):
            self.mumble.stop()
        if hasattr(self, 'simconnect'):
            self.simconnect.exit()


if __name__ == "__main__":
    client = None
    try:
        client = MumbleRadioClient(SERVER_HOST, USERNAME, PASSWORD)
        client.run()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n程序发生错误: {e}")
    finally:
        if client:
            client.cleanup()
        print("\n按回车键退出...")
        try:
            input()
        except:
            # 如果input()失败，使用time.sleep作为备选
            import time
            time.sleep(5)