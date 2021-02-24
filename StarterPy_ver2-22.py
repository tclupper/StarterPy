# Imports
import tkinter as tk                # Used for the GUI
from tkinter import filedialog      # Used for the GUI
from tkinter import messagebox      # Used for the GUI
import webbrowser as wb             # Used to spawn a browser
import time                         # Used to pause operation for a few seconds (during serial device bootup)
import serial                       # Used to communication to the Arduino (or other serial devices)
import psutil                       # Used to determine power status in laptops 
import sys                          # Used in finding availabale ports
import glob                         # Used in finding availabele ports
import smtplib, ssl                                 # Used for email notification
from email.mime.text import MIMEText                # Used for email notification
from email.mime.multipart import MIMEMultipart      # Used for email notification

#region ~~~~~~~~~~  Global variables  that can be accessed anywhere in the "StarterPy" namespace. ~~~~~~~~~~~
#   - This probably wants to be put in a data class or dictionary or something (Need ideas here...)
TimerAfterID = ""
ComPortName = ""
SenderEmail = ""
Password = ""
NotifyEmail = ""
SaveFilename = ""
# Font family examples:  Courier, Helvetica, Times, etc.
# Font size examples:  8, 10, 11, 12, etc.
# Font weight examples: Normal, Bold, Italic, italic, etc. 
normalfont = ('Helvetica','10','normal')
boldfont = ('Helvetica','10','bold')
#endregion

