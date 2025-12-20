from sqlalchemy import select,delete,update
from chats_models  import metadata_obj,chats_table
from chat_sqli import sync_engine


def create_table():
    metadata_obj.create_all(sync_engine)

def get_all_data():
    with sync_engine.connect() as conn:
        try:
            stmt = select(chats_table)
            res = conn.execute(stmt)
            return res.fetchall()
        except Exception as e:
            raise Exception(f"Error : {e}")      
print(get_all_data())