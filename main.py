from views import *
from db import Base, engine

Base.metadata.create_all(engine)

from views import grant_admin


if __name__ == "__main__":
    username = input("Enter the username to grant admin rights: ")
    grant_admin(username)