# Starter project: Python source code for a desktop application to interface with the [Arduino Uno microcontroller](https://github.com/tclupper/StarterUno).

### Rev 3/4/2021
### License: [Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0)

---
## Background
The _Starter Project_ the final part of a Basic Electronics course that was taught at the [Route 9 Library and Innovation center](https://nccde.org/1389/Route-9-Library-Innovation-Center) back in October of 2019.  The videos were recorded as a follow-up for the students taking the class (*not meant to be a substitute for the in-person class*).  They can be viewed here:

### Course title: _Basic Electrical Circuits_

[Introduction video](https://youtu.be/7xKFPJ8yrWM)

[Part1: Current, Resistance and Voltage](https://youtu.be/wcw07wuuB8o)

[Part2: Ohm's Law and Power](https://youtu.be/5naIT84_2M0)

[Part3: Sensors and the Arduino](https://youtu.be/qC13UVfvqh0)

[Part4: Programming the Arduino](https://youtu.be/MEm4goe0QIw)

---
## Python code
This repository contains the Python source code necessary to interface to the _Starter Project_ [Arduino Uno microcontroller board](https://github.com/tclupper/StarterUno). You will need a complete Python environment on your computer in order to compile the program.  If you are using an MS Windows-based computer, you can use this [install guide](https://github.com/tclupper/PythonInstallGuide) to help you.

The Python application uses tkinter to create a window with a basic set of user controls:
* text box with label
* checkbox
* radio buttons
* drop-down list box
* multi-line text box (used for input and output)
* menus with File and about boxes

It includes the necessary code to communicate with the Arduino Uno via the virtual com-port using the "commands" within the firmware.  You can even attached multiple Arduino Unos to the computer's USB ports and the program will allow you to select the one to communicated with.  When you start the program, it automatically loads the available Unos into a drop-down box for you to select.

The basic operation allows you to send commands to the Uno to control things like LEDs and get status of pushbuttons.  The main feature allows you to automatically read the analog port(s) of the Uno at regular intervals.  You specify the interval (in seconds) and the email notification information in the "starter.ini" file.  You check the box to start the streaming of the Arduino data.  If you specify a log file, it will log the data to the file as well as showing it on the screen.  Simply uncheck the box to stop.  Using an Arduino as a data-logger is an important and typical use case.  

In general, the idea is that you would use this code as a starting point to develop your own application.  The Python setup also allows you to compile the code to create a stand alone executable .exe file (for Windows...I have not tried Linux yet).

![](/images/screencapture.png)
### Figure#1: Screen capture
---
## Important first steps

The source code was developed using VScode. It is assumed you know how to use this IDE. The following are the steps you need to do in order to compile StarterPy.

1) Download the contents of this repository into a directory (we will use C:\StarterProject\StarterPy for example)

2) First, create a python environment from the conda base (we will call it "starter"):

```
(base) C:\>conda create -n starter python=3
(base) C:\>conda activate starter
```
3) Next, move into the StarterPy directory
```
(starter) C:\>cd C:\StarterProject\StarterPy
```
4) Install the necessary packages
```
(starter) C:\StarterProject\StarterPy>conda install --file StarterPy_requirements.txt
```
5) Finally, to create a stand alone .exe file, run the following
```
(starter) C:\StarterProject\StarterPy>pyinstaller --onefile --windowed --icon .\images\StarterPy.ico --clean --noconfirm .\StarterPy.py
```

---
## Notes:
* When you run the program, it extracts the necessary runtime files to a directory:
    * C:\Users\username\AppData\Local\Temp\_MEIxxxxxx

If you want to use a different temporary directory, use this option:
```
--runtime -tmpdir PATH
```
* To find out where the credentials are stored for GIT, type this:
```
(starter) C:\StarterProject\StarterPy>git config credential.helper
```
* if you get back: manager, then you would need to search on "credential manager" from windows search bar and open the Windows Credential Manager. Then, you would select the "Windows Credentials" and under "Generic Credentials", delete the GitHub reference.  This will reset GitHub stored credentials.


This project will be continuously evolving and improving.  However, I will try and prevent unnecessary "feature creep".

Enjoy!!

