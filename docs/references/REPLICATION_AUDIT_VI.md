# Kiểm tra tái thực nghiệm Hlongwane et al. (2024)

> **Hồ sơ lịch sử:** bài này không còn là tham khảo chính từ 19/11/2026. Xem [bối cảnh ICLR 2025](../PROJECT_CONTEXT.md); giữ bản kiểm tra này để giải thích lý do đổi bài nền.

Nguồn: Hlongwane, Ramaboa, Mongwe, *A novel framework for enhancing transparency in credit scoring: Leveraging Shapley values for interpretable credit scorecards*, PLOS ONE 19(8), e0308718. DOI: https://doi.org/10.1371/journal.pone.0308718. PDF gốc lưu cùng thư mục. Bài đính chính tên tác giả thứ hai: https://doi.org/10.1371/journal.pone.0329901.

## Kết quả từ Bảng 5 và 7 (ROC-AUC trên test)

| Mô hình | Taiwan | Home Credit |
| --- | ---: | ---: |
| Logistic Regression | 0.74891 | 0.69644 |
| Random Forest | 0.75929 | 0.69280 |
| XGBoost | 0.75766 | 0.69766 |
| LightGBM | 0.75690 | 0.69654 |
| CatBoost | 0.74793 | 0.68450 |

Bảng 6: Taiwan test 6.000 hồ sơ (4.685 âm, 1.315 dương). Bảng 8: Home Credit test 61.503 hồ sơ (56.499 âm, 5.004 dương). Bài dùng kiểm định DeLong để so AUC.

## Phương pháp được bài mô tả

- Taiwan UCI: 30.000 dòng, 6.636 dương, 23 predictor gốc. Home Credit Kaggle: bài ghi 356.255 hồ sơ và 24.845 dương.
- Split 80/20 train/test; grid search và 5-fold CV. Không công bố seed, ID các split, grid và tham số tối ưu đầy đủ.
- Taiwan tạo các đặc trưng rolling average, standard deviation và tỷ số tháng hiện tại / trung bình 3 tháng từ PAY, BILL_AMT, PAY_AMT: 23 thành 59. Bảng 3 giữ 7: `AVG_PAY__SEP`, `CURRENT_OVER_3MAVG_PAY__SEP`, `STD_PAY__SEP`, `AVG_PAY__JUN`, `AVG_BILL_AMT_SEP`, `AVG_PAY_AMT_SEP`, `CURRENT_OVER_3MAVG_BILL_AMT_SEP`.
- Home Credit tổng hợp dữ liệu theo khách hàng: 217 thành 767 đặc trưng, rồi Bảng 2 giữ 11. Tên feature cuối cho thấy cần `application_train`, `bureau`, `installments_payments`, `previous_application`; bài chưa mô tả đầy đủ cách tạo từng cột.
- Chọn biến bằng permutation importance và Wald test, kiểm tra tương quan dưới 0.8; mean imputation, clipping phân vị 2.5/97.5, binning hướng WOE, one-hot encoding.
- So sánh LR, RF, XGBoost, LightGBM, CatBoost. Sau bước đánh giá mô hình, SHAP được dùng để dựng scorecard có điểm trung tính.

## Điều kiện tái lập và điểm chưa rõ

1. `application_train.csv` có 307.511 dòng có nhãn, `application_test.csv` có 48.744 dòng không nhãn, cộng thành 356.255. Tỷ lệ 24.845/356.255 = 6,97% trong bài dùng cả dòng không nhãn làm mẫu số; tỷ lệ trên train có nhãn khoảng 8,08%. Bảng 8 dùng 61.503 test, gần 20% của 307.511. Không dùng `application_test.csv` để tính metric.
2. Bài không nêu seed/split IDs, bin edges/WOE rules, grid tối ưu, xử lý chia cho 0 trong ratio, threshold cho confusion matrix. Vì vậy chỉ có thể nhắm **tái lập gần**, không hứa trùng từng số.
3. Bài chưa làm rõ các thống kê impute, clipping, feature selection, WOE fit trước hay sau split. Triển khai của nhóm phải fit trong train/CV fold, chỉ transform test để tránh rò rỉ.
4. Home Credit cần chốt chính xác bảng phụ, phép tổng hợp và mốc thời gian dữ liệu trước khi chạy đầy đủ.

## Code tác giả

Trang PLOS chỉ liên kết nguồn dữ liệu UCI và Kaggle, không dẫn repository hay phụ lục code. Tìm theo DOI, tiêu đề và tên tác giả trên GitHub/web không thấy repo của nhóm tác giả; các kết quả GitHub hiện chỉ trích dẫn paper. Kết luận: **chưa tìm thấy code công khai**, chưa thể khẳng định tác giả không có code ở nơi khác.

## Đối chiếu phần A đang có

| Hạng mục | Bài gốc | Project | Cần làm |
| --- | --- | --- | --- |
| Taiwan | 30.000 dòng | Đã tải | Giữ checksum/source manifest |
| Split | 80/20 | 70/15/15 | Tạo thí nghiệm tái lập riêng và lưu ID 80/20 |
| Feature | 7 engineered từ 59 | 23 raw | Implement feature engineering và phép chọn 7 |
| Preprocessing | Mean, clipping, WOE/bin, one-hot | Median, scaler | Dựng pipeline fit train và ghi giả định |
| Models | 5 mô hình | LR smoke | Bắt đầu LR/RF/XGB smoke; đủ 5 cho full |
| Metrics | ROC-AUC, DeLong, confusion | PR-AUC/ROC-AUC/F1 LR | So AUC từng model, ghi threshold trước confusion |
| Home Credit | Aggregate và 11 feature | Chưa tải | Tải tập có nhãn và bảng phụ, chốt aggregate |

Thứ tự đề nghị: Taiwan 80/20 + EDA + feature engineering + smoke; kiểm tra chênh lệch AUC; full hai dataset và năm mô hình; khóa artifact cho B thêm SHAP; C mới nối chain/UI. LR smoke hiện có không phải lần tái thực nghiệm này.
