from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from db_helper import DatabaseHelper
from recommendation_service import RecommendationService
from fp_growth_mining import execute_mining
from order_clustering import execute_clustering


app = Flask(__name__)
app.secret_key = 'huit_datamining_project_2026'

db = DatabaseHelper()
rec_service = RecommendationService()

@app.route('/admin/cluster', methods=['POST'])
def admin_cluster():
    """API Endpoint ra lệnh chạy thuật toán K-Means trực tuyến từ trang Admin"""
    result = execute_clustering()
    return jsonify(result)

@app.route('/')
def index():
    try:
        # BẢN NÂNG CẤP: Chỉ lấy 12 sản phẩm nào THỰC SỰ CÓ LUẬT trong bảng ProductRules 
        # Giúp đảm bảo khi demo, người dùng click vào bất kỳ món nào cũng hiện tri thức thật
        query_products = """
            SELECT DISTINCT TOP 12 t.Itemname, t.Price 
            FROM CleanedTransactions t
            INNER JOIN ProductRules r ON r.antecedents = t.Itemname
            WHERE t.Itemname IS NOT NULL
        """
        df_products = db.fetch_data(query_products)
        
        # Nếu bảng luật mới chạy lại chưa đủ hoặc có vấn đề, dùng cơ chế dự phòng lấy sản phẩm thường
        if df_products.empty or len(df_products) < 12:
            query_fallback = "SELECT DISTINCT TOP 12 Itemname, Price FROM CleanedTransactions WHERE Itemname IS NOT NULL"
            df_products = db.fetch_data(query_fallback)

        df_products['Price'] = df_products['Price'].round(2)
        products = df_products.to_dict(orient='records')

        # Thống kê tổng số bản ghi phục vụ thanh trạng thái dưới chân trang
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
    """Trang xem chi tiết giỏ hàng và hiển thị kết quả phân tích AI (K-Means & K-NN)"""
    cart = session.get('cart', [])
    
    # 1. Thuật toán Gom cụm (K-Means)
    cart_cluster = rec_service.classify_live_cart(cart)
    
    # 2. Thuật toán Phân lớp (K-NN) - Dự báo chốt đơn
    checkout_prob = rec_service.predict_checkout_probability(cart)
    
    # 3. Thuật toán Gợi ý mua kèm (FP-Growth)
    suggestions = rec_service.get_suggestions(cart, limit=4)
    is_fallback = False
    
    if not suggestions and cart:
        suggestions = rec_service.get_top_selling(limit=3)
        is_fallback = True
        
    return render_template('cart.html', 
                           cart=cart, 
                           suggestions=suggestions, 
                           is_fallback=is_fallback,
                           cart_cluster=cart_cluster,
                           checkout_prob=checkout_prob)
    """Trang xem chi tiết giỏ hàng và hiển thị kết quả phân cụm K-Means thực tế"""
    cart = session.get('cart', [])
    
    # GỌI NÂNG CẤP CÁCH 2: Phân nhóm hành vi giỏ hàng bằng mô hình gom cụm
    cart_cluster = rec_service.classify_live_cart(cart)
    
    suggestions = rec_service.get_suggestions(cart, limit=4)
    is_fallback = False
    if not suggestions and cart:
        suggestions = rec_service.get_top_selling(limit=3)
        is_fallback = True
        
    return render_template('cart.html', 
                           cart=cart, 
                           suggestions=suggestions, 
                           is_fallback=is_fallback,
                           cart_cluster=cart_cluster) # Truyền nhãn phân cụm sang giao diện

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin_dashboard():
    """Trang giao diện Admin cấu hình thuật toán chuyên sâu"""
    try:
        # Lấy số lượng luật hiện tại đang có trong hệ thống để hiển thị lên bảng điều khiển
        query_rules_count = "SELECT COUNT(*) as total FROM ProductRules"
        rules_count = db.fetch_data(query_rules_count).iloc[0]['total']
    except Exception:
        rules_count = 0
        
    return render_template('admin.html', rules_count=rules_count)

@app.route('/admin/re_mine', methods=['POST'])
def admin_re_mine():
    """API Endpoint nhận lệnh AJAX chạy lại thuật toán FP-Growth trực tuyến"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dữ liệu không hợp lệ'}), 400
        
    # Lấy các tham số động từ thanh kéo slider của người dùng gửi lên
    min_support = float(data.get('min_support', 0.015))
    min_confidence = float(data.get('min_confidence', 0.5))
    
    # Kích hoạt hàm xử lý thuật toán cốt lõi
    result = execute_mining(min_support, min_confidence)
    

    """Trang xem chi tiết giỏ hàng và hiển thị kết quả phân tích AI"""
    cart = session.get('cart', [])
    
    # 1. Thuật toán Gom cụm (K-Means)
    cart_cluster = rec_service.classify_live_cart(cart)
    
    # 2. THUẬT TOÁN PHÂN LỚP (K-NN) - DỰ BÁO CHỐT ĐƠN
    checkout_prob = rec_service.predict_checkout_probability(cart)
    
    suggestions = rec_service.get_suggestions(cart, limit=4)
    is_fallback = False
    if not suggestions and cart:
        suggestions = rec_service.get_top_selling(limit=3)
        is_fallback = True
        
    return render_template('cart.html', 
                           cart=cart, 
                           suggestions=suggestions, 
                           is_fallback=is_fallback,
                           cart_cluster=cart_cluster,
                           checkout_prob=checkout_prob) # Cập nhật truyền biến dự báo ra web
    return jsonify(result)
if __name__ == '__main__':
    app.run(debug=True, port=5000)