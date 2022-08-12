# sci-streak
### Python GUI for plotting and initial analysis of Streak Camera data

For use with the streak camera in the Kambhampati Lab at McGill University (should be easy to extend to other systems).

For the scripts to correct and plot data directly see: https://github.com/dstrande/Streak-data-plotting

Currently only works for corrected picosecond/photswitch data.

Only tested on Windows with Python 3.10.

Includes example data in the form of test.hdf5. This contains only one streak dataset. Please request more if you need.

Dependencies: NumPy, Scipy, h5py, PySide6, PyQtGraph

## Modules

* sci-streak.py

## TODO

* Extend to nanosecond data.
* Include option to correct the data directly.
* Include option to "save" ROI plots in the software to compare late/early times or other differences
* Organize into modules and main
* pip installation
