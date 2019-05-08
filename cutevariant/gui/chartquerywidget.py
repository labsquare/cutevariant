"""Proof of concept: Plugin to show charts based on the current query"""
# Standard imports
from collections import Counter

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtCharts import QtCharts as charts

# Custom imports
from .plugin import QueryPluginWidget


class ChartQueryWidget(QueryPluginWidget):
    """Plugin to show charts based on the current query"""

    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle("Chart")

        self.view = charts.QChartView()

        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.view)

        self.setLayout(layout)
        self._query = None

    def on_query_changed(self):
        """Called when the VQL query is updated"""
        # TODO : not optimal, this is running many time when other queryWidget changed
        # Iterate over ALL variants ... ( can be slow.. Do I need asynchrone . )


        counter = Counter()
        # TODO Compute transition / transversion

        for i in self._query.items() :
            counter[i["chr"]] += 1


        series = charts.QPieSeries()
        series.append("sacha", 10)
        series.append("pierre",30)
        series.append("lucas",60)

        _slice = series.slices()[1]
        #_slice.setExploded()
        #_slice.setLabelVisible()

        chart = charts.QChart()
        chart.addSeries(series)
        chart.setTitle("Title")
        #chart.legend().hide()

        self.view.setChart(chart)
        self.view.setRenderHint(QPainter.Antialiasing)
