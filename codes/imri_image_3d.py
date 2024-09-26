# pyqt5 D:\Program\anaconda3\envs\MRI_SN\lib\site-packages\vtkmodules\qt\QVTKRenderWindowInteractor.py
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtkmodules.all as vtk
import math


class Image3d:
    def __init__(self, frame):
        self.frame = frame
        self.ren = vtk.vtkRenderer()
        self.ren.SetBackground(0, 0, 0)
        self.widget = QVTKRenderWindowInteractor(self.frame)
        self.renWin = self.widget.GetRenderWindow()
        self.renWin.AddRenderer(self.ren)
        self.iren = self.widget.GetRenderWindow().GetInteractor()
        self.style = vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(self.style)
        self.renWin.Render()
        self.imageActors = [
            vtk.vtkImageActor(),
            vtk.vtkImageActor(),
            vtk.vtkImageActor(),
        ]

        self.colors = vtk.vtkImageMapToWindowLevelColors()
        self.prop = vtk.vtkImageProperty()
        self.AnnotatedCubeActor = None
        self.OrientationMarkerWidget = vtk.vtkOrientationMarkerWidget()
        self.AxesActor = None

    def addAnnotatedCubeActor(self):
        if self.AnnotatedCubeActor == None:
            colors = vtk.vtkNamedColors()
            self.AnnotatedCubeActor = vtk.vtkAnnotatedCubeActor()
            self.AnnotatedCubeActor.SetXPlusFaceText("L")
            self.AnnotatedCubeActor.SetXMinusFaceText("R")
            self.AnnotatedCubeActor.SetYMinusFaceText("A")
            self.AnnotatedCubeActor.SetYPlusFaceText("P")
            self.AnnotatedCubeActor.SetZMinusFaceText("I")
            self.AnnotatedCubeActor.SetZPlusFaceText("S")
            self.AnnotatedCubeActor.GetTextEdgesProperty().SetColor(colors.GetColor3d("Yellow"))
            self.AnnotatedCubeActor.GetTextEdgesProperty().SetLineWidth(2)
            self.AnnotatedCubeActor.GetCubeProperty().SetColor(colors.GetColor3d("Blue"))

            self.OrientationMarkerWidget.SetOrientationMarker(self.AnnotatedCubeActor)
            self.OrientationMarkerWidget.SetInteractor(self.iren)
            self.OrientationMarkerWidget.EnabledOn()
            self.OrientationMarkerWidget.InteractiveOn()
            self.OrientationMarkerWidget.SetEnabled(1)
            # self.ren.ResetCamera()
            self.renWin.Render()
        else:
            self.OrientationMarkerWidget.SetEnabled(0)
            self.AnnotatedCubeActor = None
            self.renWin.Render()

    def addAxesActor(self):
        if self.AxesActor == None:
            self.AxesActor = vtk.vtkAxesActor()
            self.AxesActor.SetXAxisLabelText("L")
            self.AxesActor.SetYAxisLabelText("P")
            self.AxesActor.SetZAxisLabelText("S")
            self.AxesActor.GetXAxisCaptionActor2D().GetProperty().SetColor(1, 0, 0)  # red
            self.AxesActor.GetYAxisCaptionActor2D().GetProperty().SetColor(0, 1, 0)  # green
            self.AxesActor.GetZAxisCaptionActor2D().GetProperty().SetColor(0, 0, 1)  # blue
            self.AxesActor.GetXAxisCaptionActor2D().GetCaptionTextProperty().SetColor(1, 0, 0)
            self.AxesActor.GetYAxisCaptionActor2D().GetCaptionTextProperty().SetColor(0, 1, 0)
            self.AxesActor.GetZAxisCaptionActor2D().GetCaptionTextProperty().SetColor(0, 0, 1)
            self.AxesActor.GetZAxisCaptionActor2D().GetCaptionTextProperty().SetFontSize(10)
            self.AxesActor.GetXAxisCaptionActor2D().GetCaptionTextProperty().SetFontSize(10)
            self.AxesActor.GetYAxisCaptionActor2D().GetCaptionTextProperty().SetFontSize(10)
            self.AxesActor.SetPosition(0, 0, 0)
            self.AxesActor.SetTotalLength(50, 50, 50)
            self.AxesActor.SetShaftType(0)
            self.AxesActor.SetAxisLabels(1)
            self.AxesActor.SetCylinderRadius(0.02)
            self.ren.AddActor(self.AxesActor)
            self.renWin.Render()
        else:
            self.ren.RemoveActor(self.AxesActor)
            self.renWin.Render()

    def addSlicer(self, ImageData, last_slicer_index):
        """
        :param ImageData: class ImageData
        :param last_slicer_index: [x, y, z]
        """
        vol_extents = []
        extent = ImageData.data.GetExtent()
        x = extent[1]  # Sagittal
        y = extent[3]  # Coronal
        z = extent[5]  # Axial
        if last_slicer_index == None:
            vol_extents.append([int((x + 1) / 2), int((x + 1) / 2), 0, y, 0, z])  # Sagittal
            vol_extents.append([0, x, int((y + 1) / 2), int((y + 1) / 2), 0, z])  # Coronal
            vol_extents.append([0, x, 0, y, int((z + 1) / 2), int((z + 1) / 2)])  # Axial
            # vol_extents.append([0, int((x + 1) / 2), 0, y, 0, z])  # Sagittal
            # vol_extents.append([0, x, 0, int((y + 1) / 2), 0, z])  # Coronal
            # vol_extents.append([0, x, 0, y, 0, int((z + 1) / 2)])  # Axial
        else:
            vol_extents.append([last_slicer_index[0], last_slicer_index[0], 0, y, 0, z])  # Sagittal
            vol_extents.append([0, x, last_slicer_index[1], last_slicer_index[1], 0, z])  # Coronal
            vol_extents.append([0, x, 0, y, last_slicer_index[2], last_slicer_index[2]])  # Axial
        self.prop.SetOpacity(1)

        self.colors.SetInputData(ImageData.ori_data)
        auto_w = ImageData.getAutoGrayScale()[1] - ImageData.getAutoGrayScale()[0]
        auto_l = auto_w / 2
        self.colors.SetWindow(auto_w)
        self.colors.SetLevel(auto_l)
        self.colors.Update()  # Update() must be called before GetOutputPort() is called, otherwise the output will be empty
        for i in range(0, 3):
            self.imageActors[i] = vtk.vtkImageActor()
            self.imageActors[i].SetUserMatrix(ImageData.user_matrix)
            self.imageActors[i].SetProperty(self.prop)
            self.imageActors[i].GetMapper().SetInputConnection(self.colors.GetOutputPort())
            self.imageActors[i].SetDisplayExtent(vol_extents[i])
            self.imageActors[i].InterpolateOn()
            self.imageActors[i].ForceOpaqueOn()  # Force the actor to be rendered during the opaque rendering pass.
            self.imageActors[i].Update()
            self.ren.AddViewProp(self.imageActors[i])
        return None

    def initVolume(self, ImageData, mode=None):
        if mode == None:
            mapper = vtk.vtkGPUVolumeRayCastMapper()
            mapper.SetInputData(ImageData.data)

            volume_prop = vtk.vtkVolumeProperty()
            volume_prop.SetInterpolationTypeToLinear()
            volume_prop.SetAmbient(0.4)
            volume_prop.SetDiffuse(0.6)
            volume_prop.SetSpecular(0.2)

            PiecewiseFunc = vtk.vtkPiecewiseFunction()
            PiecewiseFunc.AddPoint(0, 0)
            PiecewiseFunc.AddPoint(350, 1.00)
            volume_prop.SetScalarOpacity(PiecewiseFunc)
            # compositeOpacity = vtk.vtkPiecewiseFunction()
            # compositeOpacity.AddPoint(70, 0.00)
            # compositeOpacity.AddPoint(90, 0.40)
            # compositeOpacity.AddPoint(180, 0.60)
            # volume_prop.SetScalarOpacity(compositeOpacity)

            # volumeGradientOpacity = vtk.vtkPiecewiseFunction()
            # volumeGradientOpacity.AddPoint(10, 0.0)
            # volumeGradientOpacity.AddPoint(90, 0.5)
            # volumeGradientOpacity.AddPoint(100, 1.0)

            color = vtk.vtkColorTransferFunction()
            color.AddRGBPoint(0.000, 0.00, 0.00, 0.00)
            color.AddRGBPoint(64.00, 1.00, 0.52, 0.30)
            color.AddRGBPoint(190.0, 1.00, 1.00, 1.00)
            color.AddRGBPoint(220.0, 0.20, 0.20, 0.20)
            volume_prop.SetColor(color)

            volume = vtk.vtkVolume()
            volume.SetMapper(mapper)
            volume.SetProperty(volume_prop)
            self.ren.AddVolume(volume)
            return volume

        elif mode == "BrainSeg":
            mapper = vtk.vtkGPUVolumeRayCastMapper()
            mapper.SetInputData(ImageData)

            volume_prop = vtk.vtkVolumeProperty()
            volume_prop.SetInterpolationTypeToLinear()
            volume_prop.SetAmbient(0.4)
            volume_prop.SetDiffuse(0.6)
            volume_prop.SetSpecular(0.2)

            opacityFunc = vtk.vtkPiecewiseFunction()
            opacityFunc.AddPoint(0, 0.00)
            opacityFunc.AddPoint(200, 0.50)
            volume_prop.SetScalarOpacity(opacityFunc)

            color = vtk.vtkColorTransferFunction()
            color.AddRGBPoint(0.000, 0.000, 0.000, 0.000)
            color.AddRGBPoint(200.00, 0.000, 1.000, 0.000)
            volume_prop.SetColor(color)

            volume = vtk.vtkVolume()
            volume.SetMapper(mapper)
            volume.SetProperty(volume_prop)
            self.ren.AddVolume(volume)
            return volume

        elif mode == "Vessel":
            mapper = vtk.vtkGPUVolumeRayCastMapper()
            mapper.SetInputData(ImageData.data)

            # mapper.SetAutoAdjustSampleDistances(0)
            # mapper.SetSampleDistance(0.5)
            # # mapper.UseJitteringOn()
            # mapper.SetGlobalIlluminationReach(0.75)
            # mapper.SetVolumetricScatteringBlending(1.0)

            volume_prop = vtk.vtkVolumeProperty()
            volume_prop.SetInterpolationTypeToLinear()
            # volume_prop.ShadeOn()
            volume_prop.SetAmbient(0.4)
            volume_prop.SetDiffuse(0.6)
            volume_prop.SetSpecular(0.2)

            opacityFunc = vtk.vtkPiecewiseFunction()
            opacityFunc.AddPoint(70, 0.00)
            opacityFunc.AddPoint(90, 0.40)
            volume_prop.SetScalarOpacity(opacityFunc)

            color = vtk.vtkColorTransferFunction()
            color.AddRGBPoint(0.000, 0.000, 0.000, 0.000)
            color.AddRGBPoint(190.00, 1.000, 0.000, 0.000)
            volume_prop.SetColor(color)

            volume = vtk.vtkVolume()
            volume.SetMapper(mapper)
            volume.SetProperty(volume_prop)
            self.ren.AddVolume(volume)
            return volume
        else:
            pass

    def updateVolume(self, volume, PiecewiseFunc=None, ColorTransferFunc=None):
        if PiecewiseFunc:
            volume.GetProperty().SetScalarOpacity(PiecewiseFunc)
        if ColorTransferFunc:
            volume.GetProperty().SetColor(ColorTransferFunc)
        self.renWin.Render()
        return volume

    def removeVolume(self, volume):
        if volume in self.ren.GetVolumes():
            self.ren.RemoveActor(volume)
        self.renWin.Render()

    def removeSlicer(self):
        for i in range(0, 3):
            self.ren.RemoveActor(self.imageActors[i])
        self.renWin.Render()

    def moveSlicer(self, ImageData, plane_index, slicer_index):
        new_extent = list(ImageData.GetNewExtent())
        new_extent[2 * plane_index] = slicer_index
        new_extent[2 * plane_index + 1] = slicer_index
        if ImageData.acqMode == 0:
            extent = [new_extent[2], new_extent[3], new_extent[4], new_extent[5], new_extent[0], new_extent[1]]
        elif ImageData.acqMode == 1:
            extent = [new_extent[0], new_extent[1], new_extent[4], new_extent[5], new_extent[2], new_extent[3]]
        elif ImageData.acqMode == 2:
            extent = new_extent
        else:
            print("acqMode error")
        self.imageActors[plane_index].SetDisplayExtent(extent[0], extent[1], extent[2], extent[3], extent[4], extent[5])
        self.renWin.Render()

    def getViewInfo(self):
        pos = self.ren.GetActiveCamera().GetPosition()
        view_up = self.ren.GetActiveCamera().GetViewUp()
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("pos:", pos)
        print("view_up:", view_up)
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

    def setSagView(self):
        self.ren.ResetCamera()
        fp = self.ren.GetActiveCamera().GetFocalPoint()
        p = self.ren.GetActiveCamera().GetPosition()
        dist = math.sqrt((p[0] - fp[0]) ** 2 + (p[1] - fp[1]) ** 2 + (p[2] - fp[2]) ** 2)
        self.ren.GetActiveCamera().SetPosition(fp[2] + dist, fp[0], fp[1])
        self.ren.GetActiveCamera().SetViewUp(0.0, 0.0, 1.0)
        self.ren.GetActiveCamera().Zoom(1.5)
        self.renWin.Render()

    def setCorView(self):
        self.ren.ResetCamera()
        fp = self.ren.GetActiveCamera().GetFocalPoint()
        p = self.ren.GetActiveCamera().GetPosition()
        dist = math.sqrt((p[0] - fp[0]) ** 2 + (p[1] - fp[1]) ** 2 + (p[2] - fp[2]) ** 2)
        self.ren.GetActiveCamera().SetPosition(fp[0], -fp[2] - dist, fp[1])
        self.ren.GetActiveCamera().SetViewUp(0.0, 0.0, 1.0)
        self.ren.GetActiveCamera().Zoom(1.5)
        self.renWin.Render()

    def setAxiView(self):
        self.ren.ResetCamera()
        fp = self.ren.GetActiveCamera().GetFocalPoint()
        p = self.ren.GetActiveCamera().GetPosition()
        dist = math.sqrt((p[0] - fp[0]) ** 2 + (p[1] - fp[1]) ** 2 + (p[2] - fp[2]) ** 2)
        self.ren.GetActiveCamera().SetPosition(fp[0], fp[1], -fp[2] - dist)
        self.ren.GetActiveCamera().SetViewUp(0.0, -1.0, 0.0)
        self.ren.GetActiveCamera().Zoom(1.5)
        self.renWin.Render()

    def renderSlicer(self, mode=2):
        if mode == 0:
            self.setSagView()
        elif mode == 1:
            self.setCorView()
        else:
            self.setAxiView()
        self.renWin.Render()
        self.iren.Initialize()
        self.iren.Start()

        return None

    def resizeScene(self, views):
        view_rect = views[2].contentsRect()  # if use self.views[i].rect(), the size will be wrong
        view_w = view_rect.width()
        view_h = view_rect.height()
        self.renWin.SetSize(view_w, view_h)

    def removeActor(self, actor):
        if actor in self.ren.GetActors():
            self.ren.RemoveActor(actor)
            self.renWin.Render()

    def addActor(self, actor):
        if actor not in self.ren.GetActors():
            self.ren.AddActor(actor)
            self.renWin.Render()

    def createPointActor(self, position, color=[1, 0, 0], opacity=0.5, radius=5):
        sphereSource = vtk.vtkSphereSource()
        sphereSource.SetRadius(radius)
        sphereSource.SetThetaResolution(40)
        sphereSource.SetPhiResolution(40)
        sphereSource.Update()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphereSource.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.SetPosition(position)
        actor.GetProperty().SetColor(color)
        actor.GetProperty().SetOpacity(opacity)
        return actor

    def createLineActor(self, start, end, color=[1, 0, 0], opacity=1, width=3):
        lineSource = vtk.vtkLineSource()
        lineSource.SetPoint1(start)
        lineSource.SetPoint2(end)
        lineSource.Update()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(lineSource.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color)
        actor.GetProperty().SetOpacity(opacity)
        actor.GetProperty().SetLineWidth(width)
        return actor
