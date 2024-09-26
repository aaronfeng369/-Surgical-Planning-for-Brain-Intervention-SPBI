import sys
import os
import time
import numpy as np
import socket
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import vtkmodules.all as vtk

from imri_ui import Ui_MainWindow
import imri_io
import imri_image_data
import imri_image_planes
import imri_image_3d
import imri_setting
import imri_plan
import imri_catheter
import imri_measure
import imri_registration_zframe
import imri_needle_recog
import imri_evaluation
import imri_vessel
import imri_fusion
import imri_brain_segment
import imri_sensor

import imri_fiber
import qdarkstyle
from functools import partial

# from memory_profiler import profile


class MainWindow(QMainWindow):
    image_read_signal = pyqtSignal(dict)  # 1 module 2 path 3 mode

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.views = [
            self.ui.SaggraphicsView,
            self.ui.CorgraphicsView,
            self.ui.AxigraphicsView,
        ]
        for i in range(3):
            self.views[i].setStyleSheet("background-color: black")
        self.scroll_bars = [
            self.ui.SagScrollBar,
            self.ui.CorScrollBar,
            self.ui.AxiScrollBar,
        ]
        self.message = [
            self.ui.sag_meg,
            self.ui.cor_meg,
            self.ui.axi_meg,
            self.ui.vol_meg,
        ]
        self.ImageDatas = []
        self.ImagePlanes = imri_image_planes.ImagePlanes()
        self.Image3d = imri_image_3d.Image3d(self.ui.VolWidget)
        self.ImageVesselData = None
        self.ImageFusionMaskData = None
        self.img_index = -1
        self.current_mouse_in_view = None
        self.real_time_file_path = None
        self.FileWatcher = QFileSystemWatcher()
        self.left_mouse_press = False
        self.right_mouse_press = False
        self.middle_mouse_press = False
        self.show_cross_line = True
        self.img_volume = None

        self.config = imri_setting.read_config()
        imri_setting.setAutoSaveFile(self.config)

        self.files_path = []  # save readed file path
        self.ImageListItems = []

        self.measure = imri_measure.Measure()
        self.measure.init(self.ui.MeasureListWidget, self.ui.MeasureLineBtn, self.ui.MeasureAngleBtn, self.Image3d, self.ImagePlanes)

        self.catheter = imri_catheter.Catheter()
        self.catheter.init(self.ui, self.Image3d, self.ImagePlanes)

        self.plan = imri_plan.Plan()
        self.plan.init(self.ui, self.Image3d, self.ImagePlanes)

        self.zFrame = imri_registration_zframe.ZFrame()
        self.zFrame.init(self.ui)

        self.needle_recog = imri_needle_recog.NeedleRecog()
        self.needle_recog.init(self.ui, self.Image3d, self.ImagePlanes, self.image_read_signal)

        self.evaluation = imri_evaluation.Evaluation()
        self.evaluation.init(self.ui, self.Image3d, self.ImagePlanes)

        self.fusion = imri_fusion.Fusion()
        self.fusion.init(self.ui, self.Image3d, self.ImagePlanes, self.image_read_signal)

        self.brainSegment = imri_brain_segment.BrainSegment()
        self.brainSegment.init(self.ui, self.Image3d, self.ImagePlanes, self.views)

        self.vessel = imri_vessel.Vessel()
        self.vessel.init(self.ui, self.Image3d, self.ImagePlanes, self.views)

        self.sensor = imri_sensor.Sensor()
        self.sensor.init(self.ui)

        self.ui.AxigraphicsView.setMouseTracking(True)
        self.ui.CorgraphicsView.setMouseTracking(True)
        self.ui.SaggraphicsView.setMouseTracking(True)
        self.ui.SaggraphicsView.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.ui.CorgraphicsView.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.ui.AxigraphicsView.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.initQt()
        # self.views[self.current_mouse_in_view].setTransformationAnchor(QGraphicsView.AnchorUnderMouse)  # set rescale anchor point to mouse position

    def initQt(self):
        self.setWindowState(self.windowState() | Qt.WindowMaximized)
        for i in range(3):
            self.views[i].setScene(self.ImagePlanes.scenes[i])

        # read file
        self.ui.ImageReadBtn.clicked.connect(self.openFile)
        self.ui.ImageListWidget.currentItemChanged.connect(self.showReadImage)
        # slice and volume control
        self.ui.showSlicerCheckBox.setCheckState(Qt.Checked)
        self.ui.showSlicerCheckBox.stateChanged.connect(self.showSlicer)
        self.ui.showVolumeCheckBox.stateChanged.connect(self.showVolume)
        self.ui.VolumeThresholdSlider.setDisabled(True)
        self.ui.VolumeThresholdSlider.valueChanged.connect(self.onVolumeThresholdChanged)
        self.ui.VolumeColorBtn.setDisabled(True)
        self.ui.VolumeColorBtn.setIcon(QIcon("image/color_dialog.png"))
        self.ui.VolumeColorBtn.clicked.connect(self.setVolumeColor)
        self.PiecewiseFunc = vtk.vtkPiecewiseFunction()
        self.PiecewiseFunc.AddPoint(0, 0)
        self.PiecewiseFunc.AddPoint(350, 1.00)
        self.ColorTransferFunc = None

        # zframe file
        self.ui.ReadZFrameBtn.clicked.connect(self.openFile_zframe)
        # catheter file
        self.ui.ReadCatheterBtn.clicked.connect(self.openFile)
        # real time file
        self.ui.RealTimeReadBtn.clicked.connect(self.openRealTimeFile)
        self.ui.RealTimeReadStartBtn.clicked.connect(self.setRealTimeRead)
        self.ui.RealTimeReadStartBtn.setEnabled(False)

        # fusion tools
        self.ui.FusionMaskThresholdSlider.valueChanged.connect(self.onFusionImageThresholdChanged)
        self.ui.FusionAcceptBtn.clicked.connect(self.accept_fusion)
        self.ui.FusionRejectBtn.clicked.connect(self.reject_fusion)
        # Tools
        self.ui.T1FileBtn.clicked.connect(self.readT1File)
        self.ui.T2FileBtn.clicked.connect(self.readT2File)
        self.ui.MRAFileBtn.clicked.connect(self.readMRAFile)
        self.ui.showT1checkBox.setDisabled(True)
        self.ui.showT2checkBox.setDisabled(True)
        self.ui.showMRAcheckBox.setDisabled(True)

        # Fiber
        self.ui.FiberTrackingBtn.clicked.connect(self.fiberTracking)
        self.ui.LoadFiberFileBtn.clicked.connect(self.loadFiber)
        self.ui.Fiber3DCheckBox.stateChanged.connect(self.showFiber3D)

        self.ui.showT1checkBox.stateChanged.connect(self.showT1Image)
        self.ui.showT2checkBox.stateChanged.connect(self.showT2Image)
        self.ui.showMRAcheckBox.stateChanged.connect(self.showMRAImage)

        # Qmenu
        self.ui.actionAdd_Nii_Data.triggered.connect(self.openFile)
        self.ui.actionAdd_Dicom.triggered.connect(self.openDicomFile)
        self.ui.actionExit.triggered.connect(self.exit)
        self.ui.actionAbout_IMRI_SN.triggered.connect(self.aboutIMRISN)
        self.ui.actionReset_Views.setIcon(QIcon("image/resetView_icon.png"))
        self.ui.actionReset_Views.triggered.connect(self.resetViews)
        self.ui.actionCrossLine.setIcon(QIcon("image/crossline_icon.png"))
        self.ui.actionCrossLine.triggered.connect(self.showCrossLine)
        self.ui.action3DAxes.setIcon(QIcon("image/3dAxes_icon.png"))
        self.ui.action3DAxes.triggered.connect(self.Image3d.addAxesActor)
        self.ui.action3DCube.setIcon(QIcon("image/3dCube_icon.png"))
        self.ui.action3DCube.triggered.connect(self.Image3d.addAnnotatedCubeActor)
        self.ui.actionConnect_Robot.setIcon(QIcon("image/connectRobot_icon.png"))
        self.ui.actionConnect_Robot.triggered.connect(self.connectRobot)

        # QToolBar
        self.ui.actionView.triggered.connect(self.switchFuncArea)
        self.ui.actionTools.triggered.connect(self.switchFuncArea)
        self.ui.actionRegistration.triggered.connect(self.switchFuncArea)
        self.ui.actionPlan.triggered.connect(self.switchFuncArea)
        self.ui.actionNavigation.triggered.connect(self.switchFuncArea)
        self.ui.actionMonitoring.triggered.connect(self.switchFuncArea)
        self.ui.actionEvaluation.triggered.connect(self.switchFuncArea)

        # ScrollBar
        self.ui.SagScrollBar.valueChanged.connect(self.onScrollBarValueChanged)
        self.ui.CorScrollBar.valueChanged.connect(self.onScrollBarValueChanged)
        self.ui.AxiScrollBar.valueChanged.connect(self.onScrollBarValueChanged)

        self.ui.GrayAutoBtn.clicked.connect(self.onGrayScaleChanged)
        self.ui.GrayResetBtn.clicked.connect(self.onGrayScaleChanged)
        self.ui.GrayMinSpinBox.valueChanged.connect(self.onGrayScaleChanged)
        self.ui.GrayMaxSpinBox.valueChanged.connect(self.onGrayScaleChanged)
        self.ui.WLSlider.valueChanged.connect(self.onGrayScaleChanged)
        self.ui.WWSlider.valueChanged.connect(self.onGrayScaleChanged)
        self.ui.WLSpinBox.valueChanged.connect(self.onGrayScaleChanged)
        self.ui.WWSpinBox.valueChanged.connect(self.onGrayScaleChanged)

        # eventFilter
        self.ui.SaggraphicsView.installEventFilter(self)
        self.ui.CorgraphicsView.installEventFilter(self)
        self.ui.AxigraphicsView.installEventFilter(self)
        self.ui.SaggraphicsView.viewport().installEventFilter(self)
        self.ui.CorgraphicsView.viewport().installEventFilter(self)
        self.ui.AxigraphicsView.viewport().installEventFilter(self)

        # self.installEventFilter(self)
        for i in range(3):
            self.views[i].verticalScrollBar().blockSignals(True)
            self.views[i].horizontalScrollBar().blockSignals(True)
            self.views[i].setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.views[i].setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # signal
        self.image_read_signal.connect(self.updateReadImage)

    def switchFuncArea(self):
        """
        switch the stackedWidget to display different function area
        """
        action = self.sender()
        if action == self.ui.actionView:
            self.ui.stackedWidget.setCurrentIndex(0)
        elif action == self.ui.actionTools:
            self.ui.stackedWidget.setCurrentIndex(1)
        elif action == self.ui.actionRegistration:
            self.ui.stackedWidget.setCurrentIndex(2)
        elif action == self.ui.actionPlan:
            self.ui.stackedWidget.setCurrentIndex(3)
        elif action == self.ui.actionNavigation:
            self.ui.stackedWidget.setCurrentIndex(4)
        elif action == self.ui.actionMonitoring:
            self.ui.stackedWidget.setCurrentIndex(5)
        elif action == self.ui.actionEvaluation:
            self.ui.stackedWidget.setCurrentIndex(6)
        else:
            pass

    def showCrossLine(self):
        if self.show_cross_line == False:
            self.show_cross_line = True
            for i in range(3):
                self.ImagePlanes.cross_line[i][0].setVisible(True)
                self.ImagePlanes.cross_line[i][1].setVisible(True)
        else:
            self.show_cross_line = False
            for i in range(3):
                self.ImagePlanes.cross_line[i][0].setVisible(False)
                self.ImagePlanes.cross_line[i][1].setVisible(False)

    def resetViews(self):

        for i in range(3):
            self.views[i].resetTransform()
        self.ImagePlanes.resizePlanes(self.views, self.ImageDatas[self.img_index])
        self.Image3d.ren.ResetCamera()
        self.Image3d.ren.GetActiveCamera().Zoom(1.5)
        self.Image3d.renWin.Render()

    def updateImage(self, index, value):
        # TODO value > slice
        extent = self.ImageDatas[self.img_index].new_extent
        if value < extent[2 * index] or value > extent[2 * index + 1]:
            return None
        else:
            self.ImageDatas[self.img_index].current_slice[index] = value
            # 2d Image
            pix_data, dis = self.ImageDatas[self.img_index].getCurrentReslice(plane=index)
            self.ImagePlanes.addPixmap(pix_data, self.ImageDatas[self.img_index].gray_scale, self.views, plane=index)
            # 2d fusion mask
            if self.ImageFusionMaskData != None:
                self.ImageFusionMaskData.current_slice[index] = value
                pix_data, _ = self.ImageFusionMaskData.getCurrentReslice(plane=index)
                if self.ImageFusionMaskData.mode == "MovingMask":
                    self.ImagePlanes.addMaskPixmap(pix_data, self.views, mode="Fusion", color_table=self.fusion.color_table, plane=index)
                elif self.ImageFusionMaskData.mode == "MovedMask":
                    self.ImagePlanes.addMaskPixmap(pix_data, self.views, mode="Fusion", color_table=self.fusion.fusioned_color_table, plane=index)
                else:
                    pass
            # 2d brain segment
            if self.brainSegment.BrainSegMaskData != None and self.ui.BrainSeg2DViewcheckBox.isChecked():
                self.brainSegment.BrainSegMaskData.current_slice[index] = value
                pix_data, _ = self.brainSegment.BrainSegMaskData.getCurrentReslice(plane=index)
                self.ImagePlanes.addMaskPixmap(pix_data, self.views, mode="BrainSeg", color_table=self.brainSegment.color_table, plane=index)
            # 2d vessel
            if self.vessel.vesselMaskData != None and self.ui.Vessel2DCheckBox.isChecked():
                self.vessel.vesselMaskData.current_slice[index] = value
                pix_data, _ = self.vessel.vesselMaskData.getCurrentReslice(plane=index)
                self.ImagePlanes.addMaskPixmap(pix_data, self.views, mode="Vessel", color_table=self.vessel.color_table, plane=index)

            # catheter
            if self.catheter.catheter_line_actor != None:
                self.catheter.updateCatheterLine2d()
            if self.catheter.nearest_point_actor != None:
                self.catheter.updateNearestPoint2d()
            # plan
            self.plan.updateCheckedItem2d()
            # measure
            if self.measure.measure_item != None:
                self.measure.updateCheckedItem2d()

            # message
            self.message[index].setText(f"{self.scroll_bars[index].value()} / {self.scroll_bars[index].maximum()}   {dis}(mm)")

            # slice and volume
            if self.ui.showSlicerCheckBox.isChecked():
                self.Image3d.moveSlicer(self.ImageDatas[self.img_index], index, value)

        # if self.ui.showVolumeCheckBox.isChecked():
        #     self.ui.showVolumeCheckBox.setCheckState(Qt.Unchecked)

    def onScrollBarValueChanged(self):
        try:
            index = self.scroll_bars.index(self.sender())
            value = self.scroll_bars[index].value()
            extent = self.ImageDatas[self.img_index].new_extent
            if value >= extent[2 * index] or value <= extent[2 * index + 1]:
                self.updateImage(index, value)
                # cross line
                if self.show_cross_line == True and self.ImageDatas != []:
                    rect1 = self.ImagePlanes.cross_line[index][0].boundingRect()
                    rect2 = self.ImagePlanes.cross_line[index][1].boundingRect()
                    pos_x = round(rect1.x() + rect1.width() / 2)
                    pos_y = round(rect2.y() + rect2.height() / 2)
                    # pos_z = value
                    # print(pos_x,pos_y,pos_z)
                    _, world_units = self.ImageDatas[self.img_index].ImageToWorld([pos_x, pos_y], self.ImagePlanes.getPixmapsSize(), plane=index)
                    for i in range(3):
                        image_pos, z = self.ImageDatas[self.img_index].WorldToImage(world_units, self.ImagePlanes.getPixmapsSize(), plane=i)
                        self.ImagePlanes.setCrossLine(self.views[i].contentsRect().width(), self.views[i].contentsRect().height(), image_pos, i)
                        if i != index:
                            self.scroll_bars[i].blockSignals(True)
                            self.scroll_bars[i].setValue(np.round(z).astype(int))
                            self.updateImage(i, np.round(z).astype(int))
                            # 2024-04-19 21:39:42.301 (  18.725s) [809E7947D047B98F]vtkDemandDrivenPipeline:677    ERR| vtkCompositeDataPipeline (00000209F69BA2B0): Input port 0 of algorithm vtkImageReslice (00000209E839E320) has 0 connections but is not optional.
                            self.scroll_bars[i].blockSignals(False)

        except:
            print("onScrollBarValueChanged error")

    def onGrayScaleChanged(self):
        if self.img_index >= 0:
            sender = self.sender()
            if sender == self.ui.GrayAutoBtn:
                self.ImageDatas[self.img_index].gray_scale = self.ImageDatas[self.img_index].getAutoGrayScale()
            elif sender == self.ui.GrayResetBtn:
                self.ImageDatas[self.img_index].gray_scale = self.ImageDatas[self.img_index].getOriginGrayScale()
            elif sender == self.ui.GrayMinSpinBox or sender == self.ui.GrayMaxSpinBox:
                self.ImageDatas[self.img_index].gray_scale = [
                    int(self.ui.GrayMinSpinBox.value()),
                    int(self.ui.GrayMaxSpinBox.value()),
                ]
            elif sender == self.ui.WLSlider or sender == self.ui.WWSlider:
                self.ImageDatas[self.img_index].gray_scale = [
                    int(self.ui.WLSlider.value() - self.ui.WWSlider.value() / 2),
                    int(self.ui.WLSlider.value() + self.ui.WWSlider.value() / 2),
                ]
            elif sender == self.ui.WLSpinBox or sender == self.ui.WWSpinBox:
                self.ImageDatas[self.img_index].gray_scale = [
                    int(self.ui.WLSpinBox.value() - self.ui.WWSpinBox.value() / 2),
                    int(self.ui.WLSpinBox.value() + self.ui.WWSpinBox.value() / 2),
                ]
            else:
                pass
            self.GrayScaleSignalBlock(True)
            min_gray, max_gray = self.ImageDatas[self.img_index].gray_scale
            ww = int(max_gray - min_gray)
            wl = int((min_gray + max_gray) / 2)
            self.ui.GrayMinSpinBox.setValue(min_gray)
            self.ui.GrayMaxSpinBox.setValue(max_gray)
            self.ui.WLSlider.setValue(wl)
            self.ui.WWSlider.setValue(ww)
            self.ui.WLSpinBox.setValue(wl)
            self.ui.WWSpinBox.setValue(ww)
            self.GrayScaleSignalBlock(False)
            # pix_data, dis = self.ImageDatas[self.img_index].getCurrentReslice(plane=2)
            for i in range(3):
                pix_data, dis = self.ImageDatas[self.img_index].getCurrentReslice(plane=i)
                self.ImagePlanes.addPixmap(
                    pix_data,
                    self.ImageDatas[self.img_index].gray_scale,
                    self.views,
                    plane=i,
                )

    def GrayScaleSignalBlock(self, block=True):
        self.ui.GrayMaxSpinBox.blockSignals(block)
        self.ui.GrayMinSpinBox.blockSignals(block)
        self.ui.WLSlider.blockSignals(block)
        self.ui.WWSlider.blockSignals(block)
        self.ui.WLSpinBox.blockSignals(block)
        self.ui.WWSpinBox.blockSignals(block)

    def updateReadImage(self, dict_data):
        if dict_data["module"] == "fusion":
            if dict_data["mode"] == "image":
                self.updateGrayImage(dict_data["path"])
                self.ImageDatas[self.img_index].mode = "FixedImage"
            else:
                self.updateFusionMaskImage(dict_data["path"], mode=dict_data["mode"])

        if dict_data["module"] == "T1":
            self.ui.showT1checkBox.setCheckState(Qt.Checked)

        if dict_data["module"] == "T2":
            self.ui.showT2checkBox.setCheckState(Qt.Checked)

        if dict_data["module"] == "MAR":
            if dict_data["mode"] == "image":
                self.updateGrayImage(dict_data["path"])
                self.ImageDatas[self.img_index].mode = "MAR"

    def updateGrayImage(self, file):
        if file not in self.files_path:
            self.img_index += 1
            self.files_path.append(file)
            file_name_with_extension = os.path.basename(file)
            file_name_without_extension = os.path.splitext(file_name_with_extension)[0]
            item = QListWidgetItem(QIcon("image/nifti_icon.png"), file_name_without_extension)
            self.ui.ImageListWidget.addItem(item)
            self.ImageListItems.append(item)
            data, ori_data = imri_io.readNiftiFile(file)
            new_data = imri_image_data.ImageData()
            new_data.initImageData(data, ori_data)
            self.ImageDatas.append(new_data)
        else:
            self.img_index = self.files_path.index(file)

        self.ui.ImageListWidget.setCurrentItem(self.ImageListItems[self.img_index])

    def showSlicer(self):
        if self.img_index != -1:
            if self.ui.showSlicerCheckBox.isChecked():
                self.Image3d.removeSlicer()
                self.Image3d.addSlicer(self.ImageDatas[self.img_index], None)
                self.Image3d.renderSlicer(mode=self.ImageDatas[self.img_index].acqMode)
                self.Image3d.resizeScene(self.views)
            else:
                self.Image3d.removeSlicer()

    def showVolume(self):
        if self.img_index != -1:
            if self.ui.showVolumeCheckBox.isChecked():
                self.Image3d.removeVolume(self.img_volume)
                self.img_volume = self.Image3d.initVolume(self.ImageDatas[self.img_index])
                self.Image3d.updateVolume(self.img_volume, self.PiecewiseFunc, self.ColorTransferFunc)
                self.ui.VolumeThresholdSlider.setDisabled(False)
                self.ui.VolumeColorBtn.setDisabled(False)
            else:
                self.Image3d.removeVolume(self.img_volume)
                self.ui.VolumeThresholdSlider.setDisabled(True)
                self.ui.VolumeColorBtn.setDisabled(True)

        else:
            print("Please load image first!")

    def onVolumeThresholdChanged(self):
        GrayScale = self.ImageDatas[self.img_index].getAutoGrayScale()
        max_value = GrayScale[1]
        threshold = self.ui.VolumeThresholdSlider.value()
        PiecewiseFunc = vtk.vtkPiecewiseFunction()
        PiecewiseFunc.AddPoint(threshold / 100 * max_value, 0)
        PiecewiseFunc.AddPoint(max_value, 1.00)
        self.PiecewiseFunc = PiecewiseFunc
        self.Image3d.updateVolume(self.img_volume, self.PiecewiseFunc, self.ColorTransferFunc)

    def setVolumeColor(self):
        qcolor = QColorDialog.getColor()
        if qcolor.isValid():
            GrayScale = self.ImageDatas[self.img_index].getAutoGrayScale()
            max_value = GrayScale[1]
            color = vtk.vtkColorTransferFunction()
            color.AddRGBPoint(0, 0, 0, 0)
            color.AddRGBPoint(max_value, qcolor.red() / 255, qcolor.green() / 255, qcolor.blue() / 255)
            self.ColorTransferFunc = color
            self.Image3d.updateVolume(self.img_volume, self.PiecewiseFunc, self.ColorTransferFunc)
        else:
            print("Invalid Color")

    """ 
    ############################################################################################################
    # Fusion Start
    ############################################################################################################
    """

    def updateFusionMaskImage(self, file, mode=None):
        if self.ImageDatas[self.img_index].mode == "FixedImage":
            data, ori_data = imri_io.readNiftiFile(file)
            self.ImageFusionMaskData = imri_image_data.ImageData()
            self.ImageFusionMaskData.initImageData(data, ori_data)
            if mode == "mask":
                self.ImageFusionMaskData.mode = "MovingMask"
                color_table = self.fusion.color_table
            else:
                self.ImageFusionMaskData.mode = "MovedMask"
                color_table = self.fusion.fusioned_color_table

            try:
                for i in range(3):
                    self.ImageFusionMaskData.initReslice(plane=i)
                self.ImageFusionMaskData.current_slice = self.ImageDatas[self.img_index].current_slice
                for i in range(3):
                    pix_data, _ = self.ImageFusionMaskData.getCurrentReslice(plane=i)
                    self.ImagePlanes.addMaskPixmap(pix_data, self.views, mode="Fusion", color_table=color_table, plane=i)
            except:
                print("Mask Slice maybe out of range")
                for i in range(3):
                    pix_data = self.ImageFusionMaskData.initReslice(plane=i)
                    self.ImagePlanes.addMaskPixmap(pix_data, self.views, mode="Fusion", color_table=color_table, plane=i)
        else:
            print("Please load fixed image first")
            meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Please load fixed image first!")
            meg_box.exec_()

    def onFusionImageThresholdChanged(self):
        self.fusion.setFusionColorTable(threshold=self.ui.FusionMaskThresholdSlider.value())
        if self.ImageFusionMaskData != None:
            for i in range(3):
                pix_data, _ = self.ImageFusionMaskData.getCurrentReslice(plane=i)
                if self.ImageFusionMaskData.mode == "MovingMask":
                    self.ImagePlanes.addMaskPixmap(pix_data, self.views, mode="Fusion", color_table=self.fusion.color_table, plane=i)
                elif self.ImageFusionMaskData.mode == "MovedMask":
                    self.ImagePlanes.addMaskPixmap(pix_data, self.views, mode="Fusion", color_table=self.fusion.fusioned_color_table, plane=i)
                else:
                    pass

    def accept_fusion(self):
        if self.ImageFusionMaskData != None:
            self.ImageFusionMaskData = None
            for i in range(3):
                self.ImagePlanes.removePlaneItem(item=self.ImagePlanes.fusion_mask_pixmap_items[i], plane=i)

            self.updateGrayImage(self.fusion.moved_image_path)

    def reject_fusion(self):
        if self.ImageFusionMaskData != None:
            self.ImageFusionMaskData = None
            for i in range(3):
                self.ImagePlanes.removePlaneItem(item=self.ImagePlanes.fusion_mask_pixmap_items[i], plane=i)

            os.remove(self.fusion.moved_image_path)
            self.ui.FusionErrorLineEdit.clear()

    """
    ############################################################################################################
    # T1/T2 MRA DTI Switch and View 
    ############################################################################################################
    """

    def readT1File(self):
        directory_path = self.config["main"]["image_directory"]
        file, _ = QFileDialog.getOpenFileName(self, "Open T1 File", directory_path, "Nii(*.nii.gz)")
        if file:
            self.config["main"]["image_directory"] = os.path.dirname(file)
            imri_setting.update_config(config=self.config)
            self.T1_file_path = file
            self.ui.T1FileLineEdit.setText(file)
            T1_file_dict = {"module": "T1", "path": file, "mode": "image"}
            self.image_read_signal.emit(T1_file_dict)
            self.ui.showT1checkBox.setDisabled(False)
            self.ui.showT1checkBox.setCheckState(Qt.Checked)

    def readT2File(self):
        directory_path = self.config["main"]["image_directory"]
        file, _ = QFileDialog.getOpenFileName(self, "Open T2 File", directory_path, "Nii(*.nii.gz)")
        if file:
            self.config["main"]["image_directory"] = os.path.dirname(file)
            imri_setting.update_config(config=self.config)
            self.T2_file_path = file
            self.ui.T2FileLineEdit.setText(file)
            T2_file_dict = {"module": "T2", "path": file, "mode": "image"}
            self.image_read_signal.emit(T2_file_dict)
            self.ui.showT2checkBox.setDisabled(False)
            self.ui.showT2checkBox.setCheckState(Qt.Checked)

    def readMRAFile(self):
        directory_path = self.config["main"]["image_directory"]
        file, _ = QFileDialog.getOpenFileName(self, "Open MRA File", directory_path, "Nii(*.nii.gz)")
        if file:
            self.config["main"]["image_directory"] = os.path.dirname(file)
            imri_setting.update_config(config=self.config)
            self.MRA_file_path = file
            self.ui.MRAFileLineEdit.setText(file)
            MRA_file_dict = {"module": "MRA", "path": file, "mode": "image"}
            self.image_read_signal.emit(MRA_file_dict)
            self.ui.showMRAcheckBox.setDisabled(False)
            self.ui.showMRAcheckBox.setCheckState(Qt.Checked)

    def showT1Image(self):
        if self.ui.showT1checkBox.isChecked():
            self.updateGrayImage(self.T1_file_path)
            self.ImageDatas[self.img_index].mode = "T1Image"
            self.ui.showT2checkBox.setCheckState(Qt.Unchecked)
        else:
            pass

    def showT2Image(self):
        if self.ui.showT2checkBox.isChecked():
            self.updateGrayImage(self.T2_file_path)
            self.ImageDatas[self.img_index].mode = "T2Image"
            self.ui.showT1checkBox.setCheckState(Qt.Unchecked)
        else:
            pass

    def showMRAImage(self):
        if self.ui.showMRAcheckBox.isChecked():
            self.updateGrayImage(self.MRA_file_path)
            self.ImageDatas[self.img_index].mode = "MRAImage"
        else:
            pass

    def openFile_zframe(self):
        directory_path = self.config["zframe"]["image_directory"]
        files, _ = QFileDialog.getOpenFileNames(self, "Open File(s)", directory_path, "Nii(*.nii.gz)")
        if len(files) > 0:
            self.config["zframe"]["image_directory"] = os.path.dirname(files[0])
            imri_setting.update_config(config=self.config)
            for file in files:
                if file not in self.files_path:
                    self.img_index += 1
                    self.files_path.append(file)
                    file_name_with_extension = os.path.basename(file)
                    file_name_without_extension = os.path.splitext(file_name_with_extension)[0]
                    item = QListWidgetItem(QIcon("image/nifti_icon.png"), file_name_without_extension)
                    self.ui.ImageListWidget.addItem(item)
                    self.ImageListItems.append(item)
                    data, ori_data = imri_io.readNiftiFile(file)
                    new_data = imri_image_data.ImageData()
                    new_data.initImageData(data, ori_data)
                    self.ImageDatas.append(new_data)
            self.ui.ImageListWidget.setCurrentItem(self.ImageListItems[-1])

    def fiberTracking(self):
        actor = imri_fiber.fiber_tracking()
        actor.SetUserMatrix(self.ImageDatas[self.img_index].user_matrix)
        actor.SetPosition(55, 140, 120)
        self.fiber_actor = actor
        self.Image3d.ren.AddActor(self.fiber_actor)
        self.Image3d.renWin.Render()

    def loadFiber(self):
        directory_path = "./data"
        file, _ = QFileDialog.getOpenFileName(self, "Open Trk File", directory_path, "Trk(*.trk)")
        if file:
            actor = imri_fiber.getFiberActor(file)
            actor.SetUserMatrix(self.ImageDatas[self.img_index].user_matrix)
            actor.SetPosition(55, 140, 120)
            self.fiber_actor = actor
            self.ui.Fiber3DCheckBox.setCheckState(Qt.Checked)

    def showFiber3D(self):
        if self.ui.Fiber3DCheckBox.isChecked():
            self.Image3d.ren.AddActor(self.fiber_actor)
        else:
            self.Image3d.ren.RemoveActor(self.fiber_actor)
        self.Image3d.renWin.Render()

    # def move_fiber_actor(self, value):

    #     x = self.ui.movefiber_spinBox_x.value()
    #     y = self.ui.movefiber_spinBox_y.value()
    #     z = self.ui.movefiber_spinBox_z.value()
    #     self.fiber_actor.SetPosition(x, y, z)
    #     print(self.fiber_actor.GetPosition())

    #     self.Image3d.renWin.Render()

    def openFile(self):
        directory_path = self.config["main"]["image_directory"]
        files, _ = QFileDialog.getOpenFileNames(self, "Open File(s)", directory_path, "Nii(*.nii.gz)")
        if len(files) > 0:
            self.config["main"]["image_directory"] = os.path.dirname(files[0])
            imri_setting.update_config(config=self.config)
            for file in files:
                if file not in self.files_path:
                    self.img_index += 1
                    self.files_path.append(file)
                    file_name_with_extension = os.path.basename(file)
                    file_name_without_extension = os.path.splitext(file_name_with_extension)[0]
                    item = QListWidgetItem(QIcon("image/nifti_icon.png"), file_name_without_extension)
                    self.ui.ImageListWidget.addItem(item)
                    self.ImageListItems.append(item)
                    data, ori_data = imri_io.readNiftiFile(file)
                    new_data = imri_image_data.ImageData()
                    new_data.initImageData(data, ori_data)
                    self.ImageDatas.append(new_data)
                else:
                    self.img_index = self.files_path.index(file)

            self.ui.ImageListWidget.setCurrentItem(self.ImageListItems[self.img_index])

    def openDicomFile(self):
        directory_path = self.config["main"]["image_directory"]
        directory = QFileDialog.getExistingDirectory(self, "Open Directory", directory_path)
        # print(directory)
        if directory:
            self.config["main"]["image_directory"] = directory
            imri_setting.update_config(config=self.config)
            data, ori_data = imri_io.read_dicom_to_vtk(directory)
            new_data = imri_image_data.ImageData()
            new_data.initImageData(data, ori_data)
            self.ImageDatas.append(new_data)
            self.img_index += 1
            file_name = os.path.basename(directory)
            item = QListWidgetItem(QIcon("image/nifti_icon.png"), file_name)
            self.ui.ImageListWidget.addItem(item)
            self.ImageListItems.append(item)
            self.ui.ImageListWidget.setCurrentItem(self.ImageListItems[-1])

    def showReadImage(self):
        selected_item = self.ui.ImageListWidget.currentItem()
        self.img_index = self.ImageListItems.index(selected_item)
        self.showImage()
        # needle recog tracking
        if self.ui.auto_tracking_btn.text() == "Stop Tracking":
            self.needle_recog.tracking()

    def showImage(self):
        # 2d
        for i in range(3):
            pix_data = self.ImageDatas[self.img_index].initReslice(plane=i)
            self.ImageDatas[self.img_index].gray_scale = self.ImageDatas[self.img_index].getAutoGrayScale()
            self.ImagePlanes.addPixmap(pix_data, self.ImageDatas[self.img_index].gray_scale, self.views, plane=i)
            self.ImagePlanes.updateCrossLine(self.views[i].contentsRect().width(), self.views[i].contentsRect().height(), plane=i)
            self.ImagePlanes.addOrientationText(self.views[i], plane=i)
            self.ImagePlanes.resizeScene(self.views, plane=i)
            self.ImagePlanes.addRuler(self.ImageDatas[self.img_index], self.views[i], plane=i)
            self.ImagePlanes.addInfoText(self.views[i], plane=i)

        # 3d  vtkImageData.cxx:1536   ERR| vtkImageData (0000021FE7FC7F00): GetScalarPointer: Pixel (0, 0, 159) not in memory.
        if self.ui.showSlicerCheckBox.isChecked():
            self.Image3d.removeSlicer()
            self.Image3d.addSlicer(self.ImageDatas[self.img_index], None)
            self.Image3d.renderSlicer(mode=self.ImageDatas[self.img_index].acqMode)
            self.Image3d.resizeScene(self.views)
        else:
            self.Image3d.removeSlicer()

        # 3d volume
        self.showVolume()

        # after add pixmap, set scrollbar. otherwise, 2024-04-28 21:45:49.351 ( 112.383s) [ 684A09503FD42DD]vtkDemandDrivenPipeline:677    ERR| vtkCompositeDataPipeline (00000253F836F670): Input port 0 of algorithm vtkImageReslice (00000253F3999AB0) has 0 connections but is not optional.
        for i in range(3):
            imri_setting.setScrollBar(self.ImageDatas[self.img_index], self.scroll_bars[i], plane=i)

        self.initGraySetting()
        self.ImagePlanes.resizePlanes(self.views, self.ImageDatas[self.img_index])

        # line and point
        self.updateImageInfo()
        self.measure.updateCheckedItem2d()
        self.measure.updateCheckedItem3d()
        self.catheter.updateAllLineAndPoint()
        # self.catheter.updateCatheterSliceRange()
        self.plan.updateCheckedItem2d()
        self.plan.updateCheckedItem3d()
        self.evaluation.updateNeedleTip2d()
        self.evaluation.updateNeedleTip3d()

        # needle tip update
        self.needle_recog.updateNeedleTip()
        if self.needle_recog.box_item != None and self.ui.show_box_checkBox.isChecked():
            self.needle_recog.resizeBox()

        # needle recog
        if self.ui.SetNeedleSliceCheckBox.isChecked():
            value = self.ui.SetNeedleSliceSpinBox.value()
            index = self.ImageDatas[self.img_index].acqMode
            extent = self.ImageDatas[self.img_index].new_extent
            if value < extent[2 * index] or value > extent[2 * index + 1]:
                return None
            else:
                self.scroll_bars[index].setValue(value)

    def openRealTimeFile(self):
        directory_path = self.config["main"]["realtime_directory"]
        self.real_time_file_path = QFileDialog.getExistingDirectory(self, "Open Directory", directory_path)
        print(self.real_time_file_path)
        if self.real_time_file_path:
            self.config["main"]["realtime_directory"] = self.real_time_file_path
            imri_setting.update_config(config=self.config)
            self.ui.RealTimeReadText.clear()
            self.ui.RealTimeReadText.insertPlainText("Current Real Time File Path:\n" + self.real_time_file_path + "\n")
            self.ui.RealTimeReadStartBtn.setEnabled(True)
        else:
            print("No Path Input")

    def setRealTimeRead(self):
        if self.ui.RealTimeReadStartBtn.text() == "Start":
            self.ui.RealTimeReadStartBtn.setText("Stop")
            self.ui.RealTimeReadBtn.setEnabled(False)
            self.ui.RealTimeReadStartBtn.setStyleSheet(self.config["button"]["active"])
            self.FileWatcher.addPath(self.real_time_file_path)
            self.FileWatcher.directoryChanged.connect(self.realTimeRead)
            readed_file = os.path.join(self.real_time_file_path, "readed_file.txt")
            with open(readed_file, "a") as f:
                files = os.listdir(self.real_time_file_path)
                for file in files:
                    if file.endswith(".nii.gz") and not self.isFileReaded(file, readed_file):
                        f.write(file + "\n")
            f.close()
        else:
            self.ui.RealTimeReadStartBtn.setText("Start")
            self.ui.RealTimeReadBtn.setEnabled(True)
            self.ui.RealTimeReadStartBtn.setStyleSheet(self.config["button"]["normal"])
            self.FileWatcher.removePath(self.real_time_file_path)
            self.FileWatcher.directoryChanged.disconnect(self.realTimeRead)

    def isFileReaded(self, file_name, txt_file):
        with open(txt_file, "r") as f:
            lines = f.readlines()
            lines = [line.strip() for line in lines]  # remove "\n"
        f.close()
        return file_name in lines

    def realTimeRead(self):
        readed_file = os.path.join(self.real_time_file_path, "readed_file.txt")
        with open(readed_file, "a") as f:
            files = os.listdir(self.real_time_file_path)
            for file in files:
                if file.endswith(".nii.gz") and not self.isFileReaded(file, readed_file):
                    file_path = os.path.join(self.real_time_file_path, file)
                    if file_path not in self.files_path:
                        self.img_index += 1
                        self.files_path.append(file_path)
                        file_name_with_extension = os.path.basename(file_path)
                        file_name_without_extension = os.path.splitext(file_name_with_extension)[0]
                        item = QListWidgetItem(QIcon("image/nifti_icon.png"), file_name_without_extension)
                        self.ui.ImageListWidget.addItem(item)
                        self.ImageListItems.append(item)
                        data, ori_data = imri_io.readNiftiFile(file_path)
                        new_data = imri_image_data.ImageData()
                        new_data.initImageData(data, ori_data)
                        self.ImageDatas.append(new_data)
                        self.ui.ImageListWidget.setCurrentItem(self.ImageListItems[-1])
                        f.write(file + "\n")
        f.close()

    def initGraySetting(self):
        # init gray scale ui
        [min_gray, max_gray] = self.ImageDatas[self.img_index].getAutoGrayScale()
        wl = (min_gray + max_gray) / 2
        ww = max_gray - min_gray
        [ori_min, ori_max] = self.ImageDatas[self.img_index].getOriginGrayScale()
        imri_setting.setSpinBox(self.ui.GrayMinSpinBox, ori_min, ori_max, min_gray, 1)
        imri_setting.setSpinBox(self.ui.GrayMaxSpinBox, ori_min, ori_max, max_gray, 1)
        imri_setting.setSlider(self.ui.WLSlider, ori_min, ori_max, wl, 1)
        imri_setting.setSlider(self.ui.WWSlider, ori_min, ori_max, ww, 1)
        imri_setting.setSpinBox(self.ui.WLSpinBox, ori_min, ori_max, wl, 1)
        imri_setting.setSpinBox(self.ui.WWSpinBox, ori_min, ori_max, ww, 1)

    def updateImageInfo(self):
        # measure
        self.measure.Image3d = self.Image3d
        self.measure.ImagePlanes = self.ImagePlanes
        if self.ImageDatas != []:
            self.measure.ImageData = self.ImageDatas[self.img_index]
        # catheter
        self.catheter.Image3d = self.Image3d
        self.catheter.ImagePlanes = self.ImagePlanes
        if self.ImageDatas != []:
            self.catheter.ImageData = self.ImageDatas[self.img_index]
        # plan
        self.plan.Image3d = self.Image3d
        self.plan.ImagePlanes = self.ImagePlanes
        if self.ImageDatas != []:
            self.plan.ImageData = self.ImageDatas[self.img_index]
        # zframe
        if self.ImageDatas != []:
            self.zFrame.ImageData = self.ImageDatas[self.img_index]
        # needle_recog
        self.needle_recog.Image3d = self.Image3d
        self.needle_recog.ImagePlanes = self.ImagePlanes
        if self.ImageDatas != []:
            self.needle_recog.ImageData = self.ImageDatas[self.img_index]
        # brain seg
        self.brainSegment.Image3d = self.Image3d
        self.brainSegment.ImagePlanes = self.ImagePlanes
        if self.ImageDatas != []:
            self.brainSegment.ImageData = self.ImageDatas[self.img_index]
        # vessel
        self.vessel.Image3d = self.Image3d
        self.vessel.ImagePlanes = self.ImagePlanes
        if self.ImageDatas != []:
            self.vessel.ImageData = self.ImageDatas[self.img_index]

    def measureInteract(self, obj, event):
        self.measure.Image3d = self.Image3d
        self.measure.ImagePlanes = self.ImagePlanes
        if self.ImageDatas != []:
            self.measure.ImageData = self.ImageDatas[self.img_index]
        # mouse left button press
        if event.type() == QEvent.MouseButtonPress and event.buttons() == Qt.LeftButton and obj in self.views:
            if self.measure.mode == "measureLine1":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                item = self.measure.measure_item
                item.start_pos = [pos.x(), pos.y()]
                _, item.start_pos_vtk = self.ImageDatas[self.img_index].ImageToWorld(item.start_pos, self.ImagePlanes.getPixmapsSize(), plane=self.current_mouse_in_view)
                item.ImageData = self.ImageDatas[self.img_index]
                item.ImagePlanes = self.ImagePlanes
                self.measure.mode = "measureLine2"
            elif self.measure.mode == "measureLine2":
                self.measure.mode = None
            else:
                pass

            if self.measure.mode == "measureAngle1":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                item = self.measure.measure_item
                item.start_pos = [pos.x(), pos.y()]
                _, item.start_pos_vtk = self.ImageDatas[self.img_index].ImageToWorld(item.start_pos, self.ImagePlanes.getPixmapsSize(), plane=self.current_mouse_in_view)
                item.ImageData = self.ImageDatas[self.img_index]
                item.ImagePlanes = self.ImagePlanes
                self.measure.mode = "measureAngle2"
            elif self.measure.mode == "measureAngle2":
                self.measure.mode = "measureAngle3"
            elif self.measure.mode == "measureAngle3":
                self.measure.mode = None
            else:
                pass

        # mouse move
        if event.type() == QEvent.MouseMove and self.current_mouse_in_view != None:
            if self.measure.mode == "measureLine2":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                item = self.measure.measure_item
                item.end_pos = [pos.x(), pos.y()]
                _, item.end_pos_vtk = self.ImageDatas[self.img_index].ImageToWorld(item.end_pos, self.ImagePlanes.getPixmapsSize(), plane=self.current_mouse_in_view)
                item.updateLine2d()
                item.updateline3d()
            else:
                pass

            if self.measure.mode == "measureAngle2":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                item = self.measure.measure_item
                item.mid_pos = [pos.x(), pos.y()]
                _, item.mid_pos_vtk = self.ImageDatas[self.img_index].ImageToWorld(item.mid_pos, self.ImagePlanes.getPixmapsSize(), plane=self.current_mouse_in_view)
                item.updateAngle12d()
                item.updateAngle13d()

            elif self.measure.mode == "measureAngle3":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                item = self.measure.measure_item
                item.end_pos = [pos.x(), pos.y()]
                _, item.end_pos_vtk = self.ImageDatas[self.img_index].ImageToWorld(item.end_pos, self.ImagePlanes.getPixmapsSize(), plane=self.current_mouse_in_view)
                item.updateAngle22d()
                item.updateAngle23d()
            else:
                pass

        # mouse wheel scroll and image slice change
        if event.type() == QEvent.Wheel and obj in self.views:
            try:
                if self.measure.measure_item != None:
                    self.measure.updateCheckedItem2d()
            except:
                pass

        # window resize
        if event.type() == QEvent.WindowStateChange or (obj in self.views and event.type() == QEvent.Resize):
            if self.measure.measure_item != None:
                self.measure.updateCheckedItem2d()

    def catheterInteract(self, obj, event):
        self.catheter.Image3d = self.Image3d
        self.catheter.ImagePlanes = self.ImagePlanes
        if self.ImageDatas != []:
            self.catheter.ImageData = self.ImageDatas[self.img_index]

        if event.type() == QEvent.MouseButtonPress and event.buttons() == Qt.LeftButton and obj in self.views:
            # Area1
            if self.catheter.mode == "ChooseArea1_Start":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                self.catheter.start_pos1 = [pos.x(), pos.y()]
                self.catheter.area_item1 = self.ImagePlanes.scenes[self.current_mouse_in_view].addRect(0, 0, 0, 0, self.catheter.area_pen)
                self.catheter.area_item1.setZValue(1)
                self.catheter.mode = "ChooseArea1_End"
                self.catheter.spinBoxSignalBlock(True)
            elif self.catheter.mode == "ChooseArea1_End":
                self.catheter.mode = None
                self.ui.ChooseArea1Btn.setStyleSheet(self.config["button"]["normal"])
                self.catheter.spinBoxSignalBlock(False)
                self.ui.BoxAreaCheckBox.setDisabled(False)
                self.ui.BoxAreaCheckBox.setCheckState(Qt.Checked)
                self.ui.FinetuneArea1CheckBox.setDisabled(False)
                if self.ui.CatheterModeComboBox.currentText() == "Double Catheter":
                    self.ui.ChooseArea2Btn.setDisabled(False)
                    self.ui.ChooseArea2Btn.setStyleSheet(self.config["button"]["normal"])
            else:
                pass

            # Area2
            if self.catheter.mode == "ChooseArea2_Start":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                self.catheter.start_pos2 = [pos.x(), pos.y()]
                self.catheter.area_item2 = self.ImagePlanes.scenes[self.current_mouse_in_view].addRect(0, 0, 0, 0, self.catheter.area_pen)
                self.catheter.area_item2.setZValue(1)
                self.catheter.mode = "ChooseArea2_End"
                self.catheter.spinBoxSignalBlock(True)
            elif self.catheter.mode == "ChooseArea2_End":
                self.catheter.mode = None
                self.ui.ChooseArea2Btn.setStyleSheet(self.config["button"]["normal"])
                self.catheter.spinBoxSignalBlock(False)
                self.ui.BoxAreaCheckBox.setDisabled(False)
                self.ui.BoxAreaCheckBox.setCheckState(Qt.Checked)
                self.ui.FinetuneArea2CheckBox.setDisabled(False)
                self.ui.ChooseArea1Btn.setDisabled(False)
                self.ui.ChooseArea1Btn.setStyleSheet(self.config["button"]["normal"])

            else:
                pass

        if event.type() == QEvent.MouseMove and self.current_mouse_in_view != None:
            if self.catheter.mode == "ChooseArea1_End":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                self.catheter.end_pos1 = [pos.x(), pos.y()]
                self.catheter.plane = self.current_mouse_in_view
                self.catheter.chooseArea()

            if self.catheter.mode == "ChooseArea2_End":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                self.catheter.end_pos2 = [pos.x(), pos.y()]
                self.catheter.plane = self.current_mouse_in_view
                self.catheter.chooseArea()

        if event.type() == QEvent.Wheel and obj in self.views:
            self.catheter.updateNearestPoint2d()
            self.catheter.updateCatheterLine2d()

        if event.type() == QEvent.WindowStateChange or (obj in self.views and event.type() == QEvent.Resize):
            self.catheter.updateNearestPoint2d()
            self.catheter.updateCatheterLine2d()
            self.catheter.resizeArea()

    def planInteract(self, obj, event):
        self.plan.Image3d = self.Image3d
        self.plan.ImagePlanes = self.ImagePlanes
        if self.ImageDatas != []:
            self.plan.ImageData = self.ImageDatas[self.img_index]

        # mouse left button press and ctrl key press
        if event.type() == QEvent.MouseButtonPress and event.buttons() == Qt.LeftButton and QApplication.keyboardModifiers() == Qt.ControlModifier and obj in self.views:
            if self.plan.mode == "target":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                target_pos = [pos.x(), pos.y()]
                _, target_pos_vtk = self.ImageDatas[self.img_index].ImageToWorld(target_pos, self.ImagePlanes.getPixmapsSize(), plane=self.current_mouse_in_view)
                self.plan.target_vtk_list[self.plan.item_index] = target_pos_vtk
                self.plan.updatePathInfo()
                self.plan.updatePath2d(self.plan.item_index)
                self.plan.updatePath3d(self.plan.item_index)
            elif self.plan.mode == "entry":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                entry_pos = [pos.x(), pos.y()]
                _, entry_pos_vtk = self.ImageDatas[self.img_index].ImageToWorld(entry_pos, self.ImagePlanes.getPixmapsSize(), plane=self.current_mouse_in_view)
                self.plan.entry_vtk_list[self.plan.item_index] = entry_pos_vtk
                self.plan.updatePathInfo()
                self.plan.updatePath2d(self.plan.item_index)
                self.plan.updatePath3d(self.plan.item_index)
            else:
                pass

        # mouse wheel scroll and image slice change
        if event.type() == QEvent.Wheel and obj in self.views:
            self.plan.updateCheckedItem2d()

        # window resize
        if event.type() == QEvent.WindowStateChange or (obj in self.views and event.type() == QEvent.Resize):
            self.plan.updateCheckedItem2d()

    def zFrameInteract(self, obj, event):
        if self.ImageDatas != []:
            self.zFrame.ImageData = self.ImageDatas[self.img_index]

    def needleRecogInteract(self, obj, event):
        if self.ImageDatas != []:
            self.needle_recog.ImageData = self.ImageDatas[self.img_index]

        if event.type() == QEvent.MouseButtonPress and event.buttons() == Qt.LeftButton and obj in self.views:
            if self.needle_recog.mode == "choose_box1":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                self.needle_recog.box = [pos.x(), pos.y(), 0, 0]
                self.needle_recog.box_item = self.ImagePlanes.scenes[self.current_mouse_in_view].addRect(0, 0, 0, 0, self.needle_recog.box_pen)
                self.needle_recog.box_item.setZValue(1)
                self.needle_recog.mode = "choose_box2"
            elif self.needle_recog.mode == "choose_box2":
                self.needle_recog.mode = None
                self.ui.choose_box_btn.setStyleSheet(self.config["button"]["normal"])
            else:
                pass

        if event.type() == QEvent.MouseMove and self.current_mouse_in_view != None:
            if self.needle_recog.mode == "choose_box2":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                self.needle_recog.box[2] = pos.x()
                self.needle_recog.box[3] = pos.y()
                self.needle_recog.plane = self.current_mouse_in_view
                self.needle_recog.chooseBox()

        if event.type() == QEvent.WindowStateChange or (obj in self.views and event.type() == QEvent.Resize):
            if self.needle_recog.box_item != None:
                self.needle_recog.resizeBox()

    def evaluationInteract(self, obj, event):
        if self.ImageDatas != []:
            self.evaluation.ImageData = self.ImageDatas[self.img_index]

        if event.type() == QEvent.MouseButtonPress and event.buttons() == Qt.LeftButton and QApplication.keyboardModifiers() == Qt.ControlModifier and obj in self.views:
            if self.evaluation.mode == "needle_tip":
                pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                # needle_tip_pos = [pos.x() - 3, pos.y() - 3]
                needle_tip_pos = [pos.x(), pos.y()]
                _, needle_tip_pos_vtk = self.ImageDatas[self.img_index].ImageToWorld(needle_tip_pos, self.ImagePlanes.getPixmapsSize(), plane=self.current_mouse_in_view)
                self.evaluation.needle_tip_pos_vtk = needle_tip_pos_vtk
                self.ui.tip_x_lineEdit.setText(str(round(needle_tip_pos_vtk[0], 1)))
                self.ui.tip_y_lineEdit.setText(str(round(needle_tip_pos_vtk[1], 1)))
                self.ui.tip_z_lineEdit.setText(str(round(needle_tip_pos_vtk[2], 1)))
                self.ui.show_seleted_tip_checkBox.setChecked(True)
                self.evaluation.updateNeedleTip2d()
                self.evaluation.updateNeedleTip3d()
                self.evaluation.updateError()

            else:
                pass

        # mouse wheel scroll and image slice change
        if event.type() == QEvent.Wheel and obj in self.views:
            if self.ui.show_seleted_tip_checkBox.isChecked():
                self.evaluation.updateNeedleTip2d()

        # window resize
        if event.type() == QEvent.WindowStateChange or (obj in self.views and event.type() == QEvent.Resize):
            if self.ui.show_seleted_tip_checkBox.isChecked():
                self.evaluation.updateNeedleTip2d()

    def eventFilter(self, obj, event):
        # Indicates the current mouse position in the widget.
        # 0 - Sagittal, 1 - Coronal, 2 - Axial
        if event.type() == QEvent.KeyPress:
            if self.ui.ImageListWidget.count() > 0:
                if event.key() == Qt.Key_Up:
                    current_item = self.ui.ImageListWidget.currentItem()
                    current_row = self.ui.ImageListWidget.row(current_item)
                    if current_row > 0:
                        self.ui.ImageListWidget.setCurrentRow(current_row - 1)
                if event.key() == Qt.Key_Down:
                    current_item = self.ui.ImageListWidget.currentItem()
                    current_row = self.ui.ImageListWidget.row(current_item)
                    if current_row < self.ui.ImageListWidget.count() - 1:
                        self.ui.ImageListWidget.setCurrentRow(current_row + 1)

        if event.type() == QEvent.Enter:
            if obj in self.views:
                self.current_mouse_in_view = self.views.index(obj)

        if event.type() == QEvent.Leave:
            if obj in self.views:
                self.current_mouse_in_view = None

        if event.type() == QEvent.WindowStateChange or (obj in self.views and event.type() == QEvent.Resize):
            if self.img_index >= 0:
                self.ImagePlanes.resizePlanes(self.views, self.ImageDatas[self.img_index])
                self.Image3d.resizeScene(self.views)

        if event.type() == QEvent.Wheel:
            try:
                self.views[self.current_mouse_in_view].verticalScrollBar().setRange(0, 0)  # disable view scroll bar
                if obj in self.views and self.img_index >= 0:
                    # if self.img_index >= 0:
                    current_value = self.scroll_bars[self.current_mouse_in_view].value()
                    new_value = int(current_value + event.angleDelta().y() / 120)  # The scroll wheel increments by 120 or -120 with each scroll
                    self.scroll_bars[self.current_mouse_in_view].setValue(new_value)
            except:
                pass
        if event.type() == QEvent.MouseMove and self.current_mouse_in_view != None:
            # show the voxel and world position of the cursor
            if self.img_index >= 0:
                scene_pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                voxel_units, world_units = self.ImageDatas[self.img_index].ImageToWorld([scene_pos.x(), scene_pos.y()], self.ImagePlanes.getPixmapsSize(), plane=self.current_mouse_in_view)
                gray_value = self.ImagePlanes.getGrayValue([scene_pos.x(), scene_pos.y()], self.current_mouse_in_view)
                self.ui.VoxelPosL.setText(str(voxel_units[0]))
                self.ui.VoxelPosP.setText(str(voxel_units[1]))
                self.ui.VoxelPosS.setText(str(voxel_units[2]))
                self.ui.WorldPosL.setText(str(world_units[0]))
                self.ui.WorldPosP.setText(str(world_units[1]))
                self.ui.WorldPosS.setText(str(world_units[2]))
                self.ui.CursorPosGray.setText(str(gray_value))
                self.ui.statusBar.showMessage(
                    f"VoxelPos:({voxel_units[0]}, {voxel_units[1]}, {voxel_units[2]}), \
                    WorldPos:({world_units[0]}, {world_units[1]}, {world_units[2]}), \
                    Gray Value:{gray_value},\
                    scene_pos:({scene_pos.x()}, {scene_pos.y()}),"
                )

            # image rescale
            if self.img_index >= 0 and self.middle_mouse_press:
                delta_x = self.lastPos.x() - event.pos().x()
                delta_y = self.lastPos.y() - event.pos().y()
                self.lastPos = event.pos()
                self.views[self.current_mouse_in_view].translate(-delta_x / 4, -delta_y / 4)
                self.ImagePlanes.resizeOrientationText(self.views[self.current_mouse_in_view], plane=self.current_mouse_in_view)
                self.ImagePlanes.resizeRuler(self.ImageDatas[self.img_index], self.views[self.current_mouse_in_view], plane=self.current_mouse_in_view)
                self.ImagePlanes.resizeInfoText(self.views[self.current_mouse_in_view], plane=self.current_mouse_in_view)

            if self.img_index >= 0 and self.right_mouse_press:
                delta = self.lastPos.y() - event.pos().y()
                self.lastPos = event.pos()
                if self.views[self.current_mouse_in_view].transform().m11() > 25 and delta > 0:
                    scale_factor = 1.0
                elif self.views[self.current_mouse_in_view].transform().m11() < 0.5 and delta < 0:
                    scale_factor = 1.0
                else:
                    scale_factor = 1.0 + delta / 100
                self.views[self.current_mouse_in_view].scale(scale_factor, scale_factor)
                self.ImagePlanes.resizeOrientationText(self.views[self.current_mouse_in_view], plane=self.current_mouse_in_view)
                self.ImagePlanes.resizeRuler(self.ImageDatas[self.img_index], self.views[self.current_mouse_in_view], plane=self.current_mouse_in_view)
                self.ImagePlanes.resizeInfoText(self.views[self.current_mouse_in_view], plane=self.current_mouse_in_view)

        if event.type() == QEvent.MouseButtonPress and event.buttons() == Qt.LeftButton:
            if obj in self.views:  # 保证只有在graphicsView中按下鼠标才会触发，在graphicsView.viewport中按下鼠标后不会触发
                self.left_mouse_press = True
                self.lastPos = event.pos()
                # cross line
                if self.show_cross_line == True and self.img_index >= 0:
                    scene_pos = self.views[self.current_mouse_in_view].mapToScene(event.pos())
                    voxel_units, world_units = self.ImageDatas[self.img_index].ImageToWorld([scene_pos.x(), scene_pos.y()], self.ImagePlanes.getPixmapsSize(), plane=self.current_mouse_in_view)
                    for i in range(3):
                        image_pos, z = self.ImageDatas[self.img_index].WorldToImage(world_units, self.ImagePlanes.getPixmapsSize(), plane=i)
                        self.ImagePlanes.setCrossLine(self.views[i].contentsRect().width(), self.views[i].contentsRect().height(), image_pos, i)
                        if i != self.current_mouse_in_view:
                            self.scroll_bars[i].setValue(np.round(z).astype(int))

        if event.type() == QEvent.MouseButtonPress and event.buttons() == Qt.RightButton:
            if obj in self.views:
                self.right_mouse_press = True
                self.lastPos = event.pos()

        if event.type() == QEvent.MouseButtonPress and event.buttons() == Qt.MiddleButton:
            if obj in self.views:
                self.middle_mouse_press = True
                self.lastPos = event.pos()

        if event.type() == QEvent.MouseButtonRelease:
            # if obj in self.views: not needed
            if event.button() == Qt.LeftButton:
                self.left_mouse_press = False
            if event.button() == Qt.RightButton:
                self.right_mouse_press = False
            if event.button() == Qt.MiddleButton:
                self.middle_mouse_press = False

        self.measureInteract(obj, event)
        self.catheterInteract(obj, event)
        self.planInteract(obj, event)
        self.zFrameInteract(obj, event)
        self.needleRecogInteract(obj, event)
        self.evaluationInteract(obj, event)

        return super().eventFilter(obj, event)

    def connectRobot(self):
        robot_ip = self.config["main"]["robot_ip"]
        robot_port = self.config["main"]["robot_port"]

        inputDialog = QInputDialog()
        inputDialog.setFixedSize(1000, 800)
        inputDialog.setWindowTitle("Connect Robot")
        inputDialog.setLabelText("Robot IP:")
        inputDialog.setTextValue(robot_ip)
        inputDialog.setOkButtonText("Connect")
        inputDialog.setCancelButtonText("Ok")
        while inputDialog.exec_():
            robot_ip = inputDialog.textValue()
            self.config["main"]["robot_ip"] = robot_ip
            imri_setting.update_config(config=self.config)
            test_info = "Connect robot test"
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_address = (robot_ip, robot_port)
                sock.connect(server_address)
                sock.sendall(test_info.encode())
                sock.close()
                QMessageBox.information(self, "Information", "Connect robot success!")
            except:
                QMessageBox.warning(self, "Warning", "Connect robot failed!")
                continue

    def aboutIMRISN(self):
        QMessageBox.about(
            self,
            "About IMRI_SN",
            "IMRI_SN is a software for image processing and navigation in interventional MRI.",
        )

    def exit(self):
        self.close()

    def processChanges(self):
        for _ in range(10):
            QApplication.processEvents()
            time.sleep(0.1)

    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)
        self.Image3d.widget.Finalize()  # important if not vtkWin32OpenGLRenderWin:217    ERR


if __name__ == "__main__":
    # QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    font = QFont("宋体")
    pointsize = font.pointSize()
    font.setPixelSize(int(pointsize * 1.5))
    app.setFont(font)
    splash_pix = QPixmap("image/start_logo.png")
    splash_pix = splash_pix.scaled(800, 600, aspectRatioMode=Qt.KeepAspectRatio)
    splash = QSplashScreen(splash_pix)
    splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.show()

    win = MainWindow()
    win.setWindowTitle("IMRI_SN")
    # setup stylesheet
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    # or in new API
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyqt5"))
    splash.finish(win)
    win.show()
    sys.exit(app.exec_())
