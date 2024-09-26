import itk.itkImageSeriesReaderPython
import vtkmodules.all as vtk
import SimpleITK as sitk
import itk
from vtkmodules.util import numpy_support
import numpy as np
import imri_setting


def read_nii_to_vtk(path):
    niftiIO = itk.NiftiImageIO.New()
    reader = itk.ImageFileReader[itk.Image[itk.D, 3]].New()
    reader.SetImageIO(niftiIO)
    reader.SetFileName(path)
    reader.Update()
    image = reader.GetOutput()
    vtkImage = itk.vtk_image_from_image(image)

    ori_data = vtk.vtkImageData()
    ori_data.DeepCopy(vtkImage)
    ori_data.SetOrigin((0, 0, 0))
    ori_data.SetDirectionMatrix((1, 0, 0, 0, 1, 0, 0, 0, 1))
    return vtkImage, ori_data


def read_single_dicom_to_vtk(path):
    gdcmIO = itk.GDCMImageIO.New()
    reader = itk.ImageFileReader[itk.Image[itk.D, 3]].New()
    seriesFileNames = itk.GDCMSeriesFileNames.New()
    seriesFileNames.SetDirectory(path)
    seriesUIDs = seriesFileNames.GetSeriesUIDs()
    filenames = seriesFileNames.GetFileNames(seriesUIDs[0])
    print("filenames:", filenames)
    reader.SetImageIO(gdcmIO)
    reader.SetFileName(filenames[9])
    reader.Update()
    image = reader.GetOutput()
    vtkImage = itk.vtk_image_from_image(image)

    ori_data = vtk.vtkImageData()
    ori_data.DeepCopy(vtkImage)
    ori_data.SetOrigin((0, 0, 0))
    ori_data.SetDirectionMatrix((1, 0, 0, 0, 1, 0, 0, 0, 1))

    return vtkImage, ori_data


# use
def read_dicom_to_vtk(path):
    gdcmIO = itk.GDCMImageIO.New()
    reader = itk.ImageSeriesReader[itk.Image[itk.D, 3]].New()
    seriesFileNames = itk.GDCMSeriesFileNames.New()
    seriesFileNames.SetDirectory(path)
    seriesUIDs = seriesFileNames.GetSeriesUIDs()
    filenames = seriesFileNames.GetFileNames(seriesUIDs[0])
    reader.SetImageIO(gdcmIO)
    reader.SetFileNames(filenames)
    reader.Update()
    image = reader.GetOutput()
    vtkImage = itk.vtk_image_from_image(image)

    ori_data = vtk.vtkImageData()
    ori_data.DeepCopy(vtkImage)
    ori_data.SetOrigin((0, 0, 0))
    ori_data.SetDirectionMatrix((1, 0, 0, 0, 1, 0, 0, 0, 1))

    # get data tag
    metadata = gdcmIO.GetMetaDataDictionary()
    entryID1 = "0010|0010"  # Patient's Name
    entryID2 = "0010|1010"  # Patient's Age
    entryID3 = "0010|0040"  # Patient’s Sex
    entryID4 = "0008|0020"  # Study Date
    entryID5 = "0018|1030"  # ProtocolName

    imri_setting.IMRIGlobal.Mode = "DICOM"
    imri_setting.IMRIGlobal.Name = getMetaData(metadata, entryID1)
    imri_setting.IMRIGlobal.Age = getMetaData(metadata, entryID2)
    imri_setting.IMRIGlobal.Sex = getMetaData(metadata, entryID3)
    imri_setting.IMRIGlobal.Date = getMetaData(metadata, entryID4)
    imri_setting.IMRIGlobal.ProtocolName = getMetaData(metadata, entryID5)

    return vtkImage, ori_data


# use
def getMetaData(metadata, entryID):
    if not metadata.HasKey(entryID):
        print("tag: " + entryID + " not found in series")
        return "Unknown"
    else:
        # The second parameter is mandatory in python to get the string label value
        # label = itk.GDCMImageIO.GetLabelFromTag(entryID, "")
        tagvalue = metadata[entryID]
        # print(label[1] + " (" + entryID + ") is: " + str(tagvalue))
        return str(tagvalue)


