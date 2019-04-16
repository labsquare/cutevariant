from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtCharts import QtCharts as charts
from cutevariant.gui.ficon import FIcon


from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.core import sql
from collections import Counter



class ChartQueryWidget(QueryPluginWidget):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle("Chart")

        self.view = charts.QChartView()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.view)

        self.setLayout(layout)
        self._query = None

    @property
    def query(self):
        return self._query  # Useless , this widget is query read only

    @query.setter
    def query(self, query: Query):

        self._query = query

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
