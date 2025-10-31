# main.py
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtSerialPort import QSerialPortInfo
from IPX import IPXSerialCommunicator
from IPX import IPXConfigurator

# Import the class from your generated UI file
from ui_main_test import Ui_MainWindow # Adjust import path if needed

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Create an instance of the UI class and set it up
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # --- 1. Connect Signals to Slots (Make buttons work) ---
        self.ui.Start_config_butto.clicked.connect(self.start_configuration)
        self.ui.get_uids_butto.clicked.connect(self.get_uids)
        
        # --- 2. Make the UI dynamic on startup ---
        self.populate_com_ports()

    # --- These are the "Slots" that your buttons will call ---

    def start_configuration(self):
        """Placeholder function for the 'Start Configuration' button."""
        com_port = self.ui.COMPort_selec.currentText()
        sensor_count_str = self.ui.NUM_Sensor.text()
        
        self.ui.Log_for_message.append("--- Starting Configuration ---")
        self.ui.Log_for_message.append(f"Selected Port: {com_port}")
        self.ui.Log_for_message.append(f"Expected Sensors: {sensor_count_str}")
        
        # Example of updating the progress bar
        self.ui.Configuration_progres.setValue(50)

    def get_uids(self):
        """Placeholder function for the 'Get UIDs' button."""
        self.ui.Log_for_message.append("\n--- Getting UIDs (Placeholder) ---")
        # In the future, this will talk to your IPXCommunicator
        
    # --- This is a helper function to populate UI elements ---
        
    def populate_com_ports(self):
        """Finds available COM ports and adds them to the combo box."""
        self.ui.COMPort_selec.clear() # Clear any existing items
        ports = QSerialPortInfo.availablePorts()
        if not ports:
            self.ui.COMPort_selec.addItem("No COM ports found")
        else:
            for port in ports:
                self.ui.COMPort_selec.addItem(port.portName())

# This is the standard boilerplate to run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())