"""Plugin to show all characteristics of a selected variant

VariantInfoWidget is showed on the GUI, it uses VariantPopupMenu to display a
contextual menu about the variant which is selected.
VariantPopupMenu is also used in viewquerywidget for the same purpose.
"""
from logging import DEBUG

# Qt imports
from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtWebEngineWidgets import *

# Custom imports
from cutevariant.gui import FIcon, style
from cutevariant.core import sql, get_sql_connection
from cutevariant.gui.plugin import PluginWidget
from cutevariant import commons as cm

from cutevariant.gui.widgets import DictWidget


from cutevariant.gui.widgets.qjsonmodel import QJsonModel, QJsonTreeItem


class IGVWebView(QWebEngineView):

    TEMPLATE = """

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <meta name="description" content="">
    <meta name="author" content="">
    <link rel="shortcut icon" href="https://igv.org/web/img/favicon.ico">

    <!-- IGV JS-->
    <script type="application/javascript" src="https://cdn.jsdelivr.net/npm/igv@2.10.1/dist/igv.min.js"></script>

</head>

<body>

<div id="myDiv" style="height: auto">
</div>

<script type="text/javascript">

    document.addEventListener("DOMContentLoaded", function () {

        var div = document.getElementById("myDiv");

        igv.createBrowser(div, {
                    genome: "hg19",
                    queryParametersSupported: true,
                    promisified: true,
                    locus: "8:128,750,948-128,751,025",

                    tracks: 
                    [

                    {
                            type: 'alignment',
                            format: 'cram',
                            url: 'https://s3.amazonaws.com/1000genomes/phase3/data/HG00096/exome_alignment/HG00096.mapped.ILLUMINA.bwa.GBR.exome.20120522.bam.cram',
                            indexURL: 'https://s3.amazonaws.com/1000genomes/phase3/data/HG00096/exome_alignment/HG00096.mapped.ILLUMINA.bwa.GBR.exome.20120522.bam.cram.crai',
                            name: 'HG00096',
                    }
                    ]

                })
                .then(function (browser) {
                    console.log("Browser ready");
                })


    })


</script>

</body>

</html>

    """

    def __init__(self):

        super().__init__()

        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
        )

        self.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)

        self.loadFinished.connect(self.create_stage)

        with open("/tmp/test.html", "w") as file:
            file.write(self.TEMPLATE)

        self.load(QUrl.fromLocalFile("/tmp/test.html"))

    def create_stage(self):

        self.page().runJavaScript(
            """
            var igvDiv = document.getElementById("igv-div");
            var options =
            {
                genome: "hg38",
                locus: "chr8:127,736,588-127,739,371",
                tracks: [
                    {
                        "name": "HG00103",
                        "url": "https://s3.amazonaws.com/1000genomes/data/HG00103/alignment/HG00103.alt_bwamem_GRCh38DH.20150718.GBR.low_coverage.cram",
                        "indexURL": "https://s3.amazonaws.com/1000genomes/data/HG00103/alignment/HG00103.alt_bwamem_GRCh38DH.20150718.GBR.low_coverage.cram.crai",
                        "format": "cram"
                    }
                ]
            };

            igv.createBrowser(igvDiv, options)
                .then(function (browser) {
                    console.log("Created IGV browser");
                })
            """
        )


class IgvWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.view = IGVWebView()
        self.vlayout = QVBoxLayout()
        self.vlayout.addWidget(self.view)
        self.setLayout(self.vlayout)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    w = IGVWebView()
    w.show()

    app.exec_()
