from ctypes.wintypes import BOOLEAN     # Not sure who included this ...

import tkinter as tk                                            # Used for the GUI
from tkinter.filedialog import askopenfilename                  # Used for the GUI
from tkinter import messagebox                                  # Used for the GUI

import serial       # Used to communication to the Arduino (or other serial devices)
import time         # Used to pause operation for a few seconds (during serial device bootup)
import sys          # Used in finding available ports
import glob         # Used in finding available ports

import psutil                       # Used to determine power status in laptops 
from datetime import timedelta      # Used to format time variables
import webbrowser as wb             # Used to spawn a browser
import configparser                                 # Used in parsing

import smtplib, ssl                                 # Used for email notification
from email.mime.text import MIMEText                # Used for email notification
from email.mime.multipart import MIMEMultipart      # Used for email notification

from pathlib import Path                            # Used for specifying a generic path
import logging                                      # Used in logging
from logging import StreamHandler, Formatter        # Used in logging        

#region ~~~~~~~~~~  Global variables  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Looking for a better way to do this ...
normalfont = ('Helvetica','10','normal')
boldfont = ('Helvetica','10','bold')
EOL = '\r'      # Constant end of line character.  This must match with Arduino starter code.
#endregion

#region ~~~~~~~~~~  Code to including error report via logging ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
stdout = StreamHandler(sys.stdout)
stdout.addFilter(lambda r: logging.INFO <= r.levelno < logging.WARNING)
stdout.setFormatter(Formatter())  # Don't take the default format we set later

stderr = StreamHandler(sys.stderr)
stderr.addFilter(lambda r: r.levelno >= logging.WARNING)
stderr.setFormatter(Formatter())  # Don't take the default format we set later

debug_output = StreamHandler(sys.stdout)
debug_output.addFilter(lambda r: logging.debug <= r.levelno < logging.INFO)

# Configure logging
logging.basicConfig(
    format="%(asctime)s -- %(name)s/ -- %(levelname)s :: %(message)s",
    datefmt="%c",
    level=logging.DEBUG,  # if debugging level disabled above, effectively sets level to logging.INFO
    handlers=[stdout, stderr, debug_output],
)

# Comment out the below to enable debug output
#logging.disable(logging.DEBUG)

#endregion

