import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Đọc file dữ liệu thô ban đầu (Báo cáo tiến độ mục 1)
print("--- Đang đọc file dữ liệu gốc Assignment-1_Data.csv ---")
df_raw = pd.read_csv('Assignment-1_Data.csv', sep=';', low_memory=False)

# 2. Phân tích cấu trúc dữ liệu sơ bộ
print("\n================ KẾT QUẢ PHÂN TÍCH CẤU TRÚC ================")
print(f"Tổng số dòng dữ liệu thô: {df_raw.shape[0]}")
print(f"Tổng số thuộc tính (cột): {df_raw.shape[1]}")
print("\n--- Các cột dữ liệu và kiểu dữ liệu ban đầu ---")
print(df_raw.dtypes)

# 3. Ép kiểu nhanh cột Price phục vụ phân tích sơ bộ
if df_raw['Price'].dtype == 'object':
    df_raw['Price'] = df_raw['Price'].str.replace(',', '.').astype(float)

# 4. Thống kê số lượng thực thể duy nhất
total_bills = df_raw['BillNo'].nunique()
total_items = df_raw['Itemname'].nunique()
print("\n================ THỐNG KÊ ĐƠN VỊ DUY NHẤT ================")
print(f"Số lượng hóa đơn (BillNo) duy nhất: {total_bills}")
print(f"Số lượng tên sản phẩm (Itemname) duy nhất: {total_items}")

# 5. Thống kê Độ phổ biến của Top 10 sản phẩm xuất hiện nhiều nhất
print("\n================ TOP 10 SẢN PHẨM PHỔ BIẾN BAN ĐẦU ================")
top_10 = df_raw['Itemname'].value_counts().head(10)
print(top_10)

# 6. Tính toán phân phối độ dài giỏ hàng (Số sản phẩm có trong mỗi hóa đơn)
basket_sizes = df_raw.groupby('BillNo')['Itemname'].count()
print("\n================ THỐNG KÊ MÔ TẢ GIỎ HÀNG (BASKET SIZE) ================")
print(basket_sizes.describe())

# 7. Vẽ biểu đồ Histogram phân phối độ dài giỏ hàng theo đúng yêu cầu bài toán
print("\n--- Đang vẽ và xuất biểu đồ phân phối giỏ hàng... ---")
plt.figure(figsize=(10, 6))
# Giới hạn x ở mức 60 mặt hàng để tránh phân tán bởi các giỏ hàng mua sỉ quá lớn
sns.histplot(basket_sizes, bins=100, kde=True, color='darkviolet')
plt.title('Biểu đồ phân phối số lượng sản phẩm trong một giỏ hàng (Raw Data)', fontsize=14, fontweight='bold')
plt.xlabel('Số lượng mặt hàng trong một giỏ hàng (Basket Size)', fontsize=12)
plt.ylabel('Số lượng hóa đơn (Tần suất xuất hiện)', fontsize=12)
plt.xlim(0, 60) 
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Lưu ảnh biểu đồ trực tiếp vào thư mục dự án để chèn vào file Word báo cáo
plt.savefig('histogram_basket_size_raw.png', dpi=300)
print("--- THÀNH CÔNG: Đã lưu biểu đồ tại file 'histogram_basket_size_raw.png' ---")
plt.show()