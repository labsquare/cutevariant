from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
from PySide2.QtGui import * 



class FIconEngine(QIconEngine):

    def __init__(self):
        super().__init__()
        self.setColor(qApp.palette().color(QPalette.Normal, QPalette.Text))

    def setCharacter(self, hex_character : int):
        self.hex_character = hex_character

    def setColor(self, color: QColor):
        self.color = color

    def paint(self, painter:QPainter, rect:QRect, mode:QIcon.Mode, state:QIcon.State):
        '''override''' 
        font = FIconEngine.font if hasattr(FIconEngine, 'font') else painter.font() 
        painter.save()

        if mode == QIcon.Disabled:
            painter.setPen(QPen(qApp.palette().color(QPalette.Disabled, QPalette.Text)))

        else:
            painter.setPen(QPen(self.color))
        
        font.setPixelSize(rect.size().width())

        painter.setFont(font)
        #painter.setRenderHint(QPainter.HighQualityAntialiasing, True)
        painter.drawText(rect, Qt.AlignCenter|Qt.AlignVCenter, str(chr(self.hex_character)))
        painter.restore()


    def pixmap(self,size,mode,state):
        pix = QPixmap(size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        self.paint(painter, QRect(QPoint(0,0),size), mode, state)
        return pix;

    @classmethod
    def setFontPath(cls, filename):
        db = QFontDatabase()
        font_id = db.addApplicationFont(filename)
        if font_id == -1:
            print("cannot load font icon")
            False

        cls.font = QFont(db.applicationFontFamilies(font_id)[0])


        return cls.font






class FIcon(QIcon):
    def __init__(self, hex_character : int, color = None):
        self.engine = FIconEngine()
        self.engine.setCharacter(hex_character)
        if color is not None:
            self.engine.setColor(color)
        super().__init__(self.engine)


    @classmethod
    def setFontPath(cls, filename):
        return FIconEngine.setFontPath(filename)

