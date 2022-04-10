import os
import signal
import sys
import subprocess
import yaml
from glob import glob

import numpy as np
from cv2 import cv2
import pydicom
import storescp

import PySide6
from PySide6 import QtWidgets
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class View(QMainWindow):
    def __init__(self):

        # Loading config file

        self.config = None
        with open("./config.yaml", 'r') as stream:
            try:
                self.config = yaml.safe_load(stream)
                print('Config: ', self.config)
            except yaml.YAMLError as exc:
                print(exc)

        super().__init__()
        self.frameCounter = 0
        self.frames = None
        self.currentFrame = None
        self.frameWidth = 800
        self.frameHeight = 600

        self._w_main = QWidget()
        self.setCentralWidget(self._w_main)
        self.tree_view = QTreeView(self._w_main)
        self.tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # self.tree_view.expanded.connect(self.onExpand)
        self.tree_view.clicked.connect(self.on_click)
        self.label = QLabel(self._w_main)
        self.buttonLayout = QVBoxLayout()
        self.convertAllToJpegButton = QPushButton("Convert All -> Jpeg")
        self.convertAllToJpegButton.clicked.connect(self.convertAllToJpeg)
        self.buttonLayout.addWidget(self.convertAllToJpegButton)
        # self.label.setFixedSize(800, 600)

        # Loading image
        self.nullImage = np.zeros((600, 800, 3))
        self.showImage(self.nullImage)

        self._layout = QHBoxLayout()
        self._layout.addWidget(self.tree_view)
        self._layout.addWidget(self.label)
        self._layout.addLayout(self.buttonLayout)
        self._w_main.setLayout(self._layout)

        # Creating and configuring model
        self.model = QFileSystemModel()
        self.model.setRootPath('./' + self.config['instance_location'])
        self.model.setFilter(QDir.NoDot | QDir.AllEntries)
        self.model.sort(0, Qt.SortOrder.AscendingOrder)

        self.sorting_model = SortingModel()
        self.sorting_model.setSourceModel(self.model)

        self.tree_view.setModel(self.sorting_model)
        self.tree_view.setRootIndex(self.sorting_model.mapFromSource(self.model.index('./' + self.config['instance_location'])))
        self.tree_view.header().setSortIndicator(0, Qt.AscendingOrder)
        self.tree_view.setSortingEnabled(True)
    
    def traverseDirectory(self, parentindex):
        print('traverseDirectory():')
        if self.hasChildren(parentindex):
            print('|children|: {}'.format(self.rowCount(parentindex)))
            for childRow in range(self.rowCount(parentindex)):
                childIndex = parentindex.child(childRow, 0)
                print('child[{}]: recursing'.format(childRow))
                self.traverseDirectory(childIndex)
        else:
            print('no children')
    
    def on_click(self, item):
        # print item from first column
        # index = self.tree_view.selectedIndexes()[0]
        index = self.tree_view.currentIndex()
        mappedIndex = self.sorting_model.mapToSource(index)

        # Getting the path of selected item
        path = QFileSystemModel(self.model).filePath(mappedIndex)
        filetype = QFileSystemModel(self.model).type(mappedIndex)
        extension = path.split('.')[-1]

        if "jpeg" in filetype or "JPEG" in filetype or "Jpeg" in filetype:
            print("file is jpeg")

            # Loading image
            self.showJpegImage(path)

        elif "dicom" in filetype or "DICOM" in filetype or "Dicom" in filetype:
            print("file is dicom")

            self.showDicomImage(path)

        else:
            print("Un-supported file type")

            self.showImage(self.nullImage)

        print("File Path:   ", path)
        print("File Type:   ", filetype)
        print("File Ext:    ", extension)

    # Expects opencv frame
    def showImage(self, frame):

        # Updating current frame (used for resizing)
        self.currentFrame = frame

        # Resizing frame to current acceptable framesize
        frame = cv2.resize(frame, (self.frameWidth, self.frameHeight), cv2.INTER_AREA)

        # Creating image from frame
        image = QImage(frame, frame.shape[1], frame.shape[0], 
                    frame.strides[0], QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(image)
        self.label.setPixmap(pixmap)
    
    def showJpegImage(self, path):
        frame = cv2.imread(path)
        
        self.showImage(frame)
    
    def showDicomImage(self, path):
        dataset = pydicom.dcmread(path)

        if(len(dataset.pixel_array.shape) == 4):
            print("FOUR FOUR FOUR FOUR FOUR")
            frame = dataset.pixel_array
            self.showVideo(frame)

        else:
            frame = dataset.pixel_array[:, :, :]
            self.showImage(frame)
    
    def showVideo(self, frame):
        self.frameCounter = 0
        self.frames = frame

        # intialize a thread timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.getNextFrame)
        self.timer.start(10)
    
    def getNextFrame(self):
        """Read frame from camera and repaint QLabel widget.
        """
        curr = self.frames[self.frameCounter, :, :, :]

        self.showImage(curr)

        # incrementing frame counter
        self.frameCounter += 1
    
    # Event
    def resizeEvent(self, event):
        # self.resized.emit()
        print(event.size())

        # Updating acceptable frame dimensions
        self.frameWidth = int(0.75 * event.size().width())
        self.frameHeight = int(0.9 * event.size().height())

        # Resizing label
        self.label.setFixedSize(self.frameWidth, self.frameHeight)

        # Updating the image by calling show image
        self.showImage(self.currentFrame)
    
    def convertAllToJpeg(self):
        for f in glob('./' + self.config['instance_location'] + '/*'):
            print("Displaying file: ", f)

            dataset = pydicom.dcmread(f)
            # print(dataset.pixel_array.shape)

            try:

                if(len(dataset.pixel_array.shape) == 4):
                    cv2.imwrite(f + '.jpg', dataset.pixel_array[int(i/2), :, :, :], [cv2.IMWRITE_JPEG_QUALITY, 100])
                else:
                    cv2.imwrite(f + '.jpg', dataset.pixel_array[:, :, :], [cv2.IMWRITE_JPEG_QUALITY, 100])
            except:
                print("ERROR! COULD NOT SAVE THIS FILE: " + f)
                pass


class SortingModel(QSortFilterProxyModel):
    def lessThan(self, source_left, source_right):
        file_info1 = self.sourceModel().fileInfo(source_left)
        file_info2 = self.sourceModel().fileInfo(source_right)       
        
        if file_info1.fileName() == "..":
            return self.sortOrder() == Qt.SortOrder.AscendingOrder

        if file_info2.fileName() == "..":
            return self.sortOrder() == Qt.SortOrder.DescendingOrder
                
        if (file_info1.isDir() and file_info2.isDir()) or (file_info1.isFile() and file_info2.isFile()):
            return super().lessThan(source_left, source_right)

        return file_info1.isDir() and self.sortOrder() == Qt.SortOrder.AscendingOrder


if __name__ == "__main__":

    app = QtWidgets.QApplication([])

    view = View()

    # Starting server
    process = subprocess.Popen(['python', 'storescp.py', 
                            str(view.config['port']), 
                            '-ba', view.config['ip'], 
                            '-od', view.config['instance_location'], 
                            '-aet', view.config['ae_title'], 
                            '-v'], 
                            stdout=subprocess.PIPE,
                            universal_newlines=True)

    view.show()
    app.exec()
    os.kill(process.pid, signal.SIGTERM)
    sys.exit()