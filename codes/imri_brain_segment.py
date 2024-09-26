from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import imri_setting
import numpy as np
import vtkmodules.all as vtk
import SimpleITK as sitk
import os
import imri_io
import imri_image_data
from functools import partial


class BrainSegment(QMainWindow):
    def __init__(self, parent=None):
        super(BrainSegment, self).__init__(parent)
        self.brain_segment_path = None
        self.color_table = []  #
        self.config = imri_setting.read_config()
        self.BrainSegMaskData = None
        self.BrainSegVolumes = []
        self.ImageData = None  # T1/T2 image
        self.BrainSeg_PiecewiseFuncs = []
        self.BrainSeg_ColorTransferFuncs = []
        self.volume_color = [[0, 0, 0], [1, 0, 1], [0, 1, 1], [1, 0, 0], [0, 0, 1], [1, 0, 0]]

    def init(self, ui, Image3d, ImagePlanes, views):
        self.ui = ui
        self.Image3d = Image3d
        self.ImagePlanes = ImagePlanes
        self.views = views
        self.initColorTable()

        self.ui.BrainSegBtn.clicked.connect(self.brainSegment)
        self.ui.LoadBrainSegFileBtn.clicked.connect(self.loadSegmentImage)
        self.ui.SaveBrainSegFileBtn.clicked.connect(self.saveSegmentImage)

        self.color_btns = [self.ui.Label1ColorBtn, self.ui.Label2ColorBtn, self.ui.Label3ColorBtn, self.ui.Label4ColorBtn, self.ui.Label5ColorBtn]
        self.sliders = [self.ui.Label1Slider, self.ui.Label2Slider, self.ui.Label3Slider, self.ui.Label4Slider, self.ui.Label5Slider]
        self.checkBoxs = [self.ui.Label1checkBox, self.ui.Label2checkBox, self.ui.Label3checkBox, self.ui.Label4checkBox, self.ui.Label5checkBox]

        icon = QIcon("image/color_dialog.png")
        for btn in self.color_btns:
            btn.setIcon(icon)
            btn.clicked.connect(partial(self.setLabelColor, self.color_btns.index(btn) + 1))
            btn.setEnabled(False)

        for slider in self.sliders:
            slider.setValue(50)
            slider.setRange(0, 100)
            slider.setSingleStep(1)
            slider.valueChanged.connect(partial(self.setLabelOpacity, self.sliders.index(slider) + 1))
            slider.setEnabled(False)

        for checkBox in self.checkBoxs:
            checkBox.setCheckState(Qt.Checked)
            checkBox.stateChanged.connect(partial(self.setLabelVisible, self.checkBoxs.index(checkBox) + 1))
            checkBox.setEnabled(False)

        self.ui.BrainSeg3DViewcheckBox.stateChanged.connect(self.updateBrainSegment3d)
        self.ui.BrainSeg2DViewcheckBox.stateChanged.connect(self.updateBrainSegment2d)

        for i in range(5):
            PiecewiseFunc = vtk.vtkPiecewiseFunction()
            PiecewiseFunc.AddPoint(0, 0.00)
            PiecewiseFunc.AddPoint(200, 0.3)
            self.BrainSeg_PiecewiseFuncs.append(PiecewiseFunc)

            color_func = vtk.vtkColorTransferFunction()
            color_func.AddRGBPoint(200, self.volume_color[i + 1][0], self.volume_color[i + 1][1], self.volume_color[i + 1][2])
            self.BrainSeg_ColorTransferFuncs.append(color_func)

    def initColorTable(self):
        color_table = []
        for i in range(256):
            if 1 <= i < 6:
                color = QColor(self.volume_color[i][0] * 255, self.volume_color[i][1] * 255, self.volume_color[i][2] * 255, 128)
            # 0 Background 1 GM 2 Subcortical GM 3 WM 4 CSF 5 Pathological Tissue
            else:
                color = QColor(0, 0, 0, 0)
            color_table.append(color.rgba())
        self.color_table = color_table

    def setLabelColor(self, value):
        color = QColorDialog.getColor()
        if color.isValid():
            # 2d
            color.setAlpha(int(self.sliders[value - 1].value() / 100 * 255))
            self.color_table[value] = color.rgba()

            # 3d
            color_func = vtk.vtkColorTransferFunction()
            self.volume_color[value] = [color.red() / 255, color.green() / 255, color.blue() / 255]
            color_func.AddRGBPoint(200, self.volume_color[value][0], self.volume_color[value][1], self.volume_color[value][2])
            self.BrainSeg_ColorTransferFuncs[value - 1] = color_func

        self.updateBrainSegment2d()
        self.updateBrainSegment3d()

    def setLabelOpacity(self, value):
        # 2d
        color = QColor(self.volume_color[value][0] * 255, self.volume_color[value][1] * 255, self.volume_color[value][2] * 255)
        alpha = int(self.sliders[value - 1].value() / 100 * 255)
        color.setAlpha(alpha)
        self.color_table[value] = color.rgba()

        # 3d
        PiecewiseFunc = vtk.vtkPiecewiseFunction()
        PiecewiseFunc.AddPoint(0, 0.00)
        PiecewiseFunc.AddPoint(200, alpha / 255)
        self.BrainSeg_PiecewiseFuncs[value - 1] = PiecewiseFunc

        self.updateBrainSegment2d()
        self.updateBrainSegment3d()

    def setLabelVisible(self, value):
        if self.checkBoxs[value - 1].isChecked():
            # 2d
            color = QColor(self.volume_color[value][0] * 255, self.volume_color[value][1] * 255, self.volume_color[value][2] * 255)
            alpha = int(self.sliders[value - 1].value() / 100 * 255)
            color.setAlpha(alpha)
            self.color_table[value] = color.rgba()

            # 3d
            PiecewiseFunc = vtk.vtkPiecewiseFunction()
            PiecewiseFunc.AddPoint(0, 0.00)
            PiecewiseFunc.AddPoint(200, alpha / 255)
            self.BrainSeg_PiecewiseFuncs[value - 1] = PiecewiseFunc

            self.color_btns[value - 1].setEnabled(True)
            self.sliders[value - 1].setEnabled(True)

        else:
            # 2d
            color = QColor(0, 0, 0, 0)
            self.color_table[value] = color.rgba()

            # 3d
            PiecewiseFunc = vtk.vtkPiecewiseFunction()
            PiecewiseFunc.AddPoint(0, 0.00)
            PiecewiseFunc.AddPoint(200, 0.00)
            self.BrainSeg_PiecewiseFuncs[value - 1] = PiecewiseFunc
            print("setLabelVisible", value - 1)

            self.color_btns[value - 1].setEnabled(False)
            self.sliders[value - 1].setEnabled(False)

        self.updateBrainSegment2d()
        self.updateBrainSegment3d()

    def brainSegment(self):
        """
        TODO segment algorithm
        INPUT T1/T2 image
        OUTPUT brain segment image
        """
        pass

    def getMaskFrom5ttImage(self, FivettImage_path, t1_path):
        FivettImage = sitk.ReadImage(FivettImage_path)
        Fivett_array = sitk.GetArrayFromImage(FivettImage)
        # 1 灰质(Grey Matter, GM)
        # 2 皮质下灰质（如杏仁核和基底神经节）(Subcortical Grey Matter,such as amygdala and basal ganglia)
        # 3 白质(White Matter, WM)
        # 4 脑脊液(Cerebrospinal Fluid, CSF)
        # 5 病理组织(Pathological Tissue)
        threshold = 0.5
        img_label = np.zeros_like(Fivett_array[0, :, :, :])
        for i in range(5):
            img = Fivett_array[i, :, :, :]
            img[img < threshold] = 0
            img[img >= threshold] = i + 1
            img_label += img

        mask_label_image = sitk.GetImageFromArray(img_label)

        t1_img = sitk.ReadImage(t1_path)
        mask_label_image.SetOrigin(t1_img.GetOrigin())
        mask_label_image.SetSpacing(t1_img.GetSpacing())
        mask_label_image.SetDirection(t1_img.GetDirection())
        # sitk.WriteImage(mask_label_image, r"D:\Code\test_data\test_t1_reg\5tt_label.nii.gz")
        return mask_label_image

    def loadSegmentImage(self):
        directory_path = self.config["brain_segment"]["image_directory"]
        file, _ = QFileDialog.getOpenFileName(self, "Open Brain Segment File", directory_path, "Nii(*.nii.gz)")
        if file:
            self.config["brain_segment"]["image_directory"] = os.path.dirname(file)
            imri_setting.update_config(config=self.config)
            self.brain_segment_path = file

            if self.BrainSegMaskData is not None:
                self.ui.BrainSeg2DViewcheckBox.setCheckState(Qt.Unchecked)
                self.ui.BrainSeg3DViewcheckBox.setCheckState(Qt.Unchecked)

            self.showBrainSegment(file)

    def showBrainSegment(self, path):
        data, ori_data = imri_io.readNiftiFile(path)
        self.BrainSegMaskData = imri_image_data.ImageData()
        self.BrainSegMaskData.initImageData(data, ori_data)

        self.initBrainSegment3d()
        self.ui.BrainSeg3DViewcheckBox.setCheckState(Qt.Checked)
        self.ui.BrainSeg2DViewcheckBox.setCheckState(Qt.Checked)

        for btn in self.color_btns:
            btn.setEnabled(True)
        for slider in self.sliders:
            slider.setEnabled(True)
        for checkBox in self.checkBoxs:
            checkBox.setEnabled(True)

    def saveSegmentImage(self):
        directory_path = self.config["brain_segment"]["image_directory"]
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Brain Segmentation File", directory_path, "NII(*.nii.gz)")
        if file_path != "":
            self.config["brain_segment"]["image_directory"] = os.path.dirname(file_path)
            imri_setting.update_config(config=self.config)
            imri_io.save_vtk_to_nii(self.BrainSegMaskData.data, file_path)

    def updateBrainSegment2d(self):
        if self.ui.BrainSeg2DViewcheckBox.isChecked():
            if self.ImageData.mode == "T1Image" or self.ImageData.mode == "T2Image":
                color_table = self.color_table
                try:
                    for i in range(3):
                        self.BrainSegMaskData.initReslice(plane=i)
                    self.BrainSegMaskData.current_slice = self.ImageData.current_slice
                    for i in range(3):
                        pix_data, _ = self.BrainSegMaskData.getCurrentReslice(plane=i)
                        self.ImagePlanes.addMaskPixmap(pix_data, self.views, mode="BrainSeg", color_table=color_table, plane=i)
                except:
                    print("Mask Slice maybe out of range")
                    for i in range(3):
                        pix_data = self.BrainSegMaskData.initReslice(plane=i)
                        self.ImagePlanes.addMaskPixmap(pix_data, self.views, mode="BrainSeg", color_table=color_table, plane=i)
            else:
                print("Please load fixed image first")
                meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Please load T1/T2 image first!")
                meg_box.exec_()
        else:
            for i in range(3):
                self.ImagePlanes.removePlaneItem(item=self.ImagePlanes.brain_seg_mask_pixmap_items[i], plane=i)

    def updateBrainSegment3d(self):
        if self.ui.BrainSeg3DViewcheckBox.isChecked():
            if self.BrainSegVolumes == []:
                self.initBrainSegment3d()

            for i in range(5):
                self.Image3d.updateVolume(self.BrainSegVolumes[i], self.BrainSeg_PiecewiseFuncs[i], self.BrainSeg_ColorTransferFuncs[i])
        else:
            self.removeBrainSegment3d()

    def initBrainSegment3d(self):
        vtkImgDatas = self.getDatasFrom5Mask()
        self.BrainSegVolumes = []
        for i in range(5):
            volume = self.Image3d.initVolume(vtkImgDatas[i], mode="BrainSeg")
            self.BrainSegVolumes.append(volume)
            self.Image3d.updateVolume(self.BrainSegVolumes[i], self.BrainSeg_PiecewiseFuncs[i], self.BrainSeg_ColorTransferFuncs[i])

    def removeBrainSegment3d(self):
        for i in range(5):
            self.Image3d.removeVolume(self.BrainSegVolumes[i])
        self.BrainSegVolumes = []

    def getDatasFrom5Mask(self):
        array = imri_setting.VTKImageDataToArray(self.BrainSegMaskData.data)
        vtkImgDatas = []
        for i in range(1, 6):
            array_tmp = array.copy()
            array_tmp = np.where(array_tmp == i, 255, 0)
            vtkImgDatas.append(
                imri_setting.ArrayToVTKImageData(
                    array_tmp, self.BrainSegMaskData.dimension, self.BrainSegMaskData.spacing, self.BrainSegMaskData.origin, self.BrainSegMaskData.data.GetDirectionMatrix()
                )
            )
        return vtkImgDatas
