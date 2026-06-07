import os

import numpy as np
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from db_helper import DatabaseHelper

class RecommendationService:
    def __init__(self):
        self.db = DatabaseHelper()
        self.knn_model = None
        self._train_checkout_classifier() # Tự động huấn luyện mô hình khi Server bật

    def _train_checkout_classifier(self):
        """
        Huấn luyện mô hình K-NN Phân lớp (Classification) bằng Dữ liệu giả lập (Synthetic Data).
        Khắc phục tình trạng mất cân bằng dữ liệu (Chỉ có hóa đơn thành công trong CSDL gốc).
        """
        np.random.seed(42)
        # Lớp 1 (Thành công - Mua sắm hợp lý): Khách hàng chọn từ 8 đến 100 sản phẩm
        qty_success = np.random.randint(8, 100, 400)
        spent_success = qty_success * 4.0 + np.random.normal(0, 5, 400)
        y_success = np.ones(400)

        # Lớp 0 (Thất bại - Hủy giỏ): Khách hàng chọn lắt nhắt 1-4 món hoặc spam hơn 150 món
        qty_fail_small = np.random.randint(1, 5, 200)
        qty_fail_large = np.random.randint(150, 300, 100)
        qty_fail = np.concatenate([qty_fail_small, qty_fail_large])
        spent_fail = qty_fail * 4.0 + np.random.normal(0, 5, 300)
        y_fail = np.zeros(300)

        # Gộp dữ liệu thành Ma trận Đặc trưng (X) và Nhãn (y)
        X_train = np.vstack([
            np.column_stack([qty_success, spent_success]),
            np.column_stack([qty_fail, spent_fail])
        ])
        y_train = np.concatenate([y_success, y_fail])

        # Huấn luyện K-NN với K=15 để làm mịn đường biên và phần trăm xác suất
        self.knn_model = KNeighborsClassifier(n_neighbors=15)
        self.knn_model.fit(X_train, y_train)

    def get_suggestions(self, cart_items, limit=6):
        """
        GIẢI PHÁP HIỆU NĂNG CAO: Tối ưu hóa truy vấn bằng mệnh đề WHERE LIKE.
        Ép SQL Server lọc trước dữ liệu, giảm tải 99% cho RAM và vòng lặp Python.
        """
        if not cart_items:
            return []
            
        cart_set = set(str(item).upper().strip() for item in cart_items)

        # 1. TẠO BỘ LỌC ĐỘNG TỪ GIỎ HÀNG ĐỂ SQL SERVER LÀM VIỆC NẶNG
        conditions = []
        for item in cart_set:
            # Xử lý an toàn chuỗi có dấu nháy đơn (ví dụ: "Ba chỉ bò Mỹ")
            safe_item = item.replace("'", "''") 
            # Dùng N'...' để tìm kiếm chính xác chuỗi tiếng Việt Unicode
            conditions.append(f"antecedents LIKE N'%{safe_item}%'")
            
        where_clause = " OR ".join(conditions)
        
        # Chỉ kéo lên những luật liên quan đến món ăn trong giỏ hàng
        query = f"SELECT antecedents, consequents, confidence, lift FROM ProductRules WHERE {where_clause}"
        
        try:
            df = self.db.fetch_data(query)
            if df.empty:
                return []

            valid_suggestions = []
            
            # 2. XỬ LÝ CHÍNH XÁC TẬP CON (Lúc này df chỉ còn vài chục dòng, Python chạy chớp mắt)
            for _, row in df.iterrows():
                antecedent_items = set(str(item).upper().strip() for item in str(row['antecedents']).split(', '))
                
                # NẾU vế trái của luật là TẬP CON của giỏ hàng hiện tại
                if antecedent_items.issubset(cart_set):
                    consequent_items = [str(item).upper().strip() for item in str(row['consequents']).split(', ')]
                    
                    # Lọc bỏ những sản phẩm khách đã có sẵn trong giỏ
                    filtered_consequents = [item for item in consequent_items if item not in cart_set]
                    
                    for item in filtered_consequents:
                        valid_suggestions.append({
                            'consequents': item,
                            'confidence': float(row['confidence']),
                            'lift': float(row['lift'])
                        })
            
            if not valid_suggestions:
                return []
                
            # Sắp xếp danh sách gợi ý theo độ tin cậy và Lift giảm dần
            valid_suggestions = sorted(valid_suggestions, key=lambda x: (-x['confidence'], -x['lift']))
            
            # Lọc bỏ các món bị trùng lặp
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
            print(f"Lỗi truy vấn tập con từ CSDL: {e}")
            return []

    def get_top_selling(self, limit=3):
        """Hệ thống dự phòng (Fallback): Gợi ý sản phẩm phổ biến bán chạy nhất"""
        query = f"""
            SELECT TOP {limit} Itemname AS consequents, COUNT(*) as SalesCount
            FROM CleanedTransactions
            GROUP BY Itemname
            ORDER BY SalesCount DESC
        """
        try:
            df = self.db.fetch_data(query)
            if not df.empty:
                # Sản phẩm top 1 sẽ có độ tin cậy cao nhất (~95%), các sản phẩm sau giảm dần
                max_sales = df['SalesCount'].max()
                
                # Biến đổi thành List để tránh lỗi cảnh báo của Pandas
                confidence_scores = []
                for sales in df['SalesCount']:
                    # Tỷ lệ dao động từ 75% đến 95%
                    score = round((sales / max_sales) * 0.20 + 0.75, 2)
                    confidence_scores.append(score)
                    
                df['confidence'] = confidence_scores
                
            return df.to_dict(orient='records')
        except Exception as e:
            print(f"Lỗi truy vấn sản phẩm bán chạy: {e}")
            return []
    
    
    def classify_live_cart(self, cart_items):
        if not cart_items:
            return "Giỏ hàng trống"
            
        total_qty = len(cart_items) 
        global_avg_price = 4.0 
        total_spent = total_qty * global_avg_price
            
        try:
            # GIẢI PHÁP TỐI THƯỢNG: Chỉ SELECT các cột số để không bao giờ bị lỗi Font tiếng Việt
            query = "SELECT ClusterID, Centroid_Qty, Centroid_Spent FROM ClusterCentroids"
            df_centroids = self.db.fetch_data(query)
            
            if df_centroids.empty:
                return "Hệ thống chưa phân cụm nền"
                
            best_cluster_id = None
            min_distance = float('inf')
            
            # Tính toán khoảng cách
            for _, row in df_centroids.iterrows():
                dist = np.sqrt(
                    (total_qty - row['Centroid_Qty'])**2 + 
                    (total_spent - row['Centroid_Spent'])**2
                )
                
                if dist < min_distance:
                    min_distance = dist
                    best_cluster_id = int(row['ClusterID'])
                    
            # TỰ ĐỘNG GÁN TÊN TRONG PYTHON BẰNG CÁCH SẮP XẾP TÂM CỤM
            # Sắp xếp các cụm theo giá tiền từ thấp đến cao để đảm bảo luôn đúng tên
            df_sorted = df_centroids.sort_values(by='Centroid_Spent')
            
            # Tạo từ điển map ID với Tên cực chuẩn
            cluster_names_ordered = [
                "Mua sắm Tiết kiệm (Giỏ nhỏ)", 
                "Mua sắm Phổ thông (Tiêu chuẩn)", 
                "Mua sắm Số lượng lớn (Bán sỉ)"
            ]
            
            mapping_dict = {}
            for idx, (index, row) in enumerate(df_sorted.iterrows()):
                mapping_dict[int(row['ClusterID'])] = cluster_names_ordered[idx]
                
            # Trả về tên tiếng Việt chuẩn xác
            return mapping_dict.get(best_cluster_id, "Mua sắm Tiết kiệm (Giỏ nhỏ)")
            
        except Exception as e:
            print(f"Lỗi TÍNH KHOẢNG CÁCH PHÂN CỤM K-MEANS: {e}")
            return "Mua sắm Tiết kiệm (Giỏ nhỏ)"
    
    def predict_checkout_probability(self, cart_items):
        """
        Dự báo xác suất khách hàng sẽ nhấn nút Thanh Toán dựa trên mô hình K-NN.
        """
        if not cart_items:
            return 0.0
            
        total_qty = len(cart_items) 
        global_avg_price = 4.0 
        total_spent = total_qty * global_avg_price
        
        try:
            # Trích xuất xác suất thuộc Lớp 1 (Chốt đơn thành công)
            prob = self.knn_model.predict_proba([[total_qty, total_spent]])[0][1]
            return round(prob * 100, 1)
        except Exception as e:
            print(f"Lỗi dự báo K-NN: {e}")
            return 0.0