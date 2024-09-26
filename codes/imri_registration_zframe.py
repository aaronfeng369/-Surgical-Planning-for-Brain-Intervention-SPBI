from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import imri_setting
import numpy as np
import os
import skimage
import math
import scipy

import matplotlib

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class MyFigure(FigureCanvasQTAgg):
    def __init__(self, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MyFigure, self).__init__(self.fig)
        self.axes = self.fig.add_subplot(111, projection="3d")


class ZFrame(QMainWindow):
    def __init__(self, parent=None):
        super(ZFrame, self).__init__(parent)
        self.read_btn = 0
        self.load_image_to_zframe_btn = 0
        self.load_zframe_to_robot_btn = 0
        self.start_registration_btn = 0
        self.start_slice_QSpinBox = 0
        self.end_slice_QSpinBox = 0
        self.process_bar = 0
        self.error_lineEdit = 0
        self.set_zframe_to_robot_btn = 0
        self.set_zframe_to_robot_spinBox_x = 0
        self.set_zframe_to_robot_spinBox_y = 0
        self.set_zframe_to_robot_spinBox_z = 0
        self.show_trans_matrix = 0
        self.show_trans_matrix_2 = 0
        self.fig_gridlayout = None
        self.config = imri_setting.read_config()
        self.ImageData = None  # initialized in imri_main.py zFrameInteract()
        self.trans_z = None  # image to zframe trans matrix
        self.trans_r = None  # zframe to robot trans matrix
        self.error = 0
        self.F = MyFigure(width=50, height=50, dpi=70)
        self.counts = 0

    def init(self, ui):
        self.read_btn = ui.ReadZFrameBtn
        self.load_image_to_zframe_btn = ui.LoadImgToZFrameBtn
        self.load_zframe_to_robot_btn = ui.LoadZFrameToRobotBtn
        self.start_registration_btn = ui.StartZFrameRegisterBtn
        self.start_slice_QSpinBox = ui.ZFrameStartSlice
        self.end_slice_QSpinBox = ui.ZFrameEndSlice
        self.save_zframe_mat_btn = ui.save_zframe_mat_btn
        self.save_robot_mat_btn = ui.save_robot_mat_btn
        self.process_bar = ui.progressBar
        self.process_bar.setRange(0, 100)
        self.process_bar.setValue(0)
        self.error_lineEdit = ui.registrationErrorLineEdit
        self.error_lineEdit.setReadOnly(True)
        # self.read_btn.clicked.connect(self.read_btn_clicked) # read button has been connected in imri_main.py
        self.start_registration_btn.clicked.connect(self.startRegistration)
        self.load_image_to_zframe_btn.clicked.connect(self.loadImageToZFrame)
        self.load_zframe_to_robot_btn.clicked.connect(self.loadZFrameToRobot)
        imri_setting.setSpinBox(self.start_slice_QSpinBox, 0, 100, 1, 1)
        imri_setting.setSpinBox(self.end_slice_QSpinBox, 0, 100, 15, 1)
        self.save_zframe_mat_btn.clicked.connect(self.saveZframeMat)
        self.save_robot_mat_btn.clicked.connect(self.saveRobotMat)

        self.set_zframe_to_robot_btn = ui.SetZFrameInRobotPosBtn
        self.set_zframe_to_robot_spinBox_x = ui.ZFrameInRobotPosX
        self.set_zframe_to_robot_spinBox_y = ui.ZFrameInRobotPosY
        self.set_zframe_to_robot_spinBox_z = ui.ZFrameInRobotPosZ
        imri_setting.setSpinBox(self.set_zframe_to_robot_spinBox_x, -1000, 1000, 0, 0.1)
        imri_setting.setSpinBox(self.set_zframe_to_robot_spinBox_y, -1000, 1000, 0, 0.1)
        imri_setting.setSpinBox(self.set_zframe_to_robot_spinBox_z, -1000, 1000, 0, 0.1)
        self.set_zframe_to_robot_btn.clicked.connect(self.setZFrameInRobotPos)

        self.show_trans_matrix = ui.ShowTransMatBrowser
        self.show_trans_matrix_2 = ui.ShowTransMatBrowser_2
        font = QFont()
        font.setPointSize(10)
        self.show_trans_matrix.setFont(font)
        self.show_trans_matrix_2.setFont(font)
        self.show_trans_matrix.insertPlainText("Image To ZFrame.\n")
        self.show_trans_matrix_2.insertPlainText("ZFrame To Robot.\n")

        self.fig_gridlayout = ui.gridLayout_zframe

        # load zframe file
        zframe_dir = self.config["zframe"]["mat_directory"]
        if os.path.exists(zframe_dir):
            file_list = os.listdir(zframe_dir)
            for file in file_list:
                if "ImageToZframeTransMatrix" in file:
                    data = scipy.io.loadmat(os.path.join(zframe_dir, file))
                    try:
                        self.trans_z = data["Trans_z"]
                        self.error = data["error"][0][0]
                        self.showImageToZFrame()
                    except:
                        print("Trans-Mat Error! Maybe it is not a ImageToZframeTransMatrix.mat file")

                if "ZframeToRobotTransMatrix" in file:
                    data = scipy.io.loadmat(os.path.join(zframe_dir, file))
                    try:
                        self.trans_r = data["Trans_r"]
                        self.set_zframe_to_robot_spinBox_x.setValue(self.trans_r[0][3])
                        self.set_zframe_to_robot_spinBox_y.setValue(self.trans_r[1][3])
                        self.set_zframe_to_robot_spinBox_z.setValue(self.trans_r[2][3])
                        self.showZFrameToRobot()
                    except:
                        print("Trans-Mat Error! Maybe it is not a ZframeToRobotTransMatrix.mat file")
        else:
            os.mkdir(zframe_dir)

    def startRegistration(self):
        try:
            start_slice = self.start_slice_QSpinBox.value()
            stop_slice = self.end_slice_QSpinBox.value()
            if start_slice >= stop_slice:
                QMessageBox.warning(self, "Warning", "Start slice should be smaller than end slice!")
                return

            nii_image = self.ImageData.Vtk2Numpy(self.ImageData.data)
            nii_image = np.transpose(nii_image, (1, 2, 0))
            nii_trans = self.ImageData.getTransMatrix()
            if stop_slice > nii_image.shape[2] - 1:
                QMessageBox.warning(self, "Warning", "End slice should be smaller than image slices!")
                return
            # print(nii_image.shape)
            self.F.axes.clear()
            # print("clear")
            self.counts += 1
            self.F.axes.set_title("Image To ZFrame Registration-" + str(self.counts), fontweight="bold")
            self.F.axes.set_xlabel("X-axis", fontweight="bold")
            self.F.axes.set_ylabel("Y-axis", fontweight="bold")
            self.F.axes.set_zlabel("Z-axis", fontweight="bold")

            def sort_center(image_center1):
                image_center2 = np.copy(image_center1)

                sortedIndex = np.argsort(image_center1[:, 0])
                sortedArray1 = image_center1[sortedIndex, :]

                leftArray = sortedArray1[0:3, :]
                rigthArray = sortedArray1[4:7, :]

                leftIndex = np.argsort(-1 * leftArray[:, 1])
                rightIndex = np.argsort(rigthArray[:, 1])

                image_center2[0:3, :] = leftArray[leftIndex, :]
                image_center2[3, :] = sortedArray1[3, :]
                image_center2[4:7, :] = rigthArray[rightIndex, :]

                return image_center2

            self.process_bar.setValue(20)
            # threshold segmentation and find fiducial centers
            lines_num = 7  # fiducial tupes
            slice_num = stop_slice - start_slice + 1  # selected slices

            img_center1 = np.zeros((lines_num, 2), dtype=float)
            coor_center = [[] for _ in range(lines_num)]
            for row in coor_center:
                row.extend([None] * slice_num)

            tt = -1
            for zz in range(start_slice, stop_slice + 1):
                tt = tt + 1
                cv_image = nii_image[:, :, zz]
                cv_image = (cv_image - np.min(cv_image)) / (np.max(cv_image) - np.min(cv_image)) * 255
                thre = skimage.filters.threshold_otsu(cv_image)
                bw = cv_image > thre
                bw = skimage.filters.median(bw)
                label = skimage.measure.label(bw)

                if tt == 0:
                    ii = -1
                    for region in skimage.measure.regionprops(label):
                        ii = ii + 1
                        img_center1[ii, :] = np.array([region.centroid[1], region.centroid[0]])

                    img_center2 = sort_center(img_center1)

                    for ii in range(0, lines_num):
                        coor = np.array([img_center2[ii, 0], img_center2[ii, 1], zz, 1])
                        coor = np.matmul(nii_trans, np.reshape(coor, (4, 1)))  # image to world
                        coor_center[ii][tt] = np.reshape(coor[0:3], (1, 3))

                else:
                    for region in skimage.measure.regionprops(label):
                        coor = np.array([region.centroid[1], region.centroid[0], zz, 1])

                        coor = np.matmul(nii_trans, np.reshape(coor, (4, 1)))  # image to world
                        coor = np.reshape(coor[0:3], (1, 3))

                        distance = []
                        for kk in range(0, 7):
                            coor1 = coor_center[kk][tt - 1]
                            distance.append(math.sqrt(np.linalg.norm(coor - coor1)))
                        min_index = distance.index(min(distance))
                        coor_center[min_index][tt] = coor

            # least square line fitting
            lines_p0_img = np.zeros((lines_num, 3))
            lines_v_img = np.zeros((lines_num, 3))
            self.process_bar.setValue(40)
            for kk in range(lines_num):
                coor_center1 = np.zeros((slice_num, 3))
                for ii in range(slice_num):
                    coor_center1[ii, :] = coor_center[kk][ii]

                p_zx = np.polyfit(coor_center1[:, 2], coor_center1[:, 0], 1)
                p_zy = np.polyfit(coor_center1[:, 2], coor_center1[:, 1], 1)

                lines_p0_img[kk, :] = [p_zx[1], p_zy[1], 0]
                lines_v_img[kk, :] = [p_zx[0], p_zy[0], 1]

                self.F.axes.scatter(coor_center1[:, 0], coor_center1[:, 1], coor_center1[:, 2], c="b")

            self.process_bar.setValue(60)
            # zframe in model coordinate system
            # 7 lines
            lines_p0_model = np.zeros_like(lines_p0_img)
            lines_v_model = np.zeros_like(lines_v_img)

            lines_p0_model[0, :] = [-40, 38, -38]
            lines_v_model[0, :] = [0, 0, 1]  # line 1

            lines_p0_model[1, :] = [-40, -38, 38]
            lines_v_model[1, :] = [0, -1, 1]  # line 2

            lines_p0_model[2, :] = [-40, -38, -40]
            lines_v_model[2, :] = [0, 0, 1]  # line 3

            lines_p0_model[3, :] = [40, -38, 40]
            lines_v_model[3, :] = [1, 0, 1]  # line 4

            lines_p0_model[4, :] = [40, -38, -38]
            lines_v_model[4, :] = [0, 0, 1]  # line 5

            lines_p0_model[5, :] = [40, 38, 38]
            lines_v_model[5, :] = [0, 1, 1]  # line 6

            lines_p0_model[6, :] = [40, 38, 38]
            lines_v_model[6, :] = [0, 0, 1]  # line 7

            self.F.axes.plot(lines_p0_model[:, 0], lines_p0_model[:, 1], lines_p0_model[:, 2], c="r", marker="*")

            # find 6 intersection points in image
            inters = np.zeros((lines_num - 1, 3))

            for ii in range(lines_num - 1):
                p1 = lines_p0_img[ii, :]
                p2 = lines_p0_img[ii + 1, :]
                v1 = lines_v_img[ii, :]
                v2 = lines_v_img[ii + 1, :]

                t1 = np.dot(np.cross((p2 - p1), v2), np.cross(v1, v2)) / (np.linalg.norm(np.cross(v1, v2))) ** 2
                t2 = np.dot(np.cross((p2 - p1), v1), np.cross(v1, v2)) / (np.linalg.norm(np.cross(v1, v2))) ** 2

                x1 = p1[0] + v1[0] * t1
                y1 = p1[1] + v1[1] * t1
                z1 = p1[2] + v1[2] * t1
                x2 = p2[0] + v2[0] * t2
                y2 = p2[1] + v2[1] * t2
                z2 = p2[2] + v2[2] * t2

                inters[ii, :] = [(x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2]

            self.F.axes.plot(inters[:, 0], inters[:, 1], inters[:, 2], c="g", marker="*")

            self.process_bar.setValue(80)
            # register image 2 frame
            data_source = inters
            data_target = lines_p0_model[0:6, :]

            data_source_mean = np.average(data_source, axis=0)
            data_target_mean = np.average(data_target, axis=0)

            data_source_c = data_source - data_source_mean
            data_target_c = data_target - data_target_mean

            W = np.matmul(data_source_c.T, data_target_c)
            U, S, VT = np.linalg.svd(W)
            Rf = np.matmul(U, VT)
            Tf = data_target_mean - np.matmul(data_source_mean, Rf)
            Tf = np.reshape(Tf, (3, 1))
            Trans_z = np.append(Rf.T, Tf, axis=1)
            Trans_z = np.append(Trans_z, [[0, 0, 0, 1]], axis=0)
            self.trans_z = Trans_z.tolist()
            # print("Trans_z:", Trans_z)s

            # calculate error
            data_source_2 = np.append(data_source.T, np.ones((1, data_source.shape[0])), axis=0)
            data_pre = np.matmul(Trans_z, data_source_2)
            data_final = data_pre.T[:, 0:3]
            self.F.axes.scatter(data_final[:, 0], data_final[:, 1], data_final[:, 2], c="y", marker="*")

            diff = np.sqrt(np.sum(np.square(data_target - data_final), axis=1))
            diff_mean = np.mean(diff)
            self.error = diff_mean
            self.error_lineEdit.setText(str(round(diff_mean, 4)))

            for kk in range(0, lines_num):
                coor_center1 = np.zeros((slice_num, 3))
                for ii in range(slice_num):
                    coor_center1[ii, :] = coor_center[kk][ii]

                coor = np.append(coor_center1.T, np.ones((1, slice_num)), axis=0)
                center_pre = np.matmul(Trans_z, coor)  # image to world
                center_final = center_pre.T[:, 0:3]
                self.F.axes.scatter(center_final[:, 0], center_final[:, 1], center_final[:, 2], c="y")

            # plt.show()
            self.fig_gridlayout.addWidget(self.F, 0, 0)
            self.process_bar.setValue(100)
            self.showImageToZFrame()
            self.autoSaveImageToZFrame()
            self.F.fig.canvas.draw()
            self.F.fig.canvas.flush_events()
        except Exception as e:
            print(e)
            QMessageBox.warning(self, "Warning", "Registration Failed! Please check the input data!")

    def autoSaveImageToZFrame(self):
        Trans_z = self.trans_z
        zframe_dir = self.config["zframe"]["mat_directory"]
        file_name = os.path.join(zframe_dir, "ImageToZframeTransMatrix.mat")
        scipy.io.savemat(file_name, {"Trans_z": Trans_z, "error": self.error})

    def showImageToZFrame(self):
        Trans_z = self.trans_z
        rows = 4
        cols = 4
        matrix_html = '<table border="1">'
        for i in range(rows):
            matrix_html += "<tr>"
            for j in range(cols):
                matrix_html += "<td>{}</td>".format(round(Trans_z[i][j], 2))
            matrix_html += "</tr>"
        matrix_html += "</table>"
        self.show_trans_matrix.clear()
        self.show_trans_matrix.insertPlainText("Image To ZFrame.\n")
        self.show_trans_matrix.insertHtml(matrix_html)

        # show registration error
        self.error_lineEdit.setText(str(round(self.error, 4)))

        imri_setting.IMRIGlobal.ImageToZframeTransMatrix = self.trans_z

    def setZFrameInRobotPos(self):
        x = self.set_zframe_to_robot_spinBox_x.value()
        y = self.set_zframe_to_robot_spinBox_y.value()
        z = self.set_zframe_to_robot_spinBox_z.value()
        self.trans_r = [[0, 0, -1, x], [1, 0, 0, y], [0, -1, 0, z], [0, 0, 0, 1]]

        self.showZFrameToRobot()
        self.autoSaveZFrameToRobot()

    def autoSaveZFrameToRobot(self):
        Trans_r = self.trans_r
        zframe_dir = self.config["zframe"]["mat_directory"]
        file_name = os.path.join(zframe_dir, "ZframeToRobotTransMatrix.mat")
        scipy.io.savemat(file_name, {"Trans_r": Trans_r})

    def showZFrameToRobot(self):
        Trans_r = self.trans_r
        rows = 4
        cols = 4
        matrix_html = '<table border="1">'
        for i in range(rows):
            matrix_html += "<tr>"
            for j in range(cols):
                matrix_html += "<td>{}</td>".format(round(Trans_r[i][j], 2))
            matrix_html += "</tr>"
        matrix_html += "</table>"
        self.show_trans_matrix_2.clear()
        self.show_trans_matrix_2.insertPlainText("ZFrame To Robot.\n")
        self.show_trans_matrix_2.insertHtml(matrix_html)

        imri_setting.IMRIGlobal.ZframeToRobotTransMatrix = self.trans_r

    def saveZframeMat(self):
        directory_path = self.config["zframe"]["mat_directory"]
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Mat File", directory_path, "Mat(*.mat)")
        if file_path != "":
            self.config["zframe"]["mat_directory"] = os.path.dirname(file_path)
            imri_setting.update_config(config=self.config)
            scipy.io.savemat(file_path, {"Trans_z": self.trans_z, "error": self.error})

    def saveRobotMat(self):
        directory_path = self.config["zframe"]["mat_directory"]
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Mat File", directory_path, "Mat(*.mat)")
        if file_path != "":
            self.config["zframe"]["mat_directory"] = os.path.dirname(file_path)
            imri_setting.update_config(config=self.config)
            scipy.io.savemat(file_path, {"Trans_r": self.trans_r})

    def loadImageToZFrame(self):
        directory_path = self.config["zframe"]["mat_directory"]
        file_path, _ = QFileDialog.getOpenFileName(None, "Open Trans-Matrix File", directory_path, "Mat(*.mat)")
        if file_path != "":
            directory_path = os.path.dirname(file_path)
            print("directory_path", directory_path)
            self.config["zframe"]["mat_directory"] = directory_path
            imri_setting.update_config(config=self.config)
            data = scipy.io.loadmat(file_path)
            try:
                self.trans_z = data["Trans_z"]
                self.showImageToZFrame()
            except:
                print("Trans-Mat Error! Maybe it is not a ImageToZframeTransMatrix.mat file")
                meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Trans-Mat Error!")
                meg_box.exec_()

    def loadZFrameToRobot(self):
        directory_path = self.config["zframe"]["mat_directory"]
        file_path, _ = QFileDialog.getOpenFileName(None, "Open Trans-Matrix File", directory_path, "Mat(*.mat)")
        if file_path != "":
            directory_path = os.path.dirname(file_path)
            self.config["zframe"]["mat_directory"] = directory_path
            imri_setting.update_config(config=self.config)
            data = scipy.io.loadmat(file_path)
            try:
                self.trans_r = data["Trans_r"]
                self.set_zframe_to_robot_spinBox_x.setValue(self.trans_r[0][3])
                self.set_zframe_to_robot_spinBox_y.setValue(self.trans_r[1][3])
                self.set_zframe_to_robot_spinBox_z.setValue(self.trans_r[2][3])
                self.showZFrameToRobot()
            except:
                print("Trans-Mat Error! Maybe it is not a ZframeToRobotTransMatrix.mat file")
                meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Trans-Mat Error!")
                meg_box.exec_()
