from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import imri_setting
import numpy as np


class Evaluation:
    def __init__(self):
        self.Image3d = None
        self.ImagePlanes = None
        self.ImageData = None
        self.mode = None
        self.config = imri_setting.read_config()
        self.needle_tip_pos_vtk = []
        self.needle_tip_items = [None, None, None]
        self.needle_tip_actor = None

    def init(self, ui, Image3d, ImagePlanes):
        self.Image3d = Image3d
        self.ImagePlanes = ImagePlanes
        self.eva_target_x_lineEdit = ui.eva_target_x_lineEdit
        self.eva_target_y_lineEdit = ui.eva_target_y_lineEdit
        self.eva_target_z_lineEdit = ui.eva_target_z_lineEdit
        self.tip_x_lineEdit = ui.tip_x_lineEdit
        self.tip_y_lineEdit = ui.tip_y_lineEdit
        self.tip_z_lineEdit = ui.tip_z_lineEdit
        self.eva_target_x_lineEdit.setReadOnly(True)
        self.eva_target_y_lineEdit.setReadOnly(True)
        self.eva_target_z_lineEdit.setReadOnly(True)
        self.tip_x_lineEdit.setReadOnly(True)
        self.tip_y_lineEdit.setReadOnly(True)
        self.tip_z_lineEdit.setReadOnly(True)

        self.eva_target_btn = ui.eva_target_btn
        self.eva_target_btn.clicked.connect(self.setTarget)
        self.set_needle_tip_btn = ui.set_needle_tip_btn
        self.set_needle_tip_btn.clicked.connect(self.setNeedleTip)
        self.error_lineEdit = ui.error_lineEdit
        self.setting_needle_tip = False
        self.show_seleted_tip = ui.show_seleted_tip_checkBox
        self.show_seleted_tip.stateChanged.connect(self.showSeletedTip)
        self.show_seleted_tip.setChecked(True)

    def setTarget(self):
        try:
            self.eva_target_x_lineEdit.setText(str(round(imri_setting.IMRIGlobal.target_pos[0], 1)))
            self.eva_target_y_lineEdit.setText(str(round(imri_setting.IMRIGlobal.target_pos[1], 1)))
            self.eva_target_z_lineEdit.setText(str(round(imri_setting.IMRIGlobal.target_pos[2], 1)))
            self.updateError()
        except:
            print("not set target position")

    def setNeedleTip(self):
        if self.setting_needle_tip == False:
            self.mode = "needle_tip"
            self.setting_needle_tip = True
            self.set_needle_tip_btn.setStyleSheet(self.config["button"]["active"])
        else:
            self.mode = None
            self.setting_needle_tip = False
            self.set_needle_tip_btn.setStyleSheet(self.config["button"]["normal"])

    def updateNeedleTip2d(self):
        needle_tip_color = self.config["evaluation"]["needle_tip_color_2d"]
        needle_tip_radius = self.config["evaluation"]["needle_tip_radius_2d"]
        if len(self.needle_tip_pos_vtk) != 0 and self.show_seleted_tip.isChecked():
            for i in range(3):
                if self.needle_tip_items[i] is not None:
                    self.ImagePlanes.removePlaneItem(self.needle_tip_items[i], plane=i)
                    self.needle_tip_items[i] = None
            points2d = self.ImageData.getPoint2dFromPoint3d(self.needle_tip_pos_vtk, self.ImagePlanes.getPixmapsSize())
            for i in range(3):
                if self.ImageData.current_slice[i] == points2d[i][2]:
                    self.needle_tip_items[i] = self.ImagePlanes.createPlanPointItem(points2d[i][:2], color=needle_tip_color, diameter=needle_tip_radius * 2)
                    self.needle_tip_items[i].setZValue(1)
                    self.ImagePlanes.addPlaneItem(self.needle_tip_items[i], plane=i)
                else:
                    self.ImagePlanes.removePlaneItem(self.needle_tip_items[i], plane=i)

    def updateNeedleTip3d(self):
        needle_tip_color = self.config["evaluation"]["needle_tip_color_3d"]
        needle_tip_radius = self.config["evaluation"]["needle_tip_radius_3d"]
        needle_tip_opacity = self.config["evaluation"]["needle_tip_opacity_3d"]
        if len(self.needle_tip_pos_vtk) != 0 and self.show_seleted_tip.isChecked():
            if self.needle_tip_actor is not None:
                self.Image3d.removeActor(self.needle_tip_actor)
                self.needle_tip_actor = None
            self.needle_tip_actor = self.Image3d.createPointActor(self.needle_tip_pos_vtk, color=needle_tip_color, opacity=needle_tip_opacity, radius=needle_tip_radius)
            self.Image3d.addActor(self.needle_tip_actor)

    def updateError(self):
        try:
            target = np.array([float(self.eva_target_x_lineEdit.text()), float(self.eva_target_y_lineEdit.text()), float(self.eva_target_z_lineEdit.text())])
            tip = np.array([float(self.tip_x_lineEdit.text()), float(self.tip_y_lineEdit.text()), float(self.tip_z_lineEdit.text())])
            error = np.linalg.norm(target - tip)
            self.error_lineEdit.setText(str(round(error, 4)))
        except:
            print("no target or tip position")

    def showSeletedTip(self):
        if len(self.needle_tip_pos_vtk) != 0:
            if self.show_seleted_tip.isChecked():
                self.updateNeedleTip2d()
                self.updateNeedleTip3d()
            else:
                if self.needle_tip_actor is not None:
                    self.Image3d.removeActor(self.needle_tip_actor)
                    self.needle_tip_actor = None
                for i in range(3):
                    if self.needle_tip_items[i] is not None:
                        self.ImagePlanes.removePlaneItem(self.needle_tip_items[i], plane=i)
                        self.needle_tip_items[i] = None
