from SimConnect import *
import pymumble_py3 as pymumble
import threading
import time
import keyboard
import pyaudio
import wave
import numpy as np  # 确保numpy被导入
import sys
import functools


# 配置服务器信息
SERVER_HOST = "hjdczy.top"  # Mumble服务器地址
USERNAME = "1005"    # 用户名
PASSWORD = "yoyo14185721"             # 密码（如果需要）

def suppress_mumble_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            # 抑制异常输出
            sys.stderr = open('nul', 'w')
            raise
    return wrapper

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
        self.on_ptt_change = None
        
        # 添加设置支持
        from settings import Settings
        self.settings = Settings()
        
        # 初始化音频设备
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
            input_device_index=self.settings.input_device_index
        )
        self.output_stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True,
            frames_per_buffer=self.CHUNK,
            output_device_index=self.settings.output_device_index
        )

        # 初始化 Mumble 客户端
        self.mumble = pymumble.Mumble(
            server_host, 
            username,
            password=password,
            reconnect=True
        )
        
        self.mumble.set_receive_sound(True)
        self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, self.handle_incoming_audio)
        self.current_channel = None
        
        # 初始应用音量设置
        self.update_volumes()
        
        # 线程管理
        self.monitor_thread = None
        self.voice_thread = None
        self.running = True

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
        while self.running:
            try:
                if self.mumble.connected:  # 只在连接成功时监控频率
                    com1_active = self.aq.get("COM_ACTIVE_FREQUENCY:1")
                    if com1_active is not None and com1_active != last_frequency:
                        self.switch_channel(com1_active)
                        last_frequency = com1_active
            except Exception as e:
                if self.running:  # 只在正常运行时打印错误
                    print(f"频率监控错误: {e}")
            time.sleep(1)  # 增加检查间隔，减少错误日志
    
    def update_volumes(self):
        """更新麦克风和扬声器音量"""
        try:
            if self.mumble and self.mumble.connected:
                # 麦克风音量 0-200% 映射到 0-2.0
                self.mumble.sound_output.volume = self.settings.mic_volume / 100.0
            if hasattr(self, 'output_stream'):
                # 扬声器音量 0-200% 映射到音频数据缩放
                volume_scale = self.settings.speaker_volume / 100.0
                def volume_modifier(audio_data):
                    return (np.frombuffer(audio_data, dtype=np.int16) * volume_scale).astype(np.int16).tobytes()
                self.audio_processor = volume_modifier
        except Exception as e:
            print(f"更新音量设置时出错: {e}")

    def handle_voice(self):
        """处理按键说话功能"""
        while True and self.running:
            try:
                is_speaking = keyboard.is_pressed(self.settings.ptt_key)
                if is_speaking != self.is_talking:
                    self.is_talking = is_speaking
                    if self.on_ptt_change:
                        self.on_ptt_change(self.is_talking)
                
                if self.is_talking and self.stream and self.mumble and self.mumble.connected:
                    try:
                        data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                        if data:
                            # 调整麦克风音量
                            audio_data = np.frombuffer(data, dtype=np.int16)
                            audio_data = (audio_data * (self.settings.mic_volume / 100.0)).astype(np.int16)
                            self.mumble.sound_output.add_sound(audio_data.tobytes())
                    except IOError as e:
                        print(f"音频读取错误: {e}")
                    except Exception as e:
                        print(f"音频发送错误: {e}")
                
                time.sleep(0.01)
            except Exception as e:
                print(f"语音处理错误: {e}")
                time.sleep(1)

    def handle_incoming_audio(self, user, soundchunk):
        """处理接收到的音频"""
        if user["name"] != self.mumble.users.myself["name"]:  # 不播放自己的声音
            try:
                # 调整收听音量
                audio_data = np.frombuffer(soundchunk.pcm, dtype=np.int16)
                audio_data = (audio_data * (self.settings.speaker_volume / 100.0)).astype(np.int16)
                self.output_stream.write(audio_data.tobytes())
            except Exception as e:
                print(f"音频输出错误: {e}")

    def reinitialize_audio(self):
        """重新初始化音频设备"""
        try:
            # 关闭现有的音频流
            if hasattr(self, 'stream') and self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if hasattr(self, 'output_stream') and self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
            
            # 重新创建音频流
            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                input_device_index=self.settings.input_device_index
            )
            self.output_stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                output=True,
                frames_per_buffer=self.CHUNK,
                output_device_index=self.settings.output_device_index
            )
            
            # 更新音量设置
            self.update_volumes()
            print("音频设备重新初始化完成")
        except Exception as e:
            print(f"重新初始化音频设备失败: {e}")
            raise

    def show_settings(self):
        """显示设置对话框"""
        from settings import SettingsDialog
        dialog = SettingsDialog(self.settings)
        if dialog.exec():
            # 如果用户点击了保存，则重新初始化音频设备
            self.reinitialize_audio()

    @suppress_mumble_errors
    def run(self):
        """启动客户端主循环"""
        try:
            self.mumble.start()
            time.sleep(1)  # 给予足够时间让连接完成或失败
            
            # 尝试执行一个操作来检查连接状态
            try:
                self.mumble.is_ready()
            except pymumble.errors.ConnectionRejectedError:
                raise pymumble.errors.ConnectionRejectedError("用户名或密码错误")
                
            while self.running:
                try:
                    self.mumble.is_ready()
                    time.sleep(1)
                except:
                    break
        except Exception as e:
            raise e from None
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        self.running = False  # 停止所有线程的运行
        
        try:
            if hasattr(self, 'stream') and self.stream:
                self.stream.stop_stream()
                self.stream.close()
                
            if hasattr(self, 'output_stream') and self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
                
            if hasattr(self, 'audio') and self.audio:
                self.audio.terminate()
                
            if hasattr(self, 'mumble') and self.mumble:
                try:
                    self.mumble.connected = 0
                except:
                    pass
                self.mumble.stop()
                
            if hasattr(self, 'simconnect') and self.simconnect:
                self.simconnect.exit()
                
            # 等待线程结束
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=1.0)
            if self.voice_thread and self.voice_thread.is_alive():
                self.voice_thread.join(timeout=1.0)
                
        except Exception as e:
            print(f"清理资源时出错: {e}")
            pass  # 确保清理过程中的错误不会影响程序


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