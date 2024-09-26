from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
import imri_setting


class ImagePlanes:
    def __init__(self):
        self.original_imageArrs = [
            np.zeros((256, 256)),
            np.zeros((256, 256)),
            np.zeros((256, 256)),
        ]

        self.sag_pixmap = QPixmap()
        self.cor_pixmap = QPixmap()
        self.axi_pixmap = QPixmap()
        self.pixmaps = [self.sag_pixmap, self.cor_pixmap, self.axi_pixmap]

        self.sag_pixmap_item = QGraphicsPixmapItem()
        self.cor_pixmap_item = QGraphicsPixmapItem()
        self.axi_pixmap_item = QGraphicsPixmapItem()
        self.pixmap_items = [self.sag_pixmap_item, self.cor_pixmap_item, self.axi_pixmap_item]

        self.sag_scene = QGraphicsScene()
        self.cor_scene = QGraphicsScene()
        self.axi_scene = QGraphicsScene()
        self.scenes = [self.sag_scene, self.cor_scene, self.axi_scene]

        self.sag_text_items = []
        self.cor_text_items = []
        self.axi_text_items = []
        self.text_items = [
            self.sag_text_items,
            self.cor_text_items,
            self.axi_text_items,
        ]

        self.sag_cross_horizontal_line = QGraphicsLineItem()
        self.sag_cross_vertical_line = QGraphicsLineItem()
        self.cor_cross_horizontal_line = QGraphicsLineItem()
        self.cor_cross_vertical_line = QGraphicsLineItem()
        self.axi_cross_horizontal_line = QGraphicsLineItem()
        self.axi_cross_vertical_line = QGraphicsLineItem()
        self.cross_line = [
            [self.sag_cross_horizontal_line, self.sag_cross_vertical_line],
            [self.cor_cross_horizontal_line, self.cor_cross_vertical_line],
            [self.axi_cross_horizontal_line, self.axi_cross_vertical_line],
        ]

        self.sag_fusion_mask_pixmap_item = QGraphicsPixmapItem()
        self.cor_fusion_mask_pixmap_item = QGraphicsPixmapItem()
        self.axi_fusion_mask_pixmap_item = QGraphicsPixmapItem()
        self.fusion_mask_pixmap_items = [self.sag_fusion_mask_pixmap_item, self.cor_fusion_mask_pixmap_item, self.axi_fusion_mask_pixmap_item]

        self.sag_brain_seg_mask_pixmap_item = QGraphicsPixmapItem()
        self.cor_brain_seg_mask_pixmap_item = QGraphicsPixmapItem()
        self.axi_brain_seg_mask_pixmap_item = QGraphicsPixmapItem()
        self.brain_seg_mask_pixmap_items = [self.sag_brain_seg_mask_pixmap_item, self.cor_brain_seg_mask_pixmap_item, self.axi_brain_seg_mask_pixmap_item]

        self.sag_vessel_pixmap_item = QGraphicsPixmapItem()
        self.cor_vessel_pixmap_item = QGraphicsPixmapItem()
        self.axi_vessel_pixmap_item = QGraphicsPixmapItem()
        self.vessel_pixmap_items = [self.sag_vessel_pixmap_item, self.cor_vessel_pixmap_item, self.axi_vessel_pixmap_item]

        self.sag_ruler_item = QGraphicsLineItem()
        self.cor_ruler_item = QGraphicsLineItem()
        self.axi_ruler_item = QGraphicsLineItem()
        self.ruler_items = [self.sag_ruler_item, self.cor_ruler_item, self.axi_ruler_item]
        self.sag_ruler_text_item = QGraphicsTextItem()
        self.cor_ruler_text_item = QGraphicsTextItem()
        self.axi_ruler_text_item = QGraphicsTextItem()
        self.ruler_text_items = [self.sag_ruler_text_item, self.cor_ruler_text_item, self.axi_ruler_text_item]

        self.sag_info_text_item = QGraphicsTextItem()
        self.cor_info_text_item = QGraphicsTextItem()
        self.axi_info_text_item = QGraphicsTextItem()
        self.info_text_items = [self.sag_info_text_item, self.cor_info_text_item, self.axi_info_text_item]

    def update(self):
        self.pixmaps = [self.sag_pixmap, self.cor_pixmap, self.axi_pixmap]
        self.pixmap_items = [
            self.sag_pixmap_item,
            self.cor_pixmap_item,
            self.axi_pixmap_item,
        ]
        self.scenes = [self.sag_scene, self.cor_scene, self.axi_scene]

    def addPlaneItem(self, item, plane=0):
        if item not in self.scenes[plane].items():
            self.scenes[plane].addItem(item)

    def removePlaneItem(self, item, plane=0):
        if item in self.scenes[plane].items():
            self.scenes[plane].removeItem(item)

    def resizeScene(self, views, plane=0):
        """
        resize scene as same as view size
        """
        view_rect = views[plane].contentsRect()  # if use self.views[i].rect(), the size will be wrong
        view_w = view_rect.width()
        view_h = view_rect.height()
        self.scenes[plane].setSceneRect(-int(view_w / 2), -int(view_h / 2), view_w, view_h)
        return view_w, view_h

    def addPixmap(self, imageArr_3d, gray_scale, views, plane=0):
        """
        :param imageArr: 3d numpy array
        :param plane: 0-sagittal, 1-coronal, 2-axial
        :function: add pixmap to scene
        """
        dim = 4 - sum(imageArr_3d.shape[i] == 1 for i in range(3))
        if self.pixmap_items[plane] in self.scenes[plane].items():
            self.scenes[plane].removeItem(self.pixmap_items[plane])
        if dim == 3:
            imageArr_2d = np.squeeze(imageArr_3d)
            np.clip(imageArr_2d, gray_scale[0], gray_scale[1], out=imageArr_2d)
            imageArr_2d = np.int32(imageArr_2d)
            self.original_imageArrs[plane] = imageArr_2d
            min_val = np.min(imageArr_2d)
            max_val = np.max(imageArr_2d)
            if min_val != max_val:
                imageArr_2d = (imageArr_2d - min_val) / (max_val - min_val) * 255
            # qimage = qimage2ndarray.gray2qimage(imageArr_2d)
            imageArr_2d = imageArr_2d.astype(np.uint8)
            qimage = QImage(
                imageArr_2d.data,
                imageArr_2d.shape[1],
                imageArr_2d.shape[0],
                imageArr_2d.strides[0],
                QImage.Format_Indexed8,
            )

        else:
            imageArr_2d = np.zeros((256, 256), dtype=np.uint8)
            self.original_imageArrs[plane] = imageArr_2d
            qimage = QImage(imageArr_2d.data, imageArr_2d.shape[1], imageArr_2d.shape[0], imageArr_2d.strides[0], QImage.Format_Indexed8)
            # qimage = qimage2ndarray.gray2qimage(imageArr_2d)
        self.pixmaps[plane] = QPixmap.fromImage(qimage)
        view_rect = views[plane].contentsRect()
        view_w = view_rect.width()
        view_h = view_rect.height()
        self.pixmap_items[plane].setPixmap(self.pixmaps[plane].scaled(view_w, view_h, Qt.KeepAspectRatio))
        rect = self.pixmap_items[plane].boundingRect()
        self.pixmap_items[plane].setPos(-rect.width() / 2, -rect.height() / 2)
        self.pixmap_items[plane].setZValue(-1)
        if self.pixmap_items[plane] not in self.scenes[plane].items():
            self.scenes[plane].addItem(self.pixmap_items[plane])
        return None

    def addMaskPixmap(self, imageArr_3d, views, mode="default", color_table=[], plane=0):
        """
        :param imageArr: 3d numpy array
        :param plane: 0-sagittal, 1-coronal, 2-axial
        :function: add pixmap to scene
        """
        if color_table == []:
            color_table = imri_setting.getMaskColorTable()

        if mode == "Fusion":
            mask_pixmap_items = self.fusion_mask_pixmap_items
        elif mode == "BrainSeg":
            mask_pixmap_items = self.brain_seg_mask_pixmap_items
        elif mode == "Vessel":
            mask_pixmap_items = self.vessel_pixmap_items
        else:
            print("addMaskPixmap mode error")
            return None

        dim = 4 - sum(imageArr_3d.shape[i] == 1 for i in range(3))
        if mask_pixmap_items[plane] in self.scenes[plane].items():
            self.scenes[plane].removeItem(mask_pixmap_items[plane])

        if dim == 3:
            imageArr_2d = np.squeeze(imageArr_3d)
            imageArr_2d = imageArr_2d.astype(np.uint8)
            qimage = QImage(imageArr_2d.data, imageArr_2d.shape[1], imageArr_2d.shape[0], imageArr_2d.strides[0], QImage.Format_Indexed8)
            qimage.setColorTable(color_table)
        else:
            # dim == 2
            print("incorrect mask image dimension")
            return None

        Mask_QPixmap = QPixmap.fromImage(qimage)
        view_rect = views[plane].contentsRect()
        view_w = view_rect.width()
        view_h = view_rect.height()
        mask_pixmap_items[plane].setPixmap(Mask_QPixmap.scaled(view_w, view_h, Qt.KeepAspectRatio))
        # mask_pixmap_items[plane].setOpacity(0.5)
        rect = mask_pixmap_items[plane].boundingRect()
        mask_pixmap_items[plane].setPos(-rect.width() / 2, -rect.height() / 2)
        mask_pixmap_items[plane].setZValue(-1)
        if mask_pixmap_items[plane] not in self.scenes[plane].items():
            self.scenes[plane].addItem(mask_pixmap_items[plane])
        return None

    def resizePixmap(self, scene_w, scene_h, plane=0):
        """
        resize pixmap as same as scene size but keep aspect ratio AND set pixmap_item position to center
        """
        self.pixmap_items[plane].setPixmap(self.pixmaps[plane].scaled(scene_w, scene_h, Qt.KeepAspectRatio))
        pixmap_item_rect = self.pixmap_items[plane].boundingRect()
        self.pixmap_items[plane].setPos(-pixmap_item_rect.width() / 2, -pixmap_item_rect.height() / 2)

    def getPixmapsSize(self):
        """
        :return: pixmap size
        """
        pixmaps_size = []
        for i in range(0, 3):
            pixmap_item_rect = self.pixmap_items[i].boundingRect()
            pixmaps_size.append([pixmap_item_rect.width(), pixmap_item_rect.height()])
        return pixmaps_size

    def getGrayValue(self, pos2d, plane=0):
        """
        Get the grayscale value of a coordinate point in a two-dimensional image
        :param pos2d: coordinates of the two-dimensional image in pixmap_item, type: [x, y]
        for pos2d,  need to set the origin of the image to the left upper corner
        """
        pixmaps_size = self.getPixmapsSize()  # [[sag_w, sag_h], [cor_w, cor_h], [axi_w, axi_h]]
        origin_array = self.original_imageArrs[plane]  # original image array
        # Map the currently zoomed-in or zoomed-out image coordinates back to the original image coordinates.
        w = origin_array.shape[1]
        h = origin_array.shape[0]
        new_pos = [0, 0]
        new_pos[0] = pos2d[0] + pixmaps_size[plane][0] / 2
        new_pos[1] = pos2d[1] + pixmaps_size[plane][1] / 2
        x = int(new_pos[0] / pixmaps_size[plane][0] * w)
        y = int(new_pos[1] / pixmaps_size[plane][1] * h)
        if x >= w or y >= h or x <= 0 or y <= 0:
            return 0
        else:
            return int(origin_array[y, x])

    def updateCrossLine(self, view_w, view_h, plane=0):
        """
        :param plane: 0-sagittal, 1-coronal, 2-axial
        :function: add cross line to scene
        """

        self.removeCrossLine(plane)
        if plane == 0:
            self.cross_line[plane][0].setPen(Qt.green)
            self.cross_line[plane][1].setPen(Qt.red)
        elif plane == 1:
            self.cross_line[plane][0].setPen(Qt.yellow)
            self.cross_line[plane][1].setPen(Qt.red)
        else:
            self.cross_line[plane][0].setPen(Qt.yellow)
            self.cross_line[plane][1].setPen(Qt.green)

        self.cross_line[plane][0].setLine(0, -view_h / 2, 0, view_h / 2)  # horizontal line
        self.cross_line[plane][1].setLine(-view_w / 2, 0, view_w / 2, 0)  # vertical line

        self.scenes[plane].addItem(self.cross_line[plane][0])
        self.scenes[plane].addItem(self.cross_line[plane][1])
        return None

    def removeCrossLine(self, plane=0):
        """
        :param plane: 0-sagittal, 1-coronal, 2-axial
        :function: remove cross line from scene
        """
        if self.cross_line[plane][0] in self.scenes[plane].items():
            self.scenes[plane].removeItem(self.cross_line[plane][0])
        if self.cross_line[plane][1] in self.scenes[plane].items():
            self.scenes[plane].removeItem(self.cross_line[plane][1])
        return None

    def setCrossLine(self, view_w, view_h, pos, plane=0):
        """
        :param pos: [x, y] in image coordinate
        :param plane: 0-sagittal, 1-coronal, 2-axial
        :function: set cross line position
        """
        h_line = view_h / 2
        v_line = view_w / 2
        self.cross_line[plane][0].setLine(pos[0], -h_line, pos[0], h_line)  # horizontal line
        self.cross_line[plane][1].setLine(-v_line, pos[1], v_line, pos[1])  # vertical line
        return None

    def resizeCrossLine(self, view_w, view_h, plane=0):
        """
        :param plane: 0-sagittal, 1-coronal, 2-axial
        :function: resize cross line to fit view
        """
        self.cross_line[plane][0].setLine(0, -view_h / 2, 0, view_h / 2)  # horizontal line
        self.cross_line[plane][1].setLine(-view_w / 2, 0, view_w / 2, 0)  # vertical line
        return None

    def createPathLineItem(self, pos1, pos2, color_start=[0, 255, 0], color_end=[255, 0, 0], width=1):
        line_item = QGraphicsLineItem(pos1[0], pos1[1], pos2[0], pos2[1])
        pen = QPen()
        gradient = QLinearGradient(pos1[0], pos1[1], pos2[0], pos2[1])
        gradient.setColorAt(0.0, QColor(color_start[0], color_start[1], color_start[2]))
        gradient.setColorAt(0.5, QColor(255, 165, 0))
        gradient.setColorAt(1.0, QColor(color_end[0], color_end[1], color_end[2]))
        pen.setBrush(gradient)
        pen.setWidth(width)
        pen.setStyle(Qt.DashLine)
        line_item.setPen(pen)
        return line_item

    def createLineItem(self, pos1, pos2, color=[0, 255, 0], width=1, style=Qt.SolidLine):
        line_item = QGraphicsLineItem(pos1[0], pos1[1], pos2[0], pos2[1])
        pen = QPen()
        pen.setColor(QColor(color[0], color[1], color[2]))
        pen.setWidth(width)
        pen.setStyle(style)
        line_item.setPen(pen)
        return line_item

    def createPlanPointItem(self, pos, color=[0, 255, 0], diameter=30):
        circle_item = QGraphicsEllipseItem(pos[0] - diameter / 2, pos[1] - diameter / 2, diameter, diameter)
        pen = QPen()
        pen.setColor(QColor(color[0], color[1], color[2]))
        pen.setWidth(1)
        pen.setStyle(Qt.SolidLine)
        circle_item.setPen(pen)
        brush = QBrush()
        brush.setColor(QColor(255, 255, 255, 0))  # rgba
        brush.setStyle(Qt.SolidPattern)
        circle_item.setBrush(brush)

        point_item = QGraphicsEllipseItem(pos[0] - diameter / 10, pos[1] - diameter / 10, diameter / 5, diameter / 5)
        point_item.setPen(pen)
        brush = QBrush()
        brush.setColor(QColor(color[0], color[1], color[2]))
        brush.setStyle(Qt.SolidPattern)
        point_item.setBrush(brush)

        line_item1 = QGraphicsLineItem(pos[0] + diameter / 3, pos[1], pos[0] + diameter / 2, pos[1])
        line_item2 = QGraphicsLineItem(pos[0] - diameter / 3, pos[1], pos[0] - diameter / 2, pos[1])
        line_item3 = QGraphicsLineItem(pos[0], pos[1] + diameter / 3, pos[0], pos[1] + diameter / 2)
        line_item4 = QGraphicsLineItem(pos[0], pos[1] - diameter / 3, pos[0], pos[1] - diameter / 2)
        line_item1.setPen(pen)
        line_item2.setPen(pen)
        line_item3.setPen(pen)
        line_item4.setPen(pen)

        point_item_group = QGraphicsItemGroup()
        point_item_group.addToGroup(circle_item)
        point_item_group.addToGroup(point_item)
        point_item_group.addToGroup(line_item1)
        point_item_group.addToGroup(line_item2)
        point_item_group.addToGroup(line_item3)
        point_item_group.addToGroup(line_item4)

        point_item_group.setZValue(1)
        # point_item_group.setFlag(QGraphicsItem.ItemIsMovable)
        return point_item_group

    def createPointItem(self, pos, color=[0, 255, 0], diameter=30):
        circle_item = QGraphicsEllipseItem(pos[0] - diameter / 2, pos[1] - diameter / 2, diameter, diameter)
        pen = QPen()
        pen.setColor(QColor(color[0], color[1], color[2]))
        pen.setWidth(1)
        pen.setStyle(Qt.SolidLine)
        circle_item.setPen(pen)
        brush = QBrush()
        brush.setColor(QColor(255, 255, 255, 0))  # rgba
        brush.setStyle(Qt.SolidPattern)
        circle_item.setBrush(brush)

        point_item = QGraphicsEllipseItem(pos[0] - diameter / 10, pos[1] - diameter / 10, diameter / 5, diameter / 5)
        point_item.setPen(pen)
        brush = QBrush()
        brush.setColor(QColor(color[0], color[1], color[2]))
        brush.setStyle(Qt.SolidPattern)
        point_item.setBrush(brush)

        line_item1 = QGraphicsLineItem(pos[0] + diameter / 3, pos[1], pos[0] + diameter / 2, pos[1])
        line_item2 = QGraphicsLineItem(pos[0] - diameter / 3, pos[1], pos[0] - diameter / 2, pos[1])
        line_item3 = QGraphicsLineItem(pos[0], pos[1] + diameter / 3, pos[0], pos[1] + diameter / 2)
        line_item4 = QGraphicsLineItem(pos[0], pos[1] - diameter / 3, pos[0], pos[1] - diameter / 2)
        line_item1.setPen(pen)
        line_item2.setPen(pen)
        line_item3.setPen(pen)
        line_item4.setPen(pen)

        point_item_group = QGraphicsItemGroup()
        point_item_group.addToGroup(circle_item)
        point_item_group.addToGroup(point_item)
        point_item_group.addToGroup(line_item1)
        point_item_group.addToGroup(line_item2)
        point_item_group.addToGroup(line_item3)
        point_item_group.addToGroup(line_item4)

        point_item_group.setZValue(1)
        return point_item_group

    def addOrientationText(self, view, plane=0):
        """
        :param view_w, view_h: view weight and height
        :param plane: 0-sagittal, 1-coronal, 2-axial
        :function: add text to scene
        """
        self.removeOrientationText(plane)

        orientation_letter = [
            ["A", "S", "P", "I"],
            ["R", "S", "L", "I"],
            ["R", "A", "L", "P"],
        ]  # sagittal, coronal, axial
        pos = self.getLetterPos(view)
        for i in range(4):
            self.text_item = QGraphicsTextItem(orientation_letter[plane][i])
            self.text_item.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
            self.text_item.setFont(QFont("Arial", 18))
            self.text_item.setDefaultTextColor(QColor(255, 215, 0))  # gold
            self.scenes[plane].addItem(self.text_item)
            self.text_item.setPos(pos[plane][i][0], pos[plane][i][1])
            self.text_items[plane].append(self.text_item)
        return None

    def getLetterPos(self, view):
        """
        :param view
        :return: text position
        :function: get text position [[[pos1],[pos2],[pos3],[pos4]],[....],[....]] size:3*4*2
        """
        x = view.rect().x()
        y = view.rect().y()
        w = view.rect().width()
        h = view.rect().height()
        pos = view.mapToScene(x, y, w - 50, h - 50)
        x1 = pos.boundingRect().x()
        y1 = pos.boundingRect().y()
        x2 = x1 + pos.boundingRect().width()
        y2 = y1 + pos.boundingRect().height()
        pos = []
        for _ in range(3):
            tmp = []
            tmp.append([x1, (y1 + y2) / 2])
            tmp.append([(x1 + x2) / 2, y1])
            tmp.append([x2, (y1 + y2) / 2])
            tmp.append([(x1 + x2) / 2, y2])
            pos.append(tmp)
        return pos

    def resizeOrientationText(self, view, plane=0):
        """
        :param view_w, view_h: view weight and height
        :param plane: 0-sagittal, 1-coronal, 2-axial
        :function: resize text to fit view
        """
        pos = self.getLetterPos(view)
        for i in range(4):
            self.text_items[plane][i].setPos(pos[plane][i][0], pos[plane][i][1])
        return None

    def removeOrientationText(self, plane=0):
        """
        :param plane: 0-sagittal, 1-coronal, 2-axial
        :function: remove text from scene
        """

        for i in range(4):
            if self.text_items[plane] != []:
                if self.text_items[plane][i] in self.scenes[plane].items():
                    self.scenes[plane].removeItem(self.text_items[plane][i])
        self.text_items[plane] = []
        return None

    def addRuler(self, ImageData, view, plane=0):
        """
        :param view
        :function: add ruler to scene
        """
        self.removeRuler(plane)
        pos = self.getRulerPos(ImageData, view, plane)
        pen = QPen()
        pen.setColor(QColor(0, 255, 0))
        pen.setWidth(0)  # must be 0 to make the line width fixed
        pen.setStyle(Qt.SolidLine)
        # self.ruler_items[plane].setFlag(QGraphicsItem.ItemIgnoresTransformations, True) #not need
        self.ruler_items[plane].setPen(pen)
        self.ruler_items[plane].setLine(pos[0], pos[1], pos[2], pos[3])

        text = "1 cm"
        self.ruler_text_items[plane].setPlainText(text)
        self.ruler_text_items[plane].setFont(QFont("Arial", 8))
        self.ruler_text_items[plane].setDefaultTextColor(QColor(0, 255, 0))
        self.ruler_text_items[plane].setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        self.ruler_text_items[plane].setPos(pos[4], pos[5])

        self.scenes[plane].addItem(self.ruler_items[plane])
        self.scenes[plane].addItem(self.ruler_text_items[plane])
        return None

    def getRulerPos(self, ImageData, view, plane=0):
        x = view.rect().x()
        y = view.rect().y()
        w = view.rect().width()
        h = view.rect().height()
        start = w - 50

        left_pos = view.mapToScene(x, y, start - 100, h - 25)
        x1 = left_pos.boundingRect().x()
        y1 = left_pos.boundingRect().y()
        left_x = x1 + left_pos.boundingRect().width()
        left_y = y1 + left_pos.boundingRect().height()

        right_pos = view.mapToScene(x, y, start, h - 25)
        x1 = right_pos.boundingRect().x()
        y1 = right_pos.boundingRect().y()
        right_x = x1 + right_pos.boundingRect().width()
        right_y = y1 + right_pos.boundingRect().height()

        _, left_world_units = ImageData.ImageToWorld([left_x, left_y], self.getPixmapsSize(), plane)
        _, right_world_units = ImageData.ImageToWorld([right_x, right_y], self.getPixmapsSize(), plane)
        distance = np.sqrt((right_world_units[0] - left_world_units[0]) ** 2 + (right_world_units[1] - left_world_units[1]) ** 2 + (right_world_units[2] - left_world_units[2]) ** 2)

        ruler_length = 10  # mm
        # print(distance)
        if distance <= 0:
            scale = 1
        else:
            scale = ruler_length / distance
        # print(x, y, w, h, start)
        moved_left_pos = view.mapToScene(x, y, start - 100 * scale, h - 25)
        x1 = left_pos.boundingRect().x()
        y1 = left_pos.boundingRect().y()
        moved_left_x = x1 + moved_left_pos.boundingRect().width()

        text_pos = view.mapToScene(x, y, start - 50, h - 60)
        x1 = left_pos.boundingRect().x()
        y1 = left_pos.boundingRect().y()
        text_x = x1 + text_pos.boundingRect().width()
        text_y = y1 + text_pos.boundingRect().height()

        return [moved_left_x, left_y, right_x, right_y, text_x, text_y]

    def resizeRuler(self, ImageData, view, plane=0):
        pos = self.getRulerPos(ImageData, view, plane)
        self.ruler_items[plane].setLine(pos[0], pos[1], pos[2], pos[3])
        self.ruler_text_items[plane].setPos(pos[4], pos[5])
        return None

    def removeRuler(self, plane=0):
        if self.ruler_items[plane] in self.scenes[plane].items():
            self.scenes[plane].removeItem(self.ruler_items[plane])
        if self.ruler_text_items[plane] in self.scenes[plane].items():
            self.scenes[plane].removeItem(self.ruler_text_items[plane])
        return None

    def addInfoText(self, view, plane=0):
        self.removeInfoText(plane)

        Infos = imri_setting.IMRIGlobal
        if Infos.Mode == "NIFIT":
            text = "上海交通大学医疗机器人研究院\n" + "NIFIT\n"
        else:
            text = "上海交通大学医疗机器人研究院\n" + "DICOM\n" + str(Infos.Name) + "\n" + str(Infos.ProtocolName) + "\n" + str(Infos.Sex) + "  " + str(Infos.Age) + "\n" + str(Infos.Date)
        pos = self.getInfoTextPos(view)
        self.info_text_items[plane].setPlainText(text)
        self.info_text_items[plane].setFont(QFont("Microsoft YaHei", 8))
        self.info_text_items[plane].setDefaultTextColor(QColor(0, 255, 0))
        self.info_text_items[plane].setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        self.info_text_items[plane].setPos(pos[0], pos[1])
        self.scenes[plane].addItem(self.info_text_items[plane])
        return None

    def getInfoTextPos(self, view):
        pos = view.mapToScene(view.rect())
        x1 = pos.boundingRect().x()
        y1 = pos.boundingRect().y()
        return x1, y1

    def resizeInfoText(self, view, plane=0):
        pos = self.getInfoTextPos(view)
        self.info_text_items[plane].setPos(pos[0], pos[1])
        return None

    def removeInfoText(self, plane=0):
        if self.info_text_items[plane] in self.scenes[plane].items():
            self.scenes[plane].removeItem(self.info_text_items[plane])
        return None

    def resizePlanes(self, views, ImageData):
        for i in range(3):
            view_w, view_h = self.resizeScene(views, plane=i)
            self.resizePixmap(view_w, view_h, plane=i)
            self.resizeCrossLine(view_w, view_h, plane=i)
            self.resizeOrientationText(views[i], plane=i)
            self.resizeRuler(ImageData, views[i], plane=i)
            self.resizeInfoText(views[i], plane=i)
