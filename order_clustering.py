import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
import seaborn as sns
from db_helper import DatabaseHelper
from sklearn.cluster import KMeans
from sqlalchemy import types
def execute_clustering():
    """
    Thực hiện thuật toán K-Means gom cụm hành vi mua sắm từ lịch sử hóa đơn.
    Đã sửa lỗi lệch index tên cụm để đồng bộ hoàn hảo với hệ thống.
    """
    db = DatabaseHelper()
    
    # 1. Thu thập dữ liệu tổng hợp theo từng Hóa đơn (BillNo)
    print("--- Đang tải dữ liệu hóa đơn từ SQL Server... ---")
    query = """
        SELECT BillNo, 
               COUNT(Itemname) as TotalQuantity, 
               SUM(Price) as TotalSpent
        FROM CleanedTransactions
        GROUP BY BillNo
    """
    df_orders = db.fetch_data(query)
    
    if df_orders.empty or len(df_orders) < 3:
        return {"error": "Dữ liệu hóa đơn quá ít, không thể phân cụm."}
        
    # Loại bỏ các hóa đơn ngoại lai quá lớn (outliers) giúp đồ thị phân cụm đẹp mắt hơn
    df_orders = df_orders[(df_orders['TotalQuantity'] < 100) & (df_orders['TotalSpent'] < 500)]
    
    # 2. Chuẩn bị đặc trưng đưa vào mô hình (X)
    X = df_orders[['TotalQuantity', 'TotalSpent']].values
    
    # 3. Khởi chạy thuật toán K-Means với K = 3 cụm
    print("--- Đang tiến hành phân cụm dữ liệu bằng K-Means... ---")
    start_time = time.time()
    kmeans = KMeans(n_clusters=3, init='k-means++', random_state=42, n_init=10)
    df_orders['Cluster'] = kmeans.fit_predict(X)
    end_time = time.time()
    
    # Lấy tọa độ tâm của các cụm (Centroids)
    centroids = kmeans.cluster_centers_
    
    # Định nhãn tên cụm chính xác dựa trên giá trị chi tiêu tăng dần của tâm cụm
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
                    
    # Vẽ các điểm tâm cụm (Centroids) bằng dấu X màu đỏ nổi bật
    plt.scatter(centroids[:, 0], centroids[:, 1], s=150, c='red', marker='X', label='Tâm cụm (Centroid)')
    
    plt.title('Biểu đồ phân cụm Hành vi mua sắm Khách hàng (K-Means Clustering)', fontsize=14, fontweight='bold')
    plt.xlabel('Tổng số lượng mặt hàng trong đơn (Total Quantity)')
    plt.ylabel('Tổng giá trị đơn hàng (Total Spent - $)')
    plt.legend(loc='upper right')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.savefig('shopping_clusters.png', dpi=300)
    plt.close()
    
    # 5. Đồng bộ kết quả phân cụm (Cluster Centroids) vào bảng ClusterCentroids trong SQL Server
    centroid_list = []
    for cluster_id in range(3):
        centroid_list.append({
            'ClusterID': cluster_id,
            'ClusterName': cluster_mapping[cluster_id],
            'Centroid_Qty': float(centroids[cluster_id, 0]),
            'Centroid_Spent': float(centroids[cluster_id, 1])
        })
    df_centroids = pd.DataFrame(centroid_list)
    
    try:
        engine = db.get_engine()
        
        sql_types = {
            'ClusterName': types.NVARCHAR(length=100)
        }
        
        # Thêm tham số dtype=sql_types vào lệnh to_sql
        df_centroids.to_sql('ClusterCentroids', con=engine, if_exists='replace', index=False, dtype=sql_types)
        print("--- ĐÃ ĐỒNG BỘ TÂM CỤM K-MEANS VÀO SQL SERVER THÀNH CÔNG! ---")
    except Exception as e:
        print(f"Lỗi khi lưu tâm cụm: {e}")