from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                         QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                         QStackedWidget, QFrame, QSlider)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import re
import keyboard
from radio import ATCRadioClient, server
from settings import Settings, SettingsDialog

class PTTIndicator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.active = False
        self.setStyleSheet("background-color: #808080; border-radius: 10px;")

    def setPTTActive(self, active):
        self.active = active
        self.setStyleSheet(f"background-color: {'#ff0000' if active else '#808080'}; border-radius: 10px;")

class ATCWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.radio_client = None
        self.settings = Settings()
        self.server = server  # 添加服务器地址属性
        self.initUI()
        self.setup_keyboard_hook()

    def initUI(self):
        self.setWindowTitle('ATC Radio Client')
        self.setGeometry(100, 100, 400, 200)

        # 创建堆叠窗口部件
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # 创建登录页面
        self.login_page = QWidget()
        self.setup_login_page()
        
        # 创建通信页面
        self.comm_page = QWidget()
        self.setup_comm_page()

        # 将页面添加到堆叠窗口
        self.stacked_widget.addWidget(self.login_page)
        self.stacked_widget.addWidget(self.comm_page)

        # 加载上次的设置
        self.username_input.setText(self.settings.last_username)
        self.freq_input.setText(self.settings.last_frequency)

    def setup_login_page(self):
        layout = QVBoxLayout(self.login_page)

        # 用户名
        username_layout = QHBoxLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('用户名')
        username_layout.addWidget(QLabel('用户名:'))
        username_layout.addWidget(self.username_input)

        # 密码
        password_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('密码')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(QLabel('密码:'))
        password_layout.addWidget(self.password_input)

        # 频率
        freq_layout = QHBoxLayout()
        self.freq_input = QLineEdit()
        self.freq_input.setPlaceholderText('频率 (例如: 118.000)')
        freq_layout.addWidget(QLabel('频率:'))
        freq_layout.addWidget(self.freq_input)

        # 连接按钮
        self.connect_btn = QPushButton('连接')
        self.connect_btn.clicked.connect(self.connect_radio)

        # 状态标签
        self.login_status_label = QLabel('未连接')
        self.login_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 添加所有部件
        layout.addLayout(username_layout)
        layout.addLayout(password_layout)
        layout.addLayout(freq_layout)
        layout.addWidget(self.connect_btn)
        layout.addWidget(self.login_status_label)

    def setup_comm_page(self):
        layout = QVBoxLayout(self.comm_page)
        
        # 顶部工具栏（频率显示和设置按钮）
        top_bar = QHBoxLayout()
        self.freq_display = QLabel()
        self.freq_display.setAlignment(Qt.AlignmentFlag.AlignLeft)
        settings_btn = QPushButton("设置")
        settings_btn.clicked.connect(self.open_settings)
        top_bar.addWidget(self.freq_display)
        top_bar.addWidget(settings_btn)
        
        # PTT状态显示
        ptt_layout = QHBoxLayout()
        self.ptt_indicator = PTTIndicator()
        ptt_label = QLabel("PTT状态")
        ptt_layout.addWidget(self.ptt_indicator)
        ptt_layout.addWidget(ptt_label)
        ptt_layout.addStretch()
        
        # PTT按钮
        self.ptt_button = QPushButton('按住说话 (PTT)')
        self.ptt_button.pressed.connect(self.ptt_pressed)
        self.ptt_button.released.connect(self.ptt_released)
        
        # 状态标签
        self.comm_status_label = QLabel('就绪')
        self.comm_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 断开连接按钮
        self.disconnect_btn = QPushButton('断开连接')
        self.disconnect_btn.clicked.connect(self.disconnect_radio)
        
        # 添加所有部件
        layout.addLayout(top_bar)
        layout.addLayout(ptt_layout)
        layout.addWidget(self.ptt_button)
        layout.addWidget(self.comm_status_label)
        layout.addWidget(self.disconnect_btn)

    def setup_keyboard_hook(self):
        keyboard.on_press_key(self.settings.ptt_key, lambda _: self.ptt_pressed())
        keyboard.on_release_key(self.settings.ptt_key, lambda _: self.ptt_released())

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            # 更新键盘钩子
            keyboard.unhook_all()
            self.setup_keyboard_hook()
            # 更新音频设备
            if self.radio_client:
                self.radio_client.setup_audio(
                    self.settings.input_device_index,
                    self.settings.output_device_index
                )

    def validate_frequency(self, freq):
        pattern = r'^\d{3}\.\d{1,3}$'
        return bool(re.match(pattern, freq))

    def format_frequency(self, freq):
        base, decimal = freq.split('.')
        decimal = decimal.ljust(3, '0')
        return f"{base}.{decimal}"

    def connect_radio(self):
        username = self.username_input.text()
        password = self.password_input.text()
        frequency = self.freq_input.text()

        if not all([username, password, frequency]):
            self.login_status_label.setText('请填写所有字段')
            return

        if not self.validate_frequency(frequency):
            self.login_status_label.setText('频率格式无效')
            return

        frequency = self.format_frequency(frequency)

        try:
            self.radio_client = ATCRadioClient(self.server, username, password, frequency)
            self.radio_client.setup_audio(
                self.settings.input_device_index,
                self.settings.output_device_index
            )
            # 设置初始音量
            self.radio_client.set_mic_volume(self.settings.mic_volume)
            self.radio_client.set_speaker_volume(self.settings.speaker_volume)
            self.radio_client.start()
            self.freq_display.setText(f'当前频率: {frequency}')
            self.stacked_widget.setCurrentIndex(1)
            
            # 保存最后使用的用户名和频率
            self.settings.last_username = username
            self.settings.last_frequency = frequency
            self.settings.save_settings()
            
        except Exception as e:
            self.login_status_label.setText(f'连接失败: {str(e)}')

    def disconnect_radio(self):
        if self.radio_client:
            self.radio_client.stop()
            self.radio_client = None
        self.stacked_widget.setCurrentIndex(0)  # 返回登录页面
        self.login_status_label.setText('未连接')

    def ptt_pressed(self):
        if self.radio_client:
            self.radio_client.start_speaking()
            self.comm_status_label.setText('正在发送...')
            self.ptt_indicator.setPTTActive(True)

    def ptt_released(self):
        if self.radio_client:
            self.radio_client.stop_speaking()
            self.comm_status_label.setText('就绪')
            self.ptt_indicator.setPTTActive(False)

    def update_mic_volume(self, value):
        if self.radio_client:
            self.radio_client.set_mic_volume(value)
        self.settings.mic_volume = value
        self.settings.save_settings()

    def update_speaker_volume(self, value):
        if self.radio_client:
            self.radio_client.set_speaker_volume(value)
        self.settings.speaker_volume = value
        self.settings.save_settings()

    def closeEvent(self, event):
        keyboard.unhook_all()
        if self.radio_client:
            self.radio_client.stop()
        event.accept()

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = ATCWindow()
    window.show()
    sys.exit(app.exec())