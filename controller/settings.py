from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                         QPushButton, QSlider, QLineEdit, QComboBox)
from PyQt6.QtCore import Qt
import json
import os
from pynput import keyboard

class Settings:
    def __init__(self):
        self.config_file = "radio_settings.json"
        self.ptt_key = "v"
        self.mic_volume = 100
        self.speaker_volume = 100
        self.input_device_index = None
        self.output_device_index = None
        self.last_username = ""
        self.last_frequency = ""
        self.load_settings()

    def load_settings(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    self.ptt_key = data.get("ptt_key", "v")
                    self.mic_volume = data.get("mic_volume", 100)
                    self.speaker_volume = data.get("speaker_volume", 100)
                    self.input_device_index = data.get("input_device_index", None)
                    self.output_device_index = data.get("output_device_index", None)
                    self.last_username = data.get("last_username", "")
                    self.last_frequency = data.get("last_frequency", "")
        except Exception as e:
            print(f"加载设置失败: {e}")

    def save_settings(self):
        try:
            data = {
                "ptt_key": self.ptt_key,
                "mic_volume": self.mic_volume,
                "speaker_volume": self.speaker_volume,
                "input_device_index": self.input_device_index,
                "output_device_index": self.output_device_index,
                "last_username": self.last_username,
                "last_frequency": self.last_frequency
            }
            with open(self.config_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"保存设置失败: {e}")

class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("设置")
        self.setup_ui()
        self.listening_for_key = False

    def setup_ui(self):
        layout = QVBoxLayout()

        # 音量控制
        volume_group = QVBoxLayout()
        volume_label = QLabel("音量控制")
        volume_label.setStyleSheet("font-weight: bold;")
        volume_group.addWidget(volume_label)

        # 麦克风音量
        mic_layout = QHBoxLayout()
        mic_label = QLabel("麦克风音量:")
        self.mic_slider = QSlider(Qt.Orientation.Horizontal)
        self.mic_slider.setRange(0, 200)
        self.mic_slider.setValue(self.settings.mic_volume)
        self.mic_value = QLabel(f"{self.settings.mic_volume}%")
        mic_layout.addWidget(mic_label)
        mic_layout.addWidget(self.mic_slider)
        mic_layout.addWidget(self.mic_value)
        volume_group.addLayout(mic_layout)

        # 扬声器音量
        speaker_layout = QHBoxLayout()
        speaker_label = QLabel("收听音量:")
        self.speaker_slider = QSlider(Qt.Orientation.Horizontal)
        self.speaker_slider.setRange(0, 200)
        self.speaker_slider.setValue(self.settings.speaker_volume)
        self.speaker_value = QLabel(f"{self.settings.speaker_volume}%")
        speaker_layout.addWidget(speaker_label)
        speaker_layout.addWidget(self.speaker_slider)
        speaker_layout.addWidget(self.speaker_value)
        volume_group.addLayout(speaker_layout)

        # PTT按键设置
        ptt_layout = QHBoxLayout()
        ptt_label = QLabel("PTT按键:")
        self.ptt_input = QLineEdit(self.settings.ptt_key)
        self.ptt_input.setReadOnly(True)
        self.ptt_reset_btn = QPushButton("重设")
        self.ptt_reset_btn.clicked.connect(self.start_key_capture)
        ptt_layout.addWidget(ptt_label)
        ptt_layout.addWidget(self.ptt_input)
        ptt_layout.addWidget(self.ptt_reset_btn)

        # 音频输入设备选择
        input_layout = QHBoxLayout()
        input_label = QLabel("输入设备:")
        self.input_combo = QComboBox()
        self.populate_audio_devices(self.input_combo, True)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_combo)

        # 音频输出设备选择
        output_layout = QHBoxLayout()
        output_label = QLabel("输出设备:")
        self.output_combo = QComboBox()
        self.populate_audio_devices(self.output_combo, False)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_combo)

        # 按钮
        button_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)

        # 连接信号
        self.mic_slider.valueChanged.connect(
            lambda v: self.mic_value.setText(f"{v}%"))
        self.speaker_slider.valueChanged.connect(
            lambda v: self.speaker_value.setText(f"{v}%"))
        save_button.clicked.connect(self.save_and_close)
        cancel_button.clicked.connect(self.reject)

        # 添加所有布局
        layout.addLayout(volume_group)
        layout.addLayout(ptt_layout)
        layout.addLayout(input_layout)
        layout.addLayout(output_layout)
        layout.addLayout(button_layout)
        layout.addStretch()
        self.setLayout(layout)

    def populate_audio_devices(self, combo_box, is_input):
        """填充音频设备下拉列表"""
        import pyaudio
        p = pyaudio.PyAudio()
        
        # 添加"系统默认"选项
        combo_box.addItem("系统默认", None)
        
        # 遍历所有音频设备
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if is_input and device_info.get('maxInputChannels') > 0:
                combo_box.addItem(device_info.get('name'), i)
            elif not is_input and device_info.get('maxOutputChannels') > 0:
                combo_box.addItem(device_info.get('name'), i)
        
        # 设置当前选中的设备
        current_index = self.settings.input_device_index if is_input else self.settings.output_device_index
        if current_index is not None:
            index = combo_box.findData(current_index)
            if index >= 0:
                combo_box.setCurrentIndex(index)
        p.terminate()

    def start_key_capture(self):
        """开始捕获键盘按键"""
        self.listening_for_key = True
        self.ptt_input.setText("请按下按键...")
        self.ptt_reset_btn.setEnabled(False)
        
        def on_key_pressed(key):
            if self.listening_for_key:
                # 转换按键为字符串格式
                key_str = key.char if hasattr(key, 'char') else key.name if hasattr(key, 'name') else str(key)
                self.ptt_input.setText(key_str)
                self.listening_for_key = False
                self.ptt_reset_btn.setEnabled(True)
                if hasattr(self, 'keyboard_listener'):
                    self.keyboard_listener.stop()
                    self.keyboard_listener = None

        # 创建新的键盘监听器
        self.keyboard_listener = keyboard.Listener(on_press=on_key_pressed)
        self.keyboard_listener.start()

    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'keyboard_listener') and self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None

    def reject(self):
        """取消时清理资源"""
        self.cleanup()
        super().reject()

    def accept(self):
        """确认时清理资源"""
        self.cleanup()
        super().accept()

    def save_and_close(self):
        self.settings.ptt_key = self.ptt_input.text() or "v"
        self.settings.mic_volume = self.mic_slider.value()
        self.settings.speaker_volume = self.speaker_slider.value()
        self.settings.input_device_index = self.input_combo.currentData()
        self.settings.output_device_index = self.output_combo.currentData()
        self.settings.save_settings()

        # 立即应用音量设置
        parent = self.parent()
        if parent and parent.radio_client:
            parent.radio_client.set_mic_volume(self.settings.mic_volume)
            parent.radio_client.set_speaker_volume(self.settings.speaker_volume)

        self.accept()