import sys
import glob
from datetime import timedelta

import tkinter as tk                                            # Used for the GUI
from tkinter.constants import N                                 # Used for the GUI
from tkinter.filedialog import asksaveasfilename                # Used for the GUI
from tkinter import messagebox                                  # Used for the GUI

import serial           # Used to communication to the Arduino (or other serial devices)
import time             # Used to pause operation for a few seconds (during serial device bootup)
import datetime         # Used to get a current time stamp

import psutil                       # Used to determine power status in laptops 
import webbrowser as wb             # Used to spawn a browser

import smtplib, ssl                                 # Used for email notification
from email.mime.text import MIMEText                # Used for email notification
from email.mime.multipart import MIMEMultipart      # Used for email notification
import configparser                                 # Used in parsing .ini file

from pathlib import Path                            # Used for specifying a generic path
import logging                                      # Used in logging
from logging import (                               # Used in logging
    FileHandler,
    Formatter,
    StreamHandler
)       

#region ~~~~~~~~~~  Global variables  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Looking for a better way to do this ...
smallfont = ('Helvetica','9','normal')
normalfont = ('Helvetica','10','normal')
boldfont = ('Helvetica','10','bold')
# There is probably a better way to track the status of these
analogread_notification_sent = False         # This is used to determine if the email notification was sent for analog read
pushbutton_notification_sent = False         # This is used to determine if the email notification was sent pushbutton state
EOL = '\r'      # Constant end of line character.  This must match with Arduino starter code.
#endregion

#region ~~~~~~~~~~  Code to including error report via logging ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Notes: 
#   CRITICAL (numeric value 50)     stderr
#   ERROR (numeric value 40)        stderr
#   WARNING (numeric value 30)      stderr
#   INFO (numeric value 20)         stdout
#   DEBUG (numeric value 10)        debug_output
#   NOTSET (numeric value 0)        debug_output
#
# Setup handlers for both displaying log records and writing them to file

# stderr will be called for WARNING level and above
stderr = StreamHandler(sys.stderr)
stderr.addFilter(lambda r: r.levelno >= logging.WARNING)
stderr.setFormatter(Formatter())
# NOTE:  you can call this by    logging.warning("This is a warning")

# stdout will be called for INFO level to just below WARNING
stdout = StreamHandler(sys.stdout)
stdout.addFilter(lambda r: logging.INFO <= r.levelno < logging.WARNING)
stdout.setFormatter(Formatter())
# NOTE:  you can call this by    logging.info("This is some information")

# Here, stdout will be called for DEBUG level to just below INFO
#  ONLY, if the logging.disable(logging.DEBUG) statement below IS commented out!
debug_output = StreamHandler(sys.stdout)
debug_output.addFilter(lambda r: logging.DEBUG <= r.levelno < logging.INFO)
# NOTE:  you can call this by (only when enabled)    logging.debug("This is some debug information")

# Configure logging
logging.basicConfig(
    format="%(asctime)s -- %(name)s/ -- %(levelname)s :: %(message)s",
    datefmt="%c",
    level=logging.DEBUG,  # if debugging level disabled above, effectively sets level to logging.INFO
    handlers=[stderr,stdout, debug_output]
)

