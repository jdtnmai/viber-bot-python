import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create the SQLAlchemy engine
engine = create_engine(os.environ["DATABASE_URL_2"])

Session = sessionmaker(bind=engine)
