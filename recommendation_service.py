import numpy as np
import pandas as pd
import os
from sklearn.neighbors import KNeighborsClassifier
from db_helper import DatabaseHelper

class RecommendationService:
    def __init__(self):
        self.db = DatabaseHelper()
        self.knn_model = None
        self._train_checkout_classifier()

    def _train_checkout_classifier(self):
        """Huấn luyện mô hình K-NN Phân lớp bằng Dữ liệu giả lập"""
        np.random.seed(42)
        qty_success = np.random.randint(8, 100, 400)
        spent_success = qty_success * 4.0 + np.random.normal(0, 5, 400)
        y_success = np.ones(400)

        qty_fail_small = np.random.randint(1, 5, 200)
        qty_fail_large = np.random.randint(150, 300, 100)
        qty_fail = np.concatenate([qty_fail_small, qty_fail_large])
        spent_fail = qty_fail * 4.0 + np.random.normal(0, 5, 300)
        y_fail = np.zeros(300)

        X_train = np.vstack([
            np.column_stack([qty_success, spent_success]),
            np.column_stack([qty_fail, spent_fail])
        ])
        y_train = np.concatenate([y_success, y_fail])

        self.knn_model = KNeighborsClassifier(n_neighbors=15)
        self.knn_model.fit(X_train, y_train)

    def get_suggestions(self, cart_items, limit=5):
        """
        GIẢI PHÁP TỐI ƯU: Đọc luật kết hợp từ file CSV (Cache) thay vì SQL Server.
        - Khắc phục 100% lỗi utf-8 codec can't decode của ODBC Driver.
        - Tăng tốc độ load giỏ hàng lên gấp nhiều lần.
        """
        if not cart_items:
            return []
            
        cart_set = set(str(item).upper().strip() for item in cart_items)

        try:
            # Kiểm tra xem file CSV luật kết hợp đã được tạo chưa
            if not os.path.exists('top_50_rules.csv'):
                return []
                
            # Đọc trực tiếp từ file CSV với chuẩn utf-8-sig
            df = pd.read_csv('top_50_rules.csv', encoding='utf-8-sig')
            
            if df.empty:
                return []

            valid_suggestions = []
            
            for _, row in df.iterrows():
                # Tách chuỗi luật từ CSV (Cột CSV in hoa chữ cái đầu)
                antecedents_str = str(row['Antecedents'])
                consequents_str = str(row['Consequents'])
                
                antecedent_items = set(str(item).upper().strip() for item in antecedents_str.split(', '))
                
                # ĐIỀU KIỆN: Nếu vế trái là TẬP CON của giỏ hàng
                if antecedent_items.issubset(cart_set):
                    consequent_items = [str(item).upper().strip() for item in consequents_str.split(', ')]
                    
                    # Lọc bỏ những mặt hàng khách đã có trong giỏ
                    filtered_consequents = [item for item in consequent_items if item not in cart_set]
                    
                    for item in filtered_consequents:
                        valid_suggestions.append({
                            'consequents': item,
                            'confidence': float(row['Confidence']),
                            'lift': float(row['Lift'])
                        })
            
            if not valid_suggestions:
                return []
                
            # Sắp xếp theo Confidence và Lift giảm dần
            valid_suggestions = sorted(valid_suggestions, key=lambda x: (-x['confidence'], -x['lift']))
            
            # Lọc trùng lặp
            seen = set()
            final_suggestions = []
            for s in valid_suggestions:
                if s['consequents'] not in seen:
                    seen.add(s['consequents'])
                    final_suggestions.append(s)
                if len(final_suggestions) == limit:
                    break
                    
            return final_suggestions
            
        except Exception as e:
            print(f"Lỗi đọc file CSV gợi ý: {e}")
            return []

    def get_top_selling(self, limit=3):
        """Hệ thống dự phòng: Gợi ý sản phẩm bán chạy nhất"""
        query = f"""
            SELECT TOP {limit} Itemname AS consequents, COUNT(*) as SalesCount
            FROM CleanedTransactions
            GROUP BY Itemname
            ORDER BY SalesCount DESC
        """
        try:
            df = self.db.fetch_data(query)
            if not df.empty:
                df['confidence'] = 0.99 
            return df.to_dict(orient='records')
        except Exception as e:
            print(f"Lỗi truy vấn sản phẩm bán chạy: {e}")
            return []
            
    def classify_live_cart(self, cart_items):
        """Phân cụm Giỏ hàng bằng K-Means (Dùng ID từ SQL để tránh lỗi Font)"""
        if not cart_items:
            return "Giỏ hàng trống"
            
        total_qty = len(cart_items) 
        global_avg_price = 4.0 
        total_spent = total_qty * global_avg_price
            
        try:
            query = "SELECT ClusterID, Centroid_Qty, Centroid_Spent FROM ClusterCentroids"
            df_centroids = self.db.fetch_data(query)
            
            if df_centroids.empty:
                return "Hệ thống chưa phân cụm nền"
                
            best_cluster_id = None
            min_distance = float('inf')
            
            for _, row in df_centroids.iterrows():
                dist = np.sqrt(
                    (total_qty - row['Centroid_Qty'])**2 + 
                    (total_spent - row['Centroid_Spent'])**2
                )
                
                if dist < min_distance:
                    min_distance = dist
                    best_cluster_id = int(row['ClusterID'])
                    
            df_sorted = df_centroids.sort_values(by='Centroid_Spent')
            cluster_names_ordered = [
                "Mua sắm Tiết kiệm (Giỏ nhỏ)", 
                "Mua sắm Phổ thông (Tiêu chuẩn)", 
                "Mua sắm Số lượng lớn (Bán sỉ)"
            ]
            
            mapping_dict = {}
            for idx, (index, row) in enumerate(df_sorted.iterrows()):
                mapping_dict[int(row['ClusterID'])] = cluster_names_ordered[idx]
                
            return mapping_dict.get(best_cluster_id, "Mua sắm Tiết kiệm (Giỏ nhỏ)")
            
        except Exception as e:
            print(f"Lỗi khoảng cách K-Means: {e}")
            return "Mua sắm Tiết kiệm (Giỏ nhỏ)"

    def predict_checkout_probability(self, cart_items):
        """Dự báo xác suất chốt đơn bằng K-NN"""
        if not cart_items:
            return 0.0
            
        total_qty = len(cart_items) 
        total_spent = total_qty * 4.0 
        
        try:
            prob = self.knn_model.predict_proba([[total_qty, total_spent]])[0][1]
            return round(prob * 100, 1)
        except Exception as e:
            print(f"Lỗi dự báo K-NN: {e}")
            return 0.0