import pandas as pd
import time
import matplotlib.pyplot as plt
import seaborn as sns
from db_helper import DatabaseHelper
from mlxtend.frequent_patterns import fpgrowth, association_rules

# 1. Kết nối và tải dữ liệu sạch từ bảng CleanedTransactions
db = DatabaseHelper()
print("--- Đang tải dữ liệu sạch từ bảng CleanedTransactions... ---")
query = "SELECT BillNo, Itemname FROM CleanedTransactions"
df = db.fetch_data(query)

print("--- Đang chuyển đổi dữ liệu sang Ma trận Giao dịch (Transaction Matrix)... ---")
basket = (df.groupby(['BillNo', 'Itemname'])['Itemname']
          .count().unstack().reset_index().fillna(0)
          .set_index('BillNo'))

def encode_units(x):
    return 1 if x >= 1 else 0

basket_sets = basket.applymap(encode_units)

# 2. KHAI PHÁ TẬP PHỔ BIẾN BẰNG FP-GROWTH VÀ ĐO THỜI GIAN
# Tối ưu hạ min_support xuống 0.015 (1.5%) để thu thập dải luật kết hợp phong phú hơn
min_sup_value = 0.015 
print(f"--- Đang chạy thuật toán FP-Growth với min_support = {min_sup_value}... ---")
start_time = time.time()

frequent_itemsets = fpgrowth(basket_sets, min_support=min_sup_value, use_colnames=True)

end_time = time.time()
execution_time = end_time - start_time
print(f"--- THÀNH CÔNG: Thời gian thực thi FP-Growth là {execution_time:.4f} giây ---")
print(f"✓ Số lượng tập phổ biến tìm thấy: {len(frequent_itemsets)}")

# 3. SINH LUẬT KẾT HỢP VÀ ĐÁNH GIÁ (ASSOCIATION RULES)
# Thiết lập min_confidence = 0.5 (50%) theo tiêu chuẩn bài toán
print("--- Đang tiến hành tạo các Luật kết hợp (Ngưỡng confidence >= 0.5)... ---")
rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.5)

# ĐẶC TẢ HUIT: Lọc các luật có tương quan dương thực sự (Lift > 1)
rules = rules[rules['lift'] > 1]

# Sắp xếp luật theo độ tin cậy và chỉ số Lift giảm dần
rules = rules.sort_values(['confidence', 'lift'], ascending=[False, False])
print(f"✓ Tổng số luật thỏa mãn tiêu chí đạt chuẩn (Lift > 1): {len(rules)}")

# 4. XUẤT BẢNG KẾT QUẢ TOP 50 LUẬT TỐT NHẤT RA FILE CSV
top_50_rules = rules.head(50).copy()
# Chuyển đổi định dạng frozenset sang chuỗi văn bản thông thường để lưu trữ dễ dàng
top_50_rules['antecedents_str'] = top_50_rules['antecedents'].apply(lambda x: ', '.join(list(x)))
top_50_rules['consequents_str'] = top_50_rules['consequents'].apply(lambda x: ', '.join(list(x)))

csv_output = top_50_rules[['antecedents_str', 'consequents_str', 'support', 'confidence', 'lift']]
csv_output.columns = ['Antecedents', 'Consequents', 'Support', 'Confidence', 'Lift']

# Xuất file CSV nộp kèm theo thư mục Source Code
csv_output.to_csv('top_50_rules.csv', index=False, encoding='utf-8-sig')
print("--- THÀNH CÔNG: Đã trích xuất danh sách và lưu tại file 'top_50_rules.csv' ---")

# 5. VẼ BIỂU ĐỒ PHÂN BỐ LUẬT KẾT HỢP (MỤC TIÊU CHẤM ĐIỂM 3)
print("--- Đang trực quan hóa đồ thị phân bố luật kết hợp... ---")
plt.figure(figsize=(10, 6))
# Vẽ biểu đồ phân tán giữa Support và Confidence, tô màu đậm nhạt dựa trên Lift
scatter = plt.scatter(rules['support'], rules['confidence'], c=rules['lift'], cmap='YlOrRd', alpha=0.8)
plt.colorbar(scatter, label='Chỉ số Lift (Mức độ cải thiện)')
plt.title('Biểu đồ phân bố Luật kết hợp (Support vs Confidence vs Lift)', fontsize=14, fontweight='bold')
plt.xlabel('Độ hỗ trợ (Support)', fontsize=12)
plt.ylabel('Độ tin cậy (Confidence)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.5)

# Lưu ảnh đồ thị phục vụ chèn trực tiếp vào báo cáo file Word
plt.savefig('association_rules_scatter.png', dpi=300)
print("--- THÀNH CÔNG: Đã lưu biểu đồ đồ thị tại file 'association_rules_scatter.png' ---")
plt.show()

# 6. CẬP NHẬT LẠI KHO TRI THỨC VÀO CƠ SỞ DỮ LIỆU SQL SERVER
try:
    rules_db = rules.copy()
    rules_db['antecedents'] = rules_db['antecedents'].apply(lambda x: ', '.join(list(x)))
    rules_db['consequents'] = rules_db['consequents'].apply(lambda x: ', '.join(list(x)))
    
    engine = db.get_engine()
    # Ghi đè lại bảng ProductRules để Backend và AJAX Frontend mới sử dụng tri thức chuẩn xác
    rules_db.to_sql('ProductRules', con=engine, if_exists='replace', index=False)
    print("--- HOÀN TẤT: Đã đồng bộ tri thức mới vào bảng ProductRules trong SQL Server! ---")
except Exception as e:
    print(f"Lỗi hệ thống khi lưu tri thức vào CSDL: {e}")