from db_helper import DatabaseHelper

class RecommendationService:
    def __init__(self):
        self.db = DatabaseHelper()

    def get_suggestions(self, product_name, limit=3):
        # Chuẩn hóa đầu vào: Viết hoa và xóa khoảng trắng thừa
        p_name = str(product_name).upper().strip()
        
        query = f"""
            SELECT TOP {limit} consequents, confidence, lift
            FROM ProductRules 
            WHERE UPPER(LTRIM(RTRIM(antecedents))) = '{p_name}'
            ORDER BY confidence DESC, lift DESC
        """
        try:
            df = self.db.fetch_data(query)
            if df.empty:
                return []
            
            return df.to_dict(orient='records')
        except Exception as e:
            print(f"Lỗi truy vấn luật kết hợp: {e}")
            return []

    def get_top_selling(self, limit=3):
        query = f"""
            SELECT TOP {limit} Itemname AS consequents, COUNT(*) as SalesCount
            FROM CleanedTransactions
            GROUP BY Itemname
            ORDER BY SalesCount DESC
        """
        try:
            df = self.db.fetch_data(query)
            # Thêm giả lập giá trị confidence cho sản phẩm bán chạy để không lỗi giao diện
            if not df.empty:
                df['confidence'] = 0.99  # Giả định độ tin cậy cực cao cho hàng hot
            return df.to_dict(orient='records')
        except Exception as e:
            print(f"Lỗi truy vấn sản phẩm bán chạy: {e}")
            return []