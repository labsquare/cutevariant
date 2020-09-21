"""Summary
"""
from PySide2.QtCore import QUrl, QDir, Slot, QFile, QIODevice, QTime
from PySide2.QtWidgets import (
    QLabel,
    QProgressBar,
    QDialogButtonBox,
    QDialog,
    QApplication,
    QVBoxLayout,
)
from PySide2.QtGui import QFont
from PySide2.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
import sys


class DownloadDialog(QDialog):

    """Summary
        A dialog to download file and display progression 

    Attributes:
        source (QUrl): url of file to download
        destination (QDir): destination folder of downloaded file 
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.file_label = QLabel()
        self.progress = QProgressBar()
        self.info_label = QLabel()
        self.btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.net = QNetworkAccessManager()

        font = QFont()
        font.setBold(True)
        self.file_label.setFont(font)

        v_layout = QVBoxLayout()
        v_layout.addWidget(self.file_label)
        v_layout.addWidget(self.progress)
        v_layout.addWidget(self.info_label)
        v_layout.addStretch()
        v_layout.addWidget(self.btn_box)

        self.btn_box.accepted.connect(self.close)
        self.btn_box.rejected.connect(self.cancel)
        self.btn_box.button(QDialogButtonBox.Ok).setVisible(False)

        self.setLayout(v_layout)

        self.setFixedSize(450, 150)
        self.setWindowTitle(self.tr("Download file"))

    def set_source(self, url: QUrl):
        """Set file url to download 
        
        Args:
            url (QUrl)
        """
        self.source = url
        self.file_label.setText(self.source.fileName())

    def set_destination(self, directory: QDir):
        """Set folder path where download the file 
        
        Args:
            directory (QDir)
        """
        self.destination = directory

    def start(self):
        """ Start downloading the file specify by set_source 
        """
        filepath = self.destination.absoluteFilePath(self.source.fileName())

        if QFile(filepath).exists():
            QFile.remove(filepath)

        self._file = QFile(filepath)

        # open the file to write in
        if self._file.open(QIODevice.WriteOnly):
            print("open file", filepath)
            # Create a Qt Request
            request = QNetworkRequest()
            request.setUrl(self.source)
            self.time = QTime.currentTime()
            self.reply = self.net.get(request)

            # Connect reply to different slots
            self.reply.downloadProgress.connect(self.on_update_progress)
            self.reply.finished.connect(self.on_finished)
            self.reply.error.connect(self.on_error)

    def cancel(self):
        """Cancel download
        """
        if hasattr(self, "reply"):
            self.reply.abort()
            self._file.remove()
            self.close()

    @Slot(int, int)
    def on_update_progress(self, read, total):
        """This methods is called by self.reply.downloadProgress signal 
        
        Args:
            read (int): Number of bytes readed
            total (int): Total bytes to download
        """
        if read <= 0:
            return

        if self.reply.error() != QNetworkReply.NoError:
            return

        self._file.write(self.reply.readAll())

        # compute speed
        duration = self.time.secsTo(QTime.currentTime()) + 1
        speed = read / duration
        remaining = (total - read) / speed

        h_remaining = QTime(0, 0, 0, 0).addSecs(remaining).toString()
        h_total = self.human_readable_bytes(total)
        h_read = self.human_readable_bytes(read)
        h_speed = self.human_readable_bytes(speed) + "/sec"

        self.info_label.setText(
            f"Time remaining {h_remaining} - {h_read} of {h_total} ({h_speed})"
        )

        # Set progression
        self.progress.setRange(0, total)
        self.progress.setValue(read)

    @Slot()
    def on_finished(self):
        """This methods is called by self.reply.finished signal
        """
        if self.reply.error() == QNetworkReply.NoError:
            self._file.close()
            self.reply.deleteLater()
            self.btn_box.button(QDialogButtonBox.Ok).setVisible(True)

    @Slot(QNetworkReply.NetworkError)
    def on_error(self, err: QNetworkReply.NetworkError):
        """This method is called by self.reply.error signal
        
        Args:
            err (QNetworkReply.NetworkError)
        """
        self.reply.deleteLater()

    def human_readable_bytes(self, num, suffix="B"):
        for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, "Yi", suffix)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    dialog = DownloadDialog()
    dialog.set_source(
        QUrl("http://hgdownload.cse.ucsc.edu/goldenPath/hg19/bigZips/mrna.fa.gz")
    )
    dialog.set_destination(QDir("/tmp/"))
    dialog.start()
    dialog.show()

    app.exec_()
