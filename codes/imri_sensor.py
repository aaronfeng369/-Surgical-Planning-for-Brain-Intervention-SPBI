from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import imri_setting
import numpy as np
import time
import modbus_tk.modbus_tcp as mt
import modbus_tk.defines as cst
import struct
import time
import datetime

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import threading  # 导入 threading 模块以使用线程功能
import re  # 正则表达式模块


class MyFigure(FigureCanvasQTAgg):
    def __init__(self, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MyFigure, self).__init__(self.fig)
        self.axes = self.fig.add_subplot(111)


class Sensor(QMainWindow):
    def __init__(self, parent=None):
        super(Sensor, self).__init__(parent)
        self.fig_gridlayout = None
        self.config = imri_setting.read_config()
        self.F = MyFigure(width=50, height=50, dpi=70)
        self.master = None  # modbus master
        self.force_record_stop_flag = False
        self.thread_force_recording_flag = False
        self.sensor_ip = self.config["sensor"]["ip"]
        self.sensor_port = self.config["sensor"]["port"]
        self.force_k = self.config["sensor"]["force_k"]
        self.force_b = self.config["sensor"]["force_b"]
        self.sample_interval = self.config["sensor"]["sample_interval(ms)"]
        self.force_values = []
        self.time_values = []

    def init(self, ui):
        self.fig_gridlayout = ui.gridLayout_sensor
        self.ForceBtn = ui.ForceBtn
        self.ForceValue = ui.ForceValue
        self.ForceValue.setText("0")
        self.ForceSetting = ui.ForceSetting
        self.ForceSetting.setIcon(QIcon("image/setting_icon.png"))
        self.ForceSetting.clicked.connect(self.setForceSensor)
        self.ForceBtn.clicked.connect(self.setForceBtn)

    def setForceSensor(self):
        inputDialog = QInputDialog()
        inputDialog.setOption(QInputDialog.UsePlainTextEditForTextInput)
        inputDialog.setFixedSize(400, 200)
        inputDialog.setWindowTitle("Setting")
        inputDialog.setLabelText("Force Sensor:")
        inputDialog.setOkButtonText("Save")
        inputDialog.setCancelButtonText("Close")
        inputDialog.setTextValue(f"IP:{self.sensor_ip}\nPort:{self.sensor_port}\nforce_k:{self.force_k}\nforce_b:{self.force_b}\nsample_interval(ms):{self.sample_interval}")
        while inputDialog.exec_():
            try:
                text = inputDialog.textValue()
                # pattern = re.compile(r":(\d+(\.\d+){3}|\d+)")
                pattern = re.compile(r":(.*)")
                matches = pattern.findall(text)
                print(matches)
                if len(matches) != 5:
                    QMessageBox.warning(self, "Warning", "Please input correct format1!")
                    continue
                else:
                    self.sensor_ip = matches[0]
                    self.sensor_port = int(matches[1])
                    self.force_k = float(matches[2])
                    self.force_b = float(matches[3])
                    self.sample_interval = int(matches[4])
                    self.config["sensor"]["ip"] = self.sensor_ip
                    self.config["sensor"]["port"] = self.sensor_port
                    self.config["sensor"]["force_k"] = self.force_k
                    self.config["sensor"]["force_b"] = self.force_b
                    self.config["sensor"]["sample_interval(ms)"] = self.sample_interval
                    imri_setting.update_config(config=self.config)
                    print("Force Sensor Setting:", self.sensor_ip, self.sensor_port, self.force_k, self.force_b, self.sample_interval)
            except Exception as e:
                print(e)
                QMessageBox.warning(self, "Warning", "Please input correct format2!")
                continue

    def setForceBtn(self):
        if self.ForceBtn.text() == "Force":
            self.F.axes.clear()
            self.force_values = []
            self.time_values = []
            self.ForceBtn.setStyleSheet(self.config["button"]["active"])
            self.ForceSetting.setEnabled(False)
            self.ForceBtn.setText("Force-Recording")
            self.connectSensor(ip=self.sensor_ip, port=self.sensor_port)
            # 创建一个新的文件，用于保存力传感器的数据
            current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            self.force_file_path = f"output/force_{current_time}.txt"
            file = open(self.force_file_path, "w")
            file.close()
            self.force_record_stop_flag = True
            if self.thread_force_recording_flag is False:
                self.thread_force_recording = threading.Thread(target=self.readForceSensor)
                self.thread_force_recording.start()
                self.thread_force_recording_flag = True

        else:
            self.ForceBtn.setText("Force")
            self.ForceBtn.setStyleSheet(self.config["button"]["normal"])
            self.ForceSetting.setEnabled(True)
            self.force_record_stop_flag = False
            self.thread_force_recording_flag = False
            self.master.close()

    def connectSensor(self, ip="192.168.100.113", port=502):
        self.master = mt.TcpMaster(ip, port)
        self.master.set_timeout(1000)

    def readForceSensor(self):
        while self.force_record_stop_flag:
            time.sleep(self.sample_interval / 1000)
            # 0x03功能码：读保持寄存器
            holding_value = self.master.execute(slave=1, function_code=cst.READ_HOLDING_REGISTERS, starting_address=1000, quantity_of_x=14)
            # print("0x03 READ_HOLDING_REGISTERS: ", holding_value)
            a1 = hex(holding_value[0])
            a2 = hex(holding_value[1])
            # print(a1, a2)

            combined_hex_a = reverse_and_combine_hex_bytes(a1, a2)
            # print(combined_hex_a)

            # 将十六进制字符串转换为字节
            hex_str = combined_hex_a[2:]
            hex_bytes = bytes.fromhex(hex_str)
            if len(hex_bytes) != 4:
                # print("字节长度不为4", len(hex_bytes), hex_bytes)
                continue

            # 使用 struct.unpack 将字节转换为浮点数
            float_num = struct.unpack(">f", hex_bytes)[0]
            # print("十六进制数 {} 转换为浮点数为：{}".format(hex_str, float_num))

            float_num = round(float_num + 1500, 2)  # 波长

            force = round(self.force_k * float_num + self.force_b, 2)
            if force < 0:
                force = 0.00
            self.ForceValue.setText(str(force))
            print("force:", force)

            # save force value to file
            with open(self.force_file_path, "a") as f:
                f.write(f"{force}\n")

            (line,) = self.F.axes.plot(self.force_values, self.time_values, marker="o", linestyle="-")

            self.force_values.append(force)
            t = (len(self.force_values) - 1) * self.sample_interval / 1000
            self.time_values.append(t)

            self.F.axes.set_xlabel("Time (s)", fontsize=20)
            self.F.axes.set_ylabel("Force Value (N)", fontsize=20)
            self.F.axes.set_title("Real-Time Force Value Changes", fontsize=25)
            self.F.axes.tick_params(labelsize=20)

            # 实时绘制图形
            self.fig_gridlayout.addWidget(self.F, 0, 0)

            line.set_xdata(self.time_values)
            line.set_ydata(self.force_values)
            self.F.axes.set_xlim(0, t + self.sample_interval / 1000 * 3)
            self.F.axes.set_ylim(min(self.force_values) - 1, max(self.force_values) + 1)

            self.F.fig.canvas.draw()

            self.F.fig.canvas.flush_events()
            # plt.pause(0.2)


def reverse_and_combine_hex_bytes(hex_number1, hex_number2):
    # 将十六进制数转换为字符串，并移除前缀'0x'
    hex_str1 = hex_number1[2:]
    # 如果长度是奇数，在前面补'0'使其长度为偶数
    if len(hex_str1) % 2 != 0:
        hex_str1 = "0" + hex_str1
    # 将字符串每两个字符分为一组，反转这些组，并重新拼接成一个字符串
    reversed_hex_str1 = "".join([hex_str1[i : i + 2] for i in range(0, len(hex_str1), 2)][::-1])

    hex_str2 = hex_number2[2:]
    if len(hex_str2) % 2 != 0:
        hex_str2 = "0" + hex_str2
    reversed_hex_str2 = "".join([hex_str2[i : i + 2] for i in range(0, len(hex_str2), 2)][::-1])

    revesed_combine_hex_str = reversed_hex_str2 + reversed_hex_str1

    # 将反转后的字符串转换回整数，并加上'0x'前缀
    reversed_hex_number = int(revesed_combine_hex_str, 16)

    return hex(reversed_hex_number)
