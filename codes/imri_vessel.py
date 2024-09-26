from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import imri_setting
import numpy as np
import vtkmodules.all as vtk
import itk
import os
import imri_io
import imri_image_data
import time


class Vessel(QMainWindow):
    def __init__(self, parent=None):
        super(Vessel, self).__init__(parent)
        self.color_table = []
        self.config = imri_setting.read_config()
        self.vesselMaskData = None
        self.vesselVolume = None
        self.ImageData = None  # T1/T2/MRA image data
        self.Vessel_PiecewiseFunc = None
        self.Vessel_ColorTransferFunc = None
        self.volume_color = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]  # background color and vessel color

    def init(self, ui, Image3d, ImagePlanes, views):
        self.ui = ui
        self.Image3d = Image3d
        self.ImagePlanes = ImagePlanes
        self.views = views
        self.initColorTable()

        self.ui.VesselSegBtn.clicked.connect(self.vesselSegment)
        self.ui.LoadVesselSegFileBtn.clicked.connect(self.LoadVesselSegFile)
        self.ui.SaveVesselSegFileBtn.clicked.connect(self.SaveVesselSegFile)

        icon = QIcon("image/color_dialog.png")
        self.ui.VesselColorBtn.setIcon(icon)
        self.ui.VesselColorBtn.clicked.connect(self.setVesselColor)
        self.ui.VesselColorBtn.setEnabled(False)

        self.ui.VesselOpacitySlider.setValue(50)
        self.ui.VesselOpacitySlider.setRange(0, 100)
        self.ui.VesselOpacitySlider.setSingleStep(1)
        self.ui.VesselOpacitySlider.valueChanged.connect(self.setVesselOpacity)
        self.ui.VesselOpacitySlider.setEnabled(False)

        self.ui.Vessel2DCheckBox.stateChanged.connect(self.updateVessel2d)
        self.ui.Vessel3DCheckBox.stateChanged.connect(self.updateVessel3d)

        self.Vessel_PiecewiseFunc = vtk.vtkPiecewiseFunction()
        self.Vessel_PiecewiseFunc.AddPoint(0, 0.0)
        self.Vessel_PiecewiseFunc.AddPoint(100, 0.5)
        self.Vessel_ColorTransferFunc = vtk.vtkColorTransferFunction()
        self.Vessel_ColorTransferFunc.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
        self.Vessel_ColorTransferFunc.AddRGBPoint(200.0, 1.0, 0.0, 0.0)

    def initColorTable(self):
        color_table = []
        for i in range(256):
            if i == 255:
                color = QColor(255, 0, 0, 128)
            else:
                color = QColor(0, 0, 0, 0)
            color_table.append(color.rgba())
        self.color_table = color_table

    def setVesselColor(self):
        color = QColorDialog.getColor()
        if color.isValid():
            # 2d
            color.setAlpha(int(self.ui.VesselOpacitySlider.value() / 100 * 255))
            self.color_table[255] = color.rgba()
            # 3d
            color_func = vtk.vtkColorTransferFunction()
            self.volume_color[1] = [color.red() / 255, color.green() / 255, color.blue() / 255]
            color_func.AddRGBPoint(0.0, self.volume_color[0][0], self.volume_color[0][1], self.volume_color[0][2])
            color_func.AddRGBPoint(200, self.volume_color[1][0], self.volume_color[1][1], self.volume_color[1][2])
            self.Vessel_ColorTransferFunc = color_func

        self.updateVessel2d()
        self.updateVessel3d()

    def setVesselOpacity(self):
        # 2d
        color = QColor(self.volume_color[1][0] * 255, self.volume_color[1][1] * 255, self.volume_color[1][2] * 255)
        color.setAlpha(int(self.ui.VesselOpacitySlider.value() / 100 * 255))
        self.color_table[255] = color.rgba()

        # 3d
        PiecewiseFunc = vtk.vtkPiecewiseFunction()
        PiecewiseFunc.AddPoint(50, 0.0)
        PiecewiseFunc.AddPoint(100, self.ui.VesselOpacitySlider.value() / 100)
        self.Vessel_PiecewiseFunc = PiecewiseFunc

        self.updateVessel2d()
        self.updateVessel3d()

    def vesselSegment(self):
        try:
            self.progress_dialog = QProgressDialog("Processing...", "Cancel", 0, 5, self)
            self.progress_dialog.setWindowModality(Qt.ApplicationModal)
            self.progress_dialog.setWindowTitle("Vessel Segmentation")
            self.progress_dialog.setAutoClose(True)
            self.progress_dialog.setCancelButton(None)  # 禁用取消按钮
            self.progress_dialog.setMinimumSize(800, 200)
            self.progress_dialog.setModal(False)
            self.progress_dialog.setValue(50)
            self.progress_dialog.setMinimumDuration(0.1)
            self.progress_dialog.show()
            QApplication.processEvents()

            start = time.time()

            path = self.ui.MRAFileLineEdit.text()
            input_image = itk.imread(path)
            print("MRA Path: ", path)
            print("Step 1: vessel image enhancement by the ITK-Hessian matrix.")
            self.progress_dialog.setLabelText("Step 1: vessel image enhancement by the ITK-Hessian matrix.")
            self.progress_dialog.setValue(2)
            ImageType = type(input_image)
            Dimension = input_image.GetImageDimension()
            HessianPixelType = itk.SymmetricSecondRankTensor[itk.D, Dimension]
            HessianImageType = itk.Image[HessianPixelType, Dimension]
            objectness_filter = itk.HessianToObjectnessMeasureImageFilter[HessianImageType, ImageType].New()
            objectness_filter.SetBrightObject(True)
            objectness_filter.SetScaleObjectnessMeasure(True)
            objectness_filter.SetAlpha(0.5)
            objectness_filter.SetBeta(1.0)
            objectness_filter.SetGamma(5.0)
            multi_scale_filter = itk.MultiScaleHessianBasedMeasureImageFilter[ImageType, HessianImageType, ImageType].New()
            multi_scale_filter.SetInput(input_image)
            multi_scale_filter.SetHessianToMeasureFilter(objectness_filter)
            multi_scale_filter.SetSigmaStepMethodToLogarithmic()
            multi_scale_filter.SetSigmaMinimum(0.2)
            multi_scale_filter.SetSigmaMaximum(3.0)
            multi_scale_filter.SetNumberOfSigmaSteps(8)
            # file_name_with_extension = os.path.basename(path)
            # file_name = os.path.splitext(file_name_with_extension)[0]
            # output_name = "middle_" + file_name + ".gz"
            # new_path = os.path.join(os.path.split(path)[0], output_name)
            # itk.imwrite(multi_scale_filter.GetOutput(), new_path)
            # print("Middle file: ", new_path)
            self.progress_dialog.setLabelText("Step 2: vessel normalization to the 0-255 range and threshold segmentation.")
            self.progress_dialog.setValue(3)
            print("Step 2: vessel normalization to the 0-255 range and threshold segmentation.")
            OutputPixelType = itk.UC
            OutputImageType = itk.Image[OutputPixelType, Dimension]
            rescale_filter = itk.RescaleIntensityImageFilter[ImageType, OutputImageType].New()
            rescale_filter.SetInput(multi_scale_filter)
            thresholdFilter = itk.BinaryThresholdImageFilter[OutputImageType, OutputImageType].New()
            thresholdFilter.SetInput(rescale_filter.GetOutput())
            thresholdFilter.SetLowerThreshold(35)
            thresholdFilter.SetUpperThreshold(255)
            thresholdFilter.SetOutsideValue(0)
            thresholdFilter.SetInsideValue(255)
            self.progress_dialog.setLabelText("Step 3: Save Segmented File.")
            self.progress_dialog.setValue(4)
            file_name_with_extension = os.path.basename(path)
            file_name = os.path.splitext(file_name_with_extension)[0]
            output_name = "vesselSeg_" + file_name + ".gz"
            self.output_path = os.path.join(os.path.split(path)[0], output_name)
            itk.imwrite(thresholdFilter.GetOutput(), self.output_path)
            end = time.time()
            print("Output file: ", self.output_path)
            print("Time: ", end - start)
            self.ShowVesselSegFile(self.output_path)
            self.progress_dialog.setLabelText("Vessel Segmentation Finished!")
            self.progress_dialog.setValue(5)
            self.progress_dialog.close()
            self.ui.statusBar.showMessage("Vessel Segmentation Finished! Time: " + str(end - start) + "s")
        except:
            print("Vessel Segmentation Error!")
            meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Vessel Segmentation Error!")
            meg_box.exec_()

    def LoadVesselSegFile(self):
        directory_path = self.config["vessel"]["image_directory"]
        file, _ = QFileDialog.getOpenFileName(self, "Open Vessel Segment File", directory_path, "Nii(*.nii.gz)")
        if file:
            self.config["vessel"]["image_directory"] = os.path.dirname(file)
            imri_setting.update_config(config=self.config)
            if self.vesselMaskData is not None:
                self.ui.Vessel2DCheckBox.setCheckState(Qt.Unchecked)
                self.ui.Vessel3DCheckBox.setCheckState(Qt.Unchecked)

            self.ShowVesselSegFile(file)

    def ShowVesselSegFile(self, path):
        data, ori_data = imri_io.readNiftiFile(path)
        self.vesselMaskData = imri_image_data.ImageData()
        self.vesselMaskData.initImageData(data, ori_data)

        self.initVessel3d()
        self.ui.Vessel2DCheckBox.setCheckState(Qt.Checked)
        self.ui.Vessel3DCheckBox.setCheckState(Qt.Checked)

        self.ui.VesselColorBtn.setEnabled(True)
        self.ui.VesselOpacitySlider.setEnabled(True)

    def SaveVesselSegFile(self):
        directory_path = self.config["vessel"]["image_directory"]
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Vessel File", directory_path, "NII(*.nii.gz)")
        if file_path != "":
            self.config["vessel"]["image_directory"] = os.path.dirname(file_path)
            imri_setting.update_config(config=self.config)
            imri_io.save_vtk_to_nii(self.vesselMaskData.data, file_path)

    def updateVessel2d(self):
        if self.ui.Vessel2DCheckBox.isChecked():
            if self.ImageData.mode == "T1Image" or self.ImageData.mode == "T2Image" or self.ImageData.mode == "MRAImage":
                color_table = self.color_table
                try:
                    for i in range(3):
                        self.vesselMaskData.initReslice(plane=i)
                    self.vesselMaskData.current_slice = self.ImageData.current_slice
                    for i in range(3):
                        pix_data, _ = self.vesselMaskData.getCurrentReslice(plane=i)
                        self.ImagePlanes.addMaskPixmap(pix_data, self.views, mode="Vessel", color_table=color_table, plane=i)
                except:
                    print("Mask Slice maybe out of range")
                    for i in range(3):
                        pix_data = self.vesselMaskData.initReslice(plane=i)
                        self.ImagePlanes.addMaskPixmap(pix_data, self.views, mode="Vessel", color_table=color_table, plane=i)
            else:
                print("Please load T1/T2/MRA image first!")
                meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Please load T1/T2?MRA image first!")
                meg_box.exec_()
        else:
            self.removeVessel2d()

    def removeVessel2d(self):
        for i in range(3):
            self.ImagePlanes.removePlaneItem(item=self.ImagePlanes.vessel_pixmap_items[i], plane=i)

    def initVessel3d(self):
        if self.vesselVolume is None:
            self.vesselVolume = self.Image3d.initVolume(self.vesselMaskData, mode="Vessel")
            self.Image3d.updateVolume(self.vesselVolume, self.Vessel_PiecewiseFunc, self.Vessel_ColorTransferFunc)

    def updateVessel3d(self):
        if self.ui.Vessel3DCheckBox.isChecked():
            self.initVessel3d()
            self.Image3d.updateVolume(self.vesselVolume, self.Vessel_PiecewiseFunc, self.Vessel_ColorTransferFunc)
        else:
            self.removeVessel3d()

    def removeVessel3d(self):
        self.Image3d.removeVolume(self.vesselVolume)
        self.vesselVolume = None

    # def vessel_process(self):
    #     sigma_minimum = 0.2
    #     sigma_maximum = 3.0
    #     number_of_sigma_steps = 8
    #     lowerThreshold = 40
    #     self.ui.VesselMessage.insertPlainText("Step 1: vessel image enhancement by the ITK-Hessian matrix.\n")
    #     self.process_changes()
    #     input_image = itk.imread(self.vessel.file)
    #     ImageType = type(input_image)
    #     Dimension = input_image.GetImageDimension()
    #     HessianPixelType = itk.SymmetricSecondRankTensor[itk.D, Dimension]
    #     HessianImageType = itk.Image[HessianPixelType, Dimension]
    #     objectness_filter = itk.HessianToObjectnessMeasureImageFilter[HessianImageType, ImageType].New()
    #     objectness_filter.SetBrightObject(True)
    #     objectness_filter.SetScaleObjectnessMeasure(True)
    #     objectness_filter.SetAlpha(0.5)
    #     objectness_filter.SetBeta(1.0)
    #     objectness_filter.SetGamma(5.0)
    #     multi_scale_filter = itk.MultiScaleHessianBasedMeasureImageFilter[ImageType, HessianImageType, ImageType].New()
    #     multi_scale_filter.SetInput(input_image)
    #     multi_scale_filter.SetHessianToMeasureFilter(objectness_filter)
    #     multi_scale_filter.SetSigmaStepMethodToLogarithmic()
    #     multi_scale_filter.SetSigmaMinimum(sigma_minimum)
    #     multi_scale_filter.SetSigmaMaximum(sigma_maximum)
    #     multi_scale_filter.SetNumberOfSigmaSteps(number_of_sigma_steps)
    #     self.ui.VesselMessage.insertPlainText("Finish Step 1!\n")
    #     # itk.imwrite(multi_scale_filter.GetOutput(), "step1.nii.gz")
    #     self.ui.VesselMessage.insertPlainText("Step 2: vessel normalization to the 0-255 range and threshold segmentation.\n")
    #     self.process_changes()
    #     OutputPixelType = itk.UC
    #     OutputImageType = itk.Image[OutputPixelType, Dimension]
    #     rescale_filter = itk.RescaleIntensityImageFilter[ImageType, OutputImageType].New()
    #     rescale_filter.SetInput(multi_scale_filter)
    #     self.ui.VesselMessage.insertPlainText("Finish Step 2!\n")
    #     self.ui.VesselMessage.insertPlainText("Step 3: threshold segmentation.\n")
    #     self.process_changes()
    #     thresholdFilter = itk.BinaryThresholdImageFilter[OutputImageType, OutputImageType].New()
    #     thresholdFilter.SetInput(rescale_filter.GetOutput())
    #     thresholdFilter.SetLowerThreshold(lowerThreshold)
    #     thresholdFilter.SetUpperThreshold(255)
    #     thresholdFilter.SetOutsideValue(0)
    #     thresholdFilter.SetInsideValue(255)
    #     self.ui.VesselMessage.insertPlainText("Finish Step 3!\n")
    #     self.process_changes()
    #     itk.imwrite(thresholdFilter.GetOutput(), self.vessel.save_path)
    #     self.ui.VesselMessage.insertPlainText("Save file over!\n")
