CREATE DATABASE ProductRecommendationDB;
GO

USE ProductRecommendationDB;
GO

CREATE TABLE Transactions
(
    -- Khóa chính tự tăng để quản lý từng dòng dữ liệu
    TransactionID INT IDENTITY(1,1) PRIMARY KEY, 
    
    BillNo NVARCHAR(50),
    Itemname NVARCHAR(255) NULL, -- Cho phép NULL để nạp được dữ liệu thiếu
    Quantity INT,
    [Date] DATETIME, -- Dùng ngoặc vuông vì Date là từ khóa hệ thống
    Price DECIMAL(18, 2), -- Kiểu dữ liệu chuẩn cho tiền tệ 
    CustomerID FLOAT,
    Country NVARCHAR(100)
);

CREATE TABLE Orders
(
    OrderID INT IDENTITY(1,1) PRIMARY KEY,
    BillNo NVARCHAR(100),
    Itemname NVARCHAR(500),
    CreatedDate DATETIME DEFAULT GETDATE()
)

SELECT COUNT(*) FROM Transactions
SELECT COUNT(*) FROM Transactions WHERE Itemname IS NULL
SELECT TOP 10 Date FROM Transactions

SELECT COUNT(*) FROM CleanedTransactions

select * from Transactions
select * from ProductRules
-- 1. Chỉnh cột BillNo về NVARCHAR(50) (đủ để chứa mã hóa đơn)
ALTER TABLE CleanedTransactions 
ALTER COLUMN BillNo NVARCHAR(50) NOT NULL;

-- 2. Chỉnh cột Itemname về NVARCHAR(255) (đủ để chứa tên sản phẩm)
ALTER TABLE CleanedTransactions 
ALTER COLUMN Itemname NVARCHAR(255);
-- Tạo Index cho mã hóa đơn để tăng tốc độ gom nhóm theo giỏ hàng
CREATE INDEX idx_BillNo ON CleanedTransactions(BillNo);
-- Tạo Index cho tên sản phẩm để tăng tốc độ tìm kiếm
CREATE INDEX idx_Itemname ON CleanedTransactions(Itemname);

-- Kiểm tra cấu trúc bảng và Index
EXEC sp_helpindex 'CleanedTransactions';

-- Chuyển antecedents về kiểu dữ liệu cố định để tạo Index
ALTER TABLE ProductRules ALTER COLUMN antecedents NVARCHAR(255) NOT NULL;

-- Tạo Index để tìm kiếm luật cực nhanh
CREATE INDEX idx_antecedents ON ProductRules(antecedents);

