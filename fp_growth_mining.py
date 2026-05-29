import pandas as pd
import time
from db_helper import DatabaseHelper
from mlxtend.frequent_patterns import fpgrowth, association_rules

# 1. Kết nối và lấy dữ liệu sạch
db = DatabaseHelper()
print("--- Đang tải dữ liệu từ SQL Server... ---")
query = "SELECT BillNo, Itemname FROM CleanedTransactions WHERE Country = 'United Kingdom'"
df = db.fetch_data(query)

print("--- Đang chuyển đổi dữ liệu sang Ma trận Giao dịch... ---")
basket = (df.groupby(['BillNo', 'Itemname'])['Itemname']
          .count().unstack().reset_index().fillna(0)
          .set_index('BillNo'))

def encode_units(x):
    return 1 if x >= 1 else 0

basket_sets = basket.applymap(encode_units)

# 2. KHAI PHÁ BẰNG FP-GROWTH VÀ ĐO THỜI GIAN
print("--- Đang chạy thuật toán FP-Growth... ---")
start_time = time.time() # Bắt đầu bấm giờ

# Sử dụng fpgrowth thay vì apriori
frequent_itemsets = fpgrowth(basket_sets, min_support=0.03, use_colnames=True)

end_time = time.time() # Kết thúc bấm giờ
execution_time = end_time - start_time
print(f"--- THÀNH CÔNG: Thời gian chạy FP-Growth là {execution_time:.4f} giây ---")

# 3. Tạo các Luật kết hợp (Giữ nguyên logic sinh luật)
print("--- Đang tạo các Luật kết hợp (Association Rules)... ---")
rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1)
rules = rules.sort_values(['confidence', 'lift'], ascending=[False, False])

print("\n--- TOP 5 LUẬT KẾT HỢP TÌM ĐƯỢC ---")
print(rules[['antecedents', 'consequents', 'support', 'confidence', 'lift']].head())

# 4. Cập nhật lại kho tri thức
try:
    rules['antecedents'] = rules['antecedents'].apply(lambda x: ', '.join(list(x)))
    rules['consequents'] = rules['consequents'].apply(lambda x: ', '.join(list(x)))
    
    engine = db.get_engine()
    rules.to_sql('ProductRules', con=engine, if_exists='replace', index=False)
    print("--- Hoàn tất cập nhật tri thức vào CSDL! ---")
except Exception as e:
    print(f"Lỗi khi lưu luật: {e}")