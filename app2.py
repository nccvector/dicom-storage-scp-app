from sys import platform

import os
import sys
from glob import glob

# Processing includes
import numpy as np

if platform == "linux":
    import cv2
    from cv2 import borderInterpolate
elif platform == "win32":
    from cv2 import borderInterpolate, cv2

from enum import Enum
from functools import partial

# GUI imports
from PySide6 import QtWidgets
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import qdarktheme

frameWidth = 800
frameHeight = 600


class Corner(Enum):
    TL = [0, 0]
    TR = [0, 1]
    BL = [1, 0]
    BR = [1, 1]


class LayoutView(QMainWindow):
    def __init__(self, path):

        super().__init__()
        self.path = path
        self.reset()

    def reset(self):
        self._w_main = QWidget()
        self.setCentralWidget(self._w_main)

        # Laying out
        self.quadImageGroupBox = QuadImageGroupBox(self)
        self.gallery = Gallery(self)
        self.saveForm = SaveForm(self)

        self.stackedLayout = QStackedLayout()
        self.stackedLayout.addWidget(self.quadImageGroupBox)
        self.stackedLayout.addWidget(self.gallery)
        self.stackedLayout.addWidget(self.saveForm)

        self._w_main.setLayout(self.stackedLayout)

    def HorzCat(self, imageA, imageB):
        width = imageA.shape[1] + imageB.shape[1]
        height = max(imageA.shape[0], imageB.shape[0])

        image = np.zeros((height, width, imageA.shape[2]), dtype=np.uint8)
        image[:imageA.shape[0], :imageA.shape[1], :] = imageA
        image[:imageB.shape[0], imageA.shape[1]:imageA.shape[1]+imageB.shape[1], :] = imageB

        return image

    def VertCat(self, imageA, imageB):
        width = max(imageA.shape[1], imageB.shape[1])
        height = imageA.shape[0] + imageB.shape[0]

        image = np.zeros((height, width, imageA.shape[2]), dtype=np.uint8)
        image[:imageA.shape[0], :imageA.shape[1], :] = imageA
        image[imageA.shape[0]:, :imageB.shape[1], :] = imageB

        return image

    def concatAndSave(self):
        topRow = self.HorzCat(
            self.quadImageGroupBox.images[Corner.TL.name],
            self.quadImageGroupBox.images[Corner.TR.name],
        )

        bottomRow = self.HorzCat(
            self.quadImageGroupBox.images[Corner.BL.name],
            self.quadImageGroupBox.images[Corner.BR.name],
        )

        fullImage = self.VertCat(
            topRow,
            bottomRow,
        )

        # fullImage = np.zeros((2 * maxHeight, 2 * maxWidth, 3), dtype=np.uint8)

        # fullImage[:maxHeight, :maxWidth, :] = self.quadImageGroupBox.images[Corner.TL.name]
        # fullImage[:maxHeight, maxWidth:, :] = self.quadImageGroupBox.images[Corner.TR.name]
        # fullImage[maxHeight:, :maxWidth, :] = self.quadImageGroupBox.images[Corner.BL.name]
        # fullImage[maxHeight:, maxWidth:, :] = self.quadImageGroupBox.images[Corner.BR.name]

        bordersize = 30
        bordered = cv2.copyMakeBorder(
            fullImage,
            top=bordersize,
            bottom=bordersize,
            left=bordersize,
            right=bordersize,
            borderType=cv2.BORDER_CONSTANT,
            value=[255, 255, 255]
        )

        cv2.imwrite('archive/' + self.saveForm.filename.text(), bordered)

        self.close()
        # self.reset()
        # self.hide()


class SaveForm(QWidget):
    def __init__(self, parent):
        super().__init__()

        self.parent = parent

        self.filename = QLineEdit("output.bmp")
        self.saveButton = QPushButton("Save")
        self.saveButton.clicked.connect(self.onSave)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.onCancel)
        self.mainLayout = QFormLayout()
        self.mainLayout.addRow('Filename:', self.filename)
        self.mainLayout.addRow(' ', self.saveButton)
        self.mainLayout.addRow(' ', self.cancelButton)

        self.setLayout(self.mainLayout)

    def onSave(self):
        self.parent.concatAndSave()

    def onCancel(self):
        self.parent.restart()


