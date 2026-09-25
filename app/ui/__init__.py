try:
    from app.ui.windows.main_window import MainWindow
    __all__ = ["MainWindow"]
except ImportError:
    __all__ = []
