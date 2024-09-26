from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import ultralytics
import numpy as np
import cv2
import socket
import imri_setting
from MARModule import predict as MAR_predict
import torch
import SimpleITK as sitk
import os
import datetime


class NeedleRecog:
    def __init__(self):
        self.yolo_model = None
        self.sam_predictor = None
        self.ImageData = None
        self.box = None  # [x1, y1, x2, y2] in image coordinate
        self.box_voxel = None  # [x1, y1, x2, y2] in voxel coordinate
        self.box_vtk = None  # [x1, y1, z1,x2, y2,z2] in vtk coordinate
        self.up2down = False
        self.x_tip = None  # needle tip x coordinate
        self.y_tip = None  # needle tip y coordinate
        self.needle_tip_vtk = None
        self.needle_tip_plane_item = None
        self.config = imri_setting.read_config()
        self.recog_algorithm_mode = 0  # 0: needle recog (artifact), 1: needle recog (no artifact)
        self.progress_MAR_value = 0
        self.progress_YoloAndSam_value = 0
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # draw box
        self.box_item = None  # QGraphicsRectItem
        color = self.config["needle_recog"]["box_color_2d"]
        width = self.config["needle_recog"]["box_width_2d"]
        self.box_pen = QPen(QColor(color[0], color[1], color[2]))
        self.box_pen.setWidth(width)
        self.plane = None
        self.mode = None
        self.z_slice_num = 0
        self.needle_file_path = None

    def init(self, ui, Image3d, ImagePlanes, image_read_signal):
        self.Image3d = Image3d
        self.ImagePlanes = ImagePlanes
        self.ui = ui
        self.image_read_signal = image_read_signal
        self.load_model_button = ui.load_model_btn
        self.load_model_progress = ui.load_model_progressBar
        self.show_needle_tip_checkBox = ui.show_needle_tip_checkBox
        self.send_to_robot_checkBox = ui.send_to_robot_checkBox
        self.up_to_down_checkBox = ui.up_to_down_checkBox
        self.auto_tracking_btn = ui.auto_tracking_btn
        self.use_custom_box_checkBox = ui.use_custom_box_checkBox
        self.choose_box_btn = ui.choose_box_btn
        self.show_box_checkBox = ui.show_box_checkBox
        self.tracking_btn = ui.tracking_btn
        self.tracking_textBrowser = ui.tracking_textBrowser
        self.reg_algorithm_combobox = ui.RecogAlgorithmComboBox
        self.reg_algorithm_combobox.addItem("Needle Recog (Artifact)")
        self.reg_algorithm_combobox.addItem("Needle Recog (No Artifact)")

        # connect button
        self.reg_algorithm_combobox.currentIndexChanged.connect(self.changeRegAlgorithm)
        self.load_model_button.clicked.connect(self.loadModel)
        self.load_model_progress.setRange(0, 100)
        self.load_model_progress.setValue(0)
        self.auto_tracking_btn.clicked.connect(self.autoTracking)
        self.tracking_btn.clicked.connect(self.tracking)
        self.show_needle_tip_checkBox.setChecked(True)
        self.show_needle_tip_checkBox.stateChanged.connect(self.showNeedleTip)
        self.send_to_robot_checkBox.stateChanged.connect(self.sendToRobot)
        self.up_to_down_checkBox.stateChanged.connect(self.upToDown)
        self.use_custom_box_checkBox.stateChanged.connect(self.useCustomBox)
        self.choose_box_btn.clicked.connect(self.chooseBoxBtn)
        self.show_box_checkBox.stateChanged.connect(self.showBox)

        # button status
        self.auto_tracking_btn.setEnabled(False)
        self.tracking_btn.setEnabled(False)
        self.choose_box_btn.setEnabled(False)

        # 创建一个新的文件，用于保存针尖识别的数据
        current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.needle_file_path = f"output/NeedleTip/NeedleTip_{current_time}.txt"
        if not os.path.exists(self.needle_file_path):
            file = open(self.needle_file_path, "w")
            file.close()
    def changeRegAlgorithm(self, index):
        if index == 0:
            self.recog_algorithm_mode = index
            self.tracking_textBrowser.append("Needle Recog (Artifact)")
            self.up_to_down_checkBox.setDisabled(True)
            self.use_custom_box_checkBox.setDisabled(True)
            self.use_custom_box_checkBox.setCheckState(Qt.Unchecked)
            self.choose_box_btn.setDisabled(True)
            self.choose_box_btn.setStyleSheet(self.config["button"]["disabled"])
            self.show_box_checkBox.setDisabled(True)
            self.show_box_checkBox.setCheckState(Qt.Unchecked)

            self.load_model_progress.setValue(self.progress_MAR_value)

        elif index == 1:
            self.recog_algorithm_mode = index
            self.tracking_textBrowser.append("Needle Recog (No Artifact)")
            self.up_to_down_checkBox.setEnabled(True)
            self.use_custom_box_checkBox.setEnabled(True)
            self.choose_box_btn.setEnabled(True)
            self.choose_box_btn.setStyleSheet(self.config["button"]["normal"])
            self.show_box_checkBox.setEnabled(True)

            self.load_model_progress.setValue(self.progress_YoloAndSam_value)

        else:
            pass

    def loadModel(self):
        if self.recog_algorithm_mode == 0:
            self.loadMARModel()
        elif self.recog_algorithm_mode == 1:
            self.loadYoloAndSamModel()
        else:
            pass

    def loadYoloAndSamModel(self):
        try:
            # load YOLO model
            self.yolo_model = ultralytics.YOLO("./yolov8/best_phantom.pt")
            self.load_model_progress.setValue(20)
            # load SAM model
            from segment_anything import sam_model_registry, SamPredictor

            sam_checkpoint = "./segment_anything/sam_vit_h_4b8939.pth"
            model_type = "vit_h"
            device = "cuda"
            self.load_model_progress.setValue(50)

            sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
            sam.to(device=device)
            self.load_model_progress.setValue(80)

            self.sam_predictor = SamPredictor(sam)
            self.load_model_progress.setValue(100)
            self.auto_tracking_btn.setEnabled(True)
            self.tracking_btn.setEnabled(True)
            self.tracking_textBrowser.append("Initialize Yolo And Sam successfully")
            self.progress_YoloAndSam_value = 100
        except:
            self.tracking_textBrowser.append("Initialize Yolo And Sam failed")
            self.progress_YoloAndSam_value = 0
            meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Load model failed!")
            meg_box.exec_()

    def loadMARModel(self):
        try:

            model_path = "./MARModule/best_model-PSNR=34.55.ckpt"
            tip_data_path = "./MARModule/tip_data.npy"
            self.load_model_progress.setValue(20)
            inpaint_model, shape_recon_model = MAR_predict.load_model(model_path=model_path, template_path=tip_data_path, device=self.device)
            self.inpaint_model = inpaint_model
            self.shape_recon_model = shape_recon_model
            self.load_model_progress.setValue(100)
            self.auto_tracking_btn.setEnabled(True)
            self.tracking_btn.setEnabled(True)
            self.tracking_textBrowser.append("Initialize MAR successfully")
            self.progress_MAR_value = 100
        except:
            self.tracking_textBrowser.append("Initialize MAR failed")
            self.progress_MAR_value = 0
            meg_box = QMessageBox(QMessageBox.Critical, "ERROR", "Load model failed!")
            meg_box.exec_()

    def autoTracking(self):

        if self.auto_tracking_btn.text() == "Auto Tracking":
            self.tracking_textBrowser.append("Start auto tracking")
            self.auto_tracking_btn.setText("Stop Tracking")
            self.auto_tracking_btn.setStyleSheet(self.config["button"]["active"])
            self.choose_box_btn.setEnabled(False)
            self.tracking_btn.setEnabled(False)

            # auto tracking
            # main.py showReadImage -> auto tracking -> showNeedleTip -> sendToRobot

        else:
            self.tracking_textBrowser.append("Stop auto tracking")
            self.auto_tracking_btn.setText("Auto Tracking")
            self.auto_tracking_btn.setStyleSheet(self.config["button"]["normal"])
            self.choose_box_btn.setEnabled(True)
            self.tracking_btn.setEnabled(True)
            self.needle_file_path = None

    def tracking(self):
        nii_image = self.ImageData.Vtk2Numpy(self.ImageData.data)
        nii_image = np.transpose(nii_image, (1, 2, 0))
        nii_image_2d = np.squeeze(nii_image)
        if nii_image_2d.ndim == 2:
            self.z_slice_num = 0
            if self.recog_algorithm_mode == 0:
                self.predict_MAR(nii_image_2d)
            elif self.recog_algorithm_mode == 1:
                self.predict_YoloAndSam(nii_image_2d)
            else:
                return None

        else:
            # 3d image [cor, sag, axi]
            self.z_slice_num = self.ImageData.current_slice[self.ImageData.acqMode]
            if self.recog_algorithm_mode == 0:
                print("No MAR 3D!")
            elif self.recog_algorithm_mode == 1:
                self.predict_YoloAndSam_3D(nii_image)
            else:
                return None

        self.updateNeedleTip2d()
        self.sendToRobot()
        self.tracking_textBrowser.append("")

    def showNeedleTip(self):
        if self.x_tip != None and self.y_tip != None:
            if self.show_needle_tip_checkBox.isChecked():
                self.updateNeedleTip2d()
            else:
                self.removeNeedleTip2d()

    def sendToRobot(self):
        if self.send_to_robot_checkBox.isChecked():
            try:
                if self.x_tip == None or self.y_tip == None:
                    self.tracking_textBrowser.append("No needle tip position")
                    return None
                voxel_pos = [self.x_tip, self.y_tip, 0]
                world_pos = self.ImageData.VoxelToWorld(voxel_pos)
                # robot_needle_tip = imri_setting.worldToRobot(world_pos)
                # print(robot_needle_tip)
                dis = self.getDisFromTarget()
                # needle_tip_info = "02," + str(robot_needle_tip[0][0]) + "," + str(robot_needle_tip[1][0]) + "," + str(robot_needle_tip[2][0]) + "," + str(dis)
                needle_tip_info = str(dis) + " "
                robot_ip = self.config["main"]["robot_ip"]
                robot_port = self.config["main"]["robot_port"]
                if self.send_to_robot_checkBox.isChecked():
                    self.tracking_textBrowser.append("Send needle tip  to robot successfully")
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    server_address = (robot_ip, robot_port)
                    sock.connect(server_address)
                    sock.sendall(needle_tip_info.encode())
                    sock.close()
            except:
                self.tracking_textBrowser.append("Send Needle Tip Info to Robot Failed")
        else:
            self.tracking_textBrowser.append("Send to robot is not checked")

    def getDisFromTarget(self):
        self.dis = 0
        if self.x_tip == None and self.y_tip == None:
            return 0
        else:
            voxel_pos = [self.x_tip, self.y_tip, self.z_slice_num]
            world_pos = self.ImageData.VoxelToWorld(voxel_pos)
            target_pos = imri_setting.IMRIGlobal.target_pos
            # self.dis = np.sqrt((world_pos[0] - target_pos[0]) ** 2 + (world_pos[1] - target_pos[1]) ** 2 + (world_pos[2] - target_pos[2]) ** 2)
            self.dis = np.sqrt((world_pos[1] - target_pos[1]) ** 2 + (world_pos[2] - target_pos[2]) ** 2)
            self.tracking_textBrowser.append("Distance: " + str(round(self.dis, 2)) + " mm")
            if self.needle_file_path != None:
                current_time = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                with open(self.needle_file_path, "a") as f:
                    tmp = "%s  Target:%f %f %f  NeedleTip:%f %f %f  Distance(YZ):%f" % (
                        current_time,
                        round(target_pos[0],2),
                        round(target_pos[1],2),
                        round(target_pos[2],2),
                        round(world_pos[0],2),
                        round(world_pos[1],2),
                        round(world_pos[2],2),
                        round(self.dis,2),
                    )
                    f.write(f"{tmp}\n")
            return self.dis

    def upToDown(self):
        if self.up_to_down_checkBox.isChecked():
            self.up2down = True
        else:
            self.up2down = False

    def useCustomBox(self):
        if self.use_custom_box_checkBox.isChecked():
            self.choose_box_btn.setEnabled(True)
        else:
            self.choose_box_btn.setEnabled(False)

    def chooseBoxBtn(self):
        self.mode = "choose_box1"
        self.choose_box_btn.setStyleSheet(self.config["button"]["active"])
        self.show_box_checkBox.setChecked(True)
        if self.box_item != None:
            self.box_item.setVisible(False)

    def chooseBox(self):
        """
        choose box from 2d image
        """
        self.box_item.setRect(self.box[0], self.box[1], self.box[2] - self.box[0], self.box[3] - self.box[1])
        start_pos_voxel, start_pos_vtk = self.ImageData.ImageToWorld([self.box[0], self.box[1]], self.ImagePlanes.getPixmapsSize(), self.plane)  # [l,p,s]
        end_pos_voxel, end_pos_vtk = self.ImageData.ImageToWorld([self.box[2], self.box[3]], self.ImagePlanes.getPixmapsSize(), self.plane)  # [l,p,s]
        self.box_voxel = [start_pos_voxel[0], start_pos_voxel[1], end_pos_voxel[0], end_pos_voxel[1]]
        self.box_vtk = [start_pos_vtk[0], start_pos_vtk[1], start_pos_vtk[2], end_pos_vtk[0], end_pos_vtk[1], end_pos_vtk[2]]

    def showBox(self):
        if self.show_box_checkBox.isChecked():
            if self.box_item != None:
                self.box_item.setVisible(True)
        else:
            if self.box_item != None:
                self.box_item.setVisible(False)

    def resizeBox(self):
        """
        resize area item when scene size changed
        """
        start_pos, _ = self.ImageData.WorldToImage([self.box_vtk[0], self.box_vtk[1], self.box_vtk[2]], self.ImagePlanes.getPixmapsSize(), self.plane)
        end_pos, _ = self.ImageData.WorldToImage([self.box_vtk[3], self.box_vtk[4], self.box_vtk[5]], self.ImagePlanes.getPixmapsSize(), self.plane)
        self.box = [start_pos[0], start_pos[1], end_pos[0], end_pos[1]]
        if self.box_item.isVisible():
            self.box_item.setRect(self.box[0], self.box[1], self.box[2] - self.box[0], self.box[3] - self.box[1])

    def updateNeedleTip(self):
        # 当切换图像时，需要根据之前针尖的世界坐标系来更新图像中的针尖位置
        if self.needle_tip_vtk != None and self.show_needle_tip_checkBox.isChecked():
            self.removeNeedleTip2d()
            image_pos, z = self.ImageData.WorldToImage(self.needle_tip_vtk, imgSize=self.ImagePlanes.getPixmapsSize(), plane=self.ImageData.acqMode)
            self.needle_tip_plane_item = self.ImagePlanes.createPointItem([image_pos[0], image_pos[1]], color=[255, 0, 0], diameter=15)
            self.needle_tip_plane_item.setZValue(1)
            self.ImagePlanes.addPlaneItem(self.needle_tip_plane_item, plane=self.ImageData.acqMode)

    def updateNeedleTip2d(self):
        try:
            self.removeNeedleTip2d()
            # acqMode 0-Sag,1-Cor,2-Axi
            if self.x_tip != None and self.y_tip != None:
                voxel_pos = [self.x_tip, self.y_tip, self.z_slice_num]
                world_pos = self.ImageData.VoxelToWorld(voxel_pos)
                self.needle_tip_vtk = world_pos
                image_pos, z = self.ImageData.WorldToImage(world_pos, imgSize=self.ImagePlanes.getPixmapsSize(), plane=self.ImageData.acqMode)
                self.needle_tip_plane_item = self.ImagePlanes.createPointItem([image_pos[0], image_pos[1]], color=[255, 0, 0], diameter=15)
                self.needle_tip_plane_item.setZValue(1)
                self.ImagePlanes.addPlaneItem(self.needle_tip_plane_item, plane=self.ImageData.acqMode)
                self.tracking_textBrowser.append("Needle tip world pos: " + str(world_pos[0]) + ", " + str(world_pos[1]) + ", " + str(world_pos[2]))
                if self.needle_file_path != None:
                    current_time = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                    with open(self.needle_file_path, "a") as f:
                        tmp = "%s  NeedleTip:%f %f %f" % (
                            current_time,
                            round(world_pos[0],2),
                            round(world_pos[1],2),
                            round(world_pos[2],2),
                        )
                        f.write(f"{tmp}\n")
            else:
                self.tracking_textBrowser.append("No needle tip position")
        except:
            self.tracking_textBrowser.append("Update needle tip 2d error")

    def removeNeedleTip2d(self):
        if self.needle_tip_plane_item != None:
            for i in range(3):
                self.ImagePlanes.removePlaneItem(self.needle_tip_plane_item, plane=i)

    def predict_MAR(self, image_pre):
        # rescale image to 0-1
        image_pre = (image_pre - np.min(image_pre)) / (np.max(image_pre) - np.min(image_pre))

        self.tracking_textBrowser.append("MAR: Start prediction")
        pred_image, pos, angle, val = MAR_predict.predict(self.inpaint_model, self.shape_recon_model, image_pre, device=self.device)

        if pos == None:
            self.tracking_textBrowser.append("MAR: Prediction failed")
            self.x_tip = None
            self.y_tip = None
            return None
        else:
            self.tracking_textBrowser.append("MAR: Needle tip voxel pos: " + str(round(pos[0], 1)) + ", " + str(round(pos[1], 1)))
            self.tracking_textBrowser.append("MAR: Needle tip angle: " + str(round(angle, 1)))
            self.tracking_textBrowser.append("MAR: Needle tip val: " + str(round(val, 1)))
            self.x_tip = pos[1]
            self.y_tip = pos[0]

        self.saveMARImage(pred_image)

    def predict_YoloAndSam(self, image_pre):
        """
        :param image_pre: image for prediction size: 2d
        :param up2down: True: insert needle from top to bottom ; False: insert needle from bottom to top
        """
        image_pre = (image_pre - np.min(image_pre)) / (np.max(image_pre) - np.min(image_pre)) * 255
        image_EP = cv2.edgePreservingFilter(image_pre, flags=1, sigma_s=1, sigma_r=0.1)
        image_EP = gammacorrection(image_EP, 0.8)

        image_detect = cv2.cvtColor(image_EP.astype(np.uint8), cv2.COLOR_GRAY2BGR)
        image_detect = cv2.cvtColor(image_detect, cv2.COLOR_BGR2RGB)

        if self.use_custom_box_checkBox.isChecked():
            ####### manual
            self.tracking_textBrowser.append("Use custom box")
            if self.box_voxel == None:
                self.tracking_textBrowser.append("No box selected")
                return None
            else:
                # SAM segment
                mask_1c = np.zeros_like(image_pre)
                box_voxel1 = self.ImageData.WorldToVoxel([self.box_vtk[0], self.box_vtk[1], self.box_vtk[2]])
                box_voxel2 = self.ImageData.WorldToVoxel([self.box_vtk[3], self.box_vtk[4], self.box_vtk[5]])
                self.box_voxel = [box_voxel1[0], box_voxel1[1], box_voxel2[0], box_voxel2[1]]
                input_box = np.array(self.box_voxel)
                self.sam_predictor.set_image(image_detect)
                masks, _, _ = self.sam_predictor.predict(
                    point_coords=None,
                    point_labels=None,
                    box=input_box[None, :],
                    multimask_output=False,
                )
                mask_1c = np.logical_or(mask_1c, masks[0])
                mask_1c = mask_1c.astype(int)

        else:
            ########### YOLO detect
            self.tracking_textBrowser.append("Use YOLO box")
            results = self.yolo_model.predict(source=image_detect, save=False, save_txt=False)  # save predictions as labels
            boxes = results[0].boxes

            if np.size(boxes, 0) > 0:  # if there is needle
                self.tracking_textBrowser.append("YOLO: Needle detected")
                # SAM segment
                mask_1c = np.zeros_like(image_pre)
                for box in boxes:
                    box = box.xyxy[0].cpu().numpy()
                    self.sam_predictor.set_image(image_detect)
                    masks, _, _ = self.sam_predictor.predict(
                        point_coords=None,
                        point_labels=None,
                        box=box[None, :],
                        multimask_output=False,
                    )
                    mask_1c = np.logical_or(mask_1c, masks[0])
                    mask_1c = mask_1c.astype(int)
            else:
                self.tracking_textBrowser.append("YOLO: No needle detected")
                return None

        # if there is masked image
        if np.sum(mask_1c) > 0:
            if self.ui.algorithm2_checkBox.isChecked():
                nii_ball_world = imri_setting.IMRIGlobal.catheter_ball
                nii_nearest_world = imri_setting.IMRIGlobal.catheter_nearest
                if nii_ball_world == [] or nii_nearest_world == []:
                    self.tracking_textBrowser.append("No Catheter ball or nearest point")
                    return None
                else:
                    nii_ball_voxel = self.ImageData.WorldToVoxel(nii_ball_world)
                    nii_nearest_voxel = self.ImageData.WorldToVoxel(nii_nearest_world)
                    nii_ball_voxel = np.reshape(np.array(nii_ball_voxel), (3, 1))
                    nii_nearest_voxel = np.reshape(np.array(nii_nearest_voxel), (3, 1))
                    [x1, y1, self.x_tip, self.y_tip] = tip_localization(mask_1c, up2down=self.up2down, nii_ball=nii_ball_voxel, nii_nearest=nii_nearest_voxel)
            else:
                [x1, y1, self.x_tip, self.y_tip] = needle_localization(mask_1c, up2down=self.up2down, left2right=self.ui.left_to_tight_checkBox.isChecked())
                self.tracking_textBrowser.append("Needle tip voxel pos: " + str(round(self.x_tip, 1)) + ", " + str(round(self.y_tip, 1)))
        else:
            self.x_tip = None
            self.y_tip = None
            self.tracking_textBrowser.append("SAM: No needle segmented")
            return None

        return None

    def predict_YoloAndSam_3D(self, image_pre_3d):
        plane = self.ImageData.acqMode
        current_slice = self.ImageData.current_slice
        slice_num = current_slice[plane]
        # print(image_pre_3d.shape)
        # print("plane: ", plane)
        # print("current_slice: ", slice_num)
        image_pre_2d = image_pre_3d[:, :, slice_num]
        # import matplotlib.pyplot as plt
        # plt.imshow(image_pre_2d, cmap="gray")
        # plt.show()
        self.predict_YoloAndSam(image_pre_2d)

    def updateMARImage(self, file):
        # load output image
        MAR_dict = {"module": "MAR", "path": file, "mode": "image"}
        self.image_read_signal.emit(MAR_dict)

    def saveMARImage(self, pre_image, save_dir="output"):
        pre_image = pre_image[:, :, np.newaxis]
        # for cor
        pre_image = np.transpose(pre_image, (2, 0, 1))
        nii_image = sitk.GetImageFromArray(pre_image)

        nii_image.SetSpacing(self.ImageData.spacing)
        nii_image.SetOrigin(self.ImageData.origin)
        nii_image.SetDirection(tuple(np.squeeze(np.array(self.ImageData.direction).reshape(1, 9))))
        file_name = self.ui.ImageListWidget.currentItem().text()
        output_name = "MAR_" + file_name + ".nii.gz"
        save_path = os.path.join(save_dir, output_name)
        sitk.WriteImage(nii_image, save_path)

        self.updateMARImage(save_path)


