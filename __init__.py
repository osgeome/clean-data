"""
Clean Data QGIS plugin for cleaning and transforming vector data.
"""

def classFactory(iface):
    """Load the plugin class.
    
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .clean_data import CleanData
    return CleanData(iface)
