import pandas as pd
from db_helper import DatabaseHelper
from mlxtend.frequent_patterns import apriori, association_rules

# 1. Kết nối và lấy dữ liệu sạch
db = DatabaseHelper()
print("--- Đang tải dữ liệu từ SQL Server... ---")
# Để đảm bảo tốc độ, ta có thể lọc theo quốc gia phổ biến nhất (ví dụ: United Kingdom)
query = "SELECT BillNo, Itemname FROM CleanedTransactions WHERE Country = 'United Kingdom'"
df = db.fetch_data(query)

print("--- Đang chuyển đổi dữ liệu sang dạng Ma trận Giao dịch... ---")
# Bước này biến mỗi BillNo thành một hàng, mỗi Itemname thành một cột (One-hot Encoding)
basket = (df.groupby(['BillNo', 'Itemname'])['Itemname']
          .count().unstack().reset_index().fillna(0)
          .set_index('BillNo'))

# Hàm chuẩn hóa: Nếu số lượng > 0 thì coi là 1 (có mua), ngược lại là 0
def encode_units(x):
    return 1 if x >= 1 else 0

basket_sets = basket.applymap(encode_units)

print("--- Đang chạy thuật toán Apriori (Tìm tập phổ biến)... ---")
# min_support=0.03 nghĩa là sản phẩm phải xuất hiện trong ít nhất 3% tổng số hóa đơn
frequent_itemsets = apriori(basket_sets, min_support=0.03, use_colnames=True)

print("--- Đang tạo các Luật kết hợp (Association Rules)... ---")
# metric="lift" > 1 cho thấy hai sản phẩm thực sự có liên quan đến nhau
rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1)

# Sắp xếp các luật theo độ tin cậy (Confidence) giảm dần
rules = rules.sort_values(['confidence', 'lift'], ascending=[False, False])

print("\n--- TOP 5 LUẬT KẾT HỢP TÌM ĐƯỢC ---")
print(rules[['antecedents', 'consequents', 'support', 'confidence', 'lift']].head())

# Bước 3: Lưu kết quả vào SQL Server để Thành viên B & C sử dụng
print("\n--- Đang lưu kết quả vào bảng ProductRules... ---")
try:
    # Chuyển đổi dữ liệu dạng set sang string để lưu được vào SQL
    rules['antecedents'] = rules['antecedents'].apply(lambda x: ', '.join(list(x)))
    rules['consequents'] = rules['consequents'].apply(lambda x: ', '.join(list(x)))
    
    engine = db.get_engine()
    rules.to_sql('ProductRules', con=engine, if_exists='replace', index=False)
    print("--- HOÀN THÀNH: Tri thức đã được lưu kho! ---")
except Exception as e:
    print(f"Lỗi khi lưu luật: {e}")