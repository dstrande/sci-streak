# sci-streak
### Python GUI for plotting and initial analysis of Streak Camera data

For use with the streak camera in the Kambhampati Lab at McGill University (should be easy to extend to systems).

Currently only works for corrected picosecond/photswitch data.

Only tested on Windows with Python 3.10.

Includes example data in the form of text.hdf5. This contains only one streak dataset. Please request more if you need.

Dependencies: NumPy, Scipy, h5py, PySide6, PyQtGraph

## Modules

* sci-streak.py

## TODO

* Extend to nanosecond data.
* Include option to correct the data directly.
* Include option to "save" ROI plots in the software to compare late/early times or other differences
* Organize into modules and main
* pip installation
