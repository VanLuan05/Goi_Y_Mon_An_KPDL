import pandas as pd

# Đọc dữ liệu với dấu phân cách là ';'
df = pd.read_csv('Assignment-1_Data.csv', sep=';', low_memory=False)

# 1. Xem 5 dòng đầu tiên
print("--- 5 dòng dữ liệu mẫu ---")
print(df.head())

# 2. Kiểm tra tổng số dòng và cột
print(f"\nTổng số dòng: {df.shape[0]}")
print(f"Tổng số cột: {df.shape[1]}")

# 3. Xem có bao nhiêu hóa đơn duy nhất (BillNo)
print(f"Số lượng hóa đơn duy nhất: {df['BillNo'].nunique()}")

# 4. Kiểm tra dữ liệu thiếu (NULL) - Chuẩn bị cho tuần 2
print("\n--- Kiểm tra dữ liệu thiếu ---")
print(df.isnull().sum())