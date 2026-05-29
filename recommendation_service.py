from db_helper import DatabaseHelper

class RecommendationService:
    def __init__(self):
        self.db = DatabaseHelper()

    def get_suggestions(self, cart_items, limit=5):
        """
        Gợi ý sản phẩm mua kèm dựa trên TOÀN BỘ giỏ hàng hiện tại.
        Đạt chuẩn yêu cầu kiểm tra tập con (Antecedent subset of Cart).
        """
        if not cart_items:
            return []
            
        # Chuẩn hóa toàn bộ sản phẩm trong giỏ thành chữ hoa và xóa khoảng trắng
        cart_set = set(str(item).upper().strip() for item in cart_items)

        # Lấy toàn bộ tập luật kết hợp từ bảng ProductRules lên bộ nhớ để duyệt set
        query = "SELECT antecedents, consequents, confidence, lift FROM ProductRules"
        try:
            df = self.db.fetch_data(query)
            if df.empty:
                return []

            valid_suggestions = []
            
            for _, row in df.iterrows():
                # Chuyển chuỗi vế trái (cách nhau bởi dấu phẩy) thành một Tập hợp (Set)
                antecedent_items = set(str(item).upper().strip() for item in row['antecedents'].split(', '))
                
                # ĐIỀU KIỆN QUAN TRỌNG: Nếu vế trái của luật là TẬP CON của giỏ hàng
                if antecedent_items.issubset(cart_set):
                    # Lấy danh sách sản phẩm gợi ý ở vế phải (consequents)
                    consequent_items = [str(item).upper().strip() for item in row['consequents'].split(', ')]
                    
                    # Lọc bỏ những sản phẩm mà người dùng đã có sẵn trong giỏ hàng
                    filtered_consequents = [item for item in consequent_items if item not in cart_set]
                    
                    for item in filtered_consequents:
                        valid_suggestions.append({
                            'consequents': item,
                            'confidence': float(row['confidence']),
                            'lift': float(row['lift'])
                        })
            
            if not valid_suggestions:
                return []
                
            # Sắp xếp danh sách gợi ý theo độ tin cậy (Confidence) và chỉ số Lift giảm dần
            valid_suggestions = sorted(valid_suggestions, key=lambda x: (-x['confidence'], -x['lift']))
            
            # Loại bỏ các mặt hàng trùng lặp trong danh sách kết quả gợi ý cuối cùng
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
            print(f"Lỗi phân tích tập con tại Service: {e}")
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
                df['confidence'] = 0.99  # Giả lập độ tin cậy cho hàng hot xu hướng
            return df.to_dict(orient='records')
        except Exception as e:
            print(f"Lỗi truy vấn sản phẩm bán chạy: {e}")
            return []