# use
def readNiftiFile(path):
    reader = vtk.vtkNIFTIImageReader()
    reader.SetDataByteOrderToBigEndian()  # for unix
    reader.SetFileName(path)
    reader.Update()

    image = sitk.ReadImage(path)
    data = vtk.vtkImageData()

    data.DeepCopy(reader.GetOutput())
    data.SetOrigin(image.GetOrigin())
    data.SetSpacing(image.GetSpacing())
    data.SetDirectionMatrix(image.GetDirection())
    # print("origin:", image.GetOrigin())
    # print("spacing:", image.GetSpacing())
    # print("direction:", image.GetDirection())

    ori_data = vtk.vtkImageData()
    ori_data.DeepCopy(reader.GetOutput())
    # print("origin:", ori_data.GetOrigin())
    # print("spacing:", ori_data.GetSpacing())
    # print("direction:", ori_data.GetDirectionMatrix())
    # del reader

    imri_setting.IMRIGlobal.Mode = "NIFIT"

    return data, ori_data


def readDicomSeriesFile(path):
    series_ids = sitk.ImageSeriesReader.GetGDCMSeriesIDs(path)
    # print("series ids:", series_ids)

    if not series_ids:
        print("ERROR: given directory dose not a DICOM series.")
        return None

    reader = vtk.vtkDICOMImageReader()
    reader.SetDirectoryName(path)
    reader.SetDataByteOrderToBigEndian()  # for unix
    reader.FileLowerLeftOn()
    reader.SetFileLowerLeft(True)
    reader.Update()

    series_file_names = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(path)
    series_reader = sitk.ImageSeriesReader()
    series_reader.SetFileNames(series_file_names)
    series_reader.SetMetaDataDictionaryArrayUpdate(True)
    image3D = series_reader.Execute()
    # image3D_array = sitk.GetArrayFromImage(image3D)
    # image3D_array = image3D_array.transpose(2, 1, 0)
    # image3D = sitk.GetImageFromArray(image3D_array)
    vtkImage = itk.vtk_image_from_image(image3D)

    data = vtk.vtkImageData()

    data.DeepCopy(reader.GetOutput())
    data.SetOrigin(image3D.GetOrigin())
    data.SetSpacing(image3D.GetSpacing())
    data.SetDirectionMatrix(image3D.GetDirection())
    print("sitk origin:", image3D.GetOrigin())
    print("sitk spacing:", image3D.GetSpacing())
    print("sitk direction:", image3D.GetDirection())
    # print("origin:", data.GetOrigin())
    # print("spacing:", data.GetSpacing())
    # print("direction:", data.GetDirectionMatrix())

    ori_data = vtk.vtkImageData()
    ori_data.DeepCopy(reader.GetOutput())
    del reader

    data = vtkImage
    return data, ori_data


def dicom_to_nii(dcm_directory, nii_name):
    reader = sitk.ImageSeriesReader()
    img_name = reader.GetGDCMSeriesFileNames(dcm_directory)
    reader.SetFileNames(img_name)
    image = reader.Execute()
    image_array = sitk.GetArrayFromImage(image)
    print(image_array.shape)

    image_out = sitk.GetImageFromArray(image_array)
    image_out.SetOrigin(image.GetOrigin())
    image_out.SetSpacing(image.GetSpacing())
    image_out.SetDirection(image.GetDirection())

    print(image.GetOrigin())
    print(image.GetSpacing())
    print(image.GetDirection())

    sitk.WriteImage(image_out, nii_name)


def save_vtk_to_nii(vtkImageData, output_path):
    writer = vtk.vtkNIFTIImageWriter()
    # origin reverse
    origin = vtkImageData.GetOrigin()
    # print("origin:", origin)
    vtkImageData.SetOrigin((-origin[0], -origin[1], origin[2]))
    writer.SetInputData(vtkImageData)
    writer.SetFileName(output_path)
    writer.Write()


