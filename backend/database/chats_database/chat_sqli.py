from sqlalchemy import create_engine
from database.chats_database.chat_config import connect


sync_engine =  create_engine(
    url = connect(),
    echo = False,
    pool_size = 5,
    max_overflow=10,
)