def gammacorrection(img, gamma=1.0):
    out = (np.power(img / 255.0, gamma)) * 255
    return out


def masked(image, mask):
    color = np.array([30 * 0.6, 144 * 0.6, 255 * 0.6])
    masked_image = np.zeros_like(image)
    for c in range(3):
        masked_image[:, :, c] = np.where(mask == 1, color[c], image[:, :, c])
    return masked_image


def needle_localization(mask_frame, up2down, left2right):

    if left2right:

        m = mask_frame.shape[0]
        n = mask_frame.shape[1]
        x = np.zeros([m])
        y = np.zeros([n])
        for ii in range(0, n):
            mask_bound = mask_frame[:, ii]
            diff_mask = np.diff(mask_bound)
            coor_edge = np.array(np.nonzero(diff_mask))

            if coor_edge.shape[1] == 1:
                y[ii] = coor_edge[0, 0] + 1
                x[ii] = ii
            if coor_edge.shape[1] == 2:
                y[ii] = int((coor_edge[0, 0] + coor_edge[0, 1]) / 2 + 1)
                x[ii] = ii

        x = x[np.nonzero(x)]
        y = y[np.nonzero(y)]

        p_xy = np.polyfit(x, y, 1)

        x1 = np.arange(np.min(x), np.max(x))
        y1 = np.polyval(p_xy, x1)

    else:
        m = mask_frame.shape[0]
        n = mask_frame.shape[1]
        x = np.zeros([m])
        y = np.zeros([n])
        for ii in range(0, m):
            mask_bound = mask_frame[ii, :]
            diff_mask = np.diff(mask_bound)
            coor_edge = np.array(np.nonzero(diff_mask))

            if coor_edge.shape[1] == 1:
                x[ii] = coor_edge[0, 0] + 1
                y[ii] = ii
            if coor_edge.shape[1] == 2:

                x[ii] = int((coor_edge[0, 0] + coor_edge[0, 1]) / 2 + 1)
                y[ii] = ii

        x = x[np.nonzero(x)]
        y = y[np.nonzero(y)]

        p_yx = np.polyfit(y, x, 1)

        y1 = np.arange(np.min(y), np.max(y))
        x1 = np.polyval(p_yx, y1)

    if up2down:
        x_tip = x1[-1]
        y_tip = y1[-1]
    else:
        x_tip = x1[0]
        y_tip = y1[0]

    return x1, y1, x_tip, y_tip


