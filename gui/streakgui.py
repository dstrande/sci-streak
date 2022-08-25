from PySide6 import QtCore, QtWidgets, QtGui, QtQuick

import pyqtgraph as pg
import numpy as np
import sys
import ctypes
import json
import glob
import h5py
from functools import partial


myappid = 'sci.streak'  # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# data = np.loadtxt('ds186_00_cwl500_700ps.txt', skiprows=16)
# wavel = data[0, 1:]
# time = data[1:, 0]
# inten = data[1:, 1:]

with open('data/experiment.json', 'r', encoding='utf-8') as f:
    experiment = json.load(f)
    experiment_list = list(experiment.keys())
    experiment_list.insert(0, '#')

bar_colors = """
QMainWindow
{
    background:rgba(20,20,20,255);
    color:#fcffa4;
    font-weight:bold;
}
QTreeWidget
{
    background:rgba(30,30,30,255);
    color:#fcffa4;
}
QTreeWidget QHeaderView
{
    background:rgba(30,30,30,255);
    background-color:rgba(30,30,30,255);
    color:#fcffa4;
}
QTreeWidget QHeaderView:section
{
    background:rgba(30,30,30,255);
    background-color:rgba(30,30,30,255);
    color:#fcffa4;
}
QSplitter::handle
{
    background:rgba(50,50,50,255);
}
QStatusBar
{
    background:rgba(20,20,20,255);
    color:#fcffa4;
    font-weight:bold;
}
QMenuBar
{
    background:rgba(30,30,30,255);
    color:#fcffa4;
}
QMenuBar::item
{
    background:rgba(50,50,50,255);
    color:#fcffa4;
}
QMenuBar::item::selected
{
    background:rgba(132,32,107,150);
    color:#fcffa4;
    font-weight:bold;
}
QMenu
{
    background:rgba(132,32,107,100);
    color:#fcffa4;
    font-weight:bold;
}
QMenu::item::selected
{
    background:rgba(132,32,107,255);
    color:#fcffa4;
    font-weight:bold;
}
"""


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setStyleSheet(bar_colors)
        self.initUI()

    def initUI(self):
        exitAction = QtGui.QAction(QtGui.QIcon('gui/icons/exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)

        self.fileMenu = self.menuBar().addMenu('&File')
        self.fileMenu.addAction(exitAction)
        self.analyzeMenu = self.menuBar().addMenu('&Analysis')
        self.settingsMenu = self.menuBar().addMenu('&Settings')
        self.menuBar().setStyleSheet(bar_colors)

        self.statusBar().showMessage('Ready')
        self.statusBar().setStyleSheet(bar_colors)

        self.setWindowIcon(QtGui.QIcon('gui/icons/icon.png'))
        self.setWindowTitle('sci-streak')
        self.resize(800, 600)
        self.showMaximized()

        # Window Layout
        self.mainWidget = QtWidgets.QWidget()
        self.hbox = QtWidgets.QHBoxLayout()
        self.splitter1 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter1.setStyleSheet(bar_colors)
        self.setCentralWidget(self.mainWidget)

        # The plotting
        self.widget = pg.GraphicsLayoutWidget()

        wavel, time, self.inten = self.openhdf5(0)
        self.plot(wavel, time, self.inten)
        self.hist()

        self.roiRow = self.widget.addLayout(row=1, col=0, colspan=6)
        self.decay_plot = self.roiRow.addPlot(row=1, col=0)
        self.decay_plot.setMaximumHeight(250)
        self.decay_plot.showAxes(True)
        self.spectrum_plot = self.roiRow.addPlot(row=1, col=3)
        self.spectrum_plot.setMaximumHeight(250)
        self.spectrum_plot.showAxes(True)
        self.widget.show()
        self.roiWidget(wavel, time)
        self.roi.sigRegionChanged.connect(self.updateDecayROI)
        self.roi.sigRegionChanged.connect(self.updateSpectrumROI)
        self.updateDecayROI()
        self.updateSpectrumROI()

        self.splitter1.addWidget(self.widget)
        self.treeWidget()
        self.hbox.addWidget(self.splitter1)
        self.mainWidget.setLayout(self.hbox)

    def plot(self, x, y, z):
        self.ax2D = self.widget.addPlot(row=0, col=0, colspan=5)
        self.img = pg.ImageItem()
        print(z.shape)
        self.img.setImage(z)
        self.ax2D.addItem(self.img)
        self.ax2D.showAxes(True)

        # Move the image by half a pixel so that the center of the pixels are
        # located at the coordinate values
        dx = x[1] - x[0]
        dy = y[1] - y[0]
        print("pixel size x: {}, pixel size y: {}".format(dx, dy))

        rect = QtCore.QRectF(x[0] - dx / 2, y[0] - dy / 2, x[-1] - x[0], y[-1] - y[0])
        print(rect)
        self.img.setRect(rect)

        self.ax2D.setLabels(left='Time (ps)', bottom='Energy (eV)')

    def updatePlot(self, x, y, z):
        self.img.setImage(z)

        print(z.shape)
        # Move the image by half a pixel so that the center of the pixels are
        # located at the coordinate values
        dx = x[1] - x[0]
        dy = y[1] - y[0]
        print("pixel size x: {}, pixel size y: {}".format(dx, dy))
        print(x[0])
        print(x[-1])
        rect = QtCore.QRectF(x[0] - dx / 2, y[0] - dy / 2, x[-1] - x[0], y[-1] - y[0])
        print(rect)
        self.img.setRect(rect)

    def hist(self):
        # Contrast/color control
        self.histItem = pg.HistogramLUTItem()
        maxi = np.max(self.inten) / 2
        mini = np.average(self.inten) + 0.2
        self.histItem.setImageItem(self.img)
        self.histItem.gradient.loadPreset('inferno')
        self.histItem.setLevels(mini, maxi)
        self.widget.addItem(self.histItem, row=0, col=5, colspan=1)

    def roiWidget(self, wavel, time):
        # Custom ROI for selecting an image region
        self.roi = pg.ROI([wavel[0], time[0]],
                          [np.abs(wavel[0] - wavel[-1]) / 10, np.abs(time[0] - time[-1]) / 10],
                          rotatable=False)
        self.roi.handleSize = 7
        self.roi.addScaleHandle([1, 1], [0, 0])
        self.roi.addScaleHandle([1, 0.5], [0, 0.5])
        self.roi.addScaleHandle([0.5, 1], [0.5, 0])
        self.ax2D.addItem(self.roi)
        self.roi.setZValue(10)  # make sure ROI is drawn above image
        self.roi.getArrayRegion(self.inten, self.img, returnMappedCoords=True)

    def updateDecayROI(self):
        selected = self.roi.getArrayRegion(self.inten, self.img, returnMappedCoords=True)
        axis_select = 1
        if axis_select == 0:
            xaxis = selected[1][1][1]
        else:
            xaxis = selected[1][0][:, 0]
        self.decay_plot.plot(xaxis, selected[0].mean(axis=axis_select), clear=True)

    def updateSpectrumROI(self):
        selected = self.roi.getArrayRegion(self.inten, self.img, returnMappedCoords=True)
        axis_select = 0
        if axis_select == 0:
            xaxis = selected[1][1][1]
        else:
            xaxis = selected[1][0][:, 0]
        self.spectrum_plot.plot(xaxis, selected[0].mean(axis=axis_select), clear=True)

    def treeWidget(self):
        self.log_widget = QtWidgets.QTreeWidget()
        self.log_widget.setHeaderItem(QtWidgets.QTreeWidgetItem(experiment_list))
        self.splitter1.addWidget(self.log_widget)
        self.treeParents = {}
        self.buttons = {}

        for i in range(len(experiment['names'])):
            self.treeParents[i] = QtWidgets.QTreeWidgetItem([f'{i:02d}'])
            # self.treeParents[i] = pg.TreeWidgetItem([f'{i:02d}'])
            self.log_widget.addTopLevelItem(self.treeParents[i])
            self.buttons[i] = QtWidgets.QPushButton(experiment['sample'])
            self.log_widget.setItemWidget(self.treeParents[i], 1, self.buttons[i])
            self.buttons[i].clicked.connect(partial(self.button, i))
            for x in range(len(experiment_list) - 2):  # -2 then +2 to account for # and sample cols.
                x += 2
                self.treeParents[i].setText(x, str(experiment[experiment_list[x]][i]))
                # self.treeParents[i].setWidget(x, QtWidgets.QLabel(str(experiment[experiment_list[x]][i])))

        self.log_widget.setStyleSheet(bar_colors)

    def openhdf5(self, idx):
        with h5py.File(glob.glob("data/*.hdf5")[0], 'r') as f:
            if isinstance(idx, str):
                pass
            else:
                idx = str(idx)
            data = np.array(f.get(str(idx)))
            wavel = data[1:, 0]
            time = data[0, 1:]
            inten = data[1:, 1:]

            return wavel, time, inten

    def button(self, idx):
        print(idx)
        if type(idx) == int:
            wavel, time, self.inten = self.openhdf5(idx)
            self.updatePlot(wavel, time, self.inten)
            maxi = np.max(self.inten) / 2
            mini = np.average(self.inten) + 0.2
            self.histItem.setLevels(mini, maxi)
            self.updateSpectrumROI()
            self.updateDecayROI()


def application():
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)
    else:
        app = QtWidgets.QApplication.instance()
    main = MainWindow()
    main.show()
    sys.exit(app.exec())
