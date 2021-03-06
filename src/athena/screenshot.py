import os
from contextlib import contextmanager
from pathlib import Path

from PySide2.QtGui import QImage, QImageWriter
from PySide2.QtWidgets import QDialog, QFileDialog
from PySide2.QtCore import QObject, QSize, Signal

from athena import mainwindow, ATHENA_DIR, viewer

@contextmanager
def SignalBlocker( *args ):
    '''
    Python context manager to block signals to any number of QObjects;
    
    '''
    original_signals = [ a.blockSignals(True) for a in args ]
    yield
    for a, s in zip( args, original_signals ):
        # restore original settings
        a.blockSignals(s)

class ScreenshotDialog(QDialog):

    default_ui_path = os.path.join( ATHENA_DIR, 'ui', 'ScreenshotDialog.ui' )

    def __init__( self, parent, view, ui_filepath=default_ui_path ):
        super().__init__(parent)
        mainwindow.UiLoader.populateUI( self, ui_filepath )
        self.view = view
        self.dpiBox.setValue( self.view.screen().physicalDotsPerInch() )

        # User may choose between inches and pixels
        self.unitsBox.currentIndexChanged.connect( self.widthBox.setCurrentIndex )
        self.unitsBox.currentIndexChanged.connect( self.heightBox.setCurrentIndex )

        # Automatically track changes to the size of the viewer window in the dimension boxes
        self.view.widthChanged.connect( self.setWidthPixels )
        self.view.heightChanged.connect( self.setHeightPixels )

        # User changes to spinners are reflected across units,
        # and if the proportionBox is checked, then width updates modify height
        # and vice-versa.
        self.widthBoxPixels.valueChanged.connect( self.changeWidthPixels )
        self.heightBoxPixels.valueChanged.connect( self.changeHeightPixels )
        self.widthBoxInches.valueChanged.connect( self.changeWidthInches )
        self.heightBoxInches.valueChanged.connect( self.changeHeightInches )
        self.dpiBox.valueChanged.connect( self.changeDpi )

        self.output_dir = str(Path.home())
        self.savetoLabel.setText( self.output_dir )
        self.dirChooserButton.clicked.connect( self.chooseOutputDir )

        self.buttonBox.accepted.connect( self.doSave )

        self.ratio = 1

    def _updateRatio( self ):
        self.ratio = self.widthBoxInches.value() / max(.00001,self.heightBoxInches.value())

    # "set*" functions are absolute and do not respect the proportionality setting
    def setWidthPixels(self, w):
        with SignalBlocker( self.widthBoxPixels, self.widthBoxInches ):
            self.widthBoxPixels.setValue(w)
            self.widthBoxInches.setValue( w / self.dpiBox.value() )
            self._updateRatio()

    def setHeightPixels(self, h):
        with SignalBlocker( self.heightBoxPixels, self.heightBoxInches ):
            self.heightBoxPixels.setValue(h)
            self.heightBoxInches.setValue( h / self.dpiBox.value() )
            self._updateRatio()

    def setSizePixels( self, w, h ):
        with SignalBlocker( self.widthBoxPixels, self.heightBoxPixels, 
                            self.widthBoxInches, self.heightBoxInches ):
            self.widthBoxPixels.setValue(w)
            self.heightBoxPixels.setValue(h)
            self.widthBoxInches.setValue( w / self.dpiBox.value() )
            self.heightBoxInches.setValue( h / self.dpiBox.value() )
            self._updateRatio()

    def setWidthInches(self, w):
        self.setWidthPixels( w * self.dpiBox.value() )

    def setHeightInches( self, h):
        self.setHeightPixels( h * self.dpiBox.value() )

    # "change*" functions respect the proportionality setting, if it's enabled
    def changeWidthPixels(self, w):
        ratio = self.ratio
        self.widthBoxInches.setValue( w / self.dpiBox.value() )
        if( self.proportionBox.isChecked() ):
            self.setHeightPixels( w / ratio )
        else:
            self._updateRatio()

    def changeHeightPixels(self, h):
        ratio = self.ratio
        self.heightBoxInches.setValue( h / self.dpiBox.value() )
        if( self.proportionBox.isChecked() ):
            self.setWidthPixels( h * ratio )
        else:
            self._updateRatio()

    def changeWidthInches(self, w):
        self.changeWidthPixels( w * self.dpiBox.value() )

    def changeHeightInches(self, h):
        self.changeHeightPixels( h * self.dpiBox.value() )

    def changeDpi(self, d):
        # Dpi changes always change the pixels values and keep the inch values as-is.
        self.setSizePixels( self.widthBoxInches.value() * d, self.heightBoxInches.value() * d)

    def chooseOutputDir( self ):
        self.output_dir = QFileDialog.getExistingDirectory( self, "Choose Screenshot Directory", self.output_dir,
                                                    QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks )
        self.savetoLabel.setText( self.output_dir )

    def doSave( self ):
        w = self.widthBoxPixels.value()
        h = self.heightBoxPixels.value()
        d = self.dpiBox.value()
        request = self.view.requestScreenshot( QSize(w, h), d )
        request.completed.connect( self.saveScreenshotCallback(request, d, self.output_dir) )

    def screenshotFilepath(self, output_path, capture_id ):
        dpath = Path(output_path)
        file_pattern = 'athena_img_{}.png'
        candidate_path = dpath / file_pattern.format( capture_id )
        idx = 1
        while candidate_path.exists() or candidate_path.is_symlink():
            candidate_path = dpath / file_pattern.format( str(capture_id) + '_' + str(idx) )
            idx += 1
        return candidate_path

    def saveScreenshotCallback(self, request, dpi, output_path):
        def doSaveScreenshot():
            iw = QImageWriter()
            iw.setFormat(str.encode('png'))
            gamma = self.view.framegraph.viewport.gamma()
            iw.setGamma( gamma )
            path = self.screenshotFilepath( output_path, request.captureId() )
            iw.setFileName( str(path) )
            img = request.image()
            in_per_meter = 39.37007874
            dpm = dpi * in_per_meter        # You're adorable, Qt
            img.setDotsPerMeterX( dpm )
            img.setDotsPerMeterY( dpm )
            iw.write(img)
            self.screenshotSaved.emit(path)
        return doSaveScreenshot

    screenshotSaved = Signal(Path)
