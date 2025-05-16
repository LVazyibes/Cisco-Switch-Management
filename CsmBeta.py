from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QListWidget, QListWidgetItem, QDialog, QMessageBox
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt
from netmiko import ConnectHandler


class InterfaceConfigDialog(QDialog):
    def __init__(self, connection, interface, parent=None):
        super().__init__(parent)
        self.connection = connection
        self.interface = interface
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f"Interface Configuration: {self.interface}")
        self.setGeometry(100, 100, 500, 400)

        layout = QVBoxLayout()

        self.config_area = QTextEdit()
        self.config_area.setPlaceholderText("Interface konfigürasyon komutlarını girin...")
        layout.addWidget(self.config_area)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setPlaceholderText("Komut çıktıları burada gösterilecek...")
        layout.addWidget(self.console_output)

        self.apply_button = QPushButton("Uygula")
        self.apply_button.clicked.connect(self.apply_configuration)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def apply_configuration(self):
        commands = self.config_area.toPlainText().strip().split('\n')
        if commands:
            try:
                # Komutları uygula ve çıktıyı al
                output = self.connection.send_config_set([f"interface {self.interface}"] + commands)
                self.console_output.append(f"> Komutlar uygulandı:\n{output}")
                QMessageBox.information(self, "Başarılı", "Konfigürasyon başarıyla uygulandı!")
            except Exception as e:
                self.console_output.append(f"> Hata: {str(e)}")
                QMessageBox.critical(self, "Hata", f"Konfigürasyon uygulanırken hata oluştu: {str(e)}")
        else:
            QMessageBox.warning(self, "Uyarı", "Lütfen geçerli komutlar girin.")


class CiscoSwitchGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.saved_switches = {}

    def initUI(self):
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        middle_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        self.switch_list = QListWidget()
        self.switch_list.itemClicked.connect(self.load_selected_switch)
        left_layout.addWidget(QLabel('Kayıtlı Switchler'))
        left_layout.addWidget(self.switch_list)

        self.ip_label = QLabel('Switch IP:')
        self.ip_input = QLineEdit()
        right_layout.addWidget(self.ip_label)
        right_layout.addWidget(self.ip_input)

        self.user_label = QLabel('Kullanıcı Adı:')
        self.user_input = QLineEdit()
        right_layout.addWidget(self.user_label)
        right_layout.addWidget(self.user_input)

        self.pass_label = QLabel('Şifre:')
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        right_layout.addWidget(self.pass_label)
        right_layout.addWidget(self.pass_input)

        self.save_button = QPushButton('Kaydet')
        self.save_button.clicked.connect(self.save_switch)
        right_layout.addWidget(self.save_button)

        self.connect_button = QPushButton('Bağlan')
        self.connect_button.clicked.connect(self.connect_to_switch)
        right_layout.addWidget(self.connect_button)

        self.interface_list = QListWidget()
        self.interface_list.itemClicked.connect(self.show_interface_details)  # Tek tıklama
        self.interface_list.itemDoubleClicked.connect(self.open_interface_config)  # Çift tıklama
        middle_layout.addWidget(QLabel('Interface Listesi'))
        middle_layout.addWidget(self.interface_list)

        self.vlan_list = QListWidget()
        self.vlan_list.itemClicked.connect(self.show_vlan_ports)
        middle_layout.addWidget(QLabel('VLAN Listesi'))
        middle_layout.addWidget(self.vlan_list)

        self.interface_info = QTextEdit()
        self.interface_info.setReadOnly(True)
        middle_layout.addWidget(QLabel('Seçili Interface Bilgisi'))
        middle_layout.addWidget(self.interface_info)

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        right_layout.addWidget(self.output_area)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Komut girin ve Enter'a basın...")
        self.command_input.returnPressed.connect(self.execute_command)
        right_layout.addWidget(self.command_input)

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(middle_layout, 2)
        main_layout.addLayout(right_layout, 2)

        self.setLayout(main_layout)
        self.setWindowTitle('Cisco Switch Kontrol')
        self.resize(800, 400)

    def save_switch(self):
        ip = self.ip_input.text()
        username = self.user_input.text()
        password = self.pass_input.text()
        if ip and username and password:
            self.saved_switches[ip] = (username, password)
            self.switch_list.addItem(ip)

    def load_selected_switch(self, item):
        ip = item.text()
        if ip in self.saved_switches:
            username, password = self.saved_switches[ip]
            self.ip_input.setText(ip)
            self.user_input.setText(username)
            self.pass_input.setText(password)

    def connect_to_switch(self):
        self.ip = self.ip_input.text()
        self.username = self.user_input.text()
        self.password = self.pass_input.text()

        self.device = {
            'device_type': 'cisco_ios',
            'host': self.ip,
            'username': self.username,
            'password': self.password,
        }

        try:
            self.output_area.append(f'Bağlanıyor: {self.ip}...')
            self.connection = ConnectHandler(**self.device)
            self.output_area.append('Bağlantı başarılı!')
            self.load_interfaces()
            self.load_vlans()
        except Exception as e:
            self.output_area.append(f'Hata: {str(e)}')
            self.connection = None

    def load_interfaces(self):
        if self.connection:
            try:
                output = self.connection.send_command("show ip interface brief")
                self.interface_list.clear()
                for line in output.split('\n')[1:]:
                    columns = line.split()
                    if columns:
                        interface_name = columns[0]
                        status = columns[4]  # Port durumu (up/down/administratively down)
                        item = QListWidgetItem(interface_name)
                        self.set_interface_icon(item, status)
                        self.interface_list.addItem(item)
            except Exception as e:
                self.output_area.append(f'Hata: {str(e)}')

    def set_interface_icon(self, item, status):
        if status == "up":
            item.setIcon(QIcon("green_icon.png"))  # Yeşil ikon
        elif status == "down":
            item.setIcon(QIcon("red_icon.png"))  # Kırmızı ikon
        elif status == "administratively down":
            item.setIcon(QIcon("black_icon.png"))  # Siyah ikon

    def load_vlans(self):
        if self.connection:
            try:
                output = self.connection.send_command("show vlan brief")
                self.vlan_list.clear()
                for line in output.split('\n')[1:]:
                    columns = line.split()
                    if columns and columns[0].isdigit():
                        vlan_id = columns[0]
                        vlan_name = columns[1]
                        item = QListWidgetItem(f"VLAN {vlan_id}: {vlan_name}")
                        item.setData(1, vlan_id)  # VLAN ID'yi sakla
                        self.vlan_list.addItem(item)
            except Exception as e:
                self.output_area.append(f'Hata: {str(e)}')

    def open_interface_config(self, item):
        if self.connection:
            interface = item.text()
            dialog = InterfaceConfigDialog(self.connection, interface, self)
            dialog.exec_()

    def show_interface_details(self, item):
        if self.connection:
            interface = item.text()
            try:
                output = self.connection.send_command(f"show running-config interface {interface}")
                self.interface_info.setText(output)
            except Exception as e:
                self.interface_info.setText(f'Hata: {str(e)}')

    def show_vlan_ports(self, item):
        if self.connection:
            vlan_id = item.data(1)  # Saklanan VLAN ID'yi al
            try:
                output = self.connection.send_command(f"show vlan id {vlan_id}")
                self.interface_info.setText(output)
            except Exception as e:
                self.interface_info.setText(f'Hata: {str(e)}')

    def execute_command(self):
        if self.connection:
            command = self.command_input.text()
            try:
                output = self.connection.send_command(command)
                self.output_area.append(f'\n> {command}\n{output}')
            except Exception as e:
                self.output_area.append(f'Hata: {str(e)}')
            self.command_input.clear()
        else:
            self.output_area.append("Önce switch'e bağlanın!")


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = CiscoSwitchGUI()
    window.show()
    sys.exit(app.exec_())
