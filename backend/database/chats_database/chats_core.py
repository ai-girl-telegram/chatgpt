from sqlalchemy import select,deletem,update
from chats_models  import metadata_obj,chats_table
from chat_sqli import sync_engine


def create_table():
    metadata_obj.create_all(sync_engine)
    