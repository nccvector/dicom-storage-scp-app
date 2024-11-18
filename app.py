from sys import platform

import os, shutil
import signal
import sys
import subprocess
import yaml
from glob import glob

# Processing includes
import numpy as np

if platform == "linux":
    import cv2
elif platform == "win32":
    from cv2 import cv2
else:
    raise Exception("Unsupported platform")

from enum import Enum

# Dicom includes
import pydicom
import storescp

# GUI imports
import PySide6
from PySide6 import QtWidgets
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import qdarktheme

# App imports
from app2 import LayoutView

class Format(Enum):
    BMP = 0
    TIF = 1
    PNG = 2
    JPG = 3

def launchLayoutManager(path):
    view = LayoutView(path)
    view.show()


class View(QMainWindow):
    def __init__(self):
        super().__init__()
        # Setting default formate
        self.format = Format.BMP
        self.reset()
    
    def reset(self):

        # Loading config file
        self.config = None
        with open("./config.yaml", 'r') as stream:
            try:
                self.config = yaml.safe_load(stream)
                print('Config: ', self.config)
            except yaml.YAMLError as exc:
                print(exc)
        
        self.paths = self.verifyAndCreatePaths()
        for path in self.paths.values():
            print(path)

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
        self.buttonLayout = QHBoxLayout()
        self.formatLabel = QLabel("Save Format:")
        self.convertAllButton = QPushButton("Convert All")
        self.convertAllButton.clicked.connect(self.convertAll)
        self.clearAllButton = QPushButton("Clear All")
        self.clearAllButton.clicked.connect(self.clearAll)
        self.layoutButton = QPushButton("Layout Images")
        self.layoutButton.clicked.connect(self.launchLayoutManager)

        # Loading image
        self.nullImage = np.zeros((self.frameHeight, self.frameWidth, 3))
        self.showImage(self.nullImage)

        # Creating combo box
        self.comboBox = QComboBox()
        for enum in Format:
            self.comboBox.addItem(enum.name)
        self.comboBox.currentIndexChanged.connect(self.index_changed)
        
        # Setting button layout
        self.buttonLayout.addWidget(self.formatLabel, alignment=Qt.AlignRight)
        self.buttonLayout.addWidget(self.comboBox)
        self.buttonLayout.addWidget(self.convertAllButton)
        self.buttonLayout.addWidget(self.clearAllButton)
        self.buttonLayout.addWidget(self.layoutButton)

        # Laying out
        self._layout = QHBoxLayout()
        self._rightLayout = QVBoxLayout()
        self._rightLayout.addLayout(self.buttonLayout)
        self._rightLayout.addWidget(self.label)
        self._layout.addWidget(self.tree_view)
        self._layout.addLayout(self._rightLayout)
        self._w_main.setLayout(self._layout)

        # Creating and configuring model
        self.model = QFileSystemModel()
        self.model.setRootPath('./' + self.paths['DCM'])
        self.model.setFilter(QDir.NoDot | QDir.AllEntries)
        self.model.sort(0, Qt.SortOrder.AscendingOrder)

        self.sorting_model = SortingModel()
        self.sorting_model.setSourceModel(self.model)

        self.tree_view.setModel(self.sorting_model)
        self.tree_view.setRootIndex(self.sorting_model.mapFromSource(self.model.index('./' + self.paths['DCM'])))
        self.tree_view.header().setSortIndicator(0, Qt.AscendingOrder)
        self.tree_view.setSortingEnabled(True)

    
    def launchLayoutManager(self):
        launchLayoutManager(self.paths[self.format.name])
    
    def verifyAndCreatePaths(self):
        # Creating paths var
        formats = [format.name for format in Format]
        formats.append('DCM')   # Adding dicom folder
        
        paths = {}
        for form in formats:
            paths[form] = self.config['archive_path'] + '/' + form
        
        # Verifying and creating paths
        for path in paths.values():
            # Creating an archive folder is doesnt exist
            if not os.path.exists(path):
                print("CREATING " + path)
                os.makedirs(path)
        
        # Creating a path for video files
        self.videosPath = self.config['archive_path'] + '/' + 'Videos'
        if not os.path.exists(self.videosPath):
            print("CREATING " + self.videosPath)
            os.makedirs(self.videosPath)
 
        return paths
    
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

        if "dicom" in filetype or "DICOM" in filetype or "Dicom" in filetype:
            print("file is dicom")

            self.showDicomImage(path)

        else:
            self.showJpegImage(path)
            # self.showImage(self.nullImage)

        print("File Path:   ", path)
        print("File Type:   ", filetype)
        print("File Ext:    ", extension)
    
    def index_changed(self, index):
        self.format = Format(index)
        print("FORMAT SELECTED: ", self.format.name)

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
            print("STARTING VIDEO...")
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
        self.timer.start(33)
    
    def getNextFrame(self):
        """Read frame from camera and repaint QLabel widget.
        """
        curr = self.frames[self.frameCounter, :, :, :]
        curr = cv2.cvtColor(curr, cv2.COLOR_YUV2RGB)

        self.showImage(curr)

        # incrementing frame counter
        self.frameCounter += 1

        if self.frameCounter >= self.frames.shape[0]:
            self.timer.stop()
    
    # Event
    def resizeEvent(self, event):
        # self.resized.emit()
        print(event.size())

        # Updating acceptable frame dimensions
        self.frameWidth = int(0.75 * event.size().width())
        self.frameHeight = int(0.75 * event.size().height())

        # Resizing label
        # self._rightLayout.SetFixedSize(self.frameWidth, self.frameHeight)
        self.label.setFixedSize(self.frameWidth, self.frameHeight)

        # Updating the image by calling show image
        self.showImage(self.currentFrame)
    
    def convertAll(self):
        print("CONVERTING FILES")
        print("Dumping ", self.format.name)
        for f in glob('./' + self.paths['DCM'] + '/*'):
            dataset = pydicom.dcmread(f)

            # Creating file path
            filename = f.split("/")[-1]
            filename = filename[4:]
            print(filename)

            # try:
            if len(dataset.pixel_array.shape) == 4:
                filepath = self.videosPath + '/' + filename + '.mp4'
                print(filepath)

                # Have to dump a video
                _, H, W, C = dataset.pixel_array.shape
                self._capture = cv2.VideoCapture(0)
                self._outVideo = cv2.VideoWriter(filepath + '.mp4', cv2.VideoWriter_fourcc(*'MP4V'), 10, (W, H))

                for ind, data in enumerate(dataset.pixel_array):
                    # Vida frames are in YUV color space
                    # Have to swtich color channels before saving with opencv
                    data = cv2.cvtColor(data, cv2.COLOR_YUV2RGB)
                    data = data[:, :, ::-1]

                    self._outVideo.write(data)
                
                # Close the video file
                self._outVideo.release()

                #     if(self.format == Format.JPG):
                #         cv2.imwrite(filepath + str(ind) + '.jpg', data, [cv2.IMWRITE_JPEG_QUALITY, 100])
                #     elif self.format == Format.BMP:
                #         cv2.imwrite(filepath + str(ind) + '.bmp', data)
                #     elif self.format == Format.TIF:
                #         cv2.imwrite(filepath + str(ind) + '.tif', data)
                #     elif self.format == Format.PNG:
                #         cv2.imwrite(filepath + str(ind) + '.png', data)
                            
                # print("4D IMAGE NOT SUPPORTED FOR CONVERSION YET...")
            else:
                filepath = self.paths[self.format.name] + '/' + filename + '.' + self.format.name.lower()
                print(filepath)

                # Have to swtich color channels before saving with opencv
                data = dataset.pixel_array[:, :, ::-1]

                if(self.format == Format.JPG):
                    cv2.imwrite(filepath + '.jpg', data, [cv2.IMWRITE_JPEG_QUALITY, 100])
                elif self.format == Format.BMP:
                    cv2.imwrite(filepath + '.bmp', data)
                elif self.format == Format.TIF:
                    cv2.imwrite(filepath + '.tif', data)
                elif self.format == Format.PNG:
                    cv2.imwrite(filepath + '.png', data)

            # except:
            #     print("ERROR! COULD NOT SAVE THIS FILE: " + f)
            #     pass
    
    def clearAll(self):

        dlg = DeleteConfirmationDialog()

        if not dlg.exec():
            print("Cancelled")
            return

        print("Deleting")
        paths = list(self.paths.values())
        paths.append('archive/')
        for folder in paths:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print('Failed to delete %s. Reason: %s' % (file_path, e))
        
        self.reset()


class DeleteConfirmationDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Confirm!")

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        message = QLabel("Are you sure you want to delete all files?")
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


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
    app.setStyleSheet(qdarktheme.load_stylesheet())

    view = View()

    # Starting server
    process = subprocess.Popen(['python', 'storescp.py', 
                            str(view.config['port']), 
                            '-ba', view.config['ip'], 
                            '-od', view.paths['DCM'], 
                            '-aet', view.config['ae_title'], 
                            '-v'], 
                            stdout=subprocess.PIPE,
                            universal_newlines=True)

    view.show()
    app.exec()
    os.kill(process.pid, signal.SIGTERM)
    sys.exit()
