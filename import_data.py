import pandas as pd
from sqlalchemy import create_engine, event
import urllib
import time

# 1. Cấu hình kết nối - SỬ DỤNG Driver 17 để tránh lỗi Precision
server = 'LUAN\\SQLEXPRESS' # Lưu ý dùng 2 dấu gạch chéo \\
database = 'ProductRecommendationDB'
driver = '{ODBC Driver 17 for SQL Server}'

params = urllib.parse.quote_plus(
    f'DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
)

# Thêm fast_executemany=True để nạp dữ liệu cực nhanh và tránh lỗi BindParameter
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", fast_executemany=True)

print("--- Đang đọc file CSV... ---")
df = pd.read_csv('Assignment-1_Data.csv', sep=';', low_memory=False)

print("--- Đang xử lý định dạng dữ liệu... ---")
# Làm sạch cột Price: đổi ',' thành '.'
df['Price'] = df['Price'].str.replace(',', '.').astype(float)

# Chuyển đổi Ngày tháng chuẩn
df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)

# Xử lý CustomerID: Vì có nhiều giá trị NULL, ta nên chuyển về kiểu số nguyên hoặc để nguyên
# Để tránh lỗi, ta lấp đầy CustomerID trống bằng 0 tạm thời (Thành viên A sẽ xử lý sau ở tuần 2)
df['CustomerID'] = df['CustomerID'].fillna(0)

print(f"--- Đang nạp {len(df)} dòng vào SQL Server... ---")
start_time = time.time()

try:
    # Nạp dữ liệu vào bảng Transactions
    # chunksize giúp quản lý bộ nhớ tốt hơn
    df.to_sql('Transactions', con=engine, if_exists='append', index=False, chunksize=1000)
    
    end_time = time.time()
    print(f"--- THÀNH CÔNG! ---")
    print(f"Thời gian: {round(end_time - start_time, 2)} giây")
except Exception as e:
    print(f"Lỗi khi nạp dữ liệu: {e}")