from views import *
from db import Base, engine

Base.metadata.create_all(engine)
