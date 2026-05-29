import pandas as pd
from db_helper import DatabaseHelper
from sqlalchemy import types

# Khởi tạo kết nối CSDL
db = DatabaseHelper()
engine = db.get_engine()

print("--- Đang tải dữ liệu thô từ bảng Transactions... ---")
df = db.fetch_data("SELECT * FROM Transactions")
total_raw = len(df)
current_count = total_raw

print(f"Số lượng bản ghi thô ban đầu: {total_raw} dòng\n")
print("--- Bắt đầu quy trình làm sạch dữ liệu chi tiết ---")

# 1. Xử lý giá trị thiếu (Missing values) [cite: 125]
df.dropna(subset=['Itemname'], inplace=True)
dropped_missing = current_count - len(df)
current_count = len(df)
print(f"-> Bước 1: Loại bỏ {dropped_missing} dòng do khuyết thiếu tên sản phẩm (Itemname).")

# 2. Loại bỏ dữ liệu nhiễu (Quantity <= 0 hoặc Price <= 0)
df_valid_metrics = df[(df['Quantity'] > 0) & (df['Price'] > 0)]
dropped_noise = current_count - len(df_valid_metrics)
df = df_valid_metrics.copy()
current_count = len(df)
print(f"-> Bước 2: Loại bỏ {dropped_noise} dòng do Số lượng (Quantity) hoặc Đơn giá (Price) <= 0.")

# 3. Chuẩn hóa chuỗi văn bản (Loại khoảng trắng, viết hoa đồng nhất)
df['Itemname'] = df['Itemname'].astype(str).str.upper().str.strip()
print("-> Bước 3: Chuẩn hóa chuỗi văn bản (Viết hoa và xóa khoảng trắng đầu/cuối của Itemname).")

# 4. Loại bỏ các mã rác không phải sản phẩm giao dịch thực tế
non_products = ['POSTAGE', 'DOTCOM POSTAGE', 'ADJUST BAD DEBT', 'POST', 'MANUAL', 'BANK CHARGES', 'PADS']
df_filtered_products = df[~df['Itemname'].isin(non_products)]
dropped_non_products = current_count - len(df_filtered_products)
df = df_filtered_products.copy()
current_count = len(df)
print(f"-> Bước 4: Loại bỏ {dropped_non_products} dòng mã rác hệ thống (POSTAGE, MANUAL, BANK CHARGES...).")

# 5. Gom nhóm xử lý trùng lặp theo đúng đặc tả của giảng viên HUIT [cite: 135]
# Gom nhóm trùng BillNo và Itemname, cộng dồn Quantity và lấy Price trung bình
print("-> Bước 5: Đang tiến hành gom nhóm theo BillNo và Itemname để cộng dồn số lượng mặt hàng trùng...")
df = df.groupby(['BillNo', 'Itemname', 'Country', 'Date'], as_index=False).agg({
    'Quantity': 'sum',
    'Price': 'mean',
    'CustomerID': 'first'
})
dropped_duplicates = current_count - len(df)
print(f"   => Đã gộp và xử lý {dropped_duplicates} dòng trùng lặp trong cùng hóa đơn.")

print(f"\n================ KẾT QUẢ QUY TRÌNH LÀM SẠCH ================")
print(f"✓ Tổng số dòng dữ liệu thô ban đầu : {total_raw} dòng")
print(f"✓ Tổng số dòng dữ liệu sạch còn lại : {len(df)} dòng")
print(f"✓ Tỷ lệ giữ lại dữ liệu đạt chuẩn   : {round((len(df)/total_raw)*100, 2)}%")

# Bước 6: Lưu trữ dữ liệu sạch vào hệ quản trị SQL Server
print("\n--- Đang ghi dữ liệu sạch vào bảng CleanedTransactions... ---")
try:
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
              dtype=sql_types)
              
    print("--- HOÀN THÀNH LÀM SẠCH VÀ TỐI ƯU CƠ SỞ DỮ LIỆU THÀNH CÔNG! ---")
except Exception as e:
    print(f"Lỗi hệ thống khi lưu bảng dữ liệu sạch: {e}")