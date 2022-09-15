from PySide6 import QtCore, QtWidgets, QtGui

import pyqtgraph as pg
import numpy as np
import sys
import os
import ctypes
import json
import glob
import h5py
from scipy import interpolate
from scipy.signal import decimate
from functools import partial
import time as timing


myappid = 'sci.streak'  # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

path = f'{os.path.dirname(sys.argv[0])}/gui'

with open('data/experiment.json', 'r', encoding='utf-8') as f:
    experiment = json.load(f)
    experiment_list = list(experiment.keys())
    experiment_list.insert(0, '#')

with open(f'{path}/ui/stylesheet.qss', 'r', encoding='utf-8') as file:
    stylesheet = file.read()

if len(glob.glob('data/*.hdf5'))==0:
    raise Exception('You should use the bksub script to create the hdf5 file.')


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setStyleSheet(stylesheet)
        self.initUI()

    def initUI(self):
        self.menuBarOutline()
        self.statusBar().showMessage('Ready')
        self.statusBar().setStyleSheet(stylesheet)

        self.setWindowIcon(QtGui.QIcon(f'{path}/icons/icon.png'))
        self.setWindowTitle('sci-streak')
        self.resize(800, 600)  # Fix for not starting maximized.
        self.showMaximized()

        # Window Layout
        self.mainWidget = QtWidgets.QWidget()
        self.hbox = QtWidgets.QHBoxLayout()
        self.splitter1 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter1.setStyleSheet(stylesheet)
        self.setCentralWidget(self.mainWidget)

        # Populate Layout
        self.plotLayout()
        self.treeWidget()
        self.controlWidgets()
        self.rightLayout()
        self.splitter1.addWidget(self.leftwidget)
        self.splitter1.addWidget(self.rightwidget)

        self.hbox.addWidget(self.splitter1)
        self.mainWidget.setLayout(self.hbox)

    def menuBarOutline(self):
        exitAction = QtGui.QAction(QtGui.QIcon(f'{path}icons/exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)

        self.fileMenu = self.menuBar().addMenu('&File')
        self.fileMenu.addAction(exitAction)
        self.analyzeMenu = self.menuBar().addMenu('&Analysis')
        self.settingsMenu = self.menuBar().addMenu('&Settings')
        self.colorMenu = self.settingsMenu.addMenu('Choose Colormap')

        self.inferno = QtGui.QAction('inferno', self)
        self.colorMenu.addAction(self.inferno)
        self.inferno.triggered.connect(partial(self.changeColormap, 'inferno'))
        self.turbo = QtGui.QAction('turbo', self)
        self.colorMenu.addAction(self.turbo)
        self.turbo.triggered.connect(partial(self.changeColormap, 'turbo'))
        self.viridis = QtGui.QAction('viridis', self)
        self.colorMenu.addAction(self.viridis)
        self.viridis.triggered.connect(partial(self.changeColormap, 'viridis'))
        self.spectral = QtGui.QAction('spectral', self)
        self.colorMenu.addAction(self.spectral)
        self.spectral.triggered.connect(partial(self.changeColormap, 'nipy_spectral'))

        self.menuBar().setStyleSheet(stylesheet)

    def plotLayout(self):
        self.leftwidget = pg.GraphicsLayoutWidget()
        self.downsampleFactor()
        wavel, time, self.inten = self.openhdf5(0)
        self.plot(wavel, time, self.inten)
        self.hist()

        self.roiRow = self.leftwidget.addLayout(row=1, col=0, colspan=6)
        self.decay_plot = self.roiRow.addPlot(row=1, col=0)
        self.decay_plot.setMaximumHeight(250)
        self.decay_plot.showAxes(True)
        self.spectrum_plot = self.roiRow.addPlot(row=1, col=3)
        self.spectrum_plot.setMaximumHeight(250)
        self.spectrum_plot.showAxes(True)
        self.leftwidget.show()
        self.roiWidget(wavel, time)
        self.roi.sigRegionChanged.connect(self.updateDecayROI)
        self.roi.sigRegionChanged.connect(self.updateSpectrumROI)
        self.updateDecayROI()
        self.updateSpectrumROI()

    def rightLayout(self):
        self.rightwidget = QtWidgets.QWidget()
        self.optionsLayout = QtWidgets.QVBoxLayout()
        self.optionsLayout.addWidget(self.log_widget)
        self.optionsLayout.addLayout(self.controlsLayout)
        self.rightwidget.setLayout(self.optionsLayout)

    def plot(self, x, y, z):
        self.ax2D = self.leftwidget.addPlot(row=0, col=0, colspan=5)
        self.img = pg.ImageItem()
        # print(z.shape)
        self.img.setImage(z)
        self.ax2D.addItem(self.img)

        # Move the image by half a pixel so that the center
        # of the pixels are located at the coordinate values
        dx = x[1] - x[0]
        dy = y[1] - y[0]
        print('pixel size x: {}, pixel size y: {}'.format(dx, dy))
        rect = QtCore.QRectF(x[0] - dx / 2, y[0] - dy / 2, x[-1] - x[0], y[-1] - y[0])
        print(rect)
        self.img.setRect(rect)

        self.ax2D.setLabels(left='Time (ps)', bottom='Energy (eV)')

    def updatePlot(self, x, y, z):
        self.img.setImage(z)

        # print(z.shape)
        # Move the image by half a pixel so that the center of the pixels are
        # located at the coordinate values
        dx = x[1] - x[0]
        dy = y[1] - y[0]
        print('pixel size x: {}, pixel size y: {}'.format(dx, dy))
        rect = QtCore.QRectF(x[0] - dx / 2, y[0] - dy / 2, x[-1] - x[0], y[-1] - y[0])
        print(rect)
        self.img.setRect(rect)

    def hist(self):
        # Contrast/color control
        self.histItem = pg.HistogramLUTItem()
        maxi = np.max(self.inten) / 2
        mini = np.average(self.inten) + 0.2
        self.histItem.setImageItem(self.img)
        cmap = pg.colormap.get('inferno', source='matplotlib', skipCache=False)
        self.histItem.gradient.setColorMap(cmap)
        self.histItem.gradient.showTicks(show=False)
        self.histItem.setLevels(mini, maxi)
        self.leftwidget.addItem(self.histItem, row=0, col=5, colspan=1)

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
        xaxis = selected[1][0][:, 0]
        self.decay_plot.plot(xaxis, selected[0].mean(axis=axis_select), clear=True)

    def updateSpectrumROI(self):
        selected = self.roi.getArrayRegion(self.inten, self.img, returnMappedCoords=True)
        axis_select = 0
        xaxis = selected[1][1][0]
        self.spectrum_plot.plot(xaxis, selected[0].mean(axis=axis_select), clear=True)

    def treeWidget(self):
        self.log_widget = QtWidgets.QTreeWidget()
        self.log_widget.setHeaderItem(QtWidgets.QTreeWidgetItem(experiment_list))
        self.treeParents = {}
        self.buttons = {}

        for i in range(len(experiment['names'])):
            self.treeParents[i] = QtWidgets.QTreeWidgetItem([f'{i:02d}'])
            self.log_widget.addTopLevelItem(self.treeParents[i])
            self.buttons[i] = QtWidgets.QPushButton(experiment['sample'])
            self.log_widget.setItemWidget(self.treeParents[i], 1, self.buttons[i])
            self.buttons[i].clicked.connect(partial(self.button, i))
            for x in range(len(experiment_list) - 2):  # -2 then +2 to account for # and sample cols.
                x += 2
                self.treeParents[i].setText(x, str(experiment[experiment_list[x]][i]))

        self.log_widget.setStyleSheet(stylesheet)

    def openhdf5(self, idx):
        """
        Method to import data for an .hdf5 file.
        Note that there should be only one hdf5 file in the working directory.
        """
        with h5py.File(glob.glob('data/*.hdf5')[0], 'r') as f:
            if isinstance(idx, str):
                pass
            else:
                idx = str(idx)
            data = np.array(f.get(str(idx)))

        wavel = data[1:, 0]
        wavel += 0.008  # Correction for this specific dataset.
        time = data[0, 1:]
        inten = data[1:, 1:]
        # print(inten.shape)

        xlabels, ylabels, data = self.downsample(wavel, time, inten)
        xlabels, ylabels, data = self.rebin(xlabels, ylabels, data, self.downsample_factor)
        # print(data.shape)

        return xlabels, ylabels, data

    def downsampleFactor(self, value=1):
        """
        TODO: add slider and button to choose downsample size.
        Currently fixed to 2.
        See the downsample method.
        """
        self.downsample_factor = value

    def rebin(self, wavel, time, inten, downsample):
        """
        Method used to downsample or rebin data for speed reasons.
        There is a trade off between speed and resolution.
        Note that the energy and time resolution is much less than the pixel size.
        e.g. time resolution of ~4 ps and pixel size of ~0.35ps per pixel.

        If the downsample factor is not a factor of axis sizes:
            - the x axis remainder sliced from the high energy side and
            - the y axis remainder sliced from before time zero.
        These areas are the most likely to not contain any important data.
        """
        M, N = inten.shape

        if M % downsample != 0:
            remove = -1 * (M % downsample)
            inten = inten[:remove, :]
            wavel = wavel[:remove]

        if N % downsample != 0:
            remove = N % downsample
            inten = inten[:, remove:]
            time = time[remove:]

        M, N = inten.shape
        m, n = M // downsample, N // downsample

        wavel = np.average(wavel.reshape(-1, downsample), axis=1)
        time = np.average(time.reshape(-1, downsample), axis=1)

        print(n, m, N, M)
        return wavel, time, inten.reshape((m, downsample, n, downsample)).mean(3).mean(1)

    def downsample(self, wavel, time, inten):
        """
        Method used to even the spacing between each point on both axes.
        For example the time axis ranges between ~0.25 to ~0.45ps spacing.

        This method uses interpolation to even the spacing to the mean.

        Currently RectBivariateSpline is used.
        """
        # Currently using the mean window sizes for the final step size.
        step_x = np.ediff1d(wavel).mean()
        step_y = np.ediff1d(time).mean()

        # Function to generate interpolated values from our irregular grid
        t0 = timing.time()
        f = interpolate.RectBivariateSpline(wavel, time, inten)
        t1 = timing.time()
        print(f'Interpolate time: {t1 - t0}')

        # Generate new data on the regular grid
        xlabels = np.arange(wavel[0], wavel[-1] + step_x, step_x)
        ylabels = np.arange(time[0], time[-1] + step_y, step_y)
        data = f(xlabels, ylabels)

        # print(data.shape)

        return xlabels, ylabels, data

    def button(self, idx):
        if type(idx) == int:
            wavel, time, self.inten = self.openhdf5(idx)
            self.updatePlot(wavel, time, self.inten)
            maxi = np.max(self.inten) / 2
            mini = np.average(self.inten) + 0.2
            self.histItem.setLevels(mini, maxi)
            self.updateSpectrumROI()
            self.updateDecayROI()

    def changeColormap(self, cmapstr):
        cmap = pg.colormap.get(cmapstr, source='matplotlib', skipCache=False)
        self.histItem.gradient.setColorMap(cmap)
        self.histItem.gradient.showTicks(show=False)

    def controlWidgets(self):
        downsampleLabel = QtWidgets.QLabel('Choose the downsample value: ')
        downsampleSpinBox = QtWidgets.QSpinBox()
        downsampleSpinBox.setValue(1)
        downsampleSpinBox.setRange(1, 5)
        colormapLabel = QtWidgets.QLabel('Choose the colormap: ')
        colormapCombo = QtWidgets.QComboBox()
        colormapCombo.addItem('inferno')
        colormapCombo.addItem('turbo')
        colormapCombo.addItem('viridis')
        colormapCombo.addItem('nipy_spectral')

        downsampleLabel.setStyleSheet(stylesheet)
        downsampleSpinBox.setStyleSheet(stylesheet)
        colormapLabel.setStyleSheet(stylesheet)
        colormapCombo.setStyleSheet(stylesheet)

        downsampleSpinBox.valueChanged.connect(self.downsampleFactor)
        colormapCombo.currentTextChanged.connect(self.changeColormap)

        self.controlsLayout = QtWidgets.QGridLayout()
        self.controlsLayout.addWidget(downsampleLabel, 0, 0)
        self.controlsLayout.addWidget(downsampleSpinBox, 0, 1)
        self.controlsLayout.addWidget(colormapLabel, 1, 0)
        self.controlsLayout.addWidget(colormapCombo, 1, 1)


def application():
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)
    else:
        app = QtWidgets.QApplication.instance()
    main = MainWindow()
    main.show()
    sys.exit(app.exec())
