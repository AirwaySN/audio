from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                         QHBoxLayout, QLabel, QPushButton, QLineEdit, QStackedWidget)
from PyQt6.QtCore import Qt
import re
from radio import ATCRadioClient

class ATCWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.radio_client = None
        self.server = "hjdczy.top"
        self.initUI()

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
        
        # 频率显示
        self.freq_display = QLabel()
        self.freq_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
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
        layout.addWidget(self.freq_display)
        layout.addWidget(self.ptt_button)
        layout.addWidget(self.comm_status_label)
        layout.addWidget(self.disconnect_btn)

    def validate_frequency(self, freq):
        pattern = r'^\d{3}\.\d{3}$'
        return bool(re.match(pattern, freq))

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

        try:
            self.radio_client = ATCRadioClient(self.server, username, password, frequency)
            self.radio_client.start()
            self.freq_display.setText(f'当前频率: {frequency}')
            self.stacked_widget.setCurrentIndex(1)  # 切换到通信页面
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

    def ptt_released(self):
        if self.radio_client:
            self.radio_client.stop_speaking()
            self.comm_status_label.setText('就绪')

    def closeEvent(self, event):
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