def tv(input):
    input2 = input.copy()
    input2[1:] = input2[0:-1]
    output = np.abs(input - input2)
    return output


def tip_localization(mask_frame, up2down, nii_ball, nii_nearest):

    # nii_ball: the  ball coordinate in the current image coordinate system
    # nii_nearest: the nearest point coordinate in the current image coordinate system

    # fit the trajectory of the lead
    traj_v = nii_ball[0:2, 0] - nii_nearest[0:2, 0]
    traj_v = traj_v / np.linalg.norm(traj_v)
    k = traj_v[0] / traj_v[1]
    b = nii_ball[0, 0] - k * nii_ball[1, 0]
    p_yx = np.array([k, b])

    # find the needle tip along the trajectory of the lead
    line_bw = np.zeros(mask_frame.shape[1])
    line_yy = np.linspace(0, 255, 256)
    line_xx = np.polyval(p_yx, line_yy)

    for yy in line_yy:

        yy = int(yy)
        if (round(line_xx[yy]) > 0) & (round(line_xx[yy]) < mask_frame.shape[0]):

            if (mask_frame[yy, round(line_xx[yy])]) == 1:

                line_bw[yy] = 1

    y1 = np.squeeze(np.array(np.nonzero(line_bw)))
    x1 = np.polyval(p_yx, y1)

    line_bw_tv = tv(line_bw)
    index_y = np.squeeze(np.array(np.nonzero(line_bw_tv)))

    if up2down:
        y_tip = index_y[1] - 0.5
        x_tip = np.polyval(p_yx, y_tip)

    else:
        y_tip = index_y[0] - 0.5
        x_tip = np.polyval(p_yx, y_tip)

    return x1, y1, x_tip, y_tip
