import pandas as pd
import time
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import seaborn as sns
from db_helper import DatabaseHelper
from mlxtend.frequent_patterns import fpgrowth, association_rules
from sqlalchemy import types  # <--- BỔ SUNG THƯ VIỆN ÉP KIỂU DỮ LIỆU CỦA SQL

def execute_mining(min_support_val=0.015, min_confidence_val=0.5):
    """
    Hàm thực thi thuật toán FP-Growth động.
    Đã tích hợp cơ chế bảo vệ mã hóa tiếng Việt (NVARCHAR) khi lưu vào CSDL.
    """
    db = DatabaseHelper()
    query = "SELECT BillNo, Itemname FROM CleanedTransactions"
    df = db.fetch_data(query)

    if df.empty:
        return {"error": "Cơ sở dữ liệu trống, không thể khai phá."}

    # Chuyển đổi sang Ma trận Giao dịch
    basket = (df.groupby(['BillNo', 'Itemname'])['Itemname']
              .count().unstack().reset_index().fillna(0)
              .set_index('BillNo'))

    def encode_units(x):
        return 1 if x >= 1 else 0

    basket_sets = basket.map(encode_units)
    basket_sets = basket_sets.astype(bool)

    # 1. Chạy thuật toán FP-Growth
    start_time = time.time()
    frequent_itemsets = fpgrowth(basket_sets, min_support=min_support_val, use_colnames=True)
    end_time = time.time()
    execution_time = end_time - start_time

    frequent_count = len(frequent_itemsets)

    # 2. Sinh luật kết hợp
    if frequent_count == 0:
        return {
            "execution_time": round(execution_time, 4),
            "frequent_count": 0,
            "rules_count": 0,
            "status": "Không tìm thấy tập phổ biến nào."
        }

    rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence_val)
    rules = rules[rules['lift'] > 1] 
    rules = rules.sort_values(['confidence', 'lift'], ascending=[False, False])
    rules_count = len(rules)

    # 3. Xuất file CSV
    if rules_count > 0:
        top_50_rules = rules.head(50).copy()
        top_50_rules['antecedents_str'] = top_50_rules['antecedents'].apply(lambda x: ', '.join(list(x)))
        top_50_rules['consequents_str'] = top_50_rules['consequents'].apply(lambda x: ', '.join(list(x)))
        csv_output = top_50_rules[['antecedents_str', 'consequents_str', 'support', 'confidence', 'lift']]
        csv_output.columns = ['Antecedents', 'Consequents', 'Support', 'Confidence', 'Lift']
        csv_output.to_csv('top_50_rules.csv', index=False, encoding='utf-8-sig')

        # 4. Vẽ đồ thị
        plt.figure(figsize=(10, 6))
        scatter = plt.scatter(rules['support'], rules['confidence'], c=rules['lift'], cmap='YlOrRd', alpha=0.8)
        plt.colorbar(scatter, label='Chỉ số Lift')
        plt.title('Biểu đồ phân bố Luật kết hợp', fontsize=14, fontweight='bold')
        plt.xlabel('Độ hỗ trợ (Support)')
        plt.ylabel('Độ tin cậy (Confidence)')
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.savefig('association_rules_scatter.png', dpi=300)
        plt.close() 

        # 5. Cập nhật SQL Server với chuẩn NVARCHAR (Bảo vệ tiếng Việt)
        try:
            rules_db = rules.copy()
            rules_db['antecedents'] = rules_db['antecedents'].apply(lambda x: ', '.join(list(x)))
            rules_db['consequents'] = rules_db['consequents'].apply(lambda x: ', '.join(list(x)))
            
            # ĐỊNH NGHĨA KIỂU NVARCHAR CHO CÁC CỘT CHỨA CHỮ
            sql_types = {
                'antecedents': types.NVARCHAR(length=500),
                'consequents': types.NVARCHAR(length=500)
            }
            
            engine = db.get_engine()
            # Bổ sung tham số dtype vào lệnh to_sql
            rules_db.to_sql('ProductRules', con=engine, if_exists='replace', index=False, dtype=sql_types)
        except Exception as e:
            print(f"Lỗi lưu CSDL ngầm: {e}")

    return {
        "execution_time": round(execution_time, 4),
        "frequent_count": frequent_count,
        "rules_count": rules_count,
        "status": "Khai phá dữ liệu và đồng bộ tri thức thành công!"
    }

if __name__ == '__main__':
    res = execute_mining(0.015, 0.5)
    print(res)