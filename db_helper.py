import pyodbc
import pandas as pd
import urllib
from sqlalchemy import create_engine, event

class DatabaseHelper:
    def __init__(self):
        self.server = 'LUAN\\SQLEXPRESS'
        self.database = 'ProductRecommendationDB'
        self.driver = '{ODBC Driver 17 for SQL Server}' 
        self.conn_str = f'DRIVER={self.driver};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes;'
        
    def get_connection(self):
        return pyodbc.connect(self.conn_str)

    def get_engine(self):
        params = urllib.parse.quote_plus(self.conn_str)
        engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", fast_executemany=True)
        return engine

    def fetch_data(self, query):
        engine = self.get_engine()
        return pd.read_sql(query, engine)

    def execute_query(self, query):

        conn = self.get_connection()

        cursor = conn.cursor()

        cursor.execute(query)

        conn.commit()

        cursor.close()

        conn.close()
if __name__ == "__main__":
    db = DatabaseHelper()
    try:
        df = db.fetch_data("SELECT DISTINCT TOP 5 Country FROM Transactions")
        print("--- KẾT NỐI VÀ LẤY DỮ LIỆU THÀNH CÔNG ---")
        print(df)
    except Exception as e:
        print(f"Vẫn còn lỗi: {e}")