#region ~~~~~~~~~~  tkinter GUI code as a Class  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class tkinterGUI(tk.Tk):

    def __init__(self):
        super().__init__(className="tkinterGUI")
        self.title('Starter Application')
        self.geometry('800x600')
        self.resizable(width=False, height=False)

        # You can find free icons here (I downloaded a 32px by 32px .png file): https://www.flaticon.com/
        # You can then convert them to an .ico image here (retain 32px by 32px size): https://icoconvert.com/
        # Put the path for the .ico file below
        try:
            self.iconbitmap(".\images\StarterPy.ico")
        except:
            pass        # If the icon file is not there

        self.availports=[]      # A list of possible serial ports available (used only in tkinterGUI class)

        self.protocol("WM_DELETE_WINDOW", self.quitprogram)     # Needed to provide a good exit stratagy

        # ================== Add a menu ======================================================================
        self.my_menu = tk.Menu(self)
        self.config(menu=self.my_menu)
        # Create menu items ---------------------------------------------------------------------
        self.file_menu = tk.Menu(self.my_menu,tearoff=False)
        self.my_menu.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Save As...", command=self.func_opendialog)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.quitprogram)
        # Create a help menu ---------------------------------------------------------------------
        self.help_menu = tk.Menu(self.my_menu,tearoff=False)
        self.my_menu.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="Browser", command=self.func_openbrowser)
        self.help_menu.add_separator()
        self.help_menu.add_command(label="About", command=self.func_aboutscreen)

        # NOTE: about the grid control method of laying out the controls......
        #    I think it is a quick way to layout the controls, but it spaces them uniformly across the width of the frame.
        #    So, you need to use tk.NW to align them left or tk.NE to align them to the right
        # Row = 0 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # ======================= add a drop down combo box of availabel Arduino serial ports
        self.scan_serial_ports()
        self.opt_serial_str = tk.StringVar()      
        self.opt_serial_str.set(self.availports[0])
        self.opt_serial = tk.OptionMenu(self, self.opt_serial_str, *self.availports, command=self.func_opt_serial)
        self.opt_serial.grid(row=0, column=0, padx=5, pady=2, sticky=tk.NW)
        self.opt_serial.config(font=normalfont)
        # ======================= add a label and text box to enter commands for the Arduino
        self.lbl_command = tk.Label(self, text='Enter command here', font=normalfont)
        self.lbl_command.config(width=19)
        self.lbl_command.grid(row=0, column=1, pady=7, sticky=tk.NE)
        self.txt_command_str = tk.StringVar()
        self.txt_command = tk.Entry(self, textvariable=self.txt_command_str,font=normalfont)
        self.txt_command.config(width=4)
        self.txt_command.grid(row=0, column=2, padx=5, pady=10, sticky=tk.NW)
        self.txt_command.bind("<Return>",self.func_txt_command)
        self.txt_command["state"] = "disable"
        # ======================= add a command submit button
        self.btn_submit = tk.Button(self, text="Submit command", command=self.func_btn_submit,font=normalfont)
        self.btn_submit.grid(row=0, column=3, padx=5, pady=5, sticky=tk.NW)
        self.btn_submit["state"] = "disable"

        # Row = 1 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
         # ======================= add a label to describe power status
        self.lbl_powerstatus = tk.Label(self, text=PowerStatus(), fg='green', font=boldfont)
        self.lbl_powerstatus.grid(row=1, column=0, pady=7, sticky=tk.NW)   
        # ======================= add check box to enable repeatative reading of the Arduino analog input
        self.chk_AnalogInCycle_str = tk.IntVar()
        self.chk_AnalogInCycle = tk.Checkbutton(self, text="Analog read mode", variable=self.chk_AnalogInCycle_str, onvalue=1, offvalue=0,command=self.func_chk_AnalogInCycle,font=normalfont)
        self.chk_AnalogInCycle.config(width=17)       
        self.chk_AnalogInCycle_str.set(1)
        self.chk_AnalogInCycle.grid(row=1, column=1, sticky=tk.NW)
        self.chk_AnalogInCycle.deselect()
        self.chk_AnalogInCycle["state"] = "disable"
        # ======================= add check box to enable flickering LED
        self.chk_LEDflicker_str = tk.IntVar()
        self.chk_LEDflicker = tk.Checkbutton(self, text="LED flicker mode", variable=self.chk_LEDflicker_str, onvalue=1, offvalue=0,command=self.func_chk_LEDflicker,font=normalfont)
        self.chk_LEDflicker.config(width=17) 
        self.chk_LEDflicker_str.set(1)
        self.chk_LEDflicker.grid(row=1, column=2, sticky=tk.NW)
        self.chk_LEDflicker.deselect()
        self.chk_LEDflicker["state"] = "disable"

        # Row = 2 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # ======================= add notify radio button and filename label
        self.rdo_Notify_str = tk.IntVar()
        self.rdo_Notify1 = tk.Radiobutton(self, text="No notification",font=normalfont, variable=self.rdo_Notify_str, value=1, command=self.func_rdo_Notify)
        self.rdo_Notify1.config(width=20)
        self.rdo_Notify1.grid(row=2, column=0, padx=10, sticky=tk.NW)
         # Row = 3 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        self.rdo_Notify2 = tk.Radiobutton(self, text="Notify on Submit",font=normalfont, variable=self.rdo_Notify_str, value=2, command=self.func_rdo_Notify)
        self.rdo_Notify2.config(width=20)        
        self.rdo_Notify2.grid(row=3, column=0, padx=10, sticky=tk.NW)
        # Row = 4 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        self.rdo_Notify3 = tk.Radiobutton(self, text="Notify on Threshold",font=normalfont, variable=self.rdo_Notify_str, value=3,  command=self.func_rdo_Notify)
        self.rdo_Notify3.config(width=20)       
        self.rdo_Notify3.grid(row=4, column=0, padx=10, sticky=tk.NW)
        self.rdo_Notify_str.set('1')
        # Row = 5 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        quote = "Hello, let's get started\r\n"
        # Add a multi-line text box with vertical scroll bar
        self.frm_name = tk.Frame(self, height=20, width=20)
        self.frm_name.grid(row=5, rowspan=5, column=0, columnspan=4, padx=10, pady=5, sticky=tk.NW)
        self.txt_name_multi = tk.Text(self.frm_name, height=25, width=109,font=normalfont)
        self.txt_name_multi.pack(expand=tk.YES, side=tk.LEFT, fill=tk.Y)
        self.txt_name_multi.yview(tk.END)
        self.sb_name = tk.Scrollbar(self.frm_name, command=self.txt_name_multi.yview, orient=tk.VERTICAL)
        self.txt_name_multi.configure(yscrollcommand=self.sb_name.set)
        self.sb_name.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_name_multi.insert(tk.END,quote)
        self.txt_name_multi.yview(tk.END)

    # Opens an About screen
    def func_aboutscreen(self):
        about = tk.Toplevel() 
        about.title('About')
        about.geometry('200x200')
        about.resizable(width=tk.FALSE, height=tk.FALSE)
        about.attributes("-toolwindow",1)
        about.focus_set()
        txt_name_about = tk.Text(about, height=20, width=70)
        aboutstuff = "Program name: Sarter Application" + "\r\n" + "Author: Bugs Bunny" + "\r\n" + "Revision: 0.01" + "\r\n" + "Date: 2/20/2021" \
            + "\r\n" + "\r\n" + "NOTE: This software is" + "\r\n" +" for fun purposes only"
        txt_name_about.insert(tk.END,aboutstuff)
        txt_name_about.pack(side=tk.LEFT, fill=tk.Y)

    # Opens a new browser window (This can also open a local .html file, e.g. documentation)
    def func_openbrowser(self):
        url="https://www.google.com"
        wb.open(url)

    # Open up a dialog box and get a filename
    def func_opendialog(self):
        global SaveFileName     # Note: "global" is only needed for modifying variable (not needed for reading only)
        self.filename = filedialog.askopenfilename(initialdir="/", title="Select a file", filetypes=( ("all files", "*.*"),("text files","*.txt"),("s-parameter files", "*.s2p"),("png files","*.png") ))
        SaveFileName = self.filename
        self.txt_name_multi.insert(tk.END,SaveFileName + "\r\n")
        self.txt_name_multi.yview(tk.END)

    # Show the contents of the text box
    def func_txt_command(self,event):
        pass

    # execute this code when you click the button.  It calls the matplotlib graph function
    def func_btn_submit(self):
        command = self.txt_command_str.get()
        SendCommand(command + '\r')         # Note: The Arduino firmware is expecting a CR as the final character!

    # display the select value from the drop down list box
    def func_opt_serial(self,event):
        global ComPortName     # Note: "global" is only needed for modifying variable (not needed for reading only)
        #data = self.opt_serial_str.get() + " {index=" + str(self.availports.index(self.opt_serial_str.get())) + "} \r\n"    
        ComPortName = self.get_com_port()
        if "COM" in ComPortName:
            self.btn_submit["state"] = "normal"
            self.txt_command["state"] = "normal"
            self.chk_AnalogInCycle["state"] = "normal"
            self.chk_LEDflicker["state"] = "normal"    
            OpenArduinoPort()         
        else:
            self.btn_submit["state"] = "disable"
            self.txt_command["state"] = "disable"
            self.chk_AnalogInCycle.deselect()
            self.chk_AnalogInCycle["state"] = "disable"
            self.chk_LEDflicker.deselect()
            self.chk_LEDflicker["state"] = "disable"
            CloseArduinoPort()

    # Show the contexts of the check box
    def func_chk_AnalogInCycle(self):
        # data = "AnalogInCycle Check box is " + str(self.chk_AnalogInCycle_str.get()) +  "\r\n"
        # self.txt_name_multi.insert(tk.END,data)
        # self.txt_name_multi.yview(tk.END)
        if self.chk_AnalogInCycle_str.get():
             SetAnalogRead()
        else:
             SetAnalogRead(False)

    def func_chk_LEDflicker(self):
        # data = "LEDflicker Check box is " + str(self.chk_LEDflicker_str.get()) +  "\r\n"
        # self.txt_name_multi.insert(tk.END,data)
        # self.txt_name_multi.yview(tk.END)
        if self.chk_LEDflicker_str.get():
             SetLEDflicker()
        else:
             SetLEDflicker(False)

    # Show which radio button was selected
    def func_rdo_Notify(self):
        selection = "You selected the option " + str(self.rdo_Notify_str.get()) + "\r\n"
        self.txt_name_multi.insert(tk.END,selection)
        self.txt_name_multi.yview(tk.END)

    # dummy command
    def dummycommand(self):
        pass

    # Routine to handle closing of the program window via the drop-down menu
    def quitprogram(self):
        CloseArduinoPort()
        if messagebox.askokcancel("Quit the program", "Are you sure you want to quit?"):
            self.destroy()

    # https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
    def scan_serial_ports(self):
        """ Lists serial port names
            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        self.availports.append("Select Arduino to use")
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(99)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        for port in ports:
            try:
                ser = serial.Serial(   # If you want higher Baud then 9600, you have to use this code (NOTE: it resets Arduino every time)
                    dsrdtr = False,
                    rtscts = False,
                    xonxoff = False,
                    port=port,
                    baudrate=115200,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=5)
                time.sleep(2)     # This is needed to wait for the Arduino to reset
                ser.flush
                ser.write(b'i\r')
                buffer = ser.read_until(expected=b'\r')
                deviceinfo = buffer.decode().split(",")
                deviceentry=""
                if len(deviceinfo) == 4:
                    manuf = deviceinfo[0].strip()
                    model = deviceinfo[1].strip()
                    sernum = deviceinfo[2].strip()
                    firmware = deviceinfo[3].strip()
                    deviceentry = port + "   (" + manuf + ", " + model + ", " + sernum + ", " + firmware + ")"
                    self.availports.append(deviceentry)
                ser.close()
            except (OSError, serial.SerialException):
                pass
        if len(self.availports) == 1:
            self.availports[0] = "No Arduino devices found"

    def get_com_port(self):
        result=""
        data = self.opt_serial_str.get()
        if "COM" in data:
            result = data[0:5]
        return result
#endregion

#region ~~~~~~~~~~  Miscellaneous functions  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Open the serial COM port that is associated with an Arduino
def OpenArduinoPort():
    global ArduinoPort     # Note: "global" is only needed for modifying variable (not needed for reading only)
    # If the Timer is running, stop it.
    try:
        my_gui.after_cancel(TimerAfterID)        
    except:
        pass

    # Open thee serial port and LEAVE OPEN !!
    # NOTE: The code below outlines the fact that the Arduino resets with DTR signal by design.
    # https://forum.arduino.cc/index.php?topic=96422.0
    # https://electronics.stackexchange.com/questions/24743/arduino-resetting-while-reconnecting-the-serial-terminal
    # https://electronics.stackexchange.com/questions/49373/how-to-keep-the-arduino-uno-up-on-serial-connections
    # https://rheingoldheavy.com/arduino-from-scratch-part-11-atmega328p-dtr-and-reset/
    try:
        ArduinoPort = serial.Serial(   # If you want higher Baud then 9600, you have to use this code (NOTE: it resets Arduino every time)
            dsrdtr = False,
            rtscts = False,
            xonxoff = False,
            port=ComPortName,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=5)
        time.sleep(2)     # This is needed to wait for the Arduino to reset
        ArduinoPort.flush
        ArduinoPort.write(b'i\r')
        buffer=''
        buffer = ArduinoPort.read_until(expected=b'\r')
        my_gui.txt_name_multi.insert(tk.END,buffer.decode() + "\r\n")
        my_gui.txt_name_multi.yview(tk.END)
    except:
        my_gui.txt_name_multi.insert(tk.END,"Error opening " + ComPortName + "\r\n")
        my_gui.txt_name_multi.yview(tk.END)

def CloseArduinoPort():
    global ArduinoPort     # Note: "global" is only needed for modifying variable (not needed for reading only)
    ErrorMessage = ""

    # If the Timer is running, stop it.
    try:
        my_gui.after_cancel(TimerAfterID)
    except:
        pass

    try:
        # Stop the Arduino from outputting data regularly
        ArduinoPort.flush   
        ArduinoPort.write(b'ae\r')
        buffer=''
        buffer = ArduinoPort.read_until(expected=b'\r')
        #print(buffer.decode())
        ErrorMessage = "Ended analog readings. Problems ending flickering.\r\n" 
        # Turn off the flicker LED
        ArduinoPort.flush
        ArduinoPort.write(b'lo\r')
        buffer=''
        buffer = ArduinoPort.read_until(expected=b'\r')
        #print(buffer.decode())
        ErrorMessage = "Ended analog readings, ended flickering. Problems closing port.\r\n"
        ArduinoPort.close()
        ErrorMessage = "Serial port closed.\r\n"
    except:
        my_gui.txt_name_multi.insert(tk.END,ErrorMessage)
        my_gui.txt_name_multi.yview(tk.END)
    return

# Send the command and output the result
def SendCommand(command):
    global ArduinoPort     # Note: "global" is only needed for modifying variable (not needed for reading only)
    if ArduinoPort.is_open:
        try:
            ArduinoPort.flush
            ArduinoPort.write(command.encode())
            buffer = ''
            buffer = ArduinoPort.read_until(expected=b'\r')
            my_gui.txt_name_multi.insert(tk.END,buffer.decode())
            my_gui.txt_name_multi.yview(tk.END)
        except:
            pass
        if (my_gui.rdo_Notify_str.get()==2):        # Only send the message of radio #2 is selected
            SendEmailMessage()   
    else:
        my_gui.chk_LEDflicker.deselect()

# Set the Arduino to flicker LED
def SetLEDflicker(FlickerOn = True):
    global ArduinoPort     # Note: "global" is only needed for modifying variable (not needed for reading only)
    if ArduinoPort.is_open:
        try:
            if FlickerOn:
                ArduinoPort.flush
                ArduinoPort.write(b'lf\r')
                buffer = ''
                buffer = ArduinoPort.read_until(expected=b'\r')
                #print(buffer.decode())
            else:
                ArduinoPort.flush
                ArduinoPort.write(b'lo\r')
                buffer = ''
                buffer = ArduinoPort.read_until(expected=b'\r')
                #print(buffer.decode())
        except:
            pass
    else:
        my_gui.chk_LEDflicker.deselect()

# Set the Arduino to read data every 1 second
def SetAnalogRead(Enable = True):
    global TimerAfterID     # Note: "global" is only needed for modifying variable (not needed for reading only)
    global ArduinoPort     # Note: "global" is only needed for modifying variable (not needed for reading only)
    if ArduinoPort.is_open:
        try:
            if Enable:
                ArduinoPort.flush   
                ArduinoPort.write(b'ab\r')
                # Start program
                # https://www.pythontutorial.net/tkinter/tkinter-after/
                TimerAfterID = my_gui.after(800,Timer1)
            else:
                # If the Timer is running, stop it.
                try:
                    my_gui.after_cancel(TimerAfterID)
                except:
                    pass
                # Stop the Arduino from outputting data regularly
                ArduinoPort.flush   
                ArduinoPort.write(b'ae\r')
                buffer = ''
                buffer = ArduinoPort.read_until(expected=b'\r')
                #print(buffer.decode())
        except:
            pass
    else:
        my_gui.chk_AnalogInCycle.deselect()

def GetEmailNotifyInfo():
    # First, let's read in the email information
    global SenderEmail     # Note: "global" is only needed for modifying variable (not needed for reading only)
    global Password        # Note: "global" is only needed for modifying variable (not needed for reading only)
    global NotifyEmail     # Note: "global" is only needed for modifying variable (not needed for reading only)
    try:
        f = open("importantinfo.txt", "r")     # Make sure there is a file of this name in the directory
        for x in f:
            SplitEntry = x.split("=")
            if (SplitEntry[0].lower().find("senderemail") >= 0 and len(SplitEntry)==2):
                SenderEmail = SplitEntry[1].strip()
            if (SplitEntry[0].lower().find("password") >= 0 and len(SplitEntry)==2):
                Password = SplitEntry[1].strip()
            if (SplitEntry[0].lower().find("notifyemail") >= 0 and len(SplitEntry)==2):
                NotifyEmail = SplitEntry[1].strip()
    except: 
        pass

def SendEmailMessage():
    if (SenderEmail != "" or Password != ""):
        smtp_server = "smtp.gmail.com"
        port = 587
        sender_email = SenderEmail
        password = Password
        receiver_email = NotifyEmail

        message = MIMEMultipart("alternative")
        message["Subject"] = "Test message"
        message["From"] = sender_email
        message["To"] = receiver_email
        # Write the plain text part
        text = """This is plain text.  Let's see how it looks"""
        # write the HTML part
        html = """\
            <html>
                <body>
                    <p>This is some HTMl text with a link <a href="http://www.github.com/tclupper"> and this is the link</a></p>
                    <p>Here is more text with <strong>Bold text</strong></p>
                </body>
            </html>
            """
        # convert both parts to MIMEText objects and add them to the MIMEMultipart message
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        message.attach(part1)
        message.attach(part2)

        # Create a secure SSL context
        context = ssl.create_default_context()

        # Try to log in to server and send email
        try:
            server = smtplib.SMTP(smtp_server,port)
            server.ehlo() # Can be omitted
            server.starttls(context=context) # Secure the connection
            server.ehlo() # Can be omitted
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        except Exception as e:
            # Print any error messages to stdout
            print(e)
        finally:
            server.quit() 

