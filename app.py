from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from db_helper import DatabaseHelper
from recommendation_service import RecommendationService

app = Flask(__name__)
app.secret_key = 'huit_datamining_project_2026'

db = DatabaseHelper()
rec_service = RecommendationService()

@app.route('/')
def index():
    try:
        # Lấy danh sách 12 sản phẩm tiêu biểu hiển thị lên trang chủ giao diện
        query_products = "SELECT DISTINCT TOP 12 Itemname, Price FROM CleanedTransactions WHERE Itemname IS NOT NULL"
        df_products = db.fetch_data(query_products)
        df_products['Price'] = df_products['Price'].round(2)
        products = df_products.to_dict(orient='records')

        # Thống kê tổng số bản ghi phục vụ thanh trạng thái
        query_count = "SELECT COUNT(*) as total FROM CleanedTransactions"
        total_cleaned = db.fetch_data(query_count).iloc[0]['total']
        
        return render_template('index.html', products=products, total_cleaned=total_cleaned)
    except Exception as e:
        return f"Lỗi hệ thống khởi chạy: {e}"

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """API Endpoint tiếp nhận request AJAX - Trả về JSON, hoàn toàn không reload trang"""
    data = request.get_json()
    if not data or 'product_name' not in data:
        return jsonify({'error': 'Dữ liệu đầu vào không hợp lệ'}), 400
        
    product_name = data['product_name']
    
    if 'cart' not in session:
        session['cart'] = []
    cart = session['cart']
    cart.append(product_name)
    session['cart'] = cart
    
    # KHAI THÁC TRI THỨC: Truyền toàn bộ cấu trúc giỏ hàng hiện tại để quét luật tập con
    suggestions = rec_service.get_suggestions(cart, limit=3)
    is_fallback = False
    
    # Nếu không tìm thấy luật thỏa mãn điều kiện tập con, kích hoạt hệ thống dự phòng bán chạy
    if not suggestions:
        suggestions = rec_service.get_top_selling(limit=3)
        is_fallback = True

    # Trả dữ liệu về cho khối lệnh JavaScript AJAX xử lý
    return jsonify({
        'cart_length': len(cart),
        'added_item': product_name,
        'suggestions': suggestions,
        'is_fallback': is_fallback
    })

@app.route('/cart')
def view_cart():
    """Trang xem chi tiết giỏ hàng và gợi ý chốt đơn bổ trợ"""
    cart = session.get('cart', [])
    # Đồng bộ gợi ý tập con ngay tại trang giỏ hàng
    suggestions = rec_service.get_suggestions(cart, limit=4)
    is_fallback = False
    if not suggestions and cart:
        suggestions = rec_service.get_top_selling(limit=3)
        is_fallback = True
    return render_template('cart.html', cart=cart, suggestions=suggestions, is_fallback=is_fallback)

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)