class QuadImageGroupBox(QGroupBox):
    def __init__(self, parent):
        super().__init__()

        self.parent = parent

        self.mainLayout = QVBoxLayout()

        self.gridLayout = QGridLayout()

        self.saveLayoutImageButton = QPushButton("Save Layout Image")
        self.mainLayout.addWidget(self.saveLayoutImageButton)
        self.saveLayoutImageButton.clicked.connect(self.onClickChangeToSaveFormView)

        self.mainLayout.addLayout(self.gridLayout)

        self.currentCorner = None

        # Filling grid layout
        self.buttons = {}
        self.images = {}
        for corner in Corner:
            button = BigButton("+ Add Image", corner)
            button.clicked.connect(partial(self.onClickChangeToImageListView, corner))
            self.gridLayout.addWidget(button, corner.value[0], corner.value[1])

            self.buttons[corner.name] = button
            self.images[corner.name] = None

        self.setLayout(self.mainLayout)
        self.updateSize()

    def updateSize(self):
        self.setFixedSize(frameWidth + 30, frameHeight + 30)

    def onClickChangeToImageListView(self, corner):
        self.currentCorner = corner  # Update selected corner
        self.parent.stackedLayout.setCurrentIndex(1)  # Change page to image list view

    def onClickChangeToSaveFormView(self):
        self.parent.stackedLayout.setCurrentIndex(2)  # Change page to image list view

    def setImage(self, path):
        # loading image using cv2
        image = cv2.imread(path)

        # Update the frame size
        global frameWidth, frameHeight
        frameWidth = int(frameWidth)
        frameHeight = int(frameWidth * image.shape[0] / image.shape[1])
        self.updateSize()

        self.images[self.currentCorner.name] = image

        # Saving preview image
        if not os.path.exists('cache'):
            os.mkdir('cache')

        imgName = path.split('/')[-1]
        previewPath = 'cache/' + imgName
        prev = image.copy()
        prev = cv2.resize(prev, (int(frameWidth/2), int(frameHeight/2)), cv2.INTER_AREA)
        cv2.imwrite(previewPath, prev)

        button = self.buttons[self.currentCorner.name]
        button.setFixedSize(frameWidth/2, frameHeight/2)
        button.setStyleSheet(
            'background-image : url(' + previewPath + ');' +
            'background-repeat: no-repeat;' +
            'background-position: center;')

        print("Setting image to", self.currentCorner)


class Gallery(QScrollArea):
    def __init__(self, parent):

        super().__init__()

        self.parent = parent
        self.vertLayout = QVBoxLayout()
        self.thumbnails = QGroupBox()

        # FIlling vertlayout
        images_path = 'archive/PNG'
        for path in glob('./' + images_path + '/*'):
            self.vertLayout.addWidget(DragLabel(path, self))

        self.thumbnails.setLayout(self.vertLayout)
        self.setWidget(self.thumbnails)
        self.setMaximumWidth(350)


class BigButton(QPushButton):
    def __init__(self, title, corner):
        super().__init__()

        # Button corner
        self.corner = corner

        self.setText(title)
        self.setFont(QFont('times', 30))
        self.setFixedSize(frameWidth/2, frameHeight/2)


class DragLabel(QLabel):
    def __init__(self, path, parent):
        super(DragLabel, self).__init__()

        self.parent = parent
        self.filePath = path

        frame = cv2.imread(self.filePath)[:, :, ::-1]
        frame = cv2.resize(frame, (300, 300), cv2.INTER_AREA)
        image = QImage(frame, frame.shape[1], frame.shape[0],
                       frame.strides[0], QImage.Format_RGB888)

        # Create a label widget and add to vertical layout
        self.setPixmap(QPixmap.fromImage(image))

    def mousePressEvent(self, event):
        self.parent.parent.stackedLayout.setCurrentIndex(0)  # change page to grid view
        self.parent.parent.quadImageGroupBox.setImage(self.filePath)


if __name__ == "__main__":

    app = QtWidgets.QApplication([])
    app.setStyleSheet(qdarktheme.load_stylesheet())

    view = LayoutView('archive/PNG')

    view.show()
    app.exec()
    sys.exit()
