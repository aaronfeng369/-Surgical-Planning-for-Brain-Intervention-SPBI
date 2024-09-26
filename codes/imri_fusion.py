from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import imri_setting
import numpy as np
import vtkmodules.all as vtk
import SimpleITK as sitk
import os


class Fusion(QMainWindow):
    def __init__(self, parent=None):
        super(Fusion, self).__init__(parent)
        self.fixed_image_path = None  # fixed image path
        self.moving_image_path = None  # moving image path
        self.moved_image_path = None  # moved image path
        self.config = imri_setting.read_config()
        self.Iter_step = 1  # learningRate
        self.Iter_num = 100  # numberOfIterations
        self.color_table = []
        self.fusioned_color_table = []

    def init(self, ui, Image3d, ImagePlanes, image_read_signal):
        self.ui = ui
        self.Image3d = Image3d
        self.ImagePlanes = ImagePlanes
        self.image_read_signal = image_read_signal
        self.setFusionColorTable()

        self.ui.LoadFixedImageBtn.clicked.connect(self.load_fixed_image)
        self.ui.LoadMovingImageBtn.clicked.connect(self.load_moving_image)

        imri_setting.setSpinBox(self.ui.IterStepDoubleSpinBox, 0.1, 1.0, 1.0, 0.1)
        imri_setting.setSpinBox(self.ui.IterNumberSpinBox, 10, 500, 100, 10)

        self.ui.IterStepDoubleSpinBox.valueChanged.connect(self.setIterParam)
        self.ui.IterNumberSpinBox.valueChanged.connect(self.setIterParam)

        self.ui.RigidFusionBtn.clicked.connect(self.rigid_fusion)
        self.ui.RigidFusionProcessBar.setRange(0, 100)
        self.ui.RigidFusionProcessBar.setValue(0)

    def load_fixed_image(self):
        directory_path = self.config["fusion"]["image_directory"]
        file, _ = QFileDialog.getOpenFileName(self, "Open Fixed File", directory_path, "Nii(*.nii.gz)")
        if file:
            self.config["fusion"]["image_directory"] = os.path.dirname(file)
            imri_setting.update_config(config=self.config)
            self.fixed_image_path = file
            self.ui.FixedImageLineEdit.setText(file)
            fixed_image_dict = {"module": "fusion", "path": file, "mode": "image"}
            self.image_read_signal.emit(fixed_image_dict)

    def load_moving_image(self):
        directory_path = self.config["fusion"]["image_directory"]
        file, _ = QFileDialog.getOpenFileName(self, "Open Moving File", directory_path, "Nii(*.nii.gz)")
        if file:
            self.config["fusion"]["image_directory"] = os.path.dirname(file)
            imri_setting.update_config(config=self.config)
            self.moving_image_path = file
            self.ui.MovingImageLineEdit.setText(file)
            moving_image_dict = {"module": "fusion", "path": file, "mode": "mask"}
            self.image_read_signal.emit(moving_image_dict)

    def load_moved_image(self):
        if self.moved_image_path:
            moved_image_dict = {"module": "fusion", "path": self.moved_image_path, "mode": "fusioned_mask"}
            self.image_read_signal.emit(moved_image_dict)

    def setIterParam(self):
        self.Iter_step = self.ui.IterStepDoubleSpinBox.value()
        self.Iter_num = self.ui.IterNumberSpinBox.value()

    def setFusionColorTable(self, threshold=50):
        color_table = []
        for i in range(256):
            if i < threshold:
                color = QColor(0, 0, 0, 48)
            else:
                color = QColor(255, i, 128, 48)
            color_table.append(color.rgba())
        self.color_table = color_table

        fusioned_color_table = []
        for i in range(256):
            if i < threshold:
                color = QColor(0, 0, 0, 48)
            else:
                color = QColor(i, 255, 0, 48)
            fusioned_color_table.append(color.rgba())
        self.fusioned_color_table = fusioned_color_table

    def rigid_fusion(self, fixed_image=None, moving_image=None):

        if fixed_image is None or moving_image is None:
            fixed_image = self.fixed_image_path
            moving_image = self.moving_image_path

        fixed_image = sitk.ReadImage(fixed_image, sitk.sitkFloat32)
        moving_image = sitk.ReadImage(moving_image, sitk.sitkFloat32)

        self.progress_dialog = QProgressDialog("Fusion...", "Cancel", 0, 5, self)
        self.progress_dialog.setWindowModality(Qt.ApplicationModal)
        self.progress_dialog.setWindowTitle("Rigid Fusion")
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setCancelButton(None)  # 禁用取消按钮
        self.progress_dialog.setMinimumSize(800, 200)
        self.progress_dialog.setModal(False)
        self.progress_dialog.setValue(50)
        self.progress_dialog.setMinimumDuration(0.1)
        self.progress_dialog.show()
        QApplication.processEvents()

        self.ui.RigidFusionProcessBar.setValue(0)
        # 设置初始变换
        initial_transform = sitk.CenteredTransformInitializer(
            fixed_image,
            moving_image,
            sitk.Euler3DTransform(),
            sitk.CenteredTransformInitializerFilter.GEOMETRY,
            # 设置过滤器，初始化过程基于图像的几何形状
        )
        # initial_transform是初始变换，作为图像配准算法的起点
        # 第三个Euler3DTransform是一种刚性变换，上面这段代码的含义是对一个Euler3DTransform进行初始化

        # 配准
        registration_method = sitk.ImageRegistrationMethod()

        # 参数一：设置相似度度量（Similarity metric）的参数
        registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=20)
        # 相似度度量时Mattes互信息，并且直方图的箱数为50
        registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
        # 相似度度量的采样策略为随机采样（RANDOM）
        registration_method.SetMetricSamplingPercentage(0.01)
        # 采样比例为0.01

        # 参数二：设置插值器类型
        registration_method.SetInterpolator(sitk.sitkLinear)
        # 将该实例的插值器类型设置为线性插值（sitkLinear）

        #  参数三：设置优化器（Optimizer）的参数
        registration_method.SetOptimizerAsGradientDescent(
            # 优化器的选取梯度下降作为优化算法
            learningRate=self.Iter_step,
            # 设置学习率（决定每次迭代对变换参数进行调整的步长）
            numberOfIterations=self.Iter_num,
            # 迭代次数设置为100
            convergenceMinimumValue=1e-6,
            # 收敛标准设置为1e-6,当相似度度量的改善（本次相比于上一次的改进，即变化值）小于该值就认为收敛，连续几次（该次数即收敛窗口大小）满足时停止迭代
            convergenceWindowSize=10,
            # 另一个收敛标准-收敛窗口大小，当相似度度量的改善连续几次小于MinimumValue时就停止迭代
        )
        registration_method.SetOptimizerScalesFromPhysicalShift()
        # 设置优化器，根据物理位移来自动计算变换参数的缩放比例（scale）
        # 变换参数的缩放比例（scale）

        # 配置一个多分辨率（multi-resolution）的框架
        # 多分辨率框架是现在较低分辨率上初步配准，找到图像间的大致对应关系，然后在高分辨率上进一步精细配准，可以提升效率减少计算量
        registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
        # 设置不同粗细的分辨率级别，最粗的为缩小4倍，还有2倍
        registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
        # 设置不同分辨率级别的平滑参数（高斯核的标准差），平滑程度降低可以保留更多细节信息
        registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
        # 指定平滑参数smoothingSigmas是以物理单位（如毫米）给出的，而不是像素单位。这意味着平滑参数与图像的空间分辨率有关
        # 而不是简单地依赖于像素间距。启用这个选项后，随着图像在多分辨率过程中的缩小，平滑核的大小也会相应地调整，以保持物理尺寸的一致性

        # Don't optimize in-place, we would possibly like to run this cell multiple times.
        registration_method.SetInitialTransform(initial_transform, inPlace=False)
        # inPlace设置为false，可以使原始的initial_transform对象保留，每次配准过程总修改的变换都是其复制过的，可以多次运行对比效果
        # 通常情况下都可以设置inPlace为false

        # registration_method.AddCommand(sitk.sitkIterationEvent, lambda: print(registration_method.GetMetricValue()))

        final_transform = registration_method.Execute(fixed_image, moving_image)
        # 执行配准过程，生成最终变换，输出的文件中包含一个变换对象

        self.ui.RigidFusionProcessBar.setValue(50)
        # 输出结果
        print("Final metric value: {0}".format(registration_method.GetMetricValue()))
        # 输出最终的相似度度量
        # 当前采用的相似度度量为Mattes互信息，理论上的取值范围应该为[0，+∞]，越大代表两张图像的重合度越高，但此处不知道为什么一直输出为负值。。
        # 不是图像的问题，使用官方的代码和官方数据也是输出负值，这个问题目前还没解决

        print("Optimizer's stopping condition, {0}".format(registration_method.GetOptimizerStopConditionDescription()))
        # 输出迭代终止的原因，是迭代次数到了设定值（100次）还是满足了收敛标准（在optimizer参数中可设置）

        moving_resampled = sitk.Resample(
            moving_image,
            fixed_image,
            final_transform,
            sitk.sitkLinear,
            # 插值方法为线性插值
            0.0,
            # 重新采样图像的默认像素值设置为0
            moving_image.GetPixelID(),
            # 确保像素类型不变
        )
        # 对moving_image重新采样（变换），使其与fixed_image的分辨率、方向等相匹配，也就是获取配准后图像的过程

        file_name_with_extension = os.path.basename(self.moving_image_path)
        file_name = os.path.splitext(file_name_with_extension)[0]
        output_name = "moved_" + file_name + ".gz"
        self.moved_image_path = os.path.join(os.path.split(self.moving_image_path)[0], output_name)
        sitk.WriteImage(moving_resampled, self.moved_image_path)
        self.ui.MovedImageLineEdit.setText(self.moved_image_path)
        self.ui.FusionErrorLineEdit.setText(str(round(registration_method.GetMetricValue(), 4)))

        self.load_moved_image()

        self.ui.RigidFusionProcessBar.setValue(100)
        self.progress_dialog.setValue(5)
        self.progress_dialog.close()
        # sitk.WriteTransform(final_transform, os.path.join(output_dir, "resultTransform.tfm"))
        # 输出配准变换（transform）文件
