import sqlalchemy as db
from sqlalchemy_views import CreateView, DropView
from sqlalchemy.sql import text


engine = db.create_engine("sqlite:////tmp/test2.db", echo=True)

conn = engine.connect()

metadata = db.MetaData()


field = db.Table("field", metadata, autoload=True, autoload_with=engine)


view = db.Table("my_view", metadata)
create_view = CreateView(view, text("SELECT * FROM field"))

print(create_view.compile())
