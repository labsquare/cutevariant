"""Plugin to show base changes chart based on the current query"""
# Standard imports
import itertools as it
from collections import Counter, defaultdict

# Qt imports
from PySide2.QtWidgets import QVBoxLayout
from PySide2.QtCore import Qt
from PySide2.QtGui import QPainter
from PySide2.QtCharts import QtCharts as charts

# Custom imports
from .plugin import QueryPluginWidget


class ChartQueryWidget(QueryPluginWidget):
    """Plugin to show charts based on the current query"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Charts"))

        self.view = charts.QChartView()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self.setLayout(layout)
        self._query = None
        self.is_query_changed = False

    def on_init_query(self):
        """Overrided from AbstractQueryWidget"""
        pass

    def on_change_query(self):
        """Build a QBarSeries which displays base changes for the current variants
        in the query

        .. note:: Called when the VQL query is updated.

        .. TODO:: not optimal, this is running many time when other queryWidget changed
            Iterate over ALL variants... can be slow. Do I need asynchrone?

        """
        # BarSet: List of cccurrences of 1 alternative base in all snps for 1 reference base
        # => 4 values for each 4 bases of reference
        # => 4 barsets

        # QBarSet *set0 = new QBarSet("Jane");
        # *set0 << 1 << 2 << 3 << 4 << 5 << 6;
        # QBarSeries *series = new QBarSeries();
        # series->append(set0);

        ## Data formatting
        # Raw variants:
        # {'id': 1, 'chr': 11, 'pos': 10000, 'ref': 'G', 'alt': 'T', 'childs': 1}
        # Build  dict like:
        # {'G': Counter({'T': 3, 'A': 1}), 'C': ...}
        data = defaultdict(Counter)
        for variant in self._query.items():
            data[variant["ref"]][variant["alt"]] += 1

        ## Create QBarSets
        references = ("A", "T", "G", "C")
        # alt bases as keys; barsets as values
        barsets = dict()

        # We iterate on data always in the same order (see references variable)
        # AA, AT, AG, AC, TA, ...
        max_value = 0
        for ref, alt in it.product(references, repeat=2):

            if alt not in barsets:
                # Init the barset for this alt base
                barset = charts.QBarSet(alt)
                barsets[alt] = barset
            else:
                barset = barsets[alt]

            # Get value and append it to the current barset
            # As it is a default dict with Counters; Missing bases have the value 0
            value = data[ref][alt]
            max_value = value if value > max_value else max_value
            # print("Append to %s, %s" % (alt, value))
            barset.append(value)

        ## Build Chart
        # Add barsets to QBarSeries
        bar_series = charts.QBarSeries()
        bar_series.append(tuple(barsets.values()))  # only takes list or tuple

        # Init chart, set title, turn on animations
        chart = charts.QChart()
        chart.addSeries(bar_series)
        chart.setTitle(self.tr("SNPs Base Changes"))
        chart.setAnimationOptions(charts.QChart.SeriesAnimations)

        # Add categories for x-axis
        axisX = charts.QBarCategoryAxis()
        axisX.append(references)
        chart.addAxis(axisX, Qt.AlignBottom)
        bar_series.attachAxis(axisX)

        # Add y-axis with the maximum value encountered
        axisY = charts.QValueAxis()
        axisY.setRange(0, max_value + 1)
        chart.addAxis(axisY, Qt.AlignLeft)
        bar_series.attachAxis(axisY)

        # Add legend
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

        # Add the chart to the view, turn on the antialiasing
        self.view.setChart(chart)
        self.view.setRenderHint(QPainter.Antialiasing)
