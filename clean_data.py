from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
import os.path

from .clean_data_dialog import CleanDataDialog

class CleanDataPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dialog = None
        self.actions = []
        self.menu = 'Clean Data'
        self.toolbar = self.iface.addToolBar('Clean Data')
        self.toolbar.setObjectName('CleanData')

    def add_action(self, icon_path, text, callback):
        icon = QIcon(icon_path) if icon_path else QIcon()
        action = QAction(icon, text, self.iface.mainWindow())
        action.triggered.connect(callback)
        
        self.iface.addToolBarIcon(action)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.add_action(
            icon_path,
            text='Clean Data',
            callback=self.run
        )

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu('Clean Data', action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""
        if not self.dialog:
            self.dialog = CleanDataDialog(self.iface)
        self.dialog.show()
