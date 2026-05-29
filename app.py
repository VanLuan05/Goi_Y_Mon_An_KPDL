from flask import Flask, render_template, request, session, redirect, url_for
from db_helper import DatabaseHelper
from recommendation_service import RecommendationService

app = Flask(__name__)
app.secret_key = 'huit_datamining_project_2026'

db = DatabaseHelper()
rec_service = RecommendationService()

@app.route('/')
def index():
    try:
        # TỐI ƯU: Chỉ lấy những sản phẩm nào thực sự có luật gợi ý để demo luôn hiện Modal
        query_products = """
            SELECT DISTINCT TOP 12 Itemname, Price 
            FROM CleanedTransactions 
            WHERE Itemname IN (SELECT DISTINCT antecedents FROM ProductRules)
        """
        df_products = db.fetch_data(query_products)
        
        # Nếu bảng luật ít sản phẩm quá không đủ 12 món, thì lấy thêm sản phẩm thường bù vào
        if len(df_products) < 12:
            query_fallback = "SELECT DISTINCT TOP 12 Itemname, Price FROM CleanedTransactions WHERE Itemname IS NOT NULL"
            df_products = db.fetch_data(query_fallback)

        df_products['Price'] = df_products['Price'].round(2)
        products = df_products.to_dict(orient='records')

        # Thống kê số lượng bản ghi sạch (Minh chứng Tuần 2)
        query_count = "SELECT COUNT(*) as total FROM CleanedTransactions"
        total_cleaned = db.fetch_data(query_count).iloc[0]['total']
        
        # Lấy gợi ý và tên món vừa thêm từ session
        last_suggestions = session.get('last_suggestions', [])
        added_item = session.get('added_item', None)
        
        return render_template('index.html', 
                               products=products, 
                               total_cleaned=total_cleaned,
                               suggestions=last_suggestions,
                               added_item=added_item)
    except Exception as e:
        return f"Lỗi hệ thống: {e}"

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_name = request.form.get('product_name')
    
    # 1. Quản lý giỏ hàng
    if 'cart' not in session:
        session['cart'] = []
    cart = session['cart']
    cart.append(product_name)
    session['cart'] = cart
    
    # 2. KHAI THÁC TRI THỨC (Nâng cấp)
    # Bước A: Tìm gợi ý từ luật Apriori
    suggestions = rec_service.get_suggestions(product_name)
    
    # Bước B: Nếu không có luật Apriori (suggestions rỗng), hãy lấy Top sản phẩm bán chạy (Dự phòng)
    if not suggestions:
        print(f"DEBUG: Khong tim thay luat cho {product_name}, dang lay Top ban chay...")
        suggestions = rec_service.get_top_selling(limit=3)
        # Sửa lại tên hiển thị một chút để giảng viên biết đây là gợi ý xu hướng
        session['is_fallback'] = True 
    else:
        session['is_fallback'] = False

    print(f"DEBUG: San pham them: {product_name}")
    print(f"DEBUG: Goi y tra ve: {suggestions}")
    
    # 3. Lưu vào session để hiển thị Modal
    session['last_suggestions'] = suggestions
    session['added_item'] = product_name 
    
    return redirect(url_for('index'))

@app.route('/cart')
def view_cart():
    """Trang giỏ hàng"""
    cart = session.get('cart', [])
    # Truyền thêm suggestions vào cart để trang giỏ hàng cũng hiện gợi ý
    last_suggestions = session.get('last_suggestions', [])
    return render_template('cart.html', cart=cart, suggestions=last_suggestions)

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    session.pop('last_suggestions', None)
    session.pop('added_item', None)
    session.pop('is_fallback', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)