#region ~~~~~~~~~~  tkinter GUI code as a Class  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class tkinterGUI(tk.Tk):
    # This allows to store all fo the available and Open Arduinos
    __open_ports__ = dict()

    def __init__(self):
        super().__init__(className="tkinterGUI")

        self.title('Starter Application')
        self.geometry('800x600')
        self.resizable(width=False, height=False)

        # You can find free icons here (I downloaded a 32px by 32px .png file): https://www.flaticon.com/
        # You can then convert them to an .ico image here (retain 32px by 32px size): https://icoconvert.com/
        # Put the path for the .ico file below
        try:
            self.iconbitmap(Path("./images/StarterPy.ico"))
        except:
            pass        # If the icon file is not there

        self.arduino_list = []      # A list of possible arduinos (used only in tkinterGUI class)
        self.timer_id = ''          # Not needed here, just a reminder this is a local variable 

        self.protocol("WM_DELETE_WINDOW", self.quit_program())     # Needed to provide a good exit stratagy

        # ================== Add a menu ======================================================================
        self.my_menu = tk.Menu(self)
        self.config(menu=self.my_menu)
        # Create menu items ---------------------------------------------------------------------
        self.file_menu = tk.Menu(self.my_menu,tearoff=False)
        self.my_menu.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Save As...", command=self.func_opendialog())
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.quit_program())
        # Create a help menu ---------------------------------------------------------------------
        self.help_menu = tk.Menu(self.my_menu,tearoff=False)
        self.my_menu.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="Browser", command=self.func_openbrowser())
        self.help_menu.add_separator()
        self.help_menu.add_command(label="About", command=self.func_aboutscreen())

        # NOTE: about the grid control method of laying out the controls......
        #    I think it is a quick way to layout the controls, but it spaces them uniformly across the width of the frame.
        #    So, you need to use tk.NW to align them left or tk.NE to align them to the right
        # Row = 0 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # ======================= add a drop down combo box of availabel Arduino serial ports
        self.scan_serial_ports()
        self.opt_serial_str = tk.StringVar()      
        self.opt_serial_str.set(self.arduino_list[0])
        self.opt_serial = tk.OptionMenu(self, self.opt_serial_str, *self.arduino_list, command=self.func_opt_serial)
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
        self.lbl_powerstatus = tk.Label(self, text=self.power_status(), fg='green', font=boldfont)
        self.lbl_powerstatus.grid(row=1, column=0, pady=7, sticky=tk.NW)   
        # ======================= add check box to enable repeatative reading of the Arduino analog input
        self.chk_analogread_str = tk.IntVar()
        self.chk_analogread = tk.Checkbutton(self, text="Analog read mode", variable=self.chk_analogread_str, onvalue=1, offvalue=0,command=self.func_chk_analogread,font=normalfont)
        self.chk_analogread.config(width=17)       
        self.chk_analogread_str.set(1)
        self.chk_analogread.grid(row=1, column=1, sticky=tk.NW)
        self.chk_analogread.deselect()
        self.chk_analogread["state"] = "disable"
        # ======================= add check box to enable flickering LED
        self.chk_flicker_str = tk.IntVar()
        self.chk_flicker = tk.Checkbutton(self, text="LED flicker mode", variable=self.chk_flicker_str, onvalue=1, offvalue=0,command=self.func_chk_flicker,font=normalfont)
        self.chk_flicker.config(width=17) 
        self.chk_flicker_str.set(1)
        self.chk_flicker.grid(row=1, column=2, sticky=tk.NW)
        self.chk_flicker.deselect()
        self.chk_flicker["state"] = "disable"

        # Row = 2 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # ======================= add notify radio button and filename label
        self.rdo_notify_str = tk.IntVar()
        self.rdo_notify1 = tk.Radiobutton(self, text="No notification",font=normalfont, variable=self.rdo_notify_str, value=1, command=self.func_rdo_notify)
        self.rdo_notify1.config(width=20)
        self.rdo_notify1.grid(row=2, column=0, padx=10, sticky=tk.NW)
         # Row = 3 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        self.rdo_notify2 = tk.Radiobutton(self, text="Notify on Submit",font=normalfont, variable=self.rdo_notify_str, value=2, command=self.func_rdo_notify)
        self.rdo_notify2.config(width=20)        
        self.rdo_notify2.grid(row=3, column=0, padx=10, sticky=tk.NW)
        # Row = 4 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        self.rdo_notify3 = tk.Radiobutton(self, text="Notify on Threshold",font=normalfont, variable=self.rdo_notify_str, value=3,  command=self.func_rdo_notify)
        self.rdo_notify3.config(width=20)       
        self.rdo_notify3.grid(row=4, column=0, padx=10, sticky=tk.NW)
        self.rdo_notify_str.set('1')        # Set the default radio button to be the first one
        # Row = 5 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        quote = "Hello, let's get started\n"
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
        aboutstuff = f"""
        Program name: Starter Application
        Author: Bugs Bunny
        Revision: 0.01
        Date: 2/23/2021
        
        NOTE: This software is for fun purposes only
        """.strip()
        txt_name_about.insert(tk.END,aboutstuff)
        txt_name_about.pack(side=tk.LEFT, fill=tk.Y)

    # Opens a new browser window (This can also open a local .html file, e.g. documentation)
    @staticmethod
    def func_openbrowser(url="https://www.google.com"):
        wb.open(url)

    # Open up a dialog box and get a filename
    # Note, to get to the filename outside of class: my_gui.filename
    def func_opendialog(self):
        self.filename = askopenfilename(
            initialdir=(Path(getattr("filename", self)).parent if getattr("filename",self) else Path.home()), 
            title="Select a file", 
            filetypes=(
                ("all files", "*.*"),
                ("text files","*.txt"),
                ("s-parameter files", "*.s2p"),
                ("png files","*.png")
            )
        )
        self.filename=""
        self.txt_name_multi.insert(tk.END, f"{self.filename}\n")
        self.txt_name_multi.yview(tk.END)

    # Show the contents of the text box
    # Note, to get to the text box contents outside of class: my_gui.txt_command_str.get()
    def func_txt_command(self,event):
        pass

    # execute this code when you click the button.  It calls the matplotlib graph function
    def func_btn_submit(self):
        message = self.send_command(self.txt_command_str.get())
        self.txt_name_multi.insert(tk.END, f"{message}\n")
        self.txt_name_multi.yview(tk.END)

    # display the select value from the drop down list box
    def func_opt_serial(self,event):
        self.cancel_timer()      # Just in case one is running (i.e. you switch Ardunios mid-stream...)
        self.reset_arduinos()    # Just in case, stop all Arduinos from outputting analog data stream
        comport_key = self.get_com_port()

        self.txt_name_multi.insert(tk.END,f"key={comport_key} \n")
        self.txt_name_multi.yview(tk.END)

        if comport_key in self.__open_ports__.keys():
            self.arduino_port = self.__open_ports__[comport_key]      # THIS IS THE MOST IMPORTANT STEP!!
            self.txt_command["state"] = "normal"
            self.btn_submit["state"] = "normal"
            self.chk_analogread["state"] = "normal"
            self.chk_flicker["state"] = "normal"
        else:
            self.txt_command["state"] = "disable"
            self.btn_submit["state"] = "disable"
            self.chk_analogread["state"] = "disable"
            self.chk_flicker["state"] = "disable"

    # Set the analog read mode
    def func_chk_analogread(self):
        set_analogread(self.arduino_port, bool(self.chk_analogread_str.get()))

    # Set the flicker mode
    def func_chk_flicker(self):
        set_flicker(self.arduino_port, bool(self.chk_flicker_str.get()))

    # Show which radio button was selected
    def func_rdo_notify(self):
        selection = f"You selected the option {self.rdo_name_str.get()}\n"
        self.txt_name_multi.insert(tk.END,selection)
        self.txt_name_multi.yview(tk.END)

    # dummy command
    def dummy_command(self):
        pass

    # Routine to handle closing of the program window via the drop-down menu
    def quit_program(self):
        self.cancel_timer()      # Just in case one is running (i.e. you switch Ardunios mid-stream...)
        self.reset_arduinos()
        self.close_ports()
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
        self.arduino_list.append("Select Arduino to use")        # This adds a default entry to the list
        if sys.platform.startswith('win'):
            ports = [f"COM{i}" for i in range(1,100)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        # Make a list and open availbale Arduino serial ports (and LEAVE THEM OPEN).
        # NOTE: The code below outlines the fact that the Arduino resets with DTR signal by design.
        # https://forum.arduino.cc/index.php?topic=96422.0
        # https://electronics.stackexchange.com/questions/24743/arduino-resetting-while-reconnecting-the-serial-terminal
        # https://electronics.stackexchange.com/questions/49373/how-to-keep-the-arduino-uno-up-on-serial-connections
        # https://rheingoldheavy.com/arduino-from-scratch-part-11-atmega328p-dtr-and-reset/

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
                ser.flush()
                ser.write(b'i\r')
                buffer = ser.read_until(expected=b'\r')
                device_info = buffer.decode().split(",")
                if len(device_info) == 4:
                    manuf, model, sernum, firmware = [_.strip() for _ in device_info]
                    device_entry = f"{port}  ({', '.join((manuf, model, sernum, firmware))})"
                    self.arduino_list.append(device_entry)
                self.__open_ports__[port] = ser
            except (OSError, serial.SerialException):
                pass
        if len(self.arduino_list) == 1:
            self.arduino_list[0] = "No Arduino devices found"

    def get_com_port(self):
        data = self.opt_serial_str.get()
        if "COM" in data:
            return data[:5]
        else:
            return ""

    def cancel_timer(self):
        # If the Timer is running, stop it.
        try:
            self.after_cancel(self.timer_id)        
        except:
            pass

    # Send the command and output the result
    def send_command(self, command:str)->str:
        if self.arduino_port.is_open:
            try:
                self.arduino_port.flush()
                self.arduino_port.write(f"{command}{EOL}".encode())
                buffer = ''
                buffer = self.arduino_port.read_until(expected=b'\r')
                message = buffer.decode().strip
            except:
                message = 'Send command failed'
        else:
            message = 'Arduino port not open'
        return message
        
    def reset_arduinos(self):
        for key, port in self.__open_ports__.items():
            self.arduino_port = port
            message = self.send_command('ae')

    def close_ports(self):
        for key, port in self.__open_ports__.items():
            port.close()

    def power_status(self):
        # returns a tuple 
        battery = psutil.sensors_battery()
        if battery.power_plugged:
            return f"Plugged in ({battery.percent}% charged)"
        else:
            return f"On battery power ({battery.percent}%) (timeleft={timedelta(seconds=battery.secsleft)})"

#endregion

#region ~~~~~~~~~~  Miscellaneous functions  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Set the Arduino to flicker LED
def set_flicker(arduino_port:serial.Serial, FlickerOn:bool = True):
    if arduino_port.is_open:
        try:
            if FlickerOn:
                message = my_gui.send_command('lf')
            else:
                message = my_gui.send_command('lo', arduino_port)
        except:
            pass
    else:
        my_gui.chk_flicker.deselect()

# Set the Arduino to read data every 1 second
def set_analogread(arduino_port:serial.Serial, Enable:bool = True):
    if arduino_port.is_open:
        try:
            if Enable:
                message = my_gui.send_command('ab', arduino_port)
                # https://www.pythontutorial.net/tkinter/tkinter-after/
                my_gui.timer_id = my_gui.after(800,analogread_timer(arduino_port))
            else:
                my_gui.cancel_timer()
                # Stop the Arduino from outputting data regularly
                message = my_gui.send_command('ae', arduino_port)
        except:
            pass
    else:
        my_gui.chk_AnalogInCycle.deselect()

# +++++++++++++++++++++ Read analog data (and re-intialze Timer afterwards) ++++++++++++++++++++++++++++
def analogread_timer(arduino_port):
    if arduino_port.is_open:     
        buffer = arduino_port.read_until(expected=b'\r')
        my_gui.txt_name_multi.insert(tk.END,buffer.decode() + " (" + str(my_gui.timer_id) + ")")
        my_gui.txt_name_multi.yview(tk.END) 
        my_gui.timer_id = my_gui.after(800,analogread_timer(arduino_port))
    else:
        my_gui.txt_name_multi.insert(tk.END,"Serial Port closed\r\n")
        my_gui.txt_name_multi.yview(tk.END)

def SendEmailMessage():
    config = configparser.ConfigParser(strict=True)
    config.read(list(Path.cwd().glob("*.ini")))

    smtp_server = config["SMTP Server"]["SMTPServer"]
    port = config.getint("SMTP Server","SMTPPort")
    sender_email = config["SMTP Credentials"]["SenderEmail"]
    password = config["SMTP Credentials"]["Password"]
    receiver_email = config["Message Settings"]["NotifyEmail"]

    if not all([smtp_server, port, sender_email, password, receiver_email]):
        return

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
        # Print any error messages to stderr via root logger
        logging.exception(str(e))
    finally:
        server.quit() 

#endregion

#region ~~~~~~~~~~  Actual main code starts here  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
if __name__ == "__main__":
    # Initialize the tkinter GUI object
    my_gui = tkinterGUI()

    # https://stackoverflow.com/questions/29158220/tkinter-understanding-mainloop
    my_gui.mainloop()

    logging.shutdown()

#endregion