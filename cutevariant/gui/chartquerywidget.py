"""Plugin to show base changes chart based on the current query"""
# Standard imports
import itertools as it
from collections import Counter, defaultdict
from copy import copy, deepcopy
from logging import DEBUG

# Qt imports
from PySide2.QtWidgets import QVBoxLayout
from PySide2.QtCore import Qt
from PySide2.QtGui import QPainter
from PySide2.QtCharts import QtCharts as charts

# Custom imports
from .plugin import QueryPluginWidget
from cutevariant.commons import logger, DEFAULT_SELECTION_NAME

LOGGER = logger()


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
        self.previous_filter = ""
        self.previous_selection = ""

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

        # print("cols", self.query.columns)
        # print("filter", self.query.filter)
        # print("groub_by", self.query.group_by)
        # print("selec", self.query.selection)

        # Do not redo the chart on if data is not changed...
        if (
            self.previous_filter == self.query.filter
            and self.previous_selection == self.query.selection
        ):
            LOGGER.debug(
                "ChartQueryWidget:on_change_query: Query filter didn't change => Do nothing!"
            )
            return

        self.previous_filter = self.query.filter
        self.previous_selection = self.query.selection

        # We don't want:
        # SELECT chr,pos,ref,alt,COUNT(variants.id) as 'children'
        # FROM variants
        # LEFT JOIN annotations ON annotations.variant_id = variants.id
        # WHERE ref IN ('A', 'T', 'G', C) AND alt IN ('A', 'T', 'G', C)
        # GROUP BY chr,pos,ref,alt

        # We just want:
        # SELECT re, alt, COUNT(*) FROM variants
        # WHERE ref IN ('A', 'T', 'G', C) AND alt IN ('A', 'T', 'G', C)
        # GROUP by ref, alt

        # AND we HAVE TO take care of current filters and selections;
        # so we will reset all fields except this ones; filter attribute
        # will be edited in place to add our new filters.

        query = copy(self.query)
        query.group_by = ("ref", "alt")
        query.order_by = None
        query.columns = ["ref", "alt", "COUNT(*)"]
        query.filter = deepcopy(self.query.filter)
        if query.selection == DEFAULT_SELECTION_NAME:
            # Explicitly query all variants
            query.selection = None
        # Example of filters:
        # filter: {'AND': [{'field': 'ref', 'operator': '=', 'value': 'G'},
        #                  {'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', C)"}]}
        # filter: {'AND': [{'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"},
        #                  {'field': 'alt', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"}]}
        # We want to add our filter in the top of filters:
        # - If there is no filters:
        # We add a new AND filter with our filters in its list.
        # - If AND operator is on TOP:
        # Just add our filters to the list of this operator.
        # - If OR operator is on TOP:
        # We have to encapsulate the whole tree of filter into a AND one;
        # so we add our filters to this new list just after the old OR filter.
        ATGC_filter = [
            {"field": "ref", "operator": "IN", "value": "('A', 'T', 'G', 'C')"},
            {"field": "alt", "operator": "IN", "value": "('A', 'T', 'G', 'C')"},
        ]

        # Avoid touching to original data since we don't do deepcopy (SQLite is not pickable)
        query.filter = deepcopy(query.filter)
        if not query.filter:
            # no filters: new AND filter
            query.filter["AND"] = ATGC_filter
        elif "AND" in query.filter:
            # AND operator on TOP: add our filters to it
            query.filter["AND"].extend(ATGC_filter)
        else:
            # OR operator on TOP: encapsulate the old filter into a AND one
            # and add our filters to this new list just after the old OR filter.
            query.filter = {"AND": [query.filter]}  # Old OR filter
            query.filter["AND"].extend(ATGC_filter)

        ## Data formatting
        # Raw variants:
        # {'ref': 'G', 'alt': 'T', 'COUNT(*)': 1}
        # Build  dict like:
        # {'G': Counter({'T': 3, 'A': 1}), 'C': ...}

        data = defaultdict(Counter)

        if LOGGER.getEffectiveLevel() == DEBUG:
            LOGGER.debug("ChartQueryWidget:on_change_query:: Custom query built:")
            import time

            start = time.time()

        # After the auto-parsing of filters by query.sql(), add manually:
        # - COUNT() function to columns
        # - GROUP BY command to query
        # We use RAW factory as tuples
        for ref, alt, value in query.conn.execute(
            query.sql(do_not_add_default_things=True)
        ):
            data[ref][alt] = value

        if LOGGER.getEffectiveLevel() == DEBUG:
            end_query = time.time()
            LOGGER.debug(
                "ChartQueryWidget:on_change_query:: number %s, query time %s",
                len(data),
                end_query - start,
            )

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
