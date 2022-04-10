from cv2 import cv2
import matplotlib.pyplot as plt
import pydicom
from pydicom.data import get_testdata_file
from glob import glob

for f in glob('./archive/*'):
    print("Displaying file: ", f)

    dataset = pydicom.dcmread(f)
    # print(dataset.pixel_array.shape)

    if(len(dataset.pixel_array.shape) == 4):
        for i in range(dataset.pixel_array.shape[0]):
            cv2.imshow("Image", dataset.pixel_array[i, :, :, 0])
            cv2.waitKey(66)
    else:
        cv2.imshow("Image", dataset.pixel_array[:, :, :])
        cv2.waitKey(0)