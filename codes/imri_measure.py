from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import math
import numpy as np
import imri_setting


class Measure:
    def __init__(self):
        self.list_widget = None
        self.line_btn = None
        self.angle_btn = None
        self.Image3d = None
        self.ImagePlanes = None
        self.ImageData = None
        self.measure_item = None
        self.mode = None
        self.config = imri_setting.read_config()

    def init(self, list_widget, line_btn, angle_btn, Image3d, ImagePlanes):
        self.list_widget = list_widget
        self.line_btn = line_btn
        self.angle_btn = angle_btn
        self.Image3d = Image3d
        self.ImagePlanes = ImagePlanes
        self.line_btn.clicked.connect(self.onLineBtnClicked)
        self.angle_btn.clicked.connect(self.onAngleBtnClicked)

    def onLineBtnClicked(self):
        self.mode = "measureLine1"
        self.measure_item = MeasureLineItem(self.list_widget, self.Image3d, self.ImagePlanes, self.ImageData)
        self.list_widget.addItem(self.measure_item)
        self.measure_item.setSizeHint(self.measure_item.item_widget.sizeHint())
        self.list_widget.setItemWidget(self.measure_item, self.measure_item.item_widget)

    def onAngleBtnClicked(self):
        self.mode = "measureAngle1"
        self.measure_item = MeasureAngleItem(self.list_widget, self.Image3d, self.ImagePlanes, self.ImageData)
        self.list_widget.addItem(self.measure_item)
        self.measure_item.setSizeHint(self.measure_item.item_widget.sizeHint())
        self.list_widget.setItemWidget(self.measure_item, self.measure_item.item_widget)

    def updateLabel(self):
        line_num = 0
        angle_num = 0
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if isinstance(item, MeasureLineItem):
                line_num += 1
                item.label.setText(f"Line{line_num}: {item.length:.2f} mm")
            elif isinstance(item, MeasureAngleItem):
                angle_num += 1
                item.label.setText(f"Angle{angle_num}: {item.degree:.2f} degree")

    def updateCheckedItem3d(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item_widget = self.list_widget.itemWidget(item)
            checkbox = item_widget.findChild(QCheckBox)
            if isinstance(item, MeasureLineItem):
                if checkbox.isChecked():
                    item.updateline3d()
                else:
                    item.removeLine3d()
            elif isinstance(item, MeasureAngleItem):
                if checkbox.isChecked():
                    item.updateAngle13d()
                    item.updateAngle23d()
                else:
                    item.removeAngle13d()
                    item.removeAngle23d()
            else:
                pass

    def updateCheckedItem2d(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item_widget = self.list_widget.itemWidget(item)
            checkbox = item_widget.findChild(QCheckBox)
            if isinstance(item, MeasureLineItem):
                if checkbox.isChecked():
                    item.updateLine2d()
                else:
                    item.removeLine2d()
            elif isinstance(item, MeasureAngleItem):
                if checkbox.isChecked():
                    item.updateAngle12d()
                    item.updateAngle22d()
                else:
                    item.removeAngle12d()
                    item.removeAngle22d()
            else:
                pass

    def removeItemFromListWidget(self, button):
        item_widget = button.parent()
        item = self.list_widget.itemAt(item_widget.pos())
        if isinstance(item, MeasureLineItem):
            item.removeLine2d()
            item.removeLine3d()
            self.list_widget.takeItem(self.list_widget.row(item))
        elif isinstance(item, MeasureAngleItem):
            item.removeAngle12d()
            item.removeAngle22d()
            item.removeAngle13d()
            item.removeAngle23d()
            self.list_widget.takeItem(self.list_widget.row(item))
        else:
            pass
        self.updateLabel()


class MeasureLineItem(QListWidgetItem, Measure):
    def __init__(self, list_widget, Image3d, ImagePlanes, ImageData):
        QListWidgetItem.__init__(self)
        Measure.__init__(self)
        self.start_pos = None
        self.end_pos = None
        self.start_pos_vtk = None
        self.end_pos_vtk = None
        self.length = None
        self.actor = None
        self.line_plane_items = [None, None, None]

        self.list_widget = list_widget
        self.Image3d = Image3d
        self.ImagePlanes = ImagePlanes
        self.ImageData = ImageData

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.setFixedSize(30, 30)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(QIcon("image/measure_line_icon.png").pixmap(30, 30))
        self.icon_label.setFixedSize(30, 30)

        self.label = QLabel("Line")
        self.label.setFixedSize(250, 30)

        self.button = QPushButton(QIcon("image/delete_icon.png"), "")
        self.button.setFixedSize(30, 30)

        self.item_widget = QWidget()
        layout = QHBoxLayout(self.item_widget)
        layout.addWidget(self.checkbox, alignment=Qt.AlignLeft)
        layout.addWidget(self.icon_label, alignment=Qt.AlignLeft)
        layout.addWidget(self.label, alignment=Qt.AlignLeft)
        layout.addWidget(self.button, alignment=Qt.AlignRight)
        self.item_widget.setLayout(layout)

        self.button.clicked.connect(self.removeMeasureItem)
        self.checkbox.stateChanged.connect(self.onCheckboxStateChanged)

    def removeMeasureItem(self):
        self.removeItemFromListWidget(self.button)

    def onCheckboxStateChanged(self):
        self.updateCheckedItem2d()
        self.updateCheckedItem3d()

    def updateLength(self):
        x1, y1, z1 = self.start_pos_vtk
        x2, y2, z2 = self.end_pos_vtk
        self.length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
        self.updateLabel()

    def updateLine2d(self):
        line_color_2d = self.config["measure"]["line_color_2d"]
        line_width_2d = self.config["measure"]["line_width_2d"]
        self.removeLine2d()
        lines2d = self.ImageData.getLine2dFromLine3d([self.start_pos_vtk, self.end_pos_vtk], self.ImagePlanes.getPixmapsSize())
        start_pos_planes = lines2d[0]  # [[x, y, z], [x, y, z], [x, y, z]]
        end_pos_planes = lines2d[1]  # [[x, y, z], [x, y, z], [x, y, z]]
        for i in range(3):
            if min(start_pos_planes[i][2], end_pos_planes[i][2]) <= self.ImageData.current_slice[i] <= max(start_pos_planes[i][2], end_pos_planes[i][2]):
                self.line_plane_items[i] = self.ImagePlanes.createLineItem(start_pos_planes[i][:2], end_pos_planes[i][:2], color=line_color_2d, width=line_width_2d)
                self.ImagePlanes.addPlaneItem(self.line_plane_items[i], plane=i)
            else:
                self.ImagePlanes.removePlaneItem(self.line_plane_items[i], plane=i)

    def updateline3d(self):
        line_color_3d = self.config["measure"]["line_color_3d"]
        line_width_3d = self.config["measure"]["line_width_3d"]
        line_opacity_3d = self.config["measure"]["line_opacity_3d"]
        self.removeLine3d()
        self.actor = self.Image3d.createLineActor(self.start_pos_vtk, self.end_pos_vtk, color=line_color_3d, opacity=line_opacity_3d, width=line_width_3d)
        self.Image3d.addActor(self.actor)
        self.updateLength()

    def removeLine3d(self):
        if self.actor != None:
            self.Image3d.removeActor(self.actor)
            self.actor = None

    def removeLine2d(self):
        for i in range(3):
            if self.line_plane_items[i] != None:
                self.ImagePlanes.removePlaneItem(self.line_plane_items[i], plane=i)
                self.line_plane_items[i] = None


class MeasureAngleItem(QListWidgetItem, Measure):
    def __init__(self, list_widget, Image3d, ImagePlanes, ImageData):
        QListWidgetItem.__init__(self)
        Measure.__init__(self)
        self.start_pos = None
        self.end_pos = None
        self.mid_pos = None
        self.start_pos_vtk = None
        self.mid_pos_vtk = None
        self.end_pos_vtk = None
        self.degree = None
        self.actor1 = None
        self.actor2 = None
        self.line_plane_items1 = [None, None, None]
        self.line_plane_items2 = [None, None, None]

        self.list_widget = list_widget
        self.Image3d = Image3d
        self.ImagePlanes = ImagePlanes
        self.ImageData = ImageData

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.setFixedSize(30, 30)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(QIcon("image/measure_angle_icon.png").pixmap(30, 30))
        self.icon_label.setFixedSize(30, 30)

        self.label = QLabel("Angle")
        self.label.setFixedSize(250, 30)

        self.button = QPushButton(QIcon("image/delete_icon.png"), "")
        self.button.setFixedSize(30, 30)

        self.item_widget = QWidget()
        layout = QHBoxLayout(self.item_widget)
        layout.addWidget(self.checkbox, alignment=Qt.AlignLeft)
        layout.addWidget(self.icon_label, alignment=Qt.AlignLeft)
        layout.addWidget(self.label, alignment=Qt.AlignLeft)
        layout.addWidget(self.button, alignment=Qt.AlignRight)
        self.item_widget.setLayout(layout)

        self.button.clicked.connect(self.removeMeasureItem)
        self.checkbox.stateChanged.connect(self.onCheckboxStateChanged)

    def removeMeasureItem(self):
        self.removeItemFromListWidget(self.button)

    def onCheckboxStateChanged(self):
        self.updateCheckedItem2d()
        self.updateCheckedItem3d()

    def updateDegree(self):
        point_a = self.mid_pos_vtk
        point_b = self.start_pos_vtk
        point_c = self.end_pos_vtk
        vector_ab = np.array(point_b) - np.array(point_a)
        vector_ac = np.array(point_c) - np.array(point_a)

        dot_product = np.dot(vector_ab, vector_ac)
        magnitude_ab = np.linalg.norm(vector_ab)
        magnitude_ac = np.linalg.norm(vector_ac)

        cosine_angle = dot_product / (magnitude_ab * magnitude_ac)
        angle_in_radians = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
        self.degree = np.degrees(angle_in_radians)
        self.updateLabel()

    def updateAngle12d(self):
        angle_color_2d = self.config["measure"]["angle_color_2d"]
        angle_width_2d = self.config["measure"]["angle_width_2d"]
        self.removeAngle12d()

        lines2d = self.ImageData.getLine2dFromLine3d([self.start_pos_vtk, self.mid_pos_vtk], self.ImagePlanes.getPixmapsSize())
        start_pos_planes = lines2d[0]  # [[x, y, z], [x, y, z], [x, y, z]]
        mid_pos_planes = lines2d[1]  # [[x, y, z], [x, y, z], [x, y, z]]
        for i in range(3):
            if min(start_pos_planes[i][2], mid_pos_planes[i][2]) <= self.ImageData.current_slice[i] <= max(start_pos_planes[i][2], mid_pos_planes[i][2]):
                self.line_plane_items1[i] = self.ImagePlanes.createLineItem(start_pos_planes[i][:2], mid_pos_planes[i][:2], color=angle_color_2d, width=angle_width_2d)
                self.ImagePlanes.addPlaneItem(self.line_plane_items1[i], plane=i)
            else:
                self.ImagePlanes.removePlaneItem(self.line_plane_items1[i], plane=i)

    def updateAngle13d(self):
        angle_color_3d = self.config["measure"]["angle_color_3d"]
        angle_width_3d = self.config["measure"]["angle_width_3d"]
        angle_opacity_3d = self.config["measure"]["angle_opacity_3d"]
        self.removeAngle13d()
        self.actor1 = self.Image3d.createLineActor(self.start_pos_vtk, self.mid_pos_vtk, color=angle_color_3d, opacity=angle_opacity_3d, width=angle_width_3d)
        self.Image3d.addActor(self.actor1)

    def updateAngle22d(self):
        angle_color_2d = self.config["measure"]["angle_color_2d"]
        angle_width_2d = self.config["measure"]["angle_width_2d"]
        self.removeAngle22d()
        lines2d = self.ImageData.getLine2dFromLine3d([self.mid_pos_vtk, self.end_pos_vtk], self.ImagePlanes.getPixmapsSize())
        mid_pos_planes = lines2d[0]  # [[x, y, z], [x, y, z], [x, y, z]]
        end_pos_planes = lines2d[1]  # [[x, y, z], [x, y, z], [x, y, z]]
        for i in range(3):
            if min(mid_pos_planes[i][2], end_pos_planes[i][2]) <= self.ImageData.current_slice[i] <= max(mid_pos_planes[i][2], end_pos_planes[i][2]):
                self.line_plane_items2[i] = self.ImagePlanes.createLineItem(mid_pos_planes[i][:2], end_pos_planes[i][:2], color=angle_color_2d, width=angle_width_2d)
                self.ImagePlanes.addPlaneItem(self.line_plane_items2[i], plane=i)
            else:
                self.ImagePlanes.removePlaneItem(self.line_plane_items2[i], plane=i)
        self.updateDegree()

    def updateAngle23d(self):
        angle_color_3d = self.config["measure"]["angle_color_3d"]
        angle_width_3d = self.config["measure"]["angle_width_3d"]
        angle_opacity_3d = self.config["measure"]["angle_opacity_3d"]
        self.removeAngle23d()
        self.actor2 = self.Image3d.createLineActor(self.mid_pos_vtk, self.end_pos_vtk, color=angle_color_3d, opacity=angle_opacity_3d, width=angle_width_3d)
        self.Image3d.addActor(self.actor2)

    def removeAngle12d(self):
        for i in range(3):
            if self.line_plane_items1[i] != None:
                self.ImagePlanes.removePlaneItem(self.line_plane_items1[i], plane=i)
                self.line_plane_items1[i] = None

    def removeAngle13d(self):
        if self.actor1 != None:
            self.Image3d.removeActor(self.actor1)
            self.actor1 = None

    def removeAngle22d(self):
        for i in range(3):
            if self.line_plane_items2[i] != None:
                self.ImagePlanes.removePlaneItem(self.line_plane_items2[i], plane=i)
                self.line_plane_items2[i] = None

    def removeAngle23d(self):
        if self.actor2 != None:
            self.Image3d.removeActor(self.actor2)
            self.actor2 = None
