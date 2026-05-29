import pandas as pd
from db_helper import DatabaseHelper
from sqlalchemy import types # Thêm thư viện này

# Khởi tạo kết nối
db = DatabaseHelper()
engine = db.get_engine()

print("--- Đang lấy dữ liệu thô từ SQL Server... ---")
df = db.fetch_data("SELECT * FROM Transactions")
total_raw = len(df)

print("--- Bắt đầu quy trình làm sạch dữ liệu... ---")

# 1. Xử lý giá trị thiếu (Missing values) [cite: 125]
df.dropna(subset=['Itemname'], inplace=True)

# 2. Loại bỏ nhiễu và dữ liệu mâu thuẫn (Quantity/Price <= 0) 
df = df[(df['Quantity'] > 0) & (df['Price'] > 0)]

# 3. Chống trùng lặp (Deduplication) [cite: 135]
df.drop_duplicates(inplace=True)

# 4. Làm sạch dữ liệu văn bản
df['Itemname'] = df['Itemname'].str.upper().str.strip()

# 5. MỞ RỘNG: Loại bỏ các mục không phải sản phẩm (Phí bưu điện, thủ công...)
# Giúp thuật toán gợi ý sản phẩm mua kèm chính xác hơn
non_products = ['POSTAGE', 'DOTCOM POSTAGE', 'ADJUST BAD DEBT', 'POST']
df = df[~df['Itemname'].isin(non_products)]

print(f"\n--- KẾT QUẢ LÀM SẠCH ---")
print(f"Số dòng ban đầu: {total_raw}")
print(f"Số dòng còn lại sau khi sạch: {len(df)}")

# Bước 6: Lưu dữ liệu sạch với KIỂU DỮ LIỆU CỐ ĐỊNH để hỗ trợ Index
print("\n--- Đang lưu vào bảng CleanedTransactions... ---")
try:
    # Thiết lập kiểu dữ liệu để tránh lỗi NVARCHAR(MAX)
    sql_types = {
        'BillNo': types.NVARCHAR(length=50),
        'Itemname': types.NVARCHAR(length=255),
        'Country': types.NVARCHAR(length=100)
    }
    
    df.to_sql('CleanedTransactions', 
              con=engine, 
              if_exists='replace', 
              index=False, 
              chunksize=1000,
              dtype=sql_types) # Sử dụng cấu hình kiểu dữ liệu
              
    print("--- HOÀN THÀNH LÀM SẠCH VÀ TỐI ƯU CƠ SỞ DỮ LIỆU! ---")
except Exception as e:
    print(f"Lỗi khi lưu dữ liệu: {e}")