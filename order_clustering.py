import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
import seaborn as sns
from db_helper import DatabaseHelper
from sklearn.cluster import KMeans

def execute_clustering():
    """
    Thực hiện thuật toán K-Means gom cụm hành vi mua sắm từ lịch sử hóa đơn.
    Áp dụng kiến thức Chương IV & V tài liệu HUIT.
    """
    db = DatabaseHelper()
    
    # 1. Thu thập dữ liệu tổng hợp theo từng Hóa đơn (BillNo)
    print("--- Đang tải dữ liệu hóa đơn từ SQL Server... ---")
    # SỬA LẠI TRONG FILE order_clustering.py
    query = """
        SELECT BillNo, 
           COUNT(Itemname) as TotalQuantity, 
           SUM(Quantity * Price) as TotalSpent
    FROM CleanedTransactions
    GROUP BY BillNo
    """
    df_orders = db.fetch_data(query)
    
    if df_orders.empty or len(df_orders) < 3:
        return {"error": "Dữ liệu hóa đơn quá ít, không thể phân cụm."}
        
    # Loại bỏ các hóa đơn ngoại lai quá lớn (outliers) để thuật toán K-Means phân cụm đẹp hơn
    df_orders = df_orders[(df_orders['TotalQuantity'] < 2000) & (df_orders['TotalSpent'] < 5000)]
    
    # 2. Chuẩn bị đặc trưng đưa vào mô hình (X)
    X = df_orders[['TotalQuantity', 'TotalSpent']].values
    
    # 3. Khởi chạy thuật toán K-Means với K = 3 cụm hành vi mẫu
    print("--- Đang tiến hành phân cụm dữ liệu bằng K-Means... ---")
    start_time = time.time()
    kmeans = KMeans(n_clusters=3, init='k-means++', random_state=42, n_init=10)
    df_orders['Cluster'] = kmeans.fit_predict(X)
    end_time = time.time()
    
    # Lấy tọa độ tâm của các cụm (Centroids)
    centroids = kmeans.cluster_centers_
    
    # Định nhãn tên cụm thông minh dựa trên vị trí giá trị chi tiêu của tâm cụm
    cluster_order = np.argsort(centroids[:, 1]) # Sắp xếp theo thứ tự chi tiêu tăng dần
    cluster_mapping = {
        cluster_order[0]: "Mua sắm Tiết kiệm (Giỏ nhỏ)",
        cluster_order[1]: "Mua sắm Phổ thông (Tiêu chuẩn)",
        cluster_order[2]: "Mua sắm Số lượng lớn (Bán sỉ)"
    }
    df_orders['ClusterName'] = df_orders['Cluster'].map(cluster_mapping)
    
    # 4. Trực quan hóa kết quả phân cụm bằng Đồ thị phân tán (Scatter Plot)
    print("--- Đang xuất đồ thị phân cụm khách hàng... ---")
    plt.figure(figsize=(10, 6))
    colors = ['#0ea5e9', '#f59e0b', '#10b981']
    
    for cluster_id in range(3):
        cluster_data = df_orders[df_orders['Cluster'] == cluster_id]
        plt.scatter(cluster_data['TotalQuantity'], cluster_data['TotalSpent'], 
                    label=cluster_mapping[cluster_id], alpha=0.6, s=15, c=colors[cluster_id])
                    
    # Vẽ các điểm tâm cụm (Centroids) lên đồ thị bằng dấu X màu đỏ nổi bật
    plt.scatter(centroids[:, 0], centroids[:, 1], s=150, c='red', marker='X', label='Tâm cụm (Centroid)')
    
    plt.title('Biểu đồ phân cụm Hành vi mua sắm Khách hàng (K-Means Clustering)', fontsize=14, fontweight='bold')
    plt.xlabel('Tổng số lượng mặt hàng trong đơn (Total Quantity)')
    plt.ylabel('Tổng giá trị đơn hàng (Total Spent - $)')
    plt.legend(loc='upper right')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.savefig('shopping_clusters.png', dpi=300)
    plt.close()
    
    # 5. Lưu trữ tọa độ tâm cụm vào CSDL SQL Server để phục vụ tính khoảng cách ở Backend
    df_centroids = pd.DataFrame({
        'ClusterID': list(cluster_mapping.keys()),
        'ClusterName': list(cluster_mapping.values()),
        'Centroid_Qty': centroids[:, 0],
        'Centroid_Spent': centroids[:, 1]
    })
    
    try:
        engine = db.get_engine()
        df_centroids.to_sql('ClusterCentroids', con=engine, if_exists='replace', index=False)
        print("--- ĐÃ ĐỒNG BỘ TÂM CỤM K-MEANS VÀO SQL SERVER THÀNH CÔNG! ---")
    except Exception as e:
        print(f"Lỗi khi lưu tâm cụm: {e}")
        
    return {
        "execution_time": round(end_time - start_time, 4),
        "status": "Phân cụm hành vi bằng K-Means thành công!",
        "centroids": df_centroids.to_dict(orient='records')
    }

if __name__ == '__main__':
    print(execute_clustering())