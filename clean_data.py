"""
Clean Data QGIS plugin.
"""
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
import os.path

from .modules.ui import CleanDataDialog

class CleanData:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dialog = None
        self.actions = []
        self.menu = 'Clean Data'

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon = QIcon(os.path.join(self.plugin_dir, 'icon.png'))
        action = QAction(icon, 'Clean Data', self.iface.mainWindow())
        action.triggered.connect(self.run)
        action.setEnabled(True)
        
        self.iface.addToolBarIcon(action)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        self.actions = []

    def run(self):
        """Run method that performs all the real work"""
        self.dialog = CleanDataDialog(self.iface)
        self.dialog.show()
