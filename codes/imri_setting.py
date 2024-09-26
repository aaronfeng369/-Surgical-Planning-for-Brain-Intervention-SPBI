from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import json
from datetime import datetime
import os
import numpy as np
from vtkmodules.util import numpy_support
import vtkmodules.all as vtk


class IMRIGlobal:
    ImageToZframeTransMatrix = []
    ZframeToRobotTransMatrix = []
    # plan path in world coordinate
    target_pos = None
    entry_pos = None
    catheter_nearest = []  # 1*3
    # send to robot
    robot_target = None
    plan_v = None
    robot_nearest = None
    traj_v = None
    angle_error = None
    radial_error = None

    # Image Info
    Mode = "NIFIT"  # DICOM or NIFIT
    Name = None
    Age = None
    Sex = None
    Date = None
    ProtocolName = None


def worldToRobot(point):
    """
    point:[x,y,z,1]
    """

    if len(IMRIGlobal.ImageToZframeTransMatrix) != 0:
        trans_z = np.array(IMRIGlobal.ImageToZframeTransMatrix)
    else:
        trans_z = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
        print("ImageToZframeTransMatrix set default")

    if len(IMRIGlobal.ZframeToRobotTransMatrix) != 0:
        trans_r = np.array(IMRIGlobal.ZframeToRobotTransMatrix)
    else:
        trans_r = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
        print("ZframeToRobotTransMatrix set default")

    point = np.array(point)
    if point.shape == (3,):
        point = np.append(point, 1)
        point = np.reshape(point, (4, 1))
    point_in_zframe = np.matmul(trans_z, point)
    point_in_robot = np.matmul(trans_r, point_in_zframe)
    return point_in_robot[0:3]


def setSpinBox(spinBox, min, max, value, step):
    spinBox.setRange(min, max)
    spinBox.setValue(value)
    spinBox.setSingleStep(step)
    spinBox.setKeyboardTracking(False)


def setSlider(slider, min, max, value, step):
    slider.setRange(min, max)
    slider.setValue(value)
    slider.setSingleStep(step)


def setScrollBar(img_data, scroll_bar, plane=0):
    """
    :param scroll_bar: QScrollBar
    :param min,max,step,value: int
    """
    scroll_bar.setMinimum(img_data.new_extent[2 * plane])
    scroll_bar.setMaximum(img_data.new_extent[2 * plane + 1])
    scroll_bar.setSingleStep(1)
    scroll_bar.setValue(int(0.5 * (img_data.new_extent[2 * plane] + img_data.new_extent[2 * plane + 1])))


def read_config(json_path=os.path.abspath("config/config.json")):
    with open(json_path) as json_file:
        config = json.load(json_file)
    return config


def update_config(json_path=os.path.abspath("config/config.json"), config=None):
    with open(json_path, "w") as json_file:
        json.dump(config, json_file, indent=4)
    return None


# path = os.path.abspath("config.json")
# print(path)


def setAutoSaveFile(config=None):
    time_str = getCurrentTime()
    path = config["main"]["auto_save_directory"]

    main_folder_name = os.path.join(path, f"AutoSave_{time_str}")
    os.makedirs(main_folder_name)

    plan_folder = os.path.join(main_folder_name, "plan")
    registration_folder = os.path.join(main_folder_name, "registration")
    config["main"]["auto_save_plan_directory"] = plan_folder
    config["main"]["auto_save_registration_directory"] = registration_folder
    update_config(config=config)
    os.makedirs(plan_folder)
    os.makedirs(registration_folder)


def getCurrentTime():
    current_time = datetime.now()
    time_str = current_time.strftime("%Y-%m-%d_%H-%M-%S")
    return time_str


def getMaskColorTable():
    color_table = []
    for i in range(256):
        if i == 0:
            color = QColor(0, 0, 0, 128)
        elif i == 1:
            color = QColor(255, 0, 0, 128)
        elif i == 2:
            color = QColor(0, 0, 255, 128)
        elif i == 3:
            color = QColor(0, 255, 0, 128)
        elif i == 4:
            color = QColor(255, 255, 0, 128)
        else:
            color = QColor(0, 0, 0, 0)
        color_table.append(color.rgba())
    return color_table


def ArrayToVTKImageData(array, dim, space, origin, direction):
    vtk_data = numpy_support.numpy_to_vtk(array.ravel(), array_type=vtk.VTK_UNSIGNED_CHAR)
    vtk_img = vtk.vtkImageData()
    vtk_img.SetDimensions(dim)
    vtk_img.SetSpacing(space)
    vtk_img.SetOrigin(origin)
    vtk_img.SetDirectionMatrix(direction)
    vtk_img.GetPointData().SetScalars(vtk_data)
    return vtk_img


def VTKImageDataToArray(vtk_img):
    vtk_data = vtk_img.GetPointData().GetScalars()
    arr = numpy_support.vtk_to_numpy(vtk_data)
    return arr.reshape(vtk_img.GetDimensions())
