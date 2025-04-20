import pymumble_py3 as pymumble
import keyboard
import pyaudio
import threading
import time

server = "hjdczy.top"

class ATCRadioClient:
    def __init__(self, server, user, password, frequency):
        self.frequency = frequency
        self.mumble = pymumble.Mumble(server, user, password=password, reconnect=True)
        self.mumble.set_receive_sound(True)  # 启用音频接收
        self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, self.sound_received)  # 设置音频接收回调
        self.mumble.callbacks.set_callback("connected", self.on_connected)
        self.connected = False
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.speaking = False
        self.current_channel = None  # 添加初始化
        self.CHUNK = 960  # 20ms @ 48000Hz
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 48000

    def start(self):
        self.mumble.start()
        self.mumble.is_ready()
        self.setup_audio()  # 初始化音频设备

    def on_connected(self):
        self.connected = True
        freq_value = int(round(float(self.frequency) * 1000))
        channel_name = f"FREQ_{str(freq_value).zfill(6)}"

        print(f"连接到服务器: {self.mumble}")
        try:
            channel = self.mumble.channels.find_by_name(channel_name)
        except pymumble.errors.UnknownChannelError:
            # 创建新频道
            self.mumble.channels.new_channel(0, channel_name, temporary=True)
            time.sleep(0.1)  # 给服务器一点时间来创建频道
            try:
                channel = self.mumble.channels.find_by_name(channel_name)
            except:
                print(f"无法创建或找到频道: {channel_name}")
                return

        if channel:
            if not hasattr(self, 'current_channel') or self.current_channel != channel["channel_id"]:
                self.mumble.users.myself.move_in(channel["channel_id"])
                self.current_channel = channel["channel_id"]
                print(f"已切换到频率: {self.frequency}")

    def setup_audio(self, input_device=None, output_device=None):
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()

        self.input_stream = self.audio.open(
            input=True,
            input_device_index=input_device,
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            frames_per_buffer=self.CHUNK
        )

        self.output_stream = self.audio.open(
            output=True,
            output_device_index=output_device,
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            frames_per_buffer=self.CHUNK
        )

    def start_speaking(self):
        if not self.speaking:
            self.speaking = True
            threading.Thread(target=self._audio_thread).start()

    def stop_speaking(self):
        self.speaking = False

    def _audio_thread(self):
        while self.speaking:
            if self.input_stream:
                try:
                    data = self.input_stream.read(self.CHUNK, exception_on_overflow=False)
                    if data:
                        self.mumble.sound_output.add_sound(data)
                except Exception as e:
                    print(f"录音错误: {e}")
            time.sleep(0.01)

    def sound_received(self, user, soundchunk):
        """处理接收到的音频"""
        try:
            if user["name"] != self.mumble.users.myself["name"]:  # 不播放自己的声音
                if self.output_stream:
                    self.output_stream.write(soundchunk.pcm)
        except Exception as e:
            print(f"处理接收音频时出错: {e}")

    def stop(self):
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        self.audio.terminate()
        self.mumble.stop()