# +++++++++++++++++++++ Read analog data (and re-intialze Timer afterwards) ++++++++++++++++++++++++++++
def Timer1():
    global TimerAfterID    # This allows us to shut down Timer1 any time
    global ArduinoPort     # Note: "global" is only needed for modifying variable (not needed for reading only)
    buffer=''
    if ArduinoPort.is_open:     
        buffer = ArduinoPort.read_until(expected=b'\r')
        my_gui.txt_name_multi.insert(tk.END,buffer.decode() + " (" + str(TimerAfterID) + ")")
        my_gui.txt_name_multi.yview(tk.END) 
        TimerAfterID = my_gui.after(800,Timer1)
    else:
        my_gui.txt_name_multi.insert(tk.END,"Serial Port closed\r\n")
        my_gui.txt_name_multi.yview(tk.END)

def PowerStatus():
    # returns a tuple 
    battery = psutil.sensors_battery()
    if battery.power_plugged:
        textmessage = "Plugged in (" + str(battery.percent) + "% charged)"
    else:
        textmessage = "On battery power (" + battery.percent + "%) (timeleft=" + str(convertTime(battery.secsleft)) + ")"
    return textmessage

# function returning time in hh:mm:ss 
def convertTime(seconds): 
    minutes, seconds = divmod(seconds, 60) 
    hours, minutes = divmod(minutes, 60) 
    return "%d:%02d:%02d" % (hours, minutes, seconds) 

#endregion

#region ~~~~~~~~~~  Actual main code starts here  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Initialize the tkinter GUI object
my_gui = tkinterGUI()

# Retrieve the email notify info from the text file
# (You might have to rename the file importantinfo.example to importantinfo.txt and populate it)
GetEmailNotifyInfo()

# https://stackoverflow.com/questions/29158220/tkinter-understanding-mainloop
my_gui.mainloop()

#endregion