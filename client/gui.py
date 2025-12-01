import sys
import os

# 在导入pygame之前设置SDL环境变量
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                         QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                         QStackedWidget, QMessageBox, QDialog)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPalette, QColor
from radio import MumbleRadioClient
import threading
import time
import keyboard
import pymumble_py3 as pymumble
import queue
import pygame

ico_path = r".\favicon.ico"

class CircleIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.is_active = False

    def setActive(self, active):
        self.is_active = active
        self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.is_active:
            color = QColor(0, 255, 0)  # 绿色
        else:
            color = QColor(128, 128, 128)  # 灰色

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(5, 5, 20, 20)

class LoginWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 用户名输入
        username_layout = QHBoxLayout()
        username_label = QLabel("用户名:")
        self.username_input = QLineEdit()
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        
        # 密码输入
        password_layout = QHBoxLayout()
        password_label = QLabel("密码:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        
        # 登录按钮和错误提示的水平布局
        button_error_layout = QHBoxLayout()
        self.login_button = QPushButton("登录")
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red")
        button_error_layout.addWidget(self.login_button)
        button_error_layout.addWidget(self.error_label)
        button_error_layout.addStretch()
        
        layout.addLayout(username_layout)
        layout.addLayout(password_layout)
        layout.addLayout(button_error_layout)
        
        self.setLayout(layout)
        
    def show_error(self, message):
        self.error_label.setText(message)
        
    def clear_error(self):
        self.error_label.setText("")

class MainWindow(QWidget):
    def __init__(self, radio_client, parent=None):
        super().__init__(parent)
        self.radio_client = radio_client
        self.setup_ui()
        
        # 设置定时器更新COM1频率
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frequency)
        self.timer.start(1000)  # 每秒更新一次
        
        # 连接设置按钮
        self.settings_button.clicked.connect(self.show_settings)

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 顶部栏：COM1频率显示
        top_layout = QHBoxLayout()
        self.freq_label = QLabel("COM1: -.--- MHz")
        self.settings_button = QPushButton("设置")
        top_layout.addWidget(self.freq_label)
        top_layout.addWidget(self.settings_button)
        
        # 中间区域：PTT指示灯
        middle_layout = QHBoxLayout()
        ptt_label = QLabel("PTT状态:")
        self.ptt_indicator = CircleIndicator()
        middle_layout.addWidget(ptt_label)
        middle_layout.addWidget(self.ptt_indicator)
        middle_layout.addStretch()
        
        layout.addLayout(top_layout)
        layout.addLayout(middle_layout)
        layout.addStretch()
        
        self.setLayout(layout)

    def update_frequency(self):
        try:
            freq = self.radio_client.aq.get("COM_ACTIVE_FREQUENCY:1")
            self.freq_label.setText(f"COM1: {freq:.3f} MHz")
        except:
            self.freq_label.setText("COM1: -.--- MHz")

    def update_ptt_status(self, is_talking):
        self.ptt_indicator.setActive(is_talking)

    def show_settings(self):
        from settings import SettingsDialog
        dialog = SettingsDialog(self.radio_client.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 更新音量设置并重新初始化音频设备
            self.radio_client.reinitialize_audio()  # 重新初始化音频设备

class ErrorSignal(QObject):
    error = pyqtSignal(str)

class ConnectSignal(QObject):
    connected = pyqtSignal()

class RadioGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # 设置应用程序图标和窗口图标
        from PyQt6.QtGui import QIcon
        icon = QIcon(ico_path)
        self.setWindowIcon(icon)
        app = QApplication.instance()
        if app:
            app.setWindowIcon(icon)

        # 初始化pygame
        try:
            print("[DEBUG-GUI] 开始初始化pygame子系统")
            pygame.init()
            print(f"[DEBUG-GUI] pygame.init() 返回值: {pygame.get_init()}")
            
            print("[DEBUG-GUI] 开始初始化显示系统")
            pygame.display.init()
            print("[DEBUG-GUI] 显示系统初始化状态:", pygame.display.get_init())
            
            print("[DEBUG-GUI] 开始初始化摇杆系统")
            pygame.joystick.init()
            print(f"[DEBUG-GUI] 摇杆系统初始化完成，检测到 {pygame.joystick.get_count()} 个摇杆")
            print(f"[DEBUG-GUI] 摇杆系统初始化状态: {pygame.joystick.get_init()}")
        except Exception as e:
            print(f"[DEBUG-GUI] Pygame初始化失败: {e}")
            print(f"[DEBUG-GUI] pygame状态:")
            print(f"- pygame.get_init(): {pygame.get_init()}")
            print(f"- pygame.display.get_init(): {pygame.display.get_init()}")
            print(f"- pygame.joystick.get_init(): {pygame.joystick.get_init()}")
            
        self.setWindowTitle("无线电-Airwaysn")
        self.setMinimumSize(300, 200)
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # 创建登录窗口
        self.login_window = LoginWindow()
        self.stacked_widget.addWidget(self.login_window)
        
        # 连接登录按钮事件
        self.login_window.login_button.clicked.connect(self.handle_login)
        
        # 新增：加载已有设置并自动填充账号密码
        from settings import Settings
        self.settings = Settings()
        try:
            self.login_window.username_input.setText(self.settings.username or "")
            self.login_window.password_input.setText(self.settings.password or "")
        except Exception as e:
            print(f"[DEBUG-GUI] 自动填充账号失败: {e}")

        self.radio_client = None
        self.main_window = None
        self.client_thread = None
        
        # 错误和连接成功信号处理
        
        self.error_signal = ErrorSignal()
        self.error_signal.error.connect(self.show_error)
        self.connect_signal = ConnectSignal()
        self.connect_signal.connected.connect(self.on_connected)

    def show_error(self, message):
        print(f"显示错误对话框: {message}")
        QMessageBox.critical(self, "登录错误", message)
        sys.stderr = sys.__stderr__

    def cleanup_client(self):
        """完全清理客户端及其资源"""
        print("开始清理客户端资源")
        if self.radio_client:
            self.radio_client.cleanup()
            self.radio_client = None
            print("已清理 radio_client")
        if self.main_window:
            self.stacked_widget.removeWidget(self.main_window)
            self.main_window.deleteLater()
            self.main_window = None
            print("已清理 main_window")
        
        # 只在非当前线程中进行线程清理
        if (not self.client_thread or 
            self.client_thread != threading.current_thread()):
            if self.client_thread and self.client_thread.is_alive():
                self.client_thread.join(timeout=1.0)
                self.client_thread = None
                print("已清理 client_thread")
        else:
            self.client_thread = None
            
        print("客户端资源清理完成")

    def on_connected(self):
        """在主线程中处理连接成功"""
        try:
            print("连接成功，正在初始化主窗口...")
            self.login_window.clear_error()
            # 新增：登录成功后保存账号与密码到设置文件
            try:
                if self.radio_client and self.radio_client.settings:
                    self.radio_client.settings.save_settings()
            except Exception as e:
                print(f"[DEBUG-GUI] 登录后保存设置失败: {e}")

            # 创建主窗口
            self.main_window = MainWindow(self.radio_client)
            self.stacked_widget.addWidget(self.main_window)
            # 切换到主窗口
            self.stacked_widget.setCurrentWidget(self.main_window)
            print("主窗口初始化完成")
            
            # 设置 PTT 状态监听函数
            def on_ptt_change(is_talking):
                if self.main_window:
                    self.main_window.update_ptt_status(is_talking)
            self.radio_client.on_ptt_change = on_ptt_change
            
            # 启动监控和语音线程
            self.radio_client.monitor_thread = threading.Thread(target=self.radio_client.monitor_frequency)
            self.radio_client.voice_thread = threading.Thread(target=self.radio_client.handle_voice)
            self.radio_client.monitor_thread.daemon = True
            self.radio_client.voice_thread.daemon = True
            self.radio_client.monitor_thread.start()
            self.radio_client.voice_thread.start()
            print("后台线程启动完成")
        except Exception as e:
            print(f"主窗口初始化失败: {e}")
            self.login_window.show_error(f"初始化失败: {str(e)}")
            self.cleanup_client()

    def handle_login(self):
        print("开始登录流程")
        self.cleanup_client()
        
        username = self.login_window.username_input.text()
        password = self.login_window.password_input.text()
        print(f"正在尝试登录，用户名: {username}")
        
        try:
            print("正在初始化 MumbleRadioClient...")
            # 新增：把输入的账号密码写入现有 Settings，并传入客户端
            try:
                self.settings.username = username or ""
                self.settings.password = password or ""
            except Exception as e:
                print(f"[DEBUG-GUI] 写入账号到设置失败: {e}")

            self.radio_client = MumbleRadioClient("118.153.226.153", username, password, settings=self.settings)
            print("MumbleRadioClient 初始化完成")
            
            # 设置连接成功回调
            self.radio_client.mumble.callbacks.set_callback(
                pymumble.constants.PYMUMBLE_CLBK_CONNECTED, 
                lambda: self.connect_signal.connected.emit()
            )

            # 添加连接错误回调
            def on_reject(error):
                print(f"连接被拒绝: {error}")
                self.error_signal.error.emit(str(error))
            
            self.radio_client.mumble.callbacks.set_callback(
                pymumble.constants.PYMUMBLE_CLBK_DISCONNECTED,
                lambda: self.error_signal.error.emit("连接断开")
            )
            
            def run_client():
                try:
                    print("正在启动客户端连接...")
                    
                    self.radio_client.mumble.run()
                    print("等待连接完成...")
                    self.radio_client.mumble.is_ready()
                    print("连接成功")
                    
                    while self.radio_client and self.radio_client.mumble.is_alive():
                        time.sleep(1)
                        
                except pymumble.errors.ConnectionRejectedError as e:
                    print(f"连接被拒绝: {str(e)}")
                    if "Wrong certificate or password" in str(e):
                        self.error_signal.error.emit("登录失败：用户名或密码错误")
                    else:
                        self.error_signal.error.emit(f"登录失败：{str(e)}")
                    self.cleanup_client()
                except Exception as e:
                    print(f"连接过程中发生错误: {str(e)}")
                    self.error_signal.error.emit(f"连接错误: {str(e)}")
                    self.cleanup_client()
                finally:
                    print("客户端线程结束")
            
            print("正在启动客户端线程...")
            self.client_thread = threading.Thread(target=run_client, daemon=True)
            self.client_thread.start()
            print("客户端线程已启动")
            
        except Exception as e:
            print(f"初始化过程发生错误: {str(e)}")
            self.error_signal.error.emit(f"初始化失败: {str(e)}")
            self.cleanup_client()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RadioGUI()
    window.show()
    sys.exit(app.exec())

