import pyttsx3
import threading
import time
import wave
import numpy as np
import os
import tempfile
from scipy import signal
import re

chinese_numbers = {
    0: "洞",
    1: "幺",
    2: "两",
    3: "三",
    4: "四",
    5: "五",
    6: "六",
    7: "拐",
    8: "八",
    9: "九",
}

english_numbers = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "niner",
}

english_characters = {
    "A": "Alpha",
    "B": "Bravo",
    "C": "Charlie",
    "D": "Delta",
    "E": "Echo",
    "F": "Foxtrot",
    "G": "Golf",
    "H": "Hotel",
    "I": "India",
    "J": "Juliett",
    "K": "Kilo",
    "L": "Lima",
    "M": "Mike",
    "N": "November",
    "O": "Oscar",
    "P": "Papa",
    "Q": "Quebec",
    "R": "Romeo",
    "S": "Sierra",
    "T": "Tango",
    "U": "Uniform",
    "V": "Victor",
    "W": "Whiskey",
    "X": "X-ray",
    "Y": "Yankee",
    "Z": "Zulu"
}

def process_atis_text(text, is_chinese=False):
    """
    处理ATIS文本，替换字母和数字为对应的无线电读法
    is_chinese: 是否为中文ATIS
    """
    if not text:
        return text
        
    # 选择对应的数字读法字典
    number_dict = chinese_numbers if is_chinese else english_numbers
    
    # 处理空格+大写字母+空格的模式
    def replace_letter(match):
        letter = match.group(1)
        return f" {english_characters.get(letter, letter)} "
    
    text = re.sub(r'\s([A-Z])\s', replace_letter, text)
    
    # 处理数字
    def replace_number(match):
        number = match.group(0)
        number_text = " ".join(number_dict[int(digit)] for digit in number)
        return f" {number_text} "
    
    text = re.sub(r'\d+', replace_number, text)
    return text

class ATISBroadcaster:
    def __init__(self, chinese_text, english_text, radio_client):
        print("初始化ATIS广播器...")
        self.chinese_text = process_atis_text(chinese_text, is_chinese=True) if chinese_text else ""
        self.english_text = process_atis_text(english_text, is_chinese=False)
        self.radio_client = radio_client
        self.running = False
        self.broadcast_thread = None
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 100)  # 降低语速
        self.engine.setProperty('volume', 0.8)
        self.target_rate = 48000  # 目标采样率
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        print(f"创建临时目录: {self.temp_dir}")
        print("ATIS广播器初始化完成")
        self.chunk_size = 960000
        self.silence_threshold = 100  # 音量阈值，低于此值视为静音
        self.silence_duration = 1.0  # 持续静音时间阈值（秒）
        self.last_sound_time = time.time()

    def text_to_audio_data(self, text):
        """将文本转换为音频数据"""
        if not text or not text.strip():
            print("警告：收到空文本")
            return None
            
        print(f"开始转换文本到音频: {text[:30]}...")
        try:
            # 使用临时文件
            temp_file = os.path.join(self.temp_dir, 'temp_atis.wav')
            print(f"使用临时文件: {temp_file}")
            
            # 保存到临时文件
            self.engine.save_to_file(text, temp_file)
            self.engine.runAndWait()
            
            # 等待文件生成完成
            retry_count = 0
            while not os.path.exists(temp_file) and retry_count < 5:
                time.sleep(0.2)
                retry_count += 1
                
            if not os.path.exists(temp_file):
                raise FileNotFoundError("音频文件未能生成")
                
            # 验证文件大小
            file_size = os.path.getsize(temp_file)
            if file_size == 0:
                raise ValueError("生成的音频文件为空")
                
            print(f"临时文件大小: {file_size} 字节")
            
            # 读取音频数据
            with wave.open(temp_file, 'rb') as wav_file:
                original_rate = wav_file.getframerate()
                if original_rate <= 0:
                    raise ValueError("无效的采样率")
                    
                print(f"音频参数: 通道数={wav_file.getnchannels()}, "
                      f"采样率={original_rate}, "
                      f"采样宽度={wav_file.getsampwidth()}")
                      
                frames = wav_file.getnframes()
                if frames <= 0:
                    raise ValueError("音频帧数为0")
                    
                audio_data = wav_file.readframes(frames)
                if not audio_data:
                    raise ValueError("无法读取音频数据")
                
            # 将字节数据转换为numpy数组
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            if len(audio_array) == 0:
                raise ValueError("转换后的音频数组为空")
            
            # 计算重采样
            if original_rate != self.target_rate:
                print(f"重采样音频从 {original_rate}Hz 到 {self.target_rate}Hz")
                samples_count = len(audio_array)
                new_samples_count = int(samples_count * (self.target_rate / original_rate))
                audio_array = signal.resample(audio_array, new_samples_count)
                # 确保数据类型正确
                audio_array = np.clip(audio_array, np.iinfo(np.int16).min, np.iinfo(np.int16).max).astype(np.int16)
            
            if len(audio_array) == 0:
                raise ValueError("重采样后的音频数组为空")
            
            # 删除临时文件
            try:
                os.remove(temp_file)
                print("临时文件已删除")
            except Exception as e:
                print(f"删除临时文件失败: {e}")
                
            # 转换回字节
            audio_data = audio_array.tobytes()
            if not audio_data:
                raise ValueError("无法将音频数组转换为字节数据")
                
            print(f"成功生成音频数据: {len(audio_data)} 字节")
            return audio_data
            
        except Exception as e:
            print(f"音频生成错误: {str(e)}")
            print(f"错误类型: {type(e)}")
            return None  # 发生错误时返回None

    def __del__(self):
        """清理临时目录"""
        try:
            os.rmdir(self.temp_dir)
            print("临时目录已清理")
        except Exception as e:
            print(f"清理临时目录失败: {e}")

    def check_channel_silence(self):
        """检查频道是否处于静音状态"""
        try:
            current_time = time.time()
            for user in self.radio_client.mumble.users.values():
                if user["name"] != self.radio_client.mumble.users.myself["name"]:
                    try:
                        sound = user.get("sound")
                        if sound is None:
                            continue
                            
                        audio_data = sound.get_sound(10)
                        if audio_data is None or len(audio_data) == 0:
                            continue
                            
                        audio_array = np.frombuffer(audio_data, dtype=np.int16)
                        if len(audio_array) > 0:
                            volume = np.abs(audio_array).mean()
                            if volume > self.silence_threshold:
                                self.last_sound_time = current_time
                                return False
                    except Exception as e:
                        print(f"检查用户 {user['name']} 音频时出错: {e}")
                        continue
                        
            return (current_time - self.last_sound_time) >= self.silence_duration
        except Exception as e:
            print(f"检查频道音量时出错: {e}")
            return True  # 出错时默认允许发送

    def send_audio_data(self, audio_data):
        """发送音频数据到mumble"""
        if not audio_data:
            print("警告: 收到空的音频数据")
            return False
            
        print(f"开始发送音频数据，总大小: {len(audio_data)} 字节")
        position = 0
        total_size = len(audio_data)
        chunks_sent = 0
        send_start_time = time.time()
        
        try:
            self.radio_client.start_speaking()
            print("已开启语音发送状态")

            while position < total_size and self.running:
                # 检查频道是否有其他声音
                if not self.check_channel_silence():
                    print("检测到频道有其他音频，暂停发送")
                    time.sleep(0.5)
                    continue

                remaining = total_size - position
                current_chunk_size = min(self.chunk_size, remaining)
                
                chunk = audio_data[position:position + current_chunk_size]
                if not chunk:  # 检查切片后的数据是否为空
                    print("警告: 生成了空的音频块")
                    break

                if len(chunk) < current_chunk_size:
                    chunk = chunk + b'\x00' * (current_chunk_size - len(chunk))
                
                self.radio_client.mumble.sound_output.add_sound(chunk)
                position += current_chunk_size
                chunks_sent += 1
                
                if chunks_sent % 10 == 0:
                    print(f"已发送 {position}/{total_size} 字节 ({(position/total_size*100):.1f}%)")
                
                time.sleep(0.02)

            print(f"音频发送完成，共发送了 {chunks_sent} 个音频块")
            return True

        except Exception as e:
            print(f"音频发送错误: {str(e)}")
            return False
        finally:
            self.radio_client.stop_speaking()

    def _broadcast_loop(self):
        print("开始ATIS广播循环")
        while self.running:
            try:
                if self.check_channel_silence():
                    if self.chinese_text:  # 只有当存在中文文本时才播放中文
                        print("\n开始播放中文ATIS...")
                        chinese_audio = self.text_to_audio_data(self.chinese_text)
                        if not self.send_audio_data(chinese_audio):
                            continue

                        if not self.running:
                            break

                        print("中文播放完成，等待检查频道状态...")
                        time.sleep(20)

                    if self.check_channel_silence():
                        print("\n开始播放英文ATIS...")
                        english_audio = self.text_to_audio_data(self.english_text)
                        if not self.send_audio_data(english_audio):
                            continue
                    
                    print("英文播放完成，等待下一轮...")
                
                  # 检查频道状态的间隔
            except Exception as e:
                print(f"ATIS播放循环错误: {str(e)}")
                time.sleep(1)

            time.sleep(60)

    def start_broadcasting(self):
        self.running = True
        self.broadcast_thread = threading.Thread(target=self._broadcast_loop)
        self.broadcast_thread.start()

    def stop_broadcasting(self):
        self.running = False
        if self.broadcast_thread:
            self.broadcast_thread.join()


