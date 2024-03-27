from app.data_models import Base
from create_postgre_session import engine


def create_tables(engine):
    Base.metadata.create_all(engine)


if __name__ == "__main__":

    create_tables(engine)
