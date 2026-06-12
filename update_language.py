import pandas as pd
import pyodbc 

def update_database_language():
    # 1. Đọc file từ điển CSV của bạn
    # Lưu ý: Sửa lại tên file cho đúng với tên file đang lưu trên máy
    df = pd.read_excel('chuyensangTV.xlsx')
    
        # 2. Kết nối đến SQL Server
    conn = pyodbc.connect('DRIVER={SQL Server};SERVER=LUAN\\SQLEXPRESS;DATABASE=ProductRecommendationDB;Trusted_Connection=yes;')
    cursor = conn.cursor()

    # 3. Nới rộng cột để tránh lỗi "String or binary data would be truncated"
    print("Đang cấu hình lại kích thước cột dữ liệu...")
    try:
        cursor.execute("ALTER TABLE CleanedTransactions ALTER COLUMN Itemname NVARCHAR(400);")
        conn.commit()
    except Exception as e:
        print("Cột đã được nới rộng từ trước.")

    # 4. Tiến hành cập nhật hàng loạt
    print("Đang đồng bộ tiếng Việt vào Cơ sở dữ liệu. Vui lòng đợi vài giây...")
    count = 0
    
    for index, row in df.iterrows():
        # Lấy tên tiếng Anh và tiếng Việt, thay thế dấu nháy đơn (') thành ('') để không bị sập SQL
        eng_name = str(row['Itemname']).replace("'", "''").strip()
        vie_name = str(row['Tên sản phẩm']).replace("'", "''").strip()
        
        # Cập nhật nếu tên tiếng Việt hợp lệ
        if pd.notna(vie_name) and vie_name != 'nan':
            query = f"UPDATE CleanedTransactions SET Itemname = N'{vie_name}' WHERE Itemname = '{eng_name}'"
            cursor.execute(query)
            count += 1
            
    # Lưu thay đổi và đóng kết nối
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"HOÀN TẤT! Đã phiên dịch thành công {count} mặt hàng sang tiếng Việt.")

if __name__ == '__main__':
    update_database_language()