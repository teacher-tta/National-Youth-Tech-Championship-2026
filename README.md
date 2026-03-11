# National Youth Tech Championship 2026

This repository contains the code and setup tutorials used for the **National Youth Tech Championship 2026** robotics challenge.

The project focuses on using **Python and computer vision** to enable your UGOT to perform **image recognition tasks**.

---

# Setup Guide

**Note:** You MUST have already downloaded Visual Studio Code (See 'tutorials/download_vscode.md'). Windows computers MUST have also downloaded Python 3.13.12 (See 'tutorials/download_python.md')

Download either "install_WIN.bat" for Windows computers, or "install_MAC.sh" for Mac computers. Double click on the file to run it. There WILL be some warnings, since this script is attempting to install the various packages; please ignore them and run the script.

This will create a folder called "nytc" on your desktop, with a requirements.txt file and virtual environment (venv) inside. Place all relevant code inside the "nytc" folder.

Open VS Code, and go to "File" > "Open Folder" > Select your "nytc" folder to start programming!

## Repository Structure

```
National-Youth-Tech-Championship-2026/
│
├── code/
│   ├── [python scripts]
│   ├── [jupyter notebooks]
|   └── requirements.txt
│
└── tutorials/
    ├── download_python.md
    └── download_vscode.md
```

### `code/`

This folder contains all the **Python scripts and Jupyter notebooks** used for the robot's image recognition system.

The code includes:

* Image capture and processing
* Model testing and debugging notebooks
* Supporting scripts used during development

### `tutorials/`

This folder contains setup guides to help users prepare their development environment.

Current tutorials include:

* **`download_python.md`**
  A guide for installing Python which is required to run the project.

* **`download_vscode.md`**
  Instructions for installing Visual Studio Code and recommended extensions for Python development.

---

## Requirements

To run the code in this repository, you will need:

* Python 3.13.12 (recommended)
* Jupyter Notebook standalone, or
* Visual Studio Code with Jupyter notebook extension (recommended)

---

## Getting Started

1. Follow the setup guides in the **`tutorials/`** folder.
2. Install Python.
3. Install Visual Studio Code.
4. Open the `code/` folder to explore the Python scripts and Jupyter notebooks.
5. Run the notebooks or scripts to test the image recognition features.

---

## Notes

Some scripts may require a connected UGOT robot to function properly.

The links to the relevant documentation of some packages we will use are below:
- [UGOT](https://docs.ubtrobot.com/ugot/#/en-us/extension/python_sdk/version)
- [opencv-python](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [ultralytics](https://docs.ultralytics.com/reference/engine/results/#ultralytics.engine.results.Boxes)
