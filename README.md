# sci-streak
### Python GUI for plotting and initial analysis of Streak Camera data

For use with the streak camera in the Kambhampati Lab at McGill University (should be easy to extend to other systems).

![Alt text](/data/screen.png?raw=true "sci-streak GUI")

For the scripts to correct and plot data directly see: https://github.com/dstrande/Streak-data-plotting

Currently only works for corrected picosecond/photswitch data.

Only tested on Windows with Python 3.10.

Includes example data in the form of test.hdf5. This contains only two streak datasets/traces. Please request more if you need.

Dependencies: NumPy, Scipy, h5py, PySide6, PyQtGraph

## Version notes

v005 - initial upload

v006 - Added ability to change between two traces/plots (also changed the data files to allow this).

v007 - stylesheet/color changes. Added ROI plot for decay (Now two roi plots are on the bottom). Organize into main.py and modules in /gui/

v008 - Separated stylesheet into a different file (stylesheet.qss), Updates to the data processing to correct for uneven axis window sizes. Added option to change between colormaps (other than default colormaps).

## Modules

* sci-streak.py

## TODO (in rough order)

* Include option to "save" ROI plots in the software to compare late/early times or other differences
* Organize into modules and main (partially done).
* pip installation.
* Extend to nanosecond data.
* Include option to correct the data directly.
