def classFactory(iface):
    from .clean_data import CleanDataPlugin
    return CleanDataPlugin(iface)
