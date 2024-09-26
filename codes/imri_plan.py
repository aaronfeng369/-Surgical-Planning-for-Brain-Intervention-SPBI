from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
import scipy
import imri_setting
import os
import socket


class Plan:
    def __init__(self):
        self.Image3d = None
        self.ImagePlanes = None
        self.ImageData = None
        self.plan_item = None
        self.mode = None
        self.config = imri_setting.read_config()
        self.setting_target_point = False
        self.setting_entry_point = False
        self.item_index = -1
        self.path_item_list = []
        self.target_vtk_list = []  # [[x,y,z], [x,y,z], ...]
        self.entry_vtk_list = []  # [[x,y,z], [x,y,z], ...]
        self.path_actor = []  # [path1_actor, path2_actor, ...]
        self.target_actor = []  # [target1_actor, target2_actor, ...]
        self.entry_actor = []  # [entry1_actor, entry2_actor, ...]
        self.target_plane_items = []  # [[tp1_item, tp2_item, tp3_item], ...]
        self.entry_plane_items = []  # [[ep1_item, ep2_item, ep3_item], ...]
        self.path_plane_items = []  # [[pp1_item, pp2_item, pp3_item], ...]

    def init(self, ui, Image3d, ImagePlanes):
        self.list_widget = ui.PlanListWidget
        self.target_btn = ui.target_btn
        self.target_btn.setDisabled(True)
        self.entry_btn = ui.entry_btn
        self.entry_btn.setDisabled(True)
        self.new_path_btn = ui.new_path_btn
        self.save_path_btn = ui.save_path_btn
        self.delete_path_btn = ui.delete_path_btn
        self.load_path_btn = ui.load_path_btn
        self.set_plan_path_btn = ui.set_plan_path_btn
        self.plan_send_to_robot_btn = ui.plan_send_to_robot_btn
        self.plan_send_to_robot_btn.setDisabled(True)
        self.save_path_btn.setDisabled(True)
        self.delete_path_btn.setDisabled(True)
        self.set_plan_path_btn.setDisabled(True)
        self.set_plan_path_btn.setStyleSheet(self.config["button"]["disabled"])
        self.Image3d = Image3d
        self.ImagePlanes = ImagePlanes
        self.list_widget.itemClicked.connect(self.modifyPlanPath)
        self.list_widget.itemChanged.connect(self.updateCheckedItem)
        self.target_btn.clicked.connect(self.setTargetPoint)
        self.entry_btn.clicked.connect(self.setEntryPoint)
        self.new_path_btn.clicked.connect(self.createNewPath)
        self.load_path_btn.clicked.connect(self.loadPath)
        self.save_path_btn.clicked.connect(self.savePath)
        self.delete_path_btn.clicked.connect(self.deletePath)
        self.set_plan_path_btn.clicked.connect(self.setPlanPath)
        self.plan_send_to_robot_btn.clicked.connect(self.sendToRobot)
        self.target_x_lineEdit = ui.target_x_lineEdit
        self.target_y_lineEdit = ui.target_y_lineEdit
        self.target_z_lineEdit = ui.target_z_lineEdit
        self.entry_x_lineEdit = ui.entry_x_lineEdit
        self.entry_y_lineEdit = ui.entry_y_lineEdit
        self.entry_z_lineEdit = ui.entry_z_lineEdit

    def modifyPlanPath(self):
        selected_item = self.list_widget.currentItem()
        self.list_widget.setCurrentItem(selected_item)
        self.item_index = self.path_item_list.index(selected_item)
        self.updatePathInfo()
        self.target_btn.setEnabled(True)
        self.entry_btn.setEnabled(True)

    def setTargetPoint(self):
        if self.setting_target_point == False:
            self.mode = "target"
            self.target_btn.setStyleSheet(self.config["button"]["active"])
            self.setting_target_point = True
            self.entry_btn.setDisabled(True)
            self.entry_btn.setStyleSheet(self.config["button"]["disabled"])
            self.new_path_btn.setDisabled(True)
            self.save_path_btn.setDisabled(True)
            self.load_path_btn.setDisabled(True)
            self.set_plan_path_btn.setDisabled(True)
            self.set_plan_path_btn.setStyleSheet(self.config["button"]["disabled"])
            self.delete_path_btn.setDisabled(True)
        else:
            self.mode = None
            self.target_btn.setStyleSheet(self.config["button"]["normal"])
            self.setting_target_point = False
            self.entry_btn.setEnabled(True)
            self.entry_btn.setStyleSheet(self.config["button"]["normal"])
            self.new_path_btn.setEnabled(True)
            self.save_path_btn.setEnabled(True)
            self.load_path_btn.setEnabled(True)
            self.set_plan_path_btn.setEnabled(True)
            self.set_plan_path_btn.setStyleSheet(self.config["button"]["normal"])
            self.delete_path_btn.setEnabled(True)

    def setEntryPoint(self):
        if self.setting_entry_point == False:
            self.mode = "entry"
            self.entry_btn.setStyleSheet(self.config["button"]["active"])
            self.setting_entry_point = True
            self.target_btn.setDisabled(True)
            self.target_btn.setStyleSheet(self.config["button"]["disabled"])
            self.new_path_btn.setDisabled(True)
            self.save_path_btn.setDisabled(True)
            self.load_path_btn.setDisabled(True)
            self.set_plan_path_btn.setDisabled(True)
            self.set_plan_path_btn.setStyleSheet(self.config["button"]["disabled"])
            self.delete_path_btn.setDisabled(True)
        else:
            self.mode = None
            self.entry_btn.setStyleSheet(self.config["button"]["normal"])
            self.setting_entry_point = False
            self.target_btn.setEnabled(True)
            self.target_btn.setStyleSheet(self.config["button"]["normal"])
            self.new_path_btn.setEnabled(True)
            self.save_path_btn.setEnabled(True)
            self.load_path_btn.setEnabled(True)
            self.set_plan_path_btn.setEnabled(True)
            self.set_plan_path_btn.setStyleSheet(self.config["button"]["normal"])
            self.delete_path_btn.setEnabled(True)

    def createNewPath(self):
        item = QListWidgetItem(QIcon("image/path_icon.png"), "New Path")
        item.setCheckState(Qt.Checked)
        self.list_widget.addItem(item)
        self.list_widget.setCurrentItem(item)
        self.item_index = self.list_widget.row(item)

        self.path_item_list.append(item)
        self.target_vtk_list.append([0, 0, 0])
        self.entry_vtk_list.append([0, 0, 0])
        self.path_actor.append(None)
        self.target_actor.append(None)
        self.entry_actor.append(None)
        self.target_plane_items.append([None, None, None])
        self.entry_plane_items.append([None, None, None])
        self.path_plane_items.append([None, None, None])

        self.target_btn.setEnabled(True)
        self.target_btn.setStyleSheet(self.config["button"]["normal"])
        self.entry_btn.setEnabled(True)
        self.entry_btn.setStyleSheet(self.config["button"]["normal"])
        self.load_path_btn.setDisabled(True)
        self.save_path_btn.setDisabled(True)
        self.delete_path_btn.setEnabled(True)
        self.set_plan_path_btn.setDisabled(True)
        self.set_plan_path_btn.setStyleSheet(self.config["button"]["disabled"])

        self.updatePathInfo()

    def loadPath(self):
        try:
            directory_path = self.config["plan"]["path_directory"]
            file_path, _ = QFileDialog.getOpenFileName(None, "Open Path File", directory_path, "Mat(*.mat)")
            if file_path != "":
                directory_path = os.path.dirname(file_path)
                self.config["plan"]["path_directory"] = directory_path
                imri_setting.update_config(config=self.config)
                data = scipy.io.loadmat(file_path)
                # show the path
                item = QListWidgetItem(QIcon("image/path_icon.png"), "New Path")
                item.setCheckState(Qt.Checked)
                self.list_widget.addItem(item)
                self.list_widget.setCurrentItem(item)
                self.item_index = self.list_widget.row(item)
                self.path_item_list.append(item)
                self.target_vtk_list.append(data["target_pos_vtk"][0].tolist())
                self.entry_vtk_list.append(data["entry_pos_vtk"][0].tolist())
                self.path_actor.append(None)
                self.target_actor.append(None)
                self.entry_actor.append(None)
                self.target_plane_items.append([None, None, None])
                self.entry_plane_items.append([None, None, None])
                self.path_plane_items.append([None, None, None])
                self.updatePath2d(self.item_index)
                self.updatePath3d(self.item_index)
                self.updatePathInfo()
                # set button
                self.target_btn.setEnabled(True)
                self.target_btn.setStyleSheet(self.config["button"]["normal"])
                self.entry_btn.setEnabled(True)
                self.entry_btn.setStyleSheet(self.config["button"]["normal"])
                self.save_path_btn.setEnabled(True)
                self.delete_path_btn.setEnabled(True)
                self.set_plan_path_btn.setEnabled(True)
                self.set_plan_path_btn.setStyleSheet(self.config["button"]["normal"])

        except:
            meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Maybe it is not a Path Mat!")
            meg_box.exec_()

    def savePath(self):
        directory_path = self.config["plan"]["path_directory"]
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Mat File", directory_path, "Path(*.mat)")
        if file_path != "":
            self.config["plan"]["path_directory"] = os.path.dirname(file_path)
            imri_setting.update_config(config=self.config)
            scipy.io.savemat(file_path, {"target_pos_vtk": self.target_vtk_list[self.item_index], "entry_pos_vtk": self.entry_vtk_list[self.item_index]})

    def deletePath(self):
        self.removePath2d(self.item_index)
        self.removePath3d(self.item_index)
        tmp = self.path_item_list.pop(self.item_index)
        tmp1 = self.target_vtk_list.pop(self.item_index)
        tmp2 = self.entry_vtk_list.pop(self.item_index)
        tmp3 = self.path_actor.pop(self.item_index)
        tmp4 = self.target_actor.pop(self.item_index)
        tmp5 = self.entry_actor.pop(self.item_index)
        tmp6 = self.target_plane_items.pop(self.item_index)
        tmp7 = self.entry_plane_items.pop(self.item_index)
        tmp8 = self.path_plane_items.pop(self.item_index)
        tmp9 = self.list_widget.takeItem(self.item_index)
        del tmp, tmp1, tmp2, tmp3, tmp4, tmp5, tmp6, tmp7, tmp8, tmp9
        num = self.list_widget.count()
        if num > 0:
            self.item_index = num - 1
            self.list_widget.setCurrentItem(self.path_item_list[self.item_index])
            self.updatePathInfo()
        else:
            self.target_x_lineEdit.setText("0")
            self.target_y_lineEdit.setText("0")
            self.target_z_lineEdit.setText("0")
            self.entry_x_lineEdit.setText("0")
            self.entry_y_lineEdit.setText("0")
            self.entry_z_lineEdit.setText("0")
            self.target_btn.setDisabled(True)
            self.target_btn.setStyleSheet(self.config["button"]["disabled"])
            self.entry_btn.setDisabled(True)
            self.entry_btn.setStyleSheet(self.config["button"]["disabled"])
            self.load_path_btn.setEnabled(True)
            self.delete_path_btn.setDisabled(True)
            self.save_path_btn.setDisabled(True)
            self.set_plan_path_btn.setDisabled(True)
            self.set_plan_path_btn.setStyleSheet(self.config["button"]["disabled"])

    def setPlanPath(self):
        # try:
        if self.set_plan_path_btn.text() == "Set Plan Path":
            imri_setting.IMRIGlobal.target_pos = self.target_vtk_list[self.item_index]
            imri_setting.IMRIGlobal.entry_pos = self.entry_vtk_list[self.item_index]
            selected_item = self.list_widget.currentItem()
            selected_item.setIcon(QIcon("image/path_icon_2.png"))
            self.new_path_btn.setDisabled(True)
            self.delete_path_btn.setDisabled(True)
            self.load_path_btn.setDisabled(True)
            self.plan_send_to_robot_btn.setEnabled(True)
            self.target_btn.setDisabled(True)
            self.target_btn.setStyleSheet(self.config["button"]["disabled"])
            self.entry_btn.setDisabled(True)
            self.entry_btn.setStyleSheet(self.config["button"]["disabled"])
            self.set_plan_path_btn.setText("Reset Plan Path")
            self.set_plan_path_btn.setStyleSheet(self.config["button"]["active"])
            self.list_widget.itemClicked.disconnect(self.modifyPlanPath)
            self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)

        else:
            imri_setting.IMRIGlobal.target_pos = None
            imri_setting.IMRIGlobal.entry_pos = None
            selected_item = self.path_item_list[self.item_index]
            selected_item.setIcon(QIcon("image/path_icon.png"))
            self.new_path_btn.setEnabled(True)
            self.delete_path_btn.setEnabled(True)
            self.load_path_btn.setEnabled(True)
            self.plan_send_to_robot_btn.setDisabled(True)
            self.target_btn.setEnabled(True)
            self.target_btn.setStyleSheet(self.config["button"]["normal"])
            self.entry_btn.setEnabled(True)
            self.entry_btn.setStyleSheet(self.config["button"]["normal"])
            self.set_plan_path_btn.setText("Set Plan Path")
            self.set_plan_path_btn.setStyleSheet(self.config["button"]["normal"])
            self.list_widget.itemClicked.connect(self.modifyPlanPath)
            self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)

        # except:
        #     print("Set Plan Path Error!")
        #     meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Set Plan Path Error!")
        #     meg_box.exec_()

    def updatePathInfo(self):
        # update target and entry point
        i = self.item_index
        self.target_x_lineEdit.setText(str(round(self.target_vtk_list[i][0], 1)))
        self.target_y_lineEdit.setText(str(round(self.target_vtk_list[i][1], 1)))
        self.target_z_lineEdit.setText(str(round(self.target_vtk_list[i][2], 1)))
        self.entry_x_lineEdit.setText(str(round(self.entry_vtk_list[i][0], 1)))
        self.entry_y_lineEdit.setText(str(round(self.entry_vtk_list[i][1], 1)))
        self.entry_z_lineEdit.setText(str(round(self.entry_vtk_list[i][2], 1)))
        # update path item
        path_num = 0
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            path_num += 1
            item.setText(f"Path{path_num}: Length={self.getPathLength(i):.2f} mm")

    def getPathLength(self, item_index):
        target_pos = np.array(self.target_vtk_list[item_index])
        entry_pos = np.array(self.entry_vtk_list[item_index])
        length = np.linalg.norm(target_pos - entry_pos)
        return length

    def updatePath2d(self, item_index):
        entry_color_2d = self.config["plan"]["entry_color_2d"]
        entry_radius_2d = self.config["plan"]["entry_radius_2d"]
        target_color_2d = self.config["plan"]["target_color_2d"]
        target_radius_2d = self.config["plan"]["target_radius_2d"]
        path_width_2d = self.config["plan"]["path_width_2d"]

        ############################################################################################################
        if self.target_vtk_list[item_index] != [0, 0, 0]:
            for i in range(3):
                if self.target_plane_items[item_index][i] != None:
                    self.ImagePlanes.removePlaneItem(self.target_plane_items[item_index][i], plane=i)
                    self.target_plane_items[item_index][i] = None
            points2d = self.ImageData.getPoint2dFromPoint3d(self.target_vtk_list[item_index], self.ImagePlanes.getPixmapsSize())
            for i in range(3):
                if self.ImageData.current_slice[i] == points2d[i][2]:
                    self.target_plane_items[item_index][i] = self.ImagePlanes.createPlanPointItem(points2d[i][:2], color=target_color_2d, diameter=target_radius_2d * 2)
                    self.target_plane_items[item_index][i].setZValue(1)
                    self.ImagePlanes.addPlaneItem(self.target_plane_items[item_index][i], plane=i)
                else:
                    self.ImagePlanes.removePlaneItem(self.target_plane_items[item_index][i], plane=i)

        ############################################################################################################
        if self.entry_vtk_list[item_index] != [0, 0, 0]:
            for i in range(3):
                if self.entry_plane_items[item_index][i] != None:
                    self.ImagePlanes.removePlaneItem(self.entry_plane_items[item_index][i], plane=i)
                    self.entry_plane_items[item_index][i] = None

            if self.target_vtk_list[item_index] == [0, 0, 0]:
                points2d = self.ImageData.getPoint2dFromPoint3d(self.entry_vtk_list[item_index], self.ImagePlanes.getPixmapsSize())
                for i in range(3):
                    if self.ImageData.current_slice[i] == points2d[i][2]:
                        self.entry_plane_items[item_index][i] = self.ImagePlanes.createPlanPointItem(points2d[i][:2], color=entry_color_2d, diameter=entry_radius_2d * 2)
                        self.entry_plane_items[item_index][i].setZValue(1)
                        self.ImagePlanes.addPlaneItem(self.entry_plane_items[item_index][i], plane=i)
                    else:
                        self.ImagePlanes.removePlaneItem(self.entry_plane_items[item_index][i], plane=i)

            else:
                start_pos_planes = self.ImageData.getPoint2dFromPoint3d(self.target_vtk_list[item_index], self.ImagePlanes.getPixmapsSize())
                end_pos_planes = self.ImageData.getPoint2dFromPoint3d(self.entry_vtk_list[item_index], self.ImagePlanes.getPixmapsSize())
                for i in range(3):
                    moved_entry_pos = self.getMovedPoint2d(start_pos_planes[i], end_pos_planes[i], self.ImageData.current_slice[i])
                    if min(start_pos_planes[i][2], end_pos_planes[i][2]) <= self.ImageData.current_slice[i] <= max(start_pos_planes[i][2], end_pos_planes[i][2]):
                        self.entry_plane_items[item_index][i] = self.ImagePlanes.createPlanPointItem(moved_entry_pos[:2], color=entry_color_2d, diameter=entry_radius_2d * 2)
                        self.entry_plane_items[item_index][i].setZValue(1)
                        self.ImagePlanes.addPlaneItem(self.entry_plane_items[item_index][i], plane=i)
                    else:
                        self.ImagePlanes.removePlaneItem(self.entry_plane_items[item_index][i], plane=i)

        ############################################################################################################
        if self.target_vtk_list[item_index] != [0, 0, 0] and self.entry_vtk_list[item_index] != [0, 0, 0]:
            for i in range(3):
                if self.path_plane_items[item_index][i] != None:
                    self.ImagePlanes.removePlaneItem(self.path_plane_items[item_index][i], plane=i)
                    self.path_plane_items[item_index][i] = None
            # draw path
            lines2d = self.ImageData.getLine2dFromLine3d([self.target_vtk_list[item_index], self.entry_vtk_list[item_index]], self.ImagePlanes.getPixmapsSize())
            start_pos_planes = lines2d[0]  # [[x, y, z], [x, y, z], [x, y, z]]
            end_pos_planes = lines2d[1]  # [[x, y, z], [x, y, z], [x, y, z]]
            for i in range(3):
                if min(start_pos_planes[i][2], end_pos_planes[i][2]) <= self.ImageData.current_slice[i] <= max(start_pos_planes[i][2], end_pos_planes[i][2]):
                    self.path_plane_items[item_index][i] = self.ImagePlanes.createPathLineItem(
                        start_pos_planes[i][:2], end_pos_planes[i][:2], color_start=target_color_2d, color_end=entry_color_2d, width=path_width_2d
                    )
                    self.ImagePlanes.addPlaneItem(self.path_plane_items[item_index][i], plane=i)
                else:
                    self.ImagePlanes.removePlaneItem(self.path_plane_items[item_index][i], plane=i)

    def getMovedPoint2d(self, target_pos, entry_pos, current_slice_z):
        """
        when mouse wheel scroll, the slice will change, so the 2d point will change
        :param entry_pos: [x, y, z] x,y in image coordinate, z in voxel coordinate
        :param target_pos: [x, y, z] x,y in image coordinate, z in voxel coordinate
        :param current_slice_z: z  ,in voxel coordinate
        :return: [x, y, z] x,y in image coordinate, z in voxel coordinate
        """
        moved_entry_pos = [0, 0, 0]

        if entry_pos[2] == target_pos[2]:
            moved_entry_pos[0] = entry_pos[0]
            moved_entry_pos[1] = entry_pos[1]
            moved_entry_pos[2] = current_slice_z
        else:
            moved_entry_pos[0] = ((entry_pos[0] - target_pos[0]) / (entry_pos[2] - target_pos[2])) * (current_slice_z - target_pos[2]) + target_pos[0]
            moved_entry_pos[1] = ((entry_pos[1] - target_pos[1]) / (entry_pos[2] - target_pos[2])) * (current_slice_z - target_pos[2]) + target_pos[1]
            moved_entry_pos[2] = current_slice_z
        return moved_entry_pos

    def updatePath3d(self, item_index):
        entry_color_3d = self.config["plan"]["entry_color_3d"]
        entry_radius_3d = self.config["plan"]["entry_radius_3d"]
        entry_opacity_3d = self.config["plan"]["entry_opacity_3d"]
        target_color_3d = self.config["plan"]["target_color_3d"]
        target_radius_3d = self.config["plan"]["target_radius_3d"]
        target_opacity_3d = self.config["plan"]["target_opacity_3d"]
        path_color_3d = self.config["plan"]["path_color_3d"]
        path_width_3d = self.config["plan"]["path_width_3d"]
        path_opacity_3d = self.config["plan"]["path_opacity_3d"]

        if self.target_vtk_list[item_index] != [0, 0, 0]:
            if self.target_actor[item_index] != None:
                self.Image3d.removeActor(self.target_actor[item_index])
                self.target_actor[item_index] = None
            self.target_actor[item_index] = self.Image3d.createPointActor(self.target_vtk_list[item_index], color=target_color_3d, opacity=target_opacity_3d, radius=target_radius_3d)
            self.Image3d.addActor(self.target_actor[item_index])

        if self.entry_vtk_list[item_index] != [0, 0, 0]:
            if self.entry_actor[item_index] != None:
                self.Image3d.removeActor(self.entry_actor[item_index])
                self.entry_actor[item_index] = None
            self.entry_actor[item_index] = self.Image3d.createPointActor(self.entry_vtk_list[item_index], color=entry_color_3d, opacity=entry_opacity_3d, radius=entry_radius_3d)
            self.Image3d.addActor(self.entry_actor[item_index])

        if self.target_vtk_list[item_index] != [0, 0, 0] and self.entry_vtk_list[item_index] != [0, 0, 0]:
            if self.path_actor[item_index] != None:
                self.Image3d.removeActor(self.path_actor[item_index])
                self.path_actor[item_index] = None
            self.path_actor[item_index] = self.Image3d.createLineActor(
                self.target_vtk_list[item_index], self.entry_vtk_list[item_index], color=path_color_3d, opacity=path_opacity_3d, width=path_width_3d
            )
            self.Image3d.addActor(self.path_actor[item_index])

    def removePath3d(self, item_index):
        if self.target_actor[item_index] != None:
            self.Image3d.removeActor(self.target_actor[item_index])
            self.target_actor[item_index] = None
        if self.entry_actor[item_index] != None:
            self.Image3d.removeActor(self.entry_actor[item_index])
            self.entry_actor[item_index] = None
        if self.path_actor[item_index] != None:
            self.Image3d.removeActor(self.path_actor[item_index])
            self.path_actor[item_index] = None

    def removePath2d(self, item_index):
        for i in range(3):
            if self.target_plane_items[item_index][i] != None:
                self.ImagePlanes.removePlaneItem(self.target_plane_items[item_index][i], plane=i)
                self.target_plane_items[item_index][i] = None
            if self.entry_plane_items[item_index][i] != None:
                self.ImagePlanes.removePlaneItem(self.entry_plane_items[item_index][i], plane=i)
                self.entry_plane_items[item_index][i] = None
            if self.path_plane_items[item_index][i] != None:
                self.ImagePlanes.removePlaneItem(self.path_plane_items[item_index][i], plane=i)
                self.path_plane_items[item_index][i] = None

    def updateCheckedItem2d(self):
        if len(self.path_item_list) == 0:
            return None

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                self.updatePath2d(i)
            else:
                self.removePath2d(i)

    def updateCheckedItem3d(self):
        if len(self.path_item_list) == 0:
            return None

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                self.updatePath3d(i)
            else:
                self.removePath3d(i)

    def updateCheckedItem(self):
        self.updateCheckedItem2d()
        self.updateCheckedItem3d()

    def sendToRobot(self):
        try:
            target_pos = imri_setting.IMRIGlobal.target_pos
            entry_pos = imri_setting.IMRIGlobal.entry_pos
            robot_target = imri_setting.worldToRobot(target_pos)
            robot_entry = imri_setting.worldToRobot(entry_pos)
            plan_v = robot_entry[0:3] - robot_target[0:3]
            plan_v = plan_v / np.linalg.norm(plan_v)
            plan_info = (
                "00"
                + ","
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
                + "0,0,0,0,0,0,0,0,0"
            )
            print("send to robot plan info: ", plan_info)
            robot_ip = self.config["main"]["robot_ip"]
            robot_port = self.config["main"]["robot_port"]
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_address = (robot_ip, robot_port)
            sock.connect(server_address)
            sock.sendall(plan_info.encode())
            sock.close()
        except:
            print("Send Plan to Robot Error!")
            meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Send Plan Error!")
            meg_box.exec_()
