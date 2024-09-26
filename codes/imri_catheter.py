import os.path

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import imri_setting
import numpy as np
import skimage
import math
import socket
import datetime


class Catheter(QMainWindow):
    def __init__(self, parent=None):
        super(Catheter, self).__init__(parent)
        self.config = imri_setting.read_config()
        self.start_pos1 = [0, 0]  # in scene coordinate
        self.end_pos1 = [0, 0]  # in scene coordinate
        self.start_pos_vtk1 = [0, 0, 0]  # [l,p,s]
        self.end_pos_vtk1 = [0, 0, 0]  # [l,p,s]
        self.start_pos_voxel1 = [0, 0, 0]  # [l,p,s]
        self.end_pos_voxel1 = [0, 0, 0]  # [l,p,s]
        self.area_item1 = None  # QGraphicsRectItem
        self.start_pos2 = [0, 0]
        self.end_pos2 = [0, 0]
        self.start_pos_vtk2 = [0, 0, 0]
        self.end_pos_vtk2 = [0, 0, 0]
        self.start_pos_voxel2 = [0, 0, 0]
        self.end_pos_voxel2 = [0, 0, 0]
        self.area_item2 = None
        color = self.config["catheter"]["box_color_2d"]
        width = self.config["catheter"]["box_width_2d"]
        self.area_pen = QPen(QColor(color[0], color[1], color[2]))
        self.area_pen.setWidth(width)
        self.area_index = 0  # 1:area1 2:area2
        self.left2right = False

        self.plane = 0  # 0:sag 1:cor 2:axi
        self.mode = None
        self.Image3d = None
        self.ImagePlanes = None
        self.ImageData = None
        self.catheter_count = 0
        # current catheter
        self.catheter_line_start = []
        self.catheter_line_end = []
        self.catheter_line_actor = None
        self.line_plane_items = [None, None, None]
        self.point_plane_items = [None, None, None]
        self.nearest_point = []
        self.nearest_point_actor = None
        self.nearest_point_plane_items = [None, None, None]
        self.nearest_dis = 0
        # last catheter
        self.last_catheter_line_start = []
        self.last_catheter_line_end = []
        self.last_catheter_line_actor = None
        self.last_line_plane_items = [None, None, None]
        self.last_point_plane_items = [None, None, None]
        self.last_nearest_point = []
        self.last_nearest_point_actor = None
        self.last_nearest_point_plane_items = [None, None, None]
        self.last_nearest_dis = 0

    def init(self, ui, Image3d, ImagePlanes):
        self.CatheterModeComboBox = ui.CatheterModeComboBox
        self.CatheterModeComboBox.addItem("Single Catheter")
        self.CatheterModeComboBox.addItem("Double Catheter")
        self.CatheterModeComboBox.currentIndexChanged.connect(self.changeCatheterMode)

        self.ChooseArea1Btn = ui.ChooseArea1Btn
        self.ChooseArea2Btn = ui.ChooseArea2Btn
        self.process_bar = ui.CatheterIdentifyProgressBar
        self.process_bar.setRange(0, 100)
        self.process_bar.setValue(0)
        self.status_bar = ui.statusBar

        self.CatheterStartSliceSpinBox1 = ui.CatheterStartSlice1
        self.CatheterEndSliceSpinBox1 = ui.CatheterEndSlice1
        self.CatheterStartSliceSpinBox2 = ui.CatheterStartSlice2
        self.CatheterEndSliceSpinBox2 = ui.CatheterEndSlice2
        self.CatheterIdentifyBtn = ui.CatheterIdentifyBtn
        self.CurrentCatheterCheckBox = ui.CurrentCatheterCheckBox
        self.CatheterLineCheckBox = ui.CatheterLineCheckBox
        self.NearestPointCheckBox = ui.NearestPointCheckBox
        self.LastCatheterCheckBox = ui.LastCatheterCheckBox
        self.LastLineCheckBox = ui.LastLineCheckBox
        self.LastNearestPointCheckBox = ui.LastNearestPointCheckBox
        self.BoxAreaCheckBox = ui.BoxAreaCheckBox
        self.FinetuneArea1CheckBox = ui.FinetuneArea1CheckBox
        self.FinetuneArea2CheckBox = ui.FinetuneArea2CheckBox
        self.CurrentCatheterCheckBox.setChecked(True)
        self.CatheterLineCheckBox.setChecked(True)
        self.NearestPointCheckBox.setChecked(True)
        self.LastCatheterCheckBox.setChecked(True)
        self.LastLineCheckBox.setChecked(True)
        self.LastNearestPointCheckBox.setChecked(True)
        self.BoxAreaCheckBox.setChecked(True)
        self.CurrentCatheterCheckBox.stateChanged.connect(lambda: self.onCatheterCheckBoxChanged(1))
        self.CatheterLineCheckBox.stateChanged.connect(lambda: self.onCatheterCheckBoxChanged(2))
        self.NearestPointCheckBox.stateChanged.connect(lambda: self.onCatheterCheckBoxChanged(3))
        self.LastCatheterCheckBox.stateChanged.connect(lambda: self.onCatheterCheckBoxChanged(4))
        self.LastLineCheckBox.stateChanged.connect(lambda: self.onCatheterCheckBoxChanged(5))
        self.LastNearestPointCheckBox.stateChanged.connect(lambda: self.onCatheterCheckBoxChanged(6))
        self.BoxAreaCheckBox.stateChanged.connect(self.onBoxAreaChanged)
        self.FinetuneArea1CheckBox.stateChanged.connect(lambda: self.onFinetuneAreaChanged(1))
        self.FinetuneArea2CheckBox.stateChanged.connect(lambda: self.onFinetuneAreaChanged(2))
        self.FinetuneArea1CheckBox.setDisabled(True)
        self.FinetuneArea2CheckBox.setDisabled(True)

        self.AreaLeftSpinBox = ui.AreaLeftSpinBox
        self.AreaRightSpinBox = ui.AreaRightSpinBox
        self.AreaTopSpinBox = ui.AreaTopSpinBox
        self.AreaBottomSpinBox = ui.AreaBottomSpinBox
        imri_setting.setSpinBox(self.AreaLeftSpinBox, -256, 256, 0, 1)
        imri_setting.setSpinBox(self.AreaRightSpinBox, -256, 256, 0, 1)
        imri_setting.setSpinBox(self.AreaTopSpinBox, -256, 256, 0, 1)
        imri_setting.setSpinBox(self.AreaBottomSpinBox, -256, 256, 0, 1)
        imri_setting.setSpinBox(self.CatheterStartSliceSpinBox1, 0, 1000, 0, 1)
        imri_setting.setSpinBox(self.CatheterEndSliceSpinBox1, 0, 1000, 0, 1)
        imri_setting.setSpinBox(self.CatheterStartSliceSpinBox2, 0, 1000, 0, 1)
        imri_setting.setSpinBox(self.CatheterEndSliceSpinBox2, 0, 1000, 0, 1)
        self.spinBoxEnable(False)

        self.ChooseArea1Btn.clicked.connect(lambda: self.chooseBtn(1))
        self.ChooseArea2Btn.clicked.connect(lambda: self.chooseBtn(2))
        self.AreaLeftSpinBox.valueChanged.connect(self.updateArea)
        self.AreaRightSpinBox.valueChanged.connect(self.updateArea)
        self.AreaTopSpinBox.valueChanged.connect(self.updateArea)
        self.AreaBottomSpinBox.valueChanged.connect(self.updateArea)

        self.navi_send_to_robot_btn = ui.NaviSendToRobotBtn
        self.navi_send_to_robot_btn.clicked.connect(self.sendToRobot)
        self.Image3d = Image3d
        self.ImagePlanes = ImagePlanes

        self.angle_error_line = ui.AngleErrorLineEdit
        self.radial_error_line = ui.RadialErrorLineEdit
        self.angle_error_line.setReadOnly(True)
        self.radial_error_line.setReadOnly(True)

        self.catheter_text = ui.CatheterTextBrowser
        self.catheter_text.setPlainText("Catheter Identification Info:\n\n")
        self.AutoSendCheckBox = ui.AutoSendCheckBox

        self.left2rightCheckBox = ui.left2rightCheckBox
        self.left2rightCheckBox.stateChanged.connect(self.onLeft2RightChanged)

        self.CatheterModeComboBox.setCurrentIndex(1)
        self.CatheterModeComboBox.setCurrentIndex(0)

        current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.catheter_file_path = f"output/Catheter/Catheter_{current_time}.txt"
        if not os.path.exists(self.catheter_file_path):
            file = open(self.catheter_file_path, "w")
            file.close()
    def changeCatheterMode(self, index):
        if index == 0:
            self.CatheterStartSliceSpinBox2.setDisabled(True)
            self.CatheterEndSliceSpinBox2.setDisabled(True)
            self.ChooseArea2Btn.setDisabled(True)
            self.ChooseArea2Btn.setStyleSheet(self.config["button"]["disabled"])
            self.FinetuneArea2CheckBox.setDisabled(True)
            if self.area_item2 != None:
                self.area_item2.setVisible(False)
            self.CatheterIdentifyBtn.disconnect()
            self.CatheterIdentifyBtn.clicked.connect(self.getCatheterLine_Single)
        elif index == 1:
            self.CatheterStartSliceSpinBox2.setEnabled(True)
            self.CatheterEndSliceSpinBox2.setEnabled(True)
            self.ChooseArea2Btn.setEnabled(True)
            self.ChooseArea2Btn.setStyleSheet(self.config["button"]["normal"])
            self.FinetuneArea2CheckBox.setEnabled(True)
            self.CatheterIdentifyBtn.disconnect()
            self.CatheterIdentifyBtn.clicked.connect(self.getCatheterLine_Double)
        else:
            pass

    def onLeft2RightChanged(self):
        if self.left2rightCheckBox.isChecked():
            self.left2right = True
        else:
            self.left2right = False

    def spinBoxSignalBlock(self, block=True):
        self.AreaLeftSpinBox.blockSignals(block)
        self.AreaRightSpinBox.blockSignals(block)
        self.AreaTopSpinBox.blockSignals(block)
        self.AreaBottomSpinBox.blockSignals(block)

    def chooseBtn(self, index):
        if index == 1:
            self.area_index = 1
            self.mode = "ChooseArea1_Start"
            self.ChooseArea1Btn.setStyleSheet(self.config["button"]["active"])
            self.BoxAreaCheckBox.setDisabled(True)
            self.FinetuneArea1CheckBox.setDisabled(True)
            self.ChooseArea2Btn.setDisabled(True)
            self.ChooseArea2Btn.setStyleSheet(self.config["button"]["disabled"])
            if self.area_item1 != None:
                self.area_item1.setVisible(False)
        elif index == 2:
            self.area_index = 2
            self.mode = "ChooseArea2_Start"
            self.ChooseArea2Btn.setStyleSheet(self.config["button"]["active"])
            self.BoxAreaCheckBox.setDisabled(True)
            self.FinetuneArea2CheckBox.setDisabled(True)
            self.ChooseArea1Btn.setDisabled(True)
            self.ChooseArea1Btn.setStyleSheet(self.config["button"]["disabled"])
            if self.area_item2 != None:
                self.area_item2.setVisible(False)
        else:
            print("Choose Area Button Error!")

    def chooseArea(self):
        """
        choose area by mouse
        """
        if self.area_index == 1:
            self.area_item1.setRect(self.start_pos1[0], self.start_pos1[1], self.end_pos1[0] - self.start_pos1[0], self.end_pos1[1] - self.start_pos1[1])
            self.start_pos_voxel1, self.start_pos_vtk1 = self.ImageData.ImageToWorld(self.start_pos1, self.ImagePlanes.getPixmapsSize(), self.plane)  # [l,p,s]
            self.end_pos_voxel1, self.end_pos_vtk1 = self.ImageData.ImageToWorld(self.end_pos1, self.ImagePlanes.getPixmapsSize(), self.plane)  # [l,p,s]
            start_pos_vtk = np.delete(self.start_pos_vtk1, self.plane)
            end_pos_vtk = np.delete(self.end_pos_vtk1, self.plane)
            self.AreaLeftSpinBox.setValue(start_pos_vtk[0])
            self.AreaRightSpinBox.setValue(end_pos_vtk[0])
            self.AreaTopSpinBox.setValue(start_pos_vtk[1])
            self.AreaBottomSpinBox.setValue(end_pos_vtk[1])
            self.FinetuneArea1CheckBox.setEnabled(True)
            if self.BoxAreaCheckBox.isChecked():
                self.area_item1.setVisible(True)

        elif self.area_index == 2:
            self.area_item2.setRect(self.start_pos2[0], self.start_pos2[1], self.end_pos2[0] - self.start_pos2[0], self.end_pos2[1] - self.start_pos2[1])
            self.start_pos_voxel2, self.start_pos_vtk2 = self.ImageData.ImageToWorld(self.start_pos2, self.ImagePlanes.getPixmapsSize(), self.plane)
            self.end_pos_voxel2, self.end_pos_vtk2 = self.ImageData.ImageToWorld(self.end_pos2, self.ImagePlanes.getPixmapsSize(), self.plane)
            start_pos_vtk = np.delete(self.start_pos_vtk2, self.plane)
            end_pos_vtk = np.delete(self.end_pos_vtk2, self.plane)
            self.AreaLeftSpinBox.setValue(start_pos_vtk[0])
            self.AreaRightSpinBox.setValue(end_pos_vtk[0])
            self.AreaTopSpinBox.setValue(start_pos_vtk[1])
            self.AreaBottomSpinBox.setValue(end_pos_vtk[1])
            self.FinetuneArea2CheckBox.setEnabled(True)
            if self.BoxAreaCheckBox.isChecked():
                self.area_item2.setVisible(True)

        else:
            print("Choose Area Error!")

    def updateArea(self):
        """
        update area item when spinBox value changed
        ui spinBox show the area position in VTK coordinate
        """
        if self.area_index == 1:
            start_pos_vtk = [self.AreaLeftSpinBox.value(), self.AreaTopSpinBox.value()]
            end_pos_vtk = [self.AreaRightSpinBox.value(), self.AreaBottomSpinBox.value()]
            start_pos_vtk.insert(self.plane, self.start_pos_vtk1[self.plane])
            end_pos_vtk.insert(self.plane, self.end_pos_vtk1[self.plane])
            self.start_pos_vtk1 = start_pos_vtk
            self.end_pos_vtk1 = end_pos_vtk
            self.start_pos1, _ = self.ImageData.WorldToImage(self.start_pos_vtk1, self.ImagePlanes.getPixmapsSize(), self.plane)
            self.end_pos1, _ = self.ImageData.WorldToImage(self.end_pos_vtk1, self.ImagePlanes.getPixmapsSize(), self.plane)
            self.start_pos_voxel1 = self.ImageData.WorldToVoxel(self.start_pos_vtk1)
            self.end_pos_voxel1 = self.ImageData.WorldToVoxel(self.end_pos_vtk1)
            self.area_item1.setRect(self.start_pos1[0], self.start_pos1[1], self.end_pos1[0] - self.start_pos1[0], self.end_pos1[1] - self.start_pos1[1])
            if self.BoxAreaCheckBox.isChecked():
                self.area_item1.setVisible(True)
        elif self.area_index == 2:
            start_pos_vtk = [self.AreaLeftSpinBox.value(), self.AreaTopSpinBox.value()]
            end_pos_vtk = [self.AreaRightSpinBox.value(), self.AreaBottomSpinBox.value()]
            start_pos_vtk.insert(self.plane, self.start_pos_vtk2[self.plane])
            end_pos_vtk.insert(self.plane, self.end_pos_vtk2[self.plane])
            self.start_pos_vtk2 = start_pos_vtk
            self.end_pos_vtk2 = end_pos_vtk
            self.start_pos2, _ = self.ImageData.WorldToImage(self.start_pos_vtk2, self.ImagePlanes.getPixmapsSize(), self.plane)
            self.end_pos2, _ = self.ImageData.WorldToImage(self.end_pos_vtk2, self.ImagePlanes.getPixmapsSize(), self.plane)
            self.start_pos_voxel2 = self.ImageData.WorldToVoxel(self.start_pos_vtk2)
            self.end_pos_voxel2 = self.ImageData.WorldToVoxel(self.end_pos_vtk2)
            self.area_item2.setRect(self.start_pos2[0], self.start_pos2[1], self.end_pos2[0] - self.start_pos2[0], self.end_pos2[1] - self.start_pos2[1])
            if self.BoxAreaCheckBox.isChecked():
                self.area_item2.setVisible(True)

    def resizeArea(self):
        """
        resize area item when scene size changed
        """
        if self.area_item1 != None:
            self.start_pos1, _ = self.ImageData.WorldToImage(self.start_pos_vtk1, self.ImagePlanes.getPixmapsSize(), self.plane)
            self.end_pos1, _ = self.ImageData.WorldToImage(self.end_pos_vtk1, self.ImagePlanes.getPixmapsSize(), self.plane)
            if self.BoxAreaCheckBox.isChecked():
                self.area_item1.setRect(self.start_pos1[0], self.start_pos1[1], self.end_pos1[0] - self.start_pos1[0], self.end_pos1[1] - self.start_pos1[1])

        if self.area_item2 != None:
            self.start_pos2, _ = self.ImageData.WorldToImage(self.start_pos_vtk2, self.ImagePlanes.getPixmapsSize(), self.plane)
            self.end_pos2, _ = self.ImageData.WorldToImage(self.end_pos_vtk2, self.ImagePlanes.getPixmapsSize(), self.plane)
            if self.BoxAreaCheckBox.isChecked():
                self.area_item2.setRect(self.start_pos2[0], self.start_pos2[1], self.end_pos2[0] - self.start_pos2[0], self.end_pos2[1] - self.start_pos2[1])

    def onBoxAreaChanged(self):
        if self.area_item1 != None:
            if self.BoxAreaCheckBox.isChecked():
                self.area_item1.setVisible(True)
            else:
                self.area_item1.setVisible(False)

        if self.area_item2 != None:
            if self.BoxAreaCheckBox.isChecked():
                self.area_item2.setVisible(True)
            else:
                self.area_item2.setVisible(False)

    def onFinetuneAreaChanged(self, index):
        if index == 1:
            self.area_index = 1
            if self.FinetuneArea1CheckBox.isChecked():

                start_pos_vtk = np.delete(self.start_pos_vtk1, self.plane)
                end_pos_vtk = np.delete(self.end_pos_vtk1, self.plane)
                self.AreaLeftSpinBox.setValue(start_pos_vtk[0])
                self.AreaRightSpinBox.setValue(end_pos_vtk[0])
                self.AreaTopSpinBox.setValue(start_pos_vtk[1])
                self.AreaBottomSpinBox.setValue(end_pos_vtk[1])

                self.BoxAreaCheckBox.setCheckState(Qt.Checked)
                self.FinetuneArea2CheckBox.setDisabled(True)
                self.spinBoxEnable(True)
                self.ChooseArea1Btn.setDisabled(True)
                self.ChooseArea1Btn.setStyleSheet(self.config["button"]["disabled"])
                self.ChooseArea2Btn.setDisabled(True)
                self.ChooseArea2Btn.setStyleSheet(self.config["button"]["disabled"])
            else:
                self.FinetuneArea2CheckBox.setEnabled(True)
                self.spinBoxEnable(False)
                self.ChooseArea1Btn.setEnabled(True)
                self.ChooseArea1Btn.setStyleSheet(self.config["button"]["normal"])
                self.ChooseArea2Btn.setEnabled(True)
                self.ChooseArea2Btn.setStyleSheet(self.config["button"]["normal"])
        elif index == 2:
            self.area_index = 2
            if self.FinetuneArea2CheckBox.isChecked():

                start_pos_vtk = np.delete(self.start_pos_vtk2, self.plane)
                end_pos_vtk = np.delete(self.end_pos_vtk2, self.plane)
                self.AreaLeftSpinBox.setValue(start_pos_vtk[0])
                self.AreaRightSpinBox.setValue(end_pos_vtk[0])
                self.AreaTopSpinBox.setValue(start_pos_vtk[1])
                self.AreaBottomSpinBox.setValue(end_pos_vtk[1])

                self.BoxAreaCheckBox.setCheckState(Qt.Checked)
                self.FinetuneArea1CheckBox.setDisabled(True)
                self.spinBoxEnable(True)
                self.ChooseArea1Btn.setDisabled(True)
                self.ChooseArea1Btn.setStyleSheet(self.config["button"]["disabled"])
                self.ChooseArea2Btn.setDisabled(True)
                self.ChooseArea2Btn.setStyleSheet(self.config["button"]["disabled"])
            else:
                self.FinetuneArea1CheckBox.setEnabled(True)
                self.spinBoxEnable(False)
                self.ChooseArea1Btn.setEnabled(True)
                self.ChooseArea1Btn.setStyleSheet(self.config["button"]["normal"])
                self.ChooseArea2Btn.setEnabled(True)
                self.ChooseArea2Btn.setStyleSheet(self.config["button"]["normal"])
        else:
            print("Finetune Area CheckBox Error!")

    def spinBoxEnable(self, enable=True):
        self.AreaLeftSpinBox.setEnabled(enable)
        self.AreaRightSpinBox.setEnabled(enable)
        self.AreaTopSpinBox.setEnabled(enable)
        self.AreaBottomSpinBox.setEnabled(enable)

    def onCatheterCheckBoxChanged(self, index):
        """
        :param index:
        1:CurrentCatheterCheckBox 2:CatheterLineCheckBox 3:NearestPointCheckBox
        4:LastCatheterCheckBox 5:LastLineCheckBox 6:LastNearestPointCheckBox
        """
        if index == 1:
            if self.CurrentCatheterCheckBox.isChecked():
                self.CatheterLineCheckBox.setEnabled(True)
                self.NearestPointCheckBox.setEnabled(True)
                self.CatheterLineCheckBox.setChecked(True)
                self.NearestPointCheckBox.setChecked(True)
            else:
                self.CatheterLineCheckBox.setEnabled(False)
                self.NearestPointCheckBox.setEnabled(False)
                self.CatheterLineCheckBox.setChecked(False)
                self.NearestPointCheckBox.setChecked(False)
        elif index == 2:
            if self.CatheterLineCheckBox.isChecked():
                self.updateCatheterLine2d(current=True, last=False)
                self.updateCatheterLine3d(current=True, last=False)
            else:
                self.removeCatheterLine2d(current=True, last=False)
                self.removeCatheterLine3d(current=True, last=False)
        elif index == 3:
            if self.NearestPointCheckBox.isChecked():
                self.updateNearestPoint2d(current=True, last=False)
                self.updateNearestPoint3d(current=True, last=False)
            else:
                self.removeNearestPoint2d(current=True, last=False)
                self.removeNearestPoint3d(current=True, last=False)

        elif index == 4:
            if self.LastCatheterCheckBox.isChecked():
                self.LastLineCheckBox.setEnabled(True)
                self.LastNearestPointCheckBox.setEnabled(True)
                self.LastLineCheckBox.setChecked(True)
                self.LastNearestPointCheckBox.setChecked(True)
            else:
                self.LastLineCheckBox.setEnabled(False)
                self.LastNearestPointCheckBox.setEnabled(False)
                self.LastLineCheckBox.setChecked(False)
                self.LastNearestPointCheckBox.setChecked(False)

        elif index == 5:
            if self.LastLineCheckBox.isChecked():
                self.updateCatheterLine2d(current=False, last=True)
                self.updateCatheterLine3d(current=False, last=True)
            else:
                self.removeCatheterLine2d(current=False, last=True)
                self.removeCatheterLine3d(current=False, last=True)
        elif index == 6:
            if self.LastNearestPointCheckBox.isChecked():
                self.updateNearestPoint2d(current=False, last=True)
                self.updateNearestPoint3d(current=False, last=True)
            else:
                self.removeNearestPoint2d(current=False, last=True)
                self.removeNearestPoint3d(current=False, last=True)
        else:
            print("Catheter CheckBox Error!")

    def getCatheterLine_Single(self):
        # try:
        self.progress_dialog = QProgressDialog("Processing...", "Cancel", 0, 5, self)
        self.progress_dialog.setWindowModality(Qt.ApplicationModal)
        self.progress_dialog.setWindowTitle("Catheter Identification")
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setCancelButton(None)  # 禁用取消按钮
        self.progress_dialog.setMinimumSize(800, 200)
        self.progress_dialog.setModal(False)
        self.progress_dialog.setValue(50)
        self.progress_dialog.setMinimumDuration(0.1)
        self.progress_dialog.show()
        QApplication.processEvents()

        self.last_catheter_line_start = self.catheter_line_start
        self.last_catheter_line_end = self.catheter_line_end
        self.last_nearest_point = self.nearest_point

        self.process_bar.reset()
        self.process_bar.setValue(0)
        self.status_bar.showMessage("Loading image data...")

        nii_image = self.ImageData.Vtk2Numpy(self.ImageData.data)
        nii_image = np.transpose(nii_image, (1, 2, 0))
        nii_image = (nii_image - np.min(nii_image)) / (np.max(nii_image) - np.min(nii_image)) * 255
        max_slice = nii_image.shape[2] - 1
        min_slice = 0

        start_slice1 = self.CatheterStartSliceSpinBox1.value()
        stop_slice1 = self.CatheterEndSliceSpinBox1.value()

        if start_slice1 >= stop_slice1:
            print("start slice should be smaller than stop slice")
            return None

        start_row1 = round(self.start_pos_voxel1[1])
        stop_row1 = round(self.end_pos_voxel1[1])
        start_col1 = round(self.start_pos_voxel1[0])
        stop_col1 = round(self.end_pos_voxel1[0])

        self.process_bar.setValue(10)

        def fill_hole(input_bw, fsize, left2right):  ## modified

            output_bw = np.copy(input_bw)
            row = input_bw.shape[0]
            col = input_bw.shape[1]

            aa = round(fsize / 2) + 1
            if left2right == False:
                for ii in range(0, row):
                    for jj in range(aa, col - aa):
                        output_bw[ii, jj] = np.max(input_bw[ii, (jj - aa) : (jj + aa)])
            else:
                for jj in range(0, col):
                    for ii in range(aa, row - aa):
                        output_bw[ii, jj] = np.max(input_bw[(ii - aa) : (ii + aa), jj])

            return output_bw

        # threshold segmentation
        self.process_bar.setValue(20)
        self.status_bar.showMessage("Threshold segmentation...")

        img_bw = np.zeros_like(nii_image)
        cv_image = nii_image[:, :, int((start_slice1 + stop_slice1) / 2)]
        thre = skimage.filters.threshold_otsu(cv_image[0:128, :])

        for zz in range(start_slice1, stop_slice1):  # new
            cv_image = nii_image[:, :, zz]
            bw = cv_image > thre
            bw = skimage.filters.median(bw, skimage.morphology.disk(2))
            bw = fill_hole(bw, 3, self.left2right)
            img_bw[:, :, zz] = bw

        # find the center of the lead
        self.process_bar.setValue(40)
        self.status_bar.showMessage("Find the center of the lead...")

        if self.left2right == False:
            # fit line1
            coor_center1 = np.zeros((stop_row1 - start_row1, 3))
            tt = -1
            for ii in range(start_row1, stop_row1):

                tt = tt + 1
                bw = img_bw[ii, start_col1:stop_col1, start_slice1:stop_slice1]
                label = skimage.measure.label(bw)
                region = skimage.measure.regionprops(label)[0]

                coor = np.array([region.centroid[0] + start_col1, ii, region.centroid[1] + start_slice1])
                coor_center1[tt, :] = coor

            p_yx1 = np.polyfit(coor_center1[:, 1], coor_center1[:, 0], 1)
            p_yz1 = np.polyfit(coor_center1[:, 1], coor_center1[:, 2], 1)
            line_yy1 = np.linspace(0, nii_image.shape[1] - 1, nii_image.shape[1])
            line_xx1 = np.polyval(p_yx1, line_yy1)
            line_zz1 = np.polyval(p_yz1, line_yy1)

            line_yy = line_yy1
            line_xx = line_xx1
            line_zz = line_zz1

            # fit line
            self.process_bar.setValue(60)
            self.status_bar.showMessage("Fit line...")

            self.p_yx = np.polyfit(line_yy, line_xx, 1)
            self.p_yz = np.polyfit(line_yy, line_zz, 1)

            self.process_bar.setValue(70)
            line_end = np.reshape(np.array([line_xx[0], line_yy[0], line_zz[0], 1]), (4, 1))
            line_start = np.reshape(np.array([line_xx[-1], line_yy[-1], line_zz[-1], 1]), (4, 1))
            Trans_nii = self.ImageData.getTransMatrix()
            self.catheter_line_start = np.squeeze(np.matmul(Trans_nii, line_start)[:3]).tolist()
            self.catheter_line_end = np.squeeze(np.matmul(Trans_nii, line_end)[:3]).tolist()

        else:
            # fit line1
            coor_center1 = np.zeros((stop_col1 - start_col1, 3))
            tt = -1
            for ii in range(start_col1, stop_col1):

                tt = tt + 1
                bw = img_bw[start_row1:stop_row1, ii, start_slice1:stop_slice1]
                label = skimage.measure.label(bw)
                region = skimage.measure.regionprops(label)[0]

                coor = np.array([ii, region.centroid[0] + start_row1, region.centroid[1] + start_slice1])
                coor_center1[tt, :] = coor

            p_xy1 = np.polyfit(coor_center1[:, 0], coor_center1[:, 1], 1)
            p_xz1 = np.polyfit(coor_center1[:, 0], coor_center1[:, 2], 1)
            line_xx1 = np.linspace(0, nii_image.shape[0] - 1, nii_image.shape[0])
            line_yy1 = np.polyval(p_xy1, line_xx1)
            line_zz1 = np.polyval(p_xz1, line_xx1)

            line_yy = line_yy1
            line_xx = line_xx1
            line_zz = line_zz1

            # fit line
            self.process_bar.setValue(60)
            self.status_bar.showMessage("Fit line...")

            self.p_xy = np.polyfit(line_xx, line_yy, 1)
            self.p_xz = np.polyfit(line_xx, line_zz, 1)

            self.process_bar.setValue(70)
            line_end = np.reshape(np.array([line_xx[0], line_yy[0], line_zz[0], 1]), (4, 1))
            line_start = np.reshape(np.array([line_xx[-1], line_yy[-1], line_zz[-1], 1]), (4, 1))
            Trans_nii = self.ImageData.getTransMatrix()
            self.catheter_line_start = np.squeeze(np.matmul(Trans_nii, line_start)[:3]).tolist()
            self.catheter_line_end = np.squeeze(np.matmul(Trans_nii, line_end)[:3]).tolist()

        # update line
        self.process_bar.setValue(90)
        self.status_bar.showMessage("Update line")
        self.catheter_count += 1

        if self.catheter_count == 1:
            self.updateAllLineAndPoint(current=True, last=False)

        if self.catheter_count > 1:
            self.updateAllLineAndPoint(current=True, last=True)

        self.process_bar.setValue(100)

        if self.nearest_point != []:
            imri_setting.IMRIGlobal.catheter_nearest = np.reshape(self.nearest_point, (3, 1))
        else:
            print("Please set and select a path!")

        self.setErrorValue()

        if self.AutoSendCheckBox.isChecked():
            self.sendToRobot()

        self.progress_dialog.setValue(5)
        self.progress_dialog.close()

        # except Exception as e:
        #     print("An error occurred:", e)
        #     print("Catheter area include non-catheter part!")
        #     meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Catheter area include non-catheter part!")
        #     meg_box.exec_()

    def getCatheterLine_Double(self):
        # try:
        self.progress_dialog = QProgressDialog("Processing...", "Cancel", 0, 5, self)
        self.progress_dialog.setWindowModality(Qt.ApplicationModal)
        self.progress_dialog.setWindowTitle("Catheter Identification")
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setCancelButton(None)  # 禁用取消按钮
        self.progress_dialog.setMinimumSize(800, 200)
        self.progress_dialog.setModal(False)
        self.progress_dialog.setValue(50)
        self.progress_dialog.setMinimumDuration(0.1)
        self.progress_dialog.show()
        QApplication.processEvents()

        self.last_catheter_line_start = self.catheter_line_start
        self.last_catheter_line_end = self.catheter_line_end
        self.last_nearest_point = self.nearest_point

        self.process_bar.reset()
        self.process_bar.setValue(0)
        self.status_bar.showMessage("Loading image data...")

        nii_image = self.ImageData.Vtk2Numpy(self.ImageData.data)
        nii_image = np.transpose(nii_image, (1, 2, 0))
        max_slice = nii_image.shape[2] - 1
        min_slice = 0
        # self.CatheterStartSliceSpinBox.setRange(min_slice, max_slice)
        # self.CatheterEndSliceSpinBox.setRange(min_slice, max_slice)
        start_slice1 = self.CatheterStartSliceSpinBox1.value()
        stop_slice1 = self.CatheterEndSliceSpinBox1.value()
        start_slice2 = self.CatheterStartSliceSpinBox2.value()
        stop_slice2 = self.CatheterEndSliceSpinBox2.value()
        # print(start_slice1, stop_slice1, start_slice2, stop_slice2)
        if start_slice1 >= stop_slice1 or start_slice2 >= stop_slice2:
            print("start slice should be smaller than stop slice")
            return None

        start_row1 = round(self.start_pos_voxel1[1])
        stop_row1 = round(self.end_pos_voxel1[1])
        start_col1 = round(self.start_pos_voxel1[0])
        stop_col1 = round(self.end_pos_voxel1[0])

        start_row2 = round(self.start_pos_voxel2[1])
        stop_row2 = round(self.end_pos_voxel2[1])
        start_col2 = round(self.start_pos_voxel2[0])
        stop_col2 = round(self.end_pos_voxel2[0])

        self.process_bar.setValue(10)

        def fill_hole(input_bw, fsize, left2right):  ## modified

            output_bw = np.copy(input_bw)
            row = input_bw.shape[0]
            col = input_bw.shape[1]

            aa = round(fsize / 2) + 1
            if left2right == False:
                for ii in range(0, row):
                    for jj in range(aa, col - aa):
                        output_bw[ii, jj] = np.max(input_bw[ii, (jj - aa) : (jj + aa)])
            else:
                for jj in range(0, col):
                    for ii in range(aa, row - aa):
                        output_bw[ii, jj] = np.max(input_bw[(ii - aa) : (ii + aa), jj])

            return output_bw

        # threshold segmentation
        self.process_bar.setValue(20)
        self.status_bar.showMessage("Threshold segmentation...")

        img_bw = np.zeros_like(nii_image)
        cv_image = nii_image[:, :, int((min_slice + max_slice) / 2)]
        thre = skimage.filters.threshold_otsu(cv_image[0:128, :])

        for zz in range(min_slice, max_slice):  # new
            cv_image = nii_image[:, :, zz]
            bw = cv_image > thre
            bw = skimage.filters.median(bw, skimage.morphology.disk(2))
            bw = fill_hole(bw, 3, self.left2right)
            img_bw[:, :, zz] = bw

        # find the center of the lead
        self.process_bar.setValue(40)
        self.status_bar.showMessage("Find the center of the lead...")

        if self.left2right == False:
            # fit line1
            coor_center1 = np.zeros((stop_row1 - start_row1, 3))
            tt = -1
            for ii in range(start_row1, stop_row1):

                tt = tt + 1
                bw = img_bw[ii, start_col1:stop_col1, start_slice1:stop_slice1]
                label = skimage.measure.label(bw)
                region = skimage.measure.regionprops(label)[0]

                coor = np.array([region.centroid[0] + start_col1, ii, region.centroid[1] + start_slice1])
                coor_center1[tt, :] = coor

            p_yx1 = np.polyfit(coor_center1[:, 1], coor_center1[:, 0], 1)
            p_yz1 = np.polyfit(coor_center1[:, 1], coor_center1[:, 2], 1)
            line_yy1 = np.linspace(0, nii_image.shape[1] - 1, nii_image.shape[1])
            line_xx1 = np.polyval(p_yx1, line_yy1)
            line_zz1 = np.polyval(p_yz1, line_yy1)

            # fit line2
            coor_center2 = np.zeros((stop_row2 - start_row2, 3))
            tt = -1
            for ii in range(start_row2, stop_row2):

                tt = tt + 1
                bw = img_bw[ii, start_col2:stop_col2, start_slice2:stop_slice2]
                label = skimage.measure.label(bw)
                region = skimage.measure.regionprops(label)[0]

                coor = np.array([region.centroid[0] + start_col2, ii, region.centroid[1] + start_slice2])
                coor_center2[tt, :] = coor

            p_yx2 = np.polyfit(coor_center2[:, 1], coor_center2[:, 0], 1)
            p_yz2 = np.polyfit(coor_center2[:, 1], coor_center2[:, 2], 1)
            line_yy2 = np.linspace(0, nii_image.shape[1] - 1, nii_image.shape[1])
            line_xx2 = np.polyval(p_yx2, line_yy2)
            line_zz2 = np.polyval(p_yz2, line_yy2)

            line_yy = (line_yy1 + line_yy2) / 2
            line_xx = (line_xx1 + line_xx2) / 2
            line_zz = (line_zz1 + line_zz2) / 2

            # fit line
            self.process_bar.setValue(60)
            self.status_bar.showMessage("Fit line...")

            self.p_yx = np.polyfit(line_yy, line_xx, 1)
            self.p_yz = np.polyfit(line_yy, line_zz, 1)

            self.process_bar.setValue(70)
            line_end = np.reshape(np.array([line_xx[0], line_yy[0], line_zz[0], 1]), (4, 1))
            line_start = np.reshape(np.array([line_xx[-1], line_yy[-1], line_zz[-1], 1]), (4, 1))
            Trans_nii = self.ImageData.getTransMatrix()
            self.catheter_line_start = np.squeeze(np.matmul(Trans_nii, line_start)[:3]).tolist()
            self.catheter_line_end = np.squeeze(np.matmul(Trans_nii, line_end)[:3]).tolist()

        else:
            # fit line1
            coor_center1 = np.zeros((stop_col1 - start_col1, 3))
            tt = -1
            for ii in range(start_col1, stop_col1):

                tt = tt + 1
                bw = img_bw[start_row1:stop_row1, ii, start_slice1:stop_slice1]
                label = skimage.measure.label(bw)
                region = skimage.measure.regionprops(label)[0]

                coor = np.array([ii, region.centroid[0] + start_row1, region.centroid[1] + start_slice1])
                coor_center1[tt, :] = coor

            p_xy1 = np.polyfit(coor_center1[:, 0], coor_center1[:, 1], 1)
            p_xz1 = np.polyfit(coor_center1[:, 0], coor_center1[:, 2], 1)
            line_xx1 = np.linspace(0, nii_image.shape[0] - 1, nii_image.shape[0])
            line_yy1 = np.polyval(p_xy1, line_xx1)
            line_zz1 = np.polyval(p_xz1, line_xx1)

            # fit line2
            coor_center2 = np.zeros((stop_col2 - start_col2, 3))
            tt = -1
            for ii in range(start_col2, stop_col2):
                tt = tt + 1
                bw = img_bw[start_row2:stop_row2, ii, start_slice2:stop_slice2]
                label = skimage.measure.label(bw)
                region = skimage.measure.regionprops(label)[0]

                coor = np.array([ii, region.centroid[0] + start_row2, region.centroid[1] + start_slice2])
                coor_center2[tt, :] = coor

            p_xy2 = np.polyfit(coor_center2[:, 0], coor_center2[:, 1], 1)
            p_xz2 = np.polyfit(coor_center2[:, 0], coor_center2[:, 2], 1)
            line_xx2 = np.linspace(0, nii_image.shape[0] - 1, nii_image.shape[0])
            line_yy2 = np.polyval(p_xy2, line_xx2)
            line_zz2 = np.polyval(p_xz2, line_xx2)

            line_yy = (line_yy1 + line_yy2) / 2
            line_xx = (line_xx1 + line_xx2) / 2
            line_zz = (line_zz1 + line_zz2) / 2

            # fit line
            self.process_bar.setValue(60)
            self.status_bar.showMessage("Fit line...")

            self.p_xy = np.polyfit(line_xx, line_yy, 1)
            self.p_xz = np.polyfit(line_xx, line_zz, 1)

            self.process_bar.setValue(70)
            line_end = np.reshape(np.array([line_xx[0], line_yy[0], line_zz[0], 1]), (4, 1))
            line_start = np.reshape(np.array([line_xx[-1], line_yy[-1], line_zz[-1], 1]), (4, 1))
            Trans_nii = self.ImageData.getTransMatrix()
            self.catheter_line_start = np.squeeze(np.matmul(Trans_nii, line_start)[:3]).tolist()
            self.catheter_line_end = np.squeeze(np.matmul(Trans_nii, line_end)[:3]).tolist()

        # update line
        self.process_bar.setValue(90)
        self.status_bar.showMessage("Update line")
        self.catheter_count += 1

        if self.catheter_count == 1:
            self.updateAllLineAndPoint(current=True, last=False)

        if self.catheter_count > 1:
            self.updateAllLineAndPoint(current=True, last=True)

        self.process_bar.setValue(100)

        if self.nearest_point != []:
            imri_setting.IMRIGlobal.catheter_nearest = np.reshape(self.nearest_point, (3, 1))
        else:
            print("Please set and select a path!")

        self.setErrorValue()

        if self.AutoSendCheckBox.isChecked():
            self.sendToRobot()

        self.progress_dialog.setValue(5)
        self.progress_dialog.close()

        # except Exception as e:
        #     print("An error occurred:", e)
        #     print("Catheter area include non-catheter part!")
        #     meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Catheter area include non-catheter part!")
        #     meg_box.exec_()

    def setErrorValue(self):
        try:
            target_point = imri_setting.IMRIGlobal.target_pos
            entry_point = imri_setting.IMRIGlobal.entry_pos
            robot_target = imri_setting.worldToRobot(target_point)
            robot_entry = imri_setting.worldToRobot(entry_point)
            plan_v = robot_entry[0:3] - robot_target[0:3]
            plan_v = plan_v / np.linalg.norm(plan_v)
            traj_start = imri_setting.worldToRobot(self.catheter_line_end)
            robot_nearest = imri_setting.worldToRobot(self.nearest_point)
            traj_v = traj_start[0:3, 0] - robot_nearest[0:3, 0]
            traj_v = traj_v / np.linalg.norm(traj_v)
            angle_error = math.degrees(math.acos(np.dot(plan_v[:, 0], traj_v) / (np.linalg.norm(plan_v) * np.linalg.norm(traj_v))))  # angle error
            radial_error = np.linalg.norm(robot_target[0:3] - robot_nearest[0:3])  # radial error = self.nearest_dis
            self.angle_error_line.setText(str(round(angle_error, 2)))
            self.radial_error_line.setText(str(round(radial_error, 2)))
            imri_setting.IMRIGlobal.angle_error = angle_error
            imri_setting.IMRIGlobal.radial_error = radial_error
            imri_setting.IMRIGlobal.plan_v = plan_v
            imri_setting.IMRIGlobal.traj_v = traj_v
            imri_setting.IMRIGlobal.robot_target = robot_target
            current_time = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S ")
            catheter_info ="Catheter " + str(self.catheter_count) + ":    " + "Angle Error: " + str(round(angle_error, 2)) + "°    " + "Radial Error: " + str(round(radial_error, 2)) + "mm    "
            self.catheter_text.append(current_time)
            self.catheter_text.append(catheter_info)
            if self.catheter_file_path != None:
                with open(self.catheter_file_path, "a") as f:
                    f.write(f"{str(current_time)+str(catheter_info)}\n")

        except:
            self.catheter_text.append("Catheter " + str(self.catheter_count) + ":    " + "No Plan Path")
            print("Please set and select a path!")

    def sendToRobot(self):
        try:
            robot_target = imri_setting.IMRIGlobal.robot_target
            plan_v = imri_setting.IMRIGlobal.plan_v
            robot_nearest = imri_setting.worldToRobot(self.nearest_point)
            traj_v = imri_setting.IMRIGlobal.traj_v
            angle_error = imri_setting.IMRIGlobal.angle_error
            radial_error = imri_setting.IMRIGlobal.radial_error
            traj_info = (
                "01,"
                + str(robot_target[0, 0])
                + ","
                + str(robot_target[1, 0])
                + ","
                + str(robot_target[2, 0])
                + ","
                + str(plan_v[0, 0])
                + ","
                + str(plan_v[1, 0])
                + ","
                + str(plan_v[2, 0])
                + ","
                + str(robot_nearest[0, 0])
                + ","
                + str(robot_nearest[1, 0])
                + ","
                + str(robot_nearest[2, 0])
                + ","
                + str(traj_v[0])
                + ","
                + str(traj_v[1])
                + ","
                + str(traj_v[2])
                + ","
                + str(angle_error)
                + ","
                + str(radial_error)
                + ","
                + str(0)
            )
            print("traj_info", traj_info)
            robot_ip = self.config["main"]["robot_ip"]
            robot_port = self.config["main"]["robot_port"]
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_address = (robot_ip, robot_port)
            sock.connect(server_address)
            sock.sendall(traj_info.encode())
            sock.close()
        except:
            print("Send Catheter Info to Robot Error!")
            meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Send Catheter Info Error!")
            meg_box.exec_()

    def pointToLineDistance(self, point_a, line_point1, line_point2):
        point_a = np.array(point_a)
        line_point1 = np.array(line_point1)
        line_point2 = np.array(line_point2)
        line_vector = line_point2 - line_point1
        u_vector = point_a - line_point1
        cross_product = np.linalg.norm(np.cross(u_vector, line_vector))
        distance = cross_product / np.linalg.norm(line_vector)
        nearest_point = line_point1 + (np.dot(u_vector, line_vector) / np.dot(line_vector, line_vector)) * line_vector
        return distance, nearest_point.tolist()

    def updateNearestPoint2d(self, current=True, last=True):
        nearest_point_color_2d = self.config["catheter"]["nearest_point_color_2d"]
        nearest_point_radius_2d = self.config["catheter"]["nearest_point_radius_2d"]
        self.removeNearestPoint2d(current, last)

        target_point = imri_setting.IMRIGlobal.target_pos
        if target_point == None:
            # print("Please select a path!")
            return None

        # draw nearest point in 2d
        if current == True:
            if self.catheter_count > 0 and self.NearestPointCheckBox.isChecked():
                if len(self.catheter_line_start) != 0:
                    self.nearest_dis, self.nearest_point = self.pointToLineDistance(target_point, self.catheter_line_start, self.catheter_line_end)
                    points2d = self.ImageData.getPoint2dFromPoint3d(self.nearest_point, self.ImagePlanes.getPixmapsSize())
                    for i in range(3):
                        if self.ImageData.current_slice[i] == points2d[i][2]:
                            self.nearest_point_plane_items[i] = self.ImagePlanes.createPointItem(points2d[i][:2], color=nearest_point_color_2d, diameter=nearest_point_radius_2d * 2)
                            self.nearest_point_plane_items[i].setZValue(1)
                            self.ImagePlanes.addPlaneItem(self.nearest_point_plane_items[i], plane=i)
                        else:
                            self.ImagePlanes.removePlaneItem(self.nearest_point_plane_items[i], plane=i)

        # draw last nearest point in 2d
        if last == True:
            if self.catheter_count > 1 and self.LastNearestPointCheckBox.isChecked():
                if len(self.last_catheter_line_start) != 0:
                    self.last_nearest_dis, self.last_nearest_point = self.pointToLineDistance(target_point, self.last_catheter_line_start, self.last_catheter_line_end)
                    points2d = self.ImageData.getPoint2dFromPoint3d(self.last_nearest_point, self.ImagePlanes.getPixmapsSize())
                    for i in range(3):
                        if self.ImageData.current_slice[i] == points2d[i][2]:
                            self.last_nearest_point_plane_items[i] = self.ImagePlanes.createPointItem(points2d[i][:2], color=nearest_point_color_2d, diameter=nearest_point_radius_2d * 2)
                            self.last_nearest_point_plane_items[i].setZValue(1)
                            self.ImagePlanes.addPlaneItem(self.last_nearest_point_plane_items[i], plane=i)
                        else:
                            self.ImagePlanes.removePlaneItem(self.last_nearest_point_plane_items[i], plane=i)

    def updateNearestPoint3d(self, current=True, last=True):
        nearest_point_color_3d = self.config["catheter"]["nearest_point_color_3d"]
        nearest_point_opacity_3d = self.config["catheter"]["nearest_point_opacity_3d"]
        nearest_point_radius_3d = self.config["catheter"]["nearest_point_radius_3d"]
        self.removeNearestPoint3d(current, last)

        target_point = imri_setting.IMRIGlobal.target_pos
        if target_point == None:
            # print("Please select a path!")
            return None

        # draw nearest point in 3d
        if current == True:
            if self.catheter_count > 0 and self.NearestPointCheckBox.isChecked():
                if len(self.catheter_line_start) != 0:
                    self.nearest_dis, self.nearest_point = self.pointToLineDistance(target_point, self.catheter_line_start, self.catheter_line_end)
                    self.nearest_point_actor = self.Image3d.createPointActor(self.nearest_point, color=nearest_point_color_3d, opacity=nearest_point_opacity_3d, radius=nearest_point_radius_3d)
                    self.Image3d.addActor(self.nearest_point_actor)

        # draw last nearest point in 3d
        if last == True:
            if self.catheter_count > 1 and self.LastNearestPointCheckBox.isChecked():
                if len(self.last_catheter_line_start) != 0:
                    self.last_nearest_dis, self.last_nearest_point = self.pointToLineDistance(target_point, self.last_catheter_line_start, self.last_catheter_line_end)
                    self.last_nearest_point_actor = self.Image3d.createPointActor(
                        self.last_nearest_point, color=nearest_point_color_3d, opacity=nearest_point_opacity_3d, radius=nearest_point_radius_3d
                    )
                    self.Image3d.addActor(self.last_nearest_point_actor)

    def removeNearestPoint2d(self, current=True, last=True):
        if current == True:
            for i in range(3):
                if self.nearest_point_plane_items[i] != None:
                    self.ImagePlanes.removePlaneItem(self.nearest_point_plane_items[i], plane=i)
                    self.nearest_point_plane_items[i] = None

        if last == True:
            for i in range(3):
                if self.last_nearest_point_plane_items[i] != None:
                    self.ImagePlanes.removePlaneItem(self.last_nearest_point_plane_items[i], plane=i)
                    self.last_nearest_point_plane_items[i] = None

    def removeNearestPoint3d(self, current=True, last=True):
        if current == True:
            if self.nearest_point_actor != None:
                self.Image3d.removeActor(self.nearest_point_actor)
                self.nearest_point_actor = None

        if last == True:
            if self.last_nearest_point_actor != None:
                self.Image3d.removeActor(self.last_nearest_point_actor)
                self.last_nearest_point_actor = None

    def updateCatheterLine2d(self, current=True, last=True):
        line_color_2d = self.config["catheter"]["line_color_2d"]
        line_width_2d = self.config["catheter"]["line_width_2d"]
        self.removeCatheterLine2d(current, last)

        # draw current line in 2d
        if current == True:
            if self.catheter_count > 0 and self.CatheterLineCheckBox.isChecked():
                if len(self.catheter_line_start) != 0:
                    lines2d = self.ImageData.getLine2dFromLine3d([self.catheter_line_start, self.catheter_line_end], self.ImagePlanes.getPixmapsSize())
                    start_pos_planes = lines2d[0]  # [[x, y, z], [x, y, z], [x, y, z]]
                    end_pos_planes = lines2d[1]  # [[x, y, z], [x, y, z], [x, y, z]]
                    for i in range(3):
                        self.line_plane_items[i] = self.ImagePlanes.createLineItem(start_pos_planes[i][:2], end_pos_planes[i][:2], color=line_color_2d, width=line_width_2d)
                        self.ImagePlanes.addPlaneItem(self.line_plane_items[i], plane=i)

        # draw last line in 2d
        if last == True:
            if self.catheter_count > 1 and self.LastLineCheckBox.isChecked():
                if len(self.last_catheter_line_start) != 0:
                    # print("last_catheter_line_start", self.last_catheter_line_start)
                    lines2d = self.ImageData.getLine2dFromLine3d([self.last_catheter_line_start, self.last_catheter_line_end], self.ImagePlanes.getPixmapsSize())
                    start_pos_planes = lines2d[0]
                    end_pos_planes = lines2d[1]
                    for i in range(3):
                        self.last_line_plane_items[i] = self.ImagePlanes.createLineItem(start_pos_planes[i][:2], end_pos_planes[i][:2], color=line_color_2d, width=line_width_2d, style=Qt.DashLine)
                        # self.last_line_plane_items[i].setOpacity(0.5)
                        self.ImagePlanes.addPlaneItem(self.last_line_plane_items[i], plane=i)

    def updateCatheterLine3d(self, current=True, last=True):
        line_color_3d = self.config["catheter"]["line_color_3d"]
        line_opacity_3d = self.config["catheter"]["line_opacity_3d"]
        line_width_3d = self.config["catheter"]["line_width_3d"]
        self.removeCatheterLine3d(current, last)

        # draw current line in 3d
        if current == True:
            if self.catheter_count > 0 and self.CatheterLineCheckBox.isChecked():
                if len(self.catheter_line_start) != 0:
                    self.catheter_line_actor = self.Image3d.createLineActor(self.catheter_line_start, self.catheter_line_end, color=line_color_3d, opacity=line_opacity_3d, width=line_width_3d)
                    self.Image3d.addActor(self.catheter_line_actor)

        # draw last line in 3d
        if last == True:
            if self.catheter_count > 1 and self.LastLineCheckBox.isChecked():
                if len(self.last_catheter_line_start) != 0:
                    self.last_catheter_line_actor = self.Image3d.createLineActor(
                        self.last_catheter_line_start, self.last_catheter_line_end, color=line_color_3d, opacity=line_opacity_3d / 2, width=line_width_3d
                    )
                    self.Image3d.addActor(self.last_catheter_line_actor)

    def removeCatheterLine2d(self, current=True, last=True):
        if current == True:
            for i in range(3):
                if self.line_plane_items[i] != None:
                    self.ImagePlanes.removePlaneItem(self.line_plane_items[i], plane=i)
                    self.line_plane_items[i] = None

        if last == True:
            for i in range(3):
                if self.last_line_plane_items[i] != None:
                    self.ImagePlanes.removePlaneItem(self.last_line_plane_items[i], plane=i)
                    self.last_line_plane_items[i] = None

    def removeCatheterLine3d(self, current=True, last=True):
        if current == True:
            if self.catheter_line_actor != None:
                self.Image3d.removeActor(self.catheter_line_actor)
                self.catheter_line_actor = None

        if last == True:
            if self.last_catheter_line_actor != None:
                self.Image3d.removeActor(self.last_catheter_line_actor)
                self.last_catheter_line_actor = None

    def updateAllLineAndPoint(self, current=True, last=True):
        self.updateCatheterLine2d(current, last)
        self.updateCatheterLine3d(current, last)
        self.updateNearestPoint2d(current, last)
        self.updateNearestPoint3d(current, last)

    # def updateCatheterSliceRange(self):
    #     nii_image = self.ImageData.Vtk2Numpy(self.ImageData.data)
    #     nii_image = np.transpose(nii_image, (1, 2, 0))
    #     max_slice = nii_image.shape[2] - 1
    #     min_slice = 0
    #     self.CatheterStartSliceSpinBox.setRange(min_slice, max_slice)
    #     self.CatheterEndSliceSpinBox.setRange(min_slice, max_slice)
    #     self.CatheterStartSliceSpinBox.setValue(min_slice)
    #     self.CatheterEndSliceSpinBox.setValue(max_slice)
