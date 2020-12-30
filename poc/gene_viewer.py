

from PySide2.QtWidgets import QApplication, QWidget, QAbstractScrollArea,QScroller, QSlider, QVBoxLayout
from PySide2.QtCore import QRect, QPoint, Qt, Slot
from PySide2.QtGui import QPainter, QPen, QBrush, QPaintEvent, QColor, QLinearGradient
import sys


        #GJB2 
        # self.name = "NM_004004"
        # self.chrom = "chr13"
        # self.strand = "+"
        # self.tx_start = 20761608
        # self.tx_end = 20767077

        # self.cds_start = 20763039
        # self.cds_end = 20763720

        # self.exon_starts = [ 20761608,20766921]
        # self.exon_ends = [20763742,20767077]
        # self.exon_count = len(self.exon_starts)

        # CFTR 
        # self.name = "NM_000492"
        # self.chrom = "chr7"
        # self.strand = "+"
        # self.tx_start = 117120078
        # self.tx_end = 117308718

        # self.cds_start = 117120148
        # self.cds_end = 117307162

        # self.exon_starts = [117120078,117144306,117149087,117170952,117174329,117175301,117176601,117180153,117182069,117188694,117199517,117227792,117230406,117231987,117234983,117242879,117243585,117246727,117250572,117251634,117254666,117267575,117282491,117292895,117304741,117305512,117306961]
        # self.exon_ends = [117120201,117144417,117149196,117171168,117174419,117175465,117176727,117180400,117182162,117188877,117199709,117227887,117230493,117232711,117235112,117242917,117243836,117246807,117250723,117251862,117254767,117267824,117282647,117292985,117304914,117305618,117308718]
        # self.exon_count = len(self.exon_starts)






class GeneWidget(QAbstractScrollArea):
    """docstring for ClassName"""
    def __init__(self, parent = None):
        super().__init__(parent)

         
        self.name = "NM_000492"
        self.chrom = "chr7"
        self.strand = "+"
        self.tx_start = 117120078
        self.tx_end = 117308718

        self.cds_start = 117120148
        self.cds_end = 117307162

        self.exon_starts = [117120078,117144306,117149087,117170952,117174329,117175301,117176601,117180153,117182069,117188694,117199517,117227792,117230406,117231987,117234983,117242879,117243585,117246727,117250572,117251634,117254666,117267575,117282491,117292895,117304741,117305512,117306961]
        self.exon_ends = [117120201,117144417,117149196,117171168,117174419,117175465,117176727,117180400,117182162,117188877,117199709,117227887,117230493,117232711,117235112,117242917,117243836,117246807,117250723,117251862,117254767,117267824,117282647,117292985,117304914,117305618,117308718]
        self.exon_count = len(self.exon_starts)
        self._margin = 10

        # style 
        self.exon_height = 30
        self.intron_height = 20

        #self.showMaximized()

        self._area = None

        self.scale_factor = 1
        self.translation = 0 

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.horizontalScrollBar().setRange(0,0)

        #QScroller.grabGesture(self, QScroller.LeftMouseButtonGesture);

        self.horizontalScrollBar().valueChanged.connect(lambda x: print(x))

        self.resize(640, 200)




    def paintEvent(self, event : QPaintEvent):

        painter = QPainter()
        painter.begin(self.viewport())
        painter.setBrush(QBrush(QColor("white")))
        painter.drawRect(self.rect())

        # draw guide 
        area = self.draw_area()
        painter.drawRect(area.adjusted(-2,-2, 2,2))
        
        # draw rule
        painter.drawLine(area.left(), area.center().y(), area.right(), area.center().y())

        # Draw intron Background 
        intron_rect = QRect(area)
        intron_rect.setHeight(self.intron_height)
        intron_rect.moveCenter(QPoint(area.center().x(), area.center().y()))
        linearGrad = QLinearGradient(QPoint(0, intron_rect.top()), QPoint(0, intron_rect.bottom()))
        linearGrad.setColorAt(0, QColor("#FDFD97"))
        linearGrad.setColorAt(1, QColor("#FDFD97").darker())
        brush = QBrush(linearGrad)
        painter.setBrush(brush)
        painter.drawRect(intron_rect)

        # draw exons 
        for i in range(self.exon_count):

            start = self._dna_to_pixel(self.exon_starts[i] )
            end = self._dna_to_pixel(self.exon_ends[i] )

            # draw exons 
            exon_rect = QRect(0,0 , end - start, self.exon_height)
            exon_rect.moveTo(start + area.left(), area.center().y() - self.exon_height/2)

            painter.drawText(exon_rect, Qt.AlignCenter, str(i))

            linearGrad = QLinearGradient(QPoint(0, exon_rect.top()), QPoint(0, exon_rect.bottom()))
            linearGrad.setColorAt(0, QColor("#789FCC"))
            linearGrad.setColorAt(1, QColor("#789FCC").darker())
            brush = QBrush(linearGrad)
            painter.setBrush(brush)
            painter.drawRect(exon_rect)

        painter.end()

    def wheelEvent(self, event):

        if event.modifiers() != Qt.ControlModifier:
            return 

        if self.horizontalScrollBar().maximum() != 0:
            percent = self.horizontalScrollBar().value()  / self.horizontalScrollBar().maximum()
        else: 
            percent = 0.5

        angle = event.angleDelta().y()

        if angle > 0:
            self.scale_factor += 2

        else:
            if self.scale_factor > 1:
                self.scale_factor -= 2

       
        self.update_scale()
        new_value = percent * self.horizontalScrollBar().maximum()
        self.horizontalScrollBar().setValue(new_value )
        self.viewport().update()


    def update_scale(self):
        self.horizontalScrollBar().setRange(0, self.draw_area().width() * self.scale_factor - self.draw_area().width())
        self.horizontalScrollBar().setPageStep(self.draw_area().width())  
      

    def _pixel_to_dna(self, pixel: int):

        tx_size = self.tx_end - self.tx_start       
        scale = tx_size / (self.draw_area().width() * self.scale_factor) 
        return (pixel + self.horizontalScrollBar().value()) * scale + self.tx_start


    def _dna_to_pixel(self, dna: int):

        # normalize dna 
        dna = dna - self.tx_start
        tx_size = self.tx_end - self.tx_start       
        scale = (self.draw_area().width() * self.scale_factor) / tx_size
        return scale * dna  - self.horizontalScrollBar().value()

    @Slot(int)
    def set_factor(self, x):
        self.scale_factor = x
        self.update_scale()
        self.viewport().update()


    def draw_area(self):

        return self.viewport().rect().adjusted(10, 10, -10, -10)

    def mousePressEvent(self, event):
        
        pass


    def mouseDoubleClickEvent(self, event):

        print("event")
        if event.button() == Qt.RightButton:
            self.scale_factor = 1 
            self.update_scale()
            self.viewport().update()

        if event.button() == Qt.LeftButton:
            print(self.scale_factor)
            print(self.horizontalScrollBar().value())
            # start = self._dna_to_pixel(117170952)
            # end = self._dna_to_pixel(117171168)

            # diff = end-start

            self.scale_factor = 397 
            self.update_scale()
            self.horizontalScrollBar().setValue(77983)
            self.viewport().update()



if __name__ == '__main__':
    app = QApplication(sys.argv)

    w = QWidget()
    g = GeneWidget()
    s = QSlider(Qt.Horizontal)
    s.setRange(1, 100)
    l = QVBoxLayout()
    l.addWidget(g)
    l.addWidget(s)
    w.setLayout(l)

    s.valueChanged.connect(lambda x: g.set_factor(x))


    w.show()


    app.exec_()