# if __name__ == "__main__":
#     input_path = r"D:\Code\test_data\test_rotate\test_rotate_2_angle\T_S20.6_C-12.0_601.nii.gz"
#     output_path = r"D:\Code\test_data\01_test_all\rigid-regis\output11.nii.gz"
#     data, _ = readNiftiFile(input_path)
#     print("origin:", data.GetOrigin())
#     print("spacing:", data.GetSpacing())
#     # print("direction:", data.GetDirectionMatrix())
#     save_vtk_to_nii(data, output_path)
#     data, _ = readNiftiFile(output_path)
#     print("origin:", data.GetOrigin())
#     print("spacing:", data.GetSpacing())


# if __name__ == "__main__":
#     path = r"D:\Code\test_data\test_rotate\test_rotate_2_angle"
#     dir_path = path + "\\" + "T_S20.6_C-12.0_601"
#     nii_path = dir_path + ".nii"
#     # print("nii path:", nii_path)

#     data1, _ = read_nii_to_vtk(nii_path)
#     print("spacing:", data1.GetSpacing())
#     print("origin:", data1.GetOrigin())
#     print("direction:", data1.GetDirectionMatrix())

#     # print("dir path:", dir_path)
#     # data2, _ = readDicomSeriesFile(dir_path)
#     data2, _ = read_dicom_to_vtk(dir_path)
#     print("spacing:", data2.GetSpacing())
#     print("origin:", data2.GetOrigin())
#     print("direction:", data2.GetDirectionMatrix())

#     data3, _ = readNiftiFile(nii_path)
#     print("spacing:", data3.GetSpacing())
#     print("origin:", data3.GetOrigin())
#     print("direction:", data3.GetDirectionMatrix())

#     imageData1 = data1
#     rows, cols, levels = imageData1.GetDimensions()
#     Scalars = imageData1.GetPointData().GetScalars()
#     imageArr = numpy_support.vtk_to_numpy(Scalars)
#     image3D1 = imageArr.reshape(levels, cols, rows)
#     print("Image size:", image3D1.shape)

#     imageData2 = data2
#     rows, cols, levels = imageData2.GetDimensions()
#     Scalars = imageData2.GetPointData().GetScalars()
#     imageArr = numpy_support.vtk_to_numpy(Scalars)
#     image3D2 = imageArr.reshape(levels, cols, rows)
#     print("Image size:", image3D2.shape)

#     imageData3 = data3
#     rows, cols, levels = imageData3.GetDimensions()
#     Scalars = imageData3.GetPointData().GetScalars()
#     imageArr = numpy_support.vtk_to_numpy(Scalars)
#     image3D3 = imageArr.reshape(levels, cols, rows)
#     print("Image size:", image3D3.shape)

#     import matplotlib.pyplot as plt

#     if np.equal(image3D1, image3D2).all():
#         print("The 12 images are the same.")
#         img = image3D1 - image3D2
#         # show the difference

#         plt.imshow(img[9][:][:], cmap="gray")
#         plt.colorbar()
#         plt.show()
#     else:
#         print("The two images are different.")
#         img = image3D1 - image3D2
#         # show the difference

#         plt.imshow(img[9][:][:], cmap="gray")
#         plt.colorbar()
#         plt.show()

#     if np.equal(image3D1, image3D3).all():
#         print("The 13 images are the same.")
#         img = image3D1 - image3D3
#         # show the difference

#         plt.imshow(img[9][:][:], cmap="gray")
#         plt.colorbar()
#         plt.show()
#     else:
#         print("The two images are different.")
#         img = image3D1 - image3D3
#         # show the difference

#         plt.imshow(img[9][:][:], cmap="gray")
#         plt.colorbar()
#         plt.show()


# if __name__ == "__main__":
#     # 转化文件夹中的所有dicom文件为nii.gz文件
#     directory = r"D:\Code\test_data\test_rotate_2_angle"
#     dir_list = os.listdir(directory)
#     for dir in dir_list:
#         path = os.path.join(directory, dir)
#         if os.path.isdir(path):
#             dicom_to_nii(path, dir + ".nii.gz")
#             print(dir + ".nii.gz" + "done!")

#     # 转化单个dicom文件为nii.gz文件
#     directory = r"E:\Data\wubochen_ZHANGYI_090514\t2_mx3d_sag_0.8mm_CBMFM_601"
#     dicom_to_nii(directory, "t2.nii.gz")
#     print("done!")
