from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import sqlite3

from .abstractquerywidget import AbstractQueryWidget
from cutevariant.core import sql, Query



class Node(object):
    def __init__(self,node_id, parent = None):
        self.parent = parent 
        self.childs = []
        self.set_node_id(node_id)



    def add_child(self, child ):
        child.parent = self
        self.childs.append(child)

    def child(self, row : int) : 
        return self.childs[row]

    def child_count(self):
        return len(self.childs)

    def fetch_count(self):
        return abs(self.right - self.left) / 2 

    def row(self):
        if self.parent:
            return self.parent.childs.index(self)
        return 0

    def __repr__(self):
        return self.name + " " + self.hpo


    def set_node_id(self, node_id = None):
        self.node_id = node_id 

        # Node vide ( QModelIndex root )
        if not node_id :
            return 

        req = Node.conn.execute(f"SELECT nodes.id as 'node_id', terms.id as 'term_id', nodes.left, nodes.right, nodes.depth, terms.name, terms.hpo FROM nodes, terms WHERE nodes.term_id = terms.id AND nodes.id = {node_id}")
        result = req.fetchone()

        self.node_id = result[0]
        self.term_id = result[1]
        self.left    = result[2]
        self.right   = result[3]
        self.depth   = result[4]
        self.name    = result[5]
        self.hpo     = result[6]


    def load_child(self):
        self.childs.clear()
        cursor = Node.conn.cursor()
        sql = f"SELECT nodes.id FROM nodes WHERE nodes.left > {self.left} AND nodes.right < {self.right} AND depth == {self.depth+1} ORDER BY (nodes.right - nodes.left) DESC"
        for record in cursor.execute(sql):
            child_node_id = record[0]
            self.add_child(Node(child_node_id))
        

    def has_children(self):

        # root node 
        if not self.node_id:
            return True 
        return abs(self.left - self.right) > 1



class HpoModel(QAbstractItemModel):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn 
        Node.conn = self.conn 
        self.root_node = Node(1)

    def columnCount(self, parent = QModelIndex()):
        return 2 

    def rowCount(self, parent = QModelIndex()):
        return self.node_from_index(parent).child_count() 

    def index(self,row,column, parent : QModelIndex()):

        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_node = self.node_from_index(parent)
        node = parent_node.child(row)

        if node:
            return self.createIndex(row, column,node)
        else:
            return QModelIndex()


    def parent(self, index : QModelIndex()):
        if not index.isValid():
            return QModelIndex()

        node = index.internalPointer()
        parent_node = node.parent

        if parent_node == self.root_node:
            return QModelIndex()

        return self.createIndex(parent_node.row(), 0, parent_node)


    def node_from_index(self,index = QModelIndex()):

        if index == QModelIndex():
            return self.root_node

        return index.internalPointer()

    def data(self, index, role):

        if not index.isValid():
            return None

        node = self.node_from_index(index)


        if role == Qt.DisplayRole:
            if index.column() == 0:
                return node.name

            if index.column() == 1:
                return node.hpo

        return None


    def hasChildren(self,parent : QModelIndex):
        node =  self.node_from_index(parent)
        return node.has_children()


    def canFetchMore(self,index: QModelIndex):
        if index == QModelIndex():
            return False 

        node = self.node_from_index(index)

        if node.has_children() and node.child_count() == 0:
            return True

        return False


    def fetchMore(self, parent : QModelIndex()):
        node = self.node_from_index(parent)
        count = node.fetch_count()

        self.beginInsertRows(parent,0, count)
        node.load_child()
        self.endInsertRows()

    def setRoot(self, node: Node):
        self.beginResetModel()

        if self.root_node == None:
            pass # delete root node ? 

        self.root_node = node
        self.root_node.load_child()
        self.endResetModel()



class HpoQueryWidget(AbstractQueryWidget):


    def __init__(self):
        super().__init__()
       
        self.setWindowTitle("HPO")
        
        conn =  sqlite3.connect("/home/schutz/Dev/hpo2sqlite/hpo.db")
        self.view = QTreeView()
        self.model = HpoModel(conn)
        self.model.setRoot(Node(1))
        self.view.setModel(self.model)

        v_layout = QVBoxLayout()
        v_layout.addWidget(self.view)
        v_layout.setContentsMargins(0,0,0,0)


        self.setLayout(v_layout)






    def setQuery(self, query: Query):
        """ Method override from AbstractQueryWidget"""
        pass

    def getQuery(self):
        """ Method override from AbstractQueryWidget"""
        return self.model.query

  