#Comment out the below to ENABLE debug output  (uncomment to DISABLE)
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

        self.protocol("WM_DELETE_WINDOW", self.quit_program)    # Needed to provide a good exit stratagy

        # ================== Add a menu ======================================================================
        self.my_menu = tk.Menu(self)
        self.config(menu=self.my_menu)
        # Create menu items ---------------------------------------------------------------------
        self.file_menu = tk.Menu(self.my_menu,tearoff=False)
        self.my_menu.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Save As...", command=self.func_saveasdialog)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.quit_program)
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
        self.chk_analogread.deselect()
        self.chk_analogread.grid(row=1, column=1, sticky=tk.NW)
        self.chk_analogread["state"] = "disable"
        # ======================= add check box to enable flickering LED
        self.chk_flicker_str = tk.IntVar()
        self.chk_flicker = tk.Checkbutton(self, text="LED flicker mode", variable=self.chk_flicker_str, onvalue=1, offvalue=0,command=self.func_chk_flicker,font=normalfont)
        self.chk_flicker.config(width=17) 
        self.chk_flicker.deselect()
        self.chk_flicker.grid(row=1, column=2, sticky=tk.NW)
        self.chk_flicker["state"] = "disable"

        # Row = 2 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # ======================= add notify radio button and filename label
        self.rdo_notify_str = tk.IntVar()
        self.rdo_notify1 = tk.Radiobutton(self, text="No notification",font=normalfont, variable=self.rdo_notify_str, value=1, command=self.func_rdo_notify)
        self.rdo_notify1.grid(row=2, column=0, padx=20, sticky=tk.NW)
         # Row = 3 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        self.rdo_notify2 = tk.Radiobutton(self, text="Notify on Pushbutton",font=normalfont, variable=self.rdo_notify_str, value=2, command=self.func_rdo_notify)     
        self.rdo_notify2.grid(row=3, column=0, padx=20, sticky=tk.NW)
        # Row = 4 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        self.rdo_notify3 = tk.Radiobutton(self, text="Notify on Threshold",font=normalfont, variable=self.rdo_notify_str, value=3,  command=self.func_rdo_notify)     
        self.rdo_notify3.grid(row=4, column=0, padx=20, sticky=tk.NW)
        self.rdo_notify_str.set('1')        # Set the default radio button to be the first one
        # Row = 5 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        quote = "Hello, let's get started\n"
        # Add a multi-line text box with vertical scroll bar
        self.frm_output = tk.Frame(self, height=20, width=20)
        self.frm_output.grid(row=5, rowspan=5, column=0, columnspan=4, padx=10, pady=5, sticky=tk.NW)
        self.txt_output_multi = tk.Text(self.frm_output, height=25, width=109,font=normalfont)
        self.txt_output_multi.pack(expand=tk.YES, side=tk.LEFT, fill=tk.Y)
        self.txt_output_multi.yview(tk.END)
        self.sb_updown = tk.Scrollbar(self.frm_output, command=self.txt_output_multi.yview, orient=tk.VERTICAL)
        self.txt_output_multi.configure(yscrollcommand=self.sb_updown.set)
        self.sb_updown.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_output_multi.insert(tk.END,quote)
        self.txt_output_multi.yview(tk.END)

    # Opens an About screen
    def func_aboutscreen(self):
        about = tk.Toplevel() 
        about.title('About')
        about.geometry('200x200')
        about.resizable(width=tk.FALSE, height=tk.FALSE)
        about.attributes("-toolwindow",1)
        about.focus_set()
        txt_about = tk.Text(about, height=20, width=70, font=smallfont)
        aboutstuff = f"""
        Program name: Starter Application
        Author: Bugs Bunny
        Revision: 0.01
        Date: 2/26/2021
        
        NOTE: This software is for fun purposes only
        """.strip()
        txt_about.insert(tk.END,aboutstuff)
        txt_about.pack(side=tk.LEFT, fill=tk.Y)

    # Opens a new browser window (This can also open a local .html file, e.g. documentation)
    @staticmethod
    def func_openbrowser(url="https://nccde.org/1389/Route-9-Library-Innovation-Center"):
        wb.open(url)

    # Open up a dialog box and get a filename
    # Note, to get to the filename outside of class: my_gui.filename
    def func_saveasdialog(self):
        self.filename = asksaveasfilename(
            initialdir=(Path(getattr(self,"filename",None)).parent if getattr(self,"filename",None) else Path.home()), 
            title="Select a file", 
            filetypes=(
                # ("all files", "*.*"),
                ("text files","*.txt"),
                ("csv files","*.csv")
            )
        )
        self.output_text(f"Data will be logged to: {self.filename}")

        # Setup a logging file that can be called upon throught the program.
        # logging is better for a "continuous stream of data", whereas a traditional "file open" is better for one-time data dumps.
        self.log = logging.getLogger(str(id(self)))
        self.log.addHandler(logging.FileHandler(self.filename))
        self.log.setLevel(logging.INFO)
        self.log.propagate=False

    # Show the contents of the text box
    # Note, to get to the text box contents outside of class: my_gui.txt_command_str.get()
    def func_txt_command(self,event):
        pass

    # execute this code when you click the button.  It calls the matplotlib graph function
    def func_btn_submit(self):
        message = self.send_command(self.txt_command_str.get().strip())
        self.output_text(f"command: {self.txt_command_str.get().strip()}, output: {message}")

    # display the select value from the drop down list box
    def func_opt_serial(self,event):
        self.cancel_timer()      # Just in case one is running (i.e. you switch Ardunios mid-stream...)
        self.reset_arduinos()    # Just in case, stop all Arduinos from outputting analog data stream
        comport_key = self.get_com_port().strip()

        logging.debug(f"key={comport_key}")

        if comport_key in self.__open_ports__.keys():
            self.manuf, self.model, self.sernum, self.firmware, self.arduino_port = self.__open_ports__[comport_key]
            self.txt_command["state"] = "normal"
            self.btn_submit["state"] = "normal"
            self.chk_flicker["state"] = "normal"
            self.chk_analogread["state"] = "normal"
        else:
            self.txt_command["state"] = "disable"
            self.btn_submit["state"] = "disable"
            self.chk_analogread["state"] = "disable"
            self.chk_flicker["state"] = "disable"

    # Set the analog read mode
    def func_chk_analogread(self):
        if self.arduino_port.is_open:
            set_analogread(bool(self.chk_analogread_str.get()))
        else:
            self.chk_analogread.deselect()

    # Set the flicker mode
    def func_chk_flicker(self):
        if self.arduino_port.is_open:
            set_flicker(bool(self.chk_flicker_str.get()))
        else:
            self.chk_flicker.deselect()

    # Show which radio button was selected
    def func_rdo_notify(self):
        if self.rdo_notify_str.get() == 1:
            self.output_text(f"No notification selected")
        elif self.rdo_notify_str.get() == 2:
            self.output_text(f"Notifcation on pushbutton state on Arduino")
        elif self.rdo_notify_str.get() == 3:
            self.output_text(f"Notifcation on Analog read > 900 (reset < 100) value on Arduino")
        else:
            self.output_text(f"Error in radio button selection")

        logging.debug(f"smtp_server={smtp_server}, port={port}")
        logging.debug(f"sender_email={sender_email}, password={password}")
        logging.debug(f"receiver_email={receiver_email}")

    # Routine to handle closing of the program window via the drop-down menu
    def quit_program(self):
        self.cancel_timer()      # Just in case one is running (i.e. you switch Ardunios mid-stream...)
        self.reset_arduinos()
        # self.close_ports()     # You can include this if you want to close the ports when you exit
        if messagebox.askokcancel("Quit the program", "Are you sure you want to quit?"):
             self.destroy()

    def scan_serial_ports(self):
        """ Lists serial port names
            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        self.arduino_list.append("Select Arduino to use")        # This adds a default entry to the list
        # https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
        if sys.platform.startswith('win'):
            ports = [f"COM{i}" for i in range(1,30)]
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
                    timeout=5)    # Increase this is you feel you need more time
                time.sleep(2)     # This is needed to wait for the Arduino to reset
                ser.flush()
                ser.write(b'i\r')
                buffer = ser.read_until(expected=b'\r')
                device_info = buffer.decode().split(",")
                if len(device_info) == 4:
                    manuf, model, sernum, firmware = [_.strip() for _ in device_info]
                    device_entry = f"{port}  ({', '.join((manuf, model, sernum, firmware))})"
                    self.arduino_list.append(device_entry)
                    self.__open_ports__[port] = [manuf, model, sernum, firmware, ser]
            except (OSError, serial.SerialException):
                pass
        if len(self.arduino_list) == 1:
            self.arduino_list[0] = "No Arduino devices found"

    def get_com_port(self):
         data = self.opt_serial_str.get()
         if "COM" in data:
             return data[:5].strip()
         else:
             return ""

    # Send the command and output the result
    def send_command(self, command:str)->str:
        if self.arduino_port.is_open:
            try:
                self.arduino_port.flush()
                self.arduino_port.write(f"{command}{EOL}".encode())
                buffer = ''
                buffer = self.arduino_port.read_until(expected=b'\r')
                message = buffer.decode().strip()
            except:
                message = 'Send command failed'
        else:
            message = 'Arduino port not open'
        return message

    # This is only used when retrieving continuous data stream from Starter Arduino     
    def get_data(self)->str:
        try:
            buffer = ''
            buffer = self.arduino_port.read_until(expected=b'\r')
            message = buffer.decode().strip()
            self.arduino_port.flush()
        except:
            message = 'Receive stream failed'
        return message

    def cancel_timer(self):
         # If the Timer is running, stop it.
         try:
             self.after_cancel(self.timer_id)        
         except:
             logging.debug(f"Cancel {self.timer_id} failed")

    # This is used to reset the Arduinos to a semi-normal state (NOT REBOOT)
    def reset_arduinos(self):

        try:
            for key, values in self.__open_ports__.items():
                man, mod, ser, firm, port = values
                self.arduino_port = port
                message = self.send_command('r')
                self.chk_analogread.deselect()
                message = self.send_command('mo')
                self.chk_flicker.deselect()
                message = self.send_command('lo')
        except:
            logging.debug(f"Error resetting {key}")

    # Use this to close all the open serial ports
    def close_ports(self):
        try:
            for key, port in self.__open_ports__.items():
                if port.is_open:
                    port.close()
        except:
            logging.debug(f"Error closing {key}")

    # This is used to display the status of battery/AC power
    def power_status(self):
        # returns a tuple 
        battery = psutil.sensors_battery()
        if battery.power_plugged:
            return f"Plugged in ({battery.percent}% charged)"
        else:
            return f"On battery power ({battery.percent}%) (timeleft={timedelta(seconds=battery.secsleft)})"

    # This is used to send text to the multi-line text box      
    def output_text(self,textstring:str):
        self.txt_output_multi.insert(tk.END, f"{textstring}\n")
        self.txt_output_multi.yview(tk.END)

#endregion

#region ~~~~~~~~~~  Miscellaneous functions  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Here is a function that is called from an event within the gui class, but has the code outside the class
# In this case, we are setting the Arduino to flicker mode.
def set_flicker(FlickerOn:bool):
    if FlickerOn:
        message = my_gui.send_command('mf')
    else:
        message = my_gui.send_command('mo')

# Set the Arduino to read data every 1 second
def set_analogread(StartRead:bool):
    if StartRead:
        message = my_gui.send_command(f"o{int(read_interval):02d}")
        logging.debug(f"Starting analog stream: o{int(read_interval):02d}  {message}")
        message = my_gui.send_command('rb')
        # https://www.pythontutorial.net/tkinter/tkinter-after/
        my_gui.timer_id = my_gui.after(timer_interval,analogread_timer)
    else:
        my_gui.cancel_timer()
        # Stop the Arduino from outputting data regularly
        message = my_gui.send_command('r')

# This is the time rthat is called every interval period
def analogread_timer(): 
    global analogread_notification_sent
    global pushbutton_notification_sent 
    
    # Get the message from teh Arduino starter stream (every interval period) 
    data_stream = my_gui.get_data()
    
    # Parse out the analog read data and Pushbutton state
    analog_value, pushbutton_state = [_.strip() for _ in data_stream.split(",")]

    #  CLear the text box of ot gets to big (> than 1000 lines)
    num_lines = my_gui.txt_output_multi.get("1.0",tk.END).count('\n')
    if num_lines > 1000:
        my_gui.txt_output_multi.delete("1.0",tk.END)

    my_gui.output_text(f"analog value={analog_value}, pushbutton state={pushbutton_state}")

    # log the data to the log data file (if it is open)
    try:    
        if my_gui.filename != "":
             my_gui.log.info(f"{datetime.datetime.now()}, {my_gui.sernum}, {data_stream}")
    except:
        pass

    # Check if pushbutton state is 1, or pressed
    if (my_gui.rdo_notify_str.get() == 2 and int(pushbutton_state) == 1):
        if not analogread_notification_sent:
            subject = f"{my_gui.get_com_port()} pushed its button"
            send_email_notification(subject)
            analogread_notification_sent = True
            my_gui.output_text(f"Notification: {subject}")
    elif (my_gui.rdo_notify_str.get() == 2 and analogread_notification_sent):
        analogread_notification_sent = False
        my_gui.output_text(f"{my_gui.get_com_port()} button released")

    # Check if the analog read value is > 900
    if (my_gui.rdo_notify_str.get() == 3 and int(analog_value) > 900):
        if not pushbutton_notification_sent:
            subject = f"{my_gui.get_com_port()} analog > 900"
            send_email_notification(subject)
            pushbutton_notification_sent = True
            my_gui.output_text(f"Notification: {subject}")
    elif (my_gui.rdo_notify_str.get() == 3 and pushbutton_notification_sent and int(analog_value) < 100):
        pushbutton_notification_sent = False
        my_gui.output_text(f"{my_gui.get_com_port()} analog < 100")

    my_gui.timer_id = my_gui.after(timer_interval,analogread_timer)

# Send an email notification based on certain events
def send_email_notification(subject:str):

    if not all([smtp_server, port, sender_email, password, receiver_email]):
        logging.debug("Error sending email")
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
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

    config = configparser.ConfigParser(strict=True)
    config.read(Path("example.ini"))
    smtp_server = config["SMTPinfo"]["SMTPServer"]
    port = config.getint("SMTPinfo","SMTPPort")
    sender_email = config["EmailInfo"]["SenderEmail"]
    password = config["EmailInfo"]["Password"]
    receiver_email = config["EmailInfo"]["NotifyEmail"]
    read_interval = config["ProgramInfo"]["ReadInterval"]
    logging.debug(f"sender_email={sender_email}, receiver_email={receiver_email}")

    # Set the timer_interval to be just shy of the Arduino output interval (within 2 seconds of actaul time)
    if int(read_interval) > 60:
        read_interval = "60"
    elif int(read_interval) < 1:
        read_interval = "1"
    timer_interval = int(read_interval)*800
    if int(read_interval)*1000 - timer_interval > 2000:
        timer_interval = int(read_interval)*1000 - 2000
    logging.debug(f"read_interval={int(read_interval):02d} , timer_interval={str(timer_interval)}")

    # https://stackoverflow.com/questions/29158220/tkinter-understanding-mainloop
    my_gui.mainloop()

    logging.shutdown()

#endregion