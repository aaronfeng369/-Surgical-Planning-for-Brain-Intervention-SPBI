import vtkmodules.all as vtk
from vtkmodules.util import numpy_support
import numpy as np


class ImageData:
    def __init__(self):
        self.data = vtk.vtkImageData()
        self.ori_data = vtk.vtkImageData()  # vtk read origin data origin=(0,0,0) ,oritation=(1,0,0,0,1,0,0,0,1)
        self.ori_mask_data = vtk.vtkImageData()
        self.resliceAxes = [vtk.vtkMatrix4x4(), vtk.vtkMatrix4x4(), vtk.vtkMatrix4x4()]
        self.reslices = [
            vtk.vtkImageReslice(),
            vtk.vtkImageReslice(),
            vtk.vtkImageReslice(),
        ]
        self.gray_scale = [0, 0]
        self.direction = 0
        self.user_matrix = 0
        self.trans_matrix = 0
        self.spacing = 0
        self.extent = 0
        self.center = 0
        self.origin = 0
        self.current_slice = 0
        self.acqMode = 0  # 0-Sag,1-Cor,2-Axi
        self.new_extent = 0
        self.plane_order = 0
        self.mode = None  # "T1 T2 Mask MRA DTI"

    def initImageData(self, data, ori_data):
        self.data = data
        self.direction = self.arrayFromVTKMatrix(self.data.GetDirectionMatrix())
        self.dimension = self.data.GetDimensions()
        self.spacing = self.data.GetSpacing()
        self.extent = self.data.GetExtent()
        self.origin = self.data.GetOrigin()
        self.center = self.getCenter()
        self.ori_data = ori_data
        self.ori_center = self.getOriginCenter()
        self.trans_matrix = self.getTransMatrix()
        self.user_matrix = self.getUserMatrix()
        self.acqMode, self.plane_order = self.GetAcqMode()
        self.new_extent = self.GetNewExtent()  # depend on acqMode
        self.current_slice = [
            int(0.5 * (self.new_extent[0] + self.new_extent[1])),
            int(0.5 * (self.new_extent[2] + self.new_extent[3])),
            int(0.5 * (self.new_extent[4] + self.new_extent[5])),
        ]

    def getUserMatrix(self):
        direction = np.copy(self.direction)
        user_matrix = np.eye(4)
        user_matrix[0:3, 0:3] = direction
        user_matrix[0:3, 3] = self.origin
        # print("user_matrix", user_matrix)
        user_matrix = self.vtkMatrixFromArray(user_matrix)
        return user_matrix

    def getTransMatrix(self):
        direction = np.copy(self.direction)
        for i in range(0, 3):
            direction[:, i] = direction[:, i] * self.spacing[i]
        trans_matrix = np.eye(4)
        trans_matrix[0:3, 0:3] = direction
        trans_matrix[0:3, 3] = self.origin
        # print("trans_matrix", trans_matrix)
        return trans_matrix

    def getCenter(self):
        """
        :return: data center but this center is not the center of the image, image center is always (0,0,0).
        """
        voxel_center = [
            self.spacing[0] * int(0.5 * (self.extent[0] + self.extent[1])),
            self.spacing[1] * int(0.5 * (self.extent[2] + self.extent[3])),
            self.spacing[2] * int(0.5 * (self.extent[4] + self.extent[5])),
        ]
        center = np.dot(self.direction, voxel_center) + self.origin
        # print("center", center)
        return center

    def getOriginCenter(self):
        extent = self.ori_data.GetExtent()
        origin = self.ori_data.GetOrigin()
        spacing = self.ori_data.GetSpacing()
        center = [0, 0, 0]
        for i in range(3):
            center[i] = origin[i] + spacing[i] * int(0.5 * (extent[2 * i] + extent[2 * i + 1]))
        return center

    def GetNewExtent(self):
        new_extent = []
        if self.acqMode == 0:
            new_extent = [self.extent[4], self.extent[5], self.extent[0], self.extent[1], self.extent[2], self.extent[3]]
        elif self.acqMode == 1:
            new_extent = [self.extent[0], self.extent[1], self.extent[4], self.extent[5], self.extent[2], self.extent[3]]
        elif self.acqMode == 2:
            new_extent = self.extent
        else:
            print("Error: acqMode is wrong!")
        return new_extent

    def GetAcqMode(self):
        sag = np.array([[0, 0, -1], [1, 0, 0], [0, -1, 0]])
        cor = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])
        axi = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        direction = self.direction
        max_index = np.argmax(np.abs(direction), axis=1)  # calculate the max index of each row
        if np.array_equal(max_index, [2, 0, 1]):
            acqMode = 0
            plane_order = [2, 0, 1]
            print("acqMode sag")
        elif np.array_equal(max_index, [0, 2, 1]):
            acqMode = 1
            plane_order = [0, 2, 1]
            print("acqMode cor")
        elif np.array_equal(max_index, [0, 1, 2]):
            acqMode = 2
            plane_order = [0, 1, 2]
            print("acqMode axi")
        else:
            acqMode = 0
            plane_order = [2, 0, 1]
            print("Error: acqMode is wrong! Using default acqMode sag.")
            print("direction:", self.direction)

        return acqMode, plane_order

    def getRealSize(self):
        """
        :return: real size type:[[sag_w, sag_h], [cor_w, cor_h], [axi_w, axi_h]]
        """
        size = []
        extent = self.data.GetExtent()
        spacing = self.data.GetSpacing()
        size.append(spacing[0] * int((extent[0] + extent[1])))  # sag slice thickness
        size.append(spacing[1] * int((extent[2] + extent[3])))  # cor slice thickness
        size.append(spacing[2] * int((extent[4] + extent[5])))  # axi slice thickness
        real_size = [[size[1], size[2]], [size[0], size[2]], [size[0], size[1]]]
        return real_size

    def initReslice(self, plane=0):
        img_mat = np.eye(4)
        img_mat[0:3, 0:3] = self.direction

        img_mat_inv = np.linalg.inv(img_mat)
        sag = np.array([[0, 0, -1, 0], [1, 0, 0, 0], [0, -1, 0, 0], [0, 0, 0, 1]])
        cor = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]])
        axi = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
        if self.acqMode == 0:
            img_mat_inv = np.linalg.inv(sag)
        elif self.acqMode == 1:
            img_mat_inv = np.linalg.inv(cor)
        elif self.acqMode == 2:
            img_mat_inv = np.linalg.inv(axi)
        else:
            print("Error: acqMode is wrong!")
        slice_mat = [np.dot(img_mat_inv, sag).flatten(), np.dot(img_mat_inv, cor).flatten(), np.dot(img_mat_inv, axi).flatten()]

        # print("slice_mat:", slice_mat)
        self.resliceAxes[plane].DeepCopy(slice_mat[plane])
        self.resliceAxes[plane].SetElement(0, 3, self.ori_center[0])
        self.resliceAxes[plane].SetElement(1, 3, self.ori_center[1])
        self.resliceAxes[plane].SetElement(2, 3, self.ori_center[2])
        self.reslices[plane].SetInputData(self.ori_data)
        self.reslices[plane].SetOutputDimensionality(2)
        self.reslices[plane].SetResliceAxes(self.resliceAxes[plane])
        self.reslices[plane].SetInterpolationModeToLinear()
        self.reslices[plane].Update()
        image_tmp = vtk.vtkImageData()
        image_tmp.DeepCopy(self.reslices[plane].GetOutput())
        image_arr_3d = self.Vtk2Numpy(image_tmp)
        del image_tmp
        return image_arr_3d

    def getCurrentReslice(self, plane=0):
        index = self.plane_order[plane]
        value = self.center[plane] + self.spacing[index] * (self.current_slice[plane] - int(0.5 * (self.extent[2 * index] + self.extent[2 * index + 1])))
        ori_value = self.ori_center[index] + self.spacing[index] * (self.current_slice[plane] - int(0.5 * (self.extent[2 * index] + self.extent[2 * index + 1])))
        if self.resliceAxes[plane].GetElement(index, 3) != ori_value:
            self.resliceAxes[plane].SetElement(index, 3, ori_value)
            self.reslices[plane].SetResliceAxes(self.resliceAxes[plane])
            self.reslices[plane].Update()
        image_tmp = vtk.vtkImageData()
        image_tmp.DeepCopy(self.reslices[plane].GetOutput())
        image_arr_3d = self.Vtk2Numpy(image_tmp)
        del image_tmp
        return image_arr_3d, value

    def getOriginGrayScale(self):
        return [round(self.data.GetScalarRange()[0]), round(self.data.GetScalarRange()[1])]

    def getAutoGrayScale(self):
        stats = vtk.vtkImageHistogramStatistics()
        stats.SetInputData(self.data)
        stats.SetAutoRangePercentiles(0.1, 99.9)
        stats.SetAutoRangeExpansionFactors(0.0, 0.0)
        stats.Update()
        return [round(stats.GetAutoRange()[0]), round(stats.GetAutoRange()[1])]

    def Vtk2Numpy(self, imageData):
        """
        :param ImageData: vtkImageData (rows, cols, levels)
        :return: 3d numpy array (levels, rows, cols)
        :info: numpy==1.23.2 to void AttributeError: module 'numpy' has no attribute 'bool'.
        """
        rows, cols, levels = imageData.GetDimensions()
        Scalars = imageData.GetPointData().GetScalars()
        imageArr = numpy_support.vtk_to_numpy(Scalars)
        image3D = imageArr.reshape(levels, cols, rows)

        return image3D

    def arrayFromVTKMatrix(self, vmatrix):
        """Return vtkMatrix4x4 or vtkMatrix3x3 elements as numpy array.
        The returned array is just a copy and so any modification in the array will not affect the input matrix.
        To set VTK matrix from a numpy array, use :py:meth:`vtkMatrixFromArray` or
        :py:meth:`updateVTKMatrixFromArray`.
        """
        from vtk import vtkMatrix4x4
        from vtk import vtkMatrix3x3
        import numpy as np

        if isinstance(vmatrix, vtkMatrix4x4):
            matrixSize = 4
        elif isinstance(vmatrix, vtkMatrix3x3):
            matrixSize = 3
        else:
            raise RuntimeError("Input must be vtk.vtkMatrix3x3 or vtk.vtkMatrix4x4")
        narray = np.eye(matrixSize)
        vmatrix.DeepCopy(narray.ravel(), vmatrix)
        return narray

    def vtkMatrixFromArray(self, narray):
        """Create VTK matrix from a 3x3 or 4x4 numpy array.
        :param narray: input numpy array
        The returned matrix is just a copy and so any modification in the array will not affect the output matrix.
        To set numpy array from VTK matrix, use :py:meth:`arrayFromVTKMatrix`.
        """
        from vtk import vtkMatrix4x4
        from vtk import vtkMatrix3x3

        narrayshape = narray.shape
        if narrayshape == (4, 4):
            vmatrix = vtkMatrix4x4()
            self.updateVTKMatrixFromArray(vmatrix, narray)
            return vmatrix
        elif narrayshape == (3, 3):
            vmatrix = vtkMatrix3x3()
            self.updateVTKMatrixFromArray(vmatrix, narray)
            return vmatrix
        else:
            raise RuntimeError("Unsupported numpy array shape: " + str(narrayshape) + " expected (4,4)")

    def updateVTKMatrixFromArray(self, vmatrix, narray):
        """Update VTK matrix values from a numpy array.
        :param vmatrix: VTK matrix (vtkMatrix4x4 or vtkMatrix3x3) that will be update
        :param narray: input numpy array
        To set numpy array from VTK matrix, use :py:meth:`arrayFromVTKMatrix`.
        """
        from vtk import vtkMatrix4x4
        from vtk import vtkMatrix3x3

        if isinstance(vmatrix, vtkMatrix4x4):
            matrixSize = 4
        elif isinstance(vmatrix, vtkMatrix3x3):
            matrixSize = 3
        else:
            raise RuntimeError("Output vmatrix must be vtk.vtkMatrix3x3 or vtk.vtkMatrix4x4")
        if narray.shape != (matrixSize, matrixSize):
            raise RuntimeError("Input narray size must match output vmatrix size ({0}x{0})".format(matrixSize))
        vmatrix.DeepCopy(narray.ravel())

    def ImageToWorld(self, pos2d, imgSize, plane=0):
        """
        :param pos2d: coordinates of 2d-image in scene, type: [x, y]
        :param imgSize: current size of image, type: [[sag_w, sag_h], [cor_w, cor_h], [axi_w, axi_h]]
        Get voxel units, transform the coordinates of 2d-image in scene to the coordinates of voxel (such as Sag-256 Cor-256 Axi-18)
        reference: ITK-SNAP/Image Layer Inspector/Info/Voxel Units
        return: voxel units, type: [x, y, z]

        STEP-1: scene axes center is the center of image, but Voxel Units axes center is the left-bottom(LB,LT,RT) of image
        According to imageSize , we can get move scene axes center to the left-top of image

        STEP-2: transform the moved scene coordinates to Voxel Units coordinates

        """

        if self.acqMode == 0:  # sag2dAxesOri = ["LT", "RT", "RT"]
            if plane == 0:
                # STEP-1 LT
                newpos = [pos2d[0] + imgSize[0][0] / 2, pos2d[1] + imgSize[0][1] / 2]
                # STEP-2
                a = self.current_slice[0]
                s = newpos[0] / imgSize[0][0] * self.new_extent[3]
                c = newpos[1] / imgSize[0][1] * self.new_extent[5]
            elif plane == 1:
                # STEP-1 RT
                newpos = [-pos2d[0] + imgSize[1][0] / 2, pos2d[1] + imgSize[1][1] / 2]
                # STEP-2
                a = newpos[0] / imgSize[1][0] * self.new_extent[1]
                s = self.current_slice[1]
                c = newpos[1] / imgSize[1][1] * self.new_extent[5]
            else:
                # STEP-1 RT
                newpos = [-pos2d[0] + imgSize[2][0] / 2, pos2d[1] + imgSize[2][1] / 2]
                # STEP-2
                a = newpos[0] / imgSize[2][0] * self.new_extent[1]
                s = newpos[1] / imgSize[2][1] * self.new_extent[3]
                c = self.current_slice[2]

        elif self.acqMode == 1:  # cor2dAxesOri = ["LT", "LT", "LT"]
            if plane == 0:
                # STEP-1 LT
                newpos = [pos2d[0] + imgSize[0][0] / 2, pos2d[1] + imgSize[0][1] / 2]
                # STEP-2
                s = self.current_slice[0]
                a = newpos[0] / imgSize[0][0] * self.new_extent[3]
                c = newpos[1] / imgSize[0][1] * self.new_extent[5]
            elif plane == 1:
                # STEP-1 LT
                newpos = [pos2d[0] + imgSize[1][0] / 2, pos2d[1] + imgSize[1][1] / 2]
                # STEP-2
                s = newpos[0] / imgSize[1][0] * self.new_extent[1]
                a = self.current_slice[1]
                c = newpos[1] / imgSize[1][1] * self.new_extent[5]
            else:
                # STEP-1 LT
                newpos = [pos2d[0] + imgSize[2][0] / 2, pos2d[1] + imgSize[2][1] / 2]
                # STEP-2
                s = newpos[0] / imgSize[2][0] * self.new_extent[1]
                a = newpos[1] / imgSize[2][1] * self.new_extent[3]
                c = self.current_slice[2]

        else:  # axi2dAxesOri = ["LB", "LB", "LT"]
            if plane == 0:
                # STEP-1 LB
                newpos = [pos2d[0] + imgSize[0][0] / 2, -pos2d[1] + imgSize[0][1] / 2]
                # STEP-2
                s = self.current_slice[0]
                c = newpos[0] / imgSize[0][0] * self.new_extent[3]
                a = newpos[1] / imgSize[0][1] * self.new_extent[5]
            elif plane == 1:
                # STEP-1 LB
                newpos = [pos2d[0] + imgSize[1][0] / 2, -pos2d[1] + imgSize[1][1] / 2]
                # STEP-2
                s = newpos[0] / imgSize[1][0] * self.new_extent[1]
                c = self.current_slice[1]
                a = newpos[1] / imgSize[1][1] * self.new_extent[5]
            else:
                # STEP-1 LT
                newpos = [pos2d[0] + imgSize[2][0] / 2, pos2d[1] + imgSize[2][1] / 2]
                # STEP-2
                s = newpos[0] / imgSize[2][0] * self.new_extent[1]
                c = newpos[1] / imgSize[2][1] * self.new_extent[3]
                a = self.current_slice[2]

        voxel_units = [round(s), round(c), round(a)]
        world_units = self.VoxelToWorld([s, c, a])
        return voxel_units, world_units

    def VoxelToWorld(self, voxel_units):
        s, c, a = voxel_units
        world_units = np.round(np.dot(self.trans_matrix, [s, c, a, 1]), 1)
        return [world_units[0], world_units[1], world_units[2]]

    def WorldToImage(self, world_units, imgSize, plane=0):
        s, c, a = self.WorldToVoxel(world_units)
        # from voxel units to image pos
        if self.acqMode == 0:
            if plane == 0:
                x = (s / self.new_extent[3]) * imgSize[0][0] - imgSize[0][0] / 2
                y = (c / self.new_extent[5]) * imgSize[0][1] - imgSize[0][1] / 2
                z = a
            elif plane == 1:
                x = -(a / self.new_extent[1]) * imgSize[1][0] + imgSize[1][0] / 2
                y = (c / self.new_extent[5]) * imgSize[1][1] - imgSize[1][1] / 2
                z = s
            else:
                x = -(a / self.new_extent[1]) * imgSize[2][0] + imgSize[2][0] / 2
                y = (s / self.new_extent[3]) * imgSize[2][1] - imgSize[2][1] / 2
                z = c

        elif self.acqMode == 1:
            if plane == 0:
                x = (a / self.new_extent[3]) * imgSize[0][0] - imgSize[0][0] / 2
                y = (c / self.new_extent[5]) * imgSize[0][1] - imgSize[0][1] / 2
                z = s
            elif plane == 1:
                x = (s / self.new_extent[1]) * imgSize[1][0] - imgSize[1][0] / 2
                y = (c / self.new_extent[5]) * imgSize[1][1] - imgSize[1][1] / 2
                z = a
            else:
                x = (s / self.new_extent[1]) * imgSize[2][0] - imgSize[2][0] / 2
                y = (a / self.new_extent[3]) * imgSize[2][1] - imgSize[2][1] / 2
                z = c

        else:
            if plane == 0:
                x = (c / self.new_extent[3]) * imgSize[0][0] - imgSize[0][0] / 2
                y = -(a / self.new_extent[5]) * imgSize[0][1] + imgSize[0][1] / 2
                z = s
            elif plane == 1:
                x = (s / self.new_extent[1]) * imgSize[1][0] - imgSize[1][0] / 2
                y = -(a / self.new_extent[5]) * imgSize[1][1] + imgSize[1][1] / 2
                z = c
            else:
                x = (s / self.new_extent[1]) * imgSize[2][0] - imgSize[2][0] / 2
                y = (c / self.new_extent[3]) * imgSize[2][1] - imgSize[2][1] / 2
                z = a

        image_pos = [x, y]
        return image_pos, z

    def WorldToVoxel(self, world_units):
        # from world units to voxel units
        inv_trans_matrix = np.linalg.inv(self.trans_matrix)
        voxel_units = np.dot(inv_trans_matrix, np.append(world_units, 1))
        s, c, a = voxel_units[:3]
        return [s, c, a]

    def getPoint2dFromPoint3d(self, point2d, imgSize):
        """
        :param point2d: type: [x,y,z]
        :param imgSize: type: [[sag_w, sag_h], [cor_w, cor_h], [axi_w, axi_h]]
        :return: type: [[x1,y1,z1],[x2,y2,z2],[x3,y3,z3]] 3d point to 2d point of each plane
        """
        point3d = []
        for i in range(3):
            pos, z = self.WorldToImage(point2d, imgSize, plane=i)
            pos.append(round(z))
            point3d.append(pos)
        return point3d

    def getLine2dFromLine3d(self, line3d, imgSize):
        """
        :param line3d: type: [[x1,y1,z1],[x2,y2,z2]]
        :param imgSize: type: [[sag_w, sag_h], [cor_w, cor_h], [axi_w, axi_h]]
        :return: type: [[[x1,y1,z1],[x2,y2,z2],[x3,y3,z3]],[[x1,y1,z1],[x2,y2,z2],[x3,y3,z3]]] 3d line to 2d line of each plane
        """
        line2d = []
        points2d = self.getPoint2dFromPoint3d(line3d[0], imgSize)
        line2d.append(points2d)
        points2d = self.getPoint2dFromPoint3d(line3d[1], imgSize)
        line2d.append(points2d)
        return line2d

    # def getSeparateLine2dFromLine3d(self, line3d, imgSize):
    #     """
    #     :param line3d: type: [[x1,y1,z1],[x2,y2,z2]]
    #     :param imgSize: type: [[sag_w, sag_h], [cor_w, cor_h], [axi_w, axi_h]]
    #     :return: type: [[[x1,y1,z1],[x2,y2,z2],[x3,y3,z3]],[[x1,y1,z1],[x2,y2,z2],[x3,y3,z3]]] 3d line to 2d line of each plane
    #     """
    #     pass

    def getPoints2dFromPoints3d(self, points3d, imgSize):
        """
        :param points3d: type: [[x,y,z],[x,y,z],...]
        :param imgSize: type: [[sag_w, sag_h], [cor_w, cor_h], [axi_w, axi_h]]
        :return: type: [[[x1,y1,z1],[x2,y2,z2],[x3,y3,z3]],[[x1,y1,z1],[x2,y2,z2],[x3,y3,z3]],...] 3d points to 2d points of each plane
        """
        points2d = []
        for point3d in points3d:
            point2d = []
            for i in range(3):
                pos, z = self.WorldToImage(point3d, imgSize, plane=i)
                pos.append(round(z))
                point2d.append(pos)
            points2d.append(point2d)
        return points2d

    def getLines2dFromLines3d(self, lines3d, imgSize):
        """
        :param lines3d: type: [[[x1,y1,z1],[x2,y2,z2]],[[x1,y1,z1],[x2,y2,z2]],...] 3d lines [[x1,y1,z1],[x2,y2,z2]]
        :param imgSize: type: [[sag_w, sag_h], [cor_w, cor_h], [axi_w, axi_h]]
        :return: type: [[[[x1,y1,z1],[x2,y2,z2],[x3,y3,z3]],[[x1,y1,z1],[x2,y2,z2],[x3,y3,z3]]],...] 3d lines to 2d lines of each plane
        """
        lines2d = []
        for line3d in lines3d:
            points2d = self.getPoints2dFromPoints3d(line3d, imgSize)
            lines2d.append(points2d)
        return lines2d
