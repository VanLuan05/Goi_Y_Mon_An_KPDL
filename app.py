from tracemalloc import start

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from db_helper import DatabaseHelper
from recommendation_service import RecommendationService
from fp_growth_mining import execute_mining
from order_clustering import execute_clustering

app = Flask(__name__)
app.secret_key = 'huit_datamining_project_2026'

db = DatabaseHelper()
rec_service = RecommendationService()
translation_dict = {}

@app.route('/admin/cluster', methods=['POST'])
def admin_cluster():
    """API Endpoint ra lệnh chạy thuật toán K-Means trực tuyến từ trang Admin"""
    result = execute_clustering()
    return jsonify(result)
# Hàm nạp từ điển dịch tiếng Việt vào RAM để sử dụng cho toàn bộ ứng dụng
def load_translation_dictionary():
    global translation_dict

    try:
        import pandas as pd

        df_trans = pd.read_excel('chuyensangTV.xlsx')

        translation_dict = dict(
            zip(
                df_trans['Itemname'].astype(str).str.strip(),
                df_trans['Tên sản phẩm'].astype(str).str.strip()
            )
        )

        print(
            f"✅ ĐÃ NẠP TỪ ĐIỂN VÀO RAM: {len(translation_dict)} sản phẩm"
        )

    except Exception as e:
        print(f"❌ Lỗi nạp từ điển: {e}")
        translation_dict = {}
# Gọi hàm nạp từ điển ngay khi khởi động ứng dụng
@app.route('/')
def index():
    print("INDEX LOADED")
    page = request.args.get('page', 1, type=int)
    per_page = 24
    try:
        # 1. TRUY VẤN TẤT CẢ CÁC MÓN ĂN KÈM GIÁ (Siêu nhanh vì dùng GROUP BY)
        # Sắp xếp theo SalesCount DESC để ưu tiên các món bán chạy nhất
        query_all = """
            SELECT Itemname, MAX(Price) as Price, COUNT(*) as SalesCount 
            FROM CleanedTransactions 
            WHERE Itemname IS NOT NULL 
            GROUP BY Itemname 
            ORDER BY SalesCount DESC
        """
        df_all = db.fetch_data(query_all)
        
        # 2. LẤY DANH SÁCH MÓN ĂN CÓ LUẬT TỪ RAM (Đã IN HOA để chuẩn hóa so sánh)
        valid_items_upper = set()

        if rec_service.cached_rules:
            for rule in rec_service.cached_rules:

                for item in rule['antecedents']:
                    valid_items_upper.add(item.upper())

                for item in rule['consequents']:
                    valid_items_upper.add(item.upper())
                    
        dict_trans = translation_dict

        final_products = []
        fallback_products = []
        
        for _, row in df_all.iterrows():
            eng_name = str(row['Itemname']).strip()
            
            # KHI TRÍCH XUẤT TÊN: Tra từ điển ngay lập tức. Nếu có tiếng Anh thì đổi sang tiếng Việt.
            item_name = dict_trans.get(eng_name, eng_name)
            
            # Lúc này item_upper đã là TIẾNG VIỆT VIẾT HOA
            item_upper = item_name.upper()
            
            # Ép kiểu giá tiền cực kỳ an toàn (Bỏ qua lỗi to_numeric)
            try:
                price = float(row['Price'])
            except:
                price = 0.0
                
            product_dict = {'Itemname': item_name, 'Price': round(price, 2)}
            
            # Lưu 24 món bán chạy nhất làm danh sách dự phòng
            if len(fallback_products) < 24:
                fallback_products.append(product_dict)
                
            # NẾU món này có xuất hiện trong kho Luật trên RAM -> Cho hiển thị ra Web
            if item_upper in valid_items_upper:
                final_products.append(product_dict)
                
           
                
        # 4. CHỐT CHẶN CUỐI: Nếu không có luật nào khớp, dùng luôn 12 món bán chạy
        if not final_products:
            final_products = fallback_products

        # Thống kê tổng số bản ghi
        query_count = "SELECT COUNT(*) as total FROM CleanedTransactions"
        total_cleaned = db.fetch_data(query_count).iloc[0]['total']
        
        print("Số sản phẩm trong luật:", len(valid_items_upper))
        print("Số sản phẩm hiển thị:", len(final_products))
        total_products = len(final_products)

        start = (page - 1) * per_page
        end = start + per_page

        paginated_products = final_products[start:end]

        total_pages = (total_products + per_page - 1) // per_page

        return render_template(
            'index.html',
            products=paginated_products,
            total_cleaned=total_cleaned,
            page=page,
            total_pages=total_pages
    )
    except Exception as e:
        return f"Lỗi hệ thống khởi chạy: {e}"

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """API Endpoint tiếp nhận request AJAX"""
    data = request.get_json()
    if not data or 'product_name' not in data:
        return jsonify({'error': 'Dữ liệu đầu vào không hợp lệ'}), 400
        
    product_name = data['product_name']
    
    if 'cart' not in session:
        session['cart'] = []
    cart = session['cart']
    cart.append(product_name)
    session['cart'] = cart
    
    #suggestions = rec_service.get_suggestions(cart, limit=3) # Lấy gợi ý mới sau khi thêm sản phẩm vào giỏ
    suggestions = rec_service.get_suggestions([product_name], limit=3) #chỉ lấy gợi ý cho sản phẩm vừa bấm 
    is_fallback = False
    
    if not suggestions:
        print("FALLBACK MODE")
        suggestions = rec_service.get_top_selling(limit=3)
        is_fallback = True
    print("Suggestions:", suggestions)
    print("Fallback:", is_fallback)
    return jsonify({
        'cart_length': len(cart),
        'added_item': product_name,
        'suggestions': suggestions,
        'is_fallback': is_fallback
    })

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin_dashboard():
    """Trang giao diện Admin cấu hình thuật toán chuyên sâu"""
    try:
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
        
    min_support = float(data.get('min_support', 0.015))
    min_confidence = float(data.get('min_confidence', 0.5))
    
    # Kích hoạt hàm xử lý thuật toán cốt lõi
    result = execute_mining(min_support, min_confidence)
    rec_service.reload_rules()
    # ĐÃ FIX: Trả về chuẩn JSON cho trang Admin, bỏ mớ code giao diện giỏ hàng bị dán nhầm ở đây
    return jsonify(result)

@app.route('/cart')
def view_cart():
    """Trang xem chi tiết giỏ hàng và hiển thị kết quả phân tích AI (K-Means & K-NN)"""
    cart = session.get('cart', [])
    
    # 1. Thuật toán Gom cụm (K-Means)
    cart_cluster = rec_service.classify_live_cart(cart)
    
    # 2. Thuật toán Phân lớp (K-NN) - Dự báo chốt đơn
    checkout_prob = rec_service.predict_checkout_probability(cart)
    
    # 3. Thuật toán Gợi ý mua kèm (FP-Growth)
    suggestions = rec_service.get_suggestions(cart, limit=3)
    print("Suggestions:", suggestions)
    is_fallback = False
    
    if not suggestions and cart:
        suggestions = rec_service.get_top_selling(limit=4)
        is_fallback = True
        
    return render_template('cart.html', 
                           cart=cart, 
                           suggestions=suggestions, 
                           is_fallback=is_fallback,
                           cart_cluster=cart_cluster,

                          checkout_prob=checkout_prob)
load_translation_dictionary()
if __name__ == '__main__':
    app.run(debug=True, port=5000)