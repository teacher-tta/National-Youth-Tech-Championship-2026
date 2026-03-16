# National Youth Tech Championship 2026

This repository contains the code and setup tutorials used for the **National Youth Tech Championship 2026** robotics challenge.

The project focuses on using **Python and computer vision** to enable your UGOT to perform **image recognition tasks**.

This repository contains some sample files, but more **in depth guides** on OpenCV and UGOT can be found in [Notes](#notes).

---

# Relevant links

1. [Setup Guide](#setup-guide)
2. [How to Download and Install Visual Studio Code (Windows and Mac)](tutorials/VSCODE_DOWNLOAD.md)
3. [How to Download and Install Python 3.13 (Windows Only)](tutorials/WINDOWS_PYTHON.md)
4. [Connecting to the UGOT Robot](tutorials/UGOT_CONNECTION.md)

# Setup Guide

**Note:** You MUST have already downloaded Visual Studio Code [(click here)](tutorials/VSCODE_DOWNLOAD.md). Windows computers MUST have also already downloaded Python 3.13.12 [(click here)](tutorials/WINDOWS_PYTHON.md). Mac users do not need to download Python manually, as the following tutorial will auto install the correct version of Python for them.

Download either ["install_WIN.bat"](install_WIN.bat) for Windows computers, or ["install_MAC.sh"](install_MAC.sh) for Mac computers. Once you have downloaded it, double click on the file to run it. There WILL be some warnings, since this script is attempting to install the various packages; please ignore them and run the script.

This will create a folder called "National-Youth-Tech-Championship-2026" on your desktop, with a requirements.txt file and virtual environment (venv) inside. Place all relevant code inside the "National-Youth-Tech-Championship-2026" folder.

Open VS Code, and go to "File" > "Open Folder" > Select your "National-Youth-Tech-Championship-2026" folder to start programming!

# Notes

Some scripts may require a connected UGOT robot to function properly.

The links to the relevant documentation of some packages we will use are below:
- [UGOT](https://docs.ubtrobot.com/ugot/#/en-us/extension/python_sdk/version)
- [opencv-python](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [ultralytics](https://docs.ultralytics.com/reference/engine/results/#ultralytics.engine.results.Boxes)
