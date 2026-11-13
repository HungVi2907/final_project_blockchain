# Hướng dẫn cho người A — Dữ liệu và mô hình học máy

**Người phụ trách:** Chưa gán tên. **Hạn nộp chính thức:** 04/12/2026 (giờ Moodle chưa rõ). Lịch nội bộ và các cổng tích hợp ở [kế hoạch chung](TEAM_3_PERSON_EXECUTION_GUIDE.md); toàn bộ giờ nội bộ là UTC+7.

## Mục tiêu và phạm vi

Bạn sở hữu S1–S6, E1 và E7: lấy và kiểm tra dữ liệu, chia train/validation/test độc lập cho `taiwan_uci350` và `home_credit_2018`, fit tiền xử lý chỉ trên train, so sánh LR/RF/XGBoost, chọn model/ngưỡng trên validation, đánh giá một lần trên test, đóng băng artifact và cung cấp `predict()` theo [giao diện v1](interface_contract.md). Không gộp hai dataset, không chuyển model qua dataset, không đưa ID hoặc target vào predictor.

File sở hữu: `src/credit_audit/data.py`, `src/credit_audit/ml.py`, `scripts/download_taiwan.py`, `scripts/taiwan_smoke.py`, `docs/data_contract.md`, `tests/test_data_ml.py` và các file data/ML mới. Không sửa `records.py`, `storage.py`, `chain.py`, `contracts/`, `schemas/` hoặc UI. File chung cần PR riêng và review của B/C.

## Trạng thái đang có

Nguồn Taiwan UCI đã tải và kiểm tra: 30.000 hàng, 23 predictor, 6.636 nhãn dương; SHA-256 XLS và vấn đề mã giá trị/duplicate được ghi trong `docs/data_contract.md`. Bản smoke hiện chỉ dùng LR, split 21.000/4.500/4.500 với seed 42 và ngưỡng chọn trên validation. Các metric smoke không phải so sánh E1. Home Credit chưa được tải. Dữ liệu gốc và artifact nằm ngoài Git.

## Việc cần làm theo thứ tự

1. **Đến G0 — 16/11, 20:00:** Kiểm tra lại checksum Taiwan, manifest split và allow-list. Chốt chính sách duplicate, mã EDUCATION/MARRIAGE/PAY bất thường và feature nhạy cảm; ghi quyết định vào data contract. Với Home Credit, kiểm tra quyền truy cập Kaggle, xác định `application_train.csv` và phạm vi bảng phụ; chỉ dùng bảng phụ nếu có quy tắc dữ liệu sẵn tại thời điểm quyết định.
2. **Đến G1 — 20/11, 20:00:** Cài đặt cùng một giao thức chọn LR/RF/XGBoost trên Taiwan. Tuning chỉ trong train (CV hoặc grid đã ghi), chọn model và threshold trên validation, test một lần. Lưu metric ROC-AUC, PR-AUC, Recall/F1 cho lớp 1, confusion matrix, seed, split checksum và các phiên bản. Xuất artifact gồm pipeline đã fit, thứ tự feature, `dataset_id`, ngưỡng, version và hash file bundle. Bàn giao `predict()` và fixture cho B/C.
3. **Đến G2 — 25/11, 20:00:** Lặp lại quy trình độc lập trên Home Credit dữ liệu có nhãn. Không dùng `application_test.csv` không nhãn để báo metric. Chứng minh chọn đúng artifact theo `dataset_id`; đưa một hồ sơ Taiwan và một hồ sơ Home Credit hợp lệ cho B thử `explain()`.
4. **Đến G3 — 29/11, 20:00:** Chạy E1/E7, lưu bảng kết quả thực tế, phân tích lỗi/imbalance. Nếu báo khoảng tin cậy, chốt phương pháp bootstrap/seed trước khi tính. Không so AUC giữa hai dataset như bằng chứng độ khó hay chuyển giao.
5. **Đến G4 — 02/12, 20:00:** Chạy lại từ môi trường sạch, kiểm tra artifact hash và figure/bảng trong báo cáo; giao hướng dẫn tái lập cho C.

## Tiêu chí nghiệm thu

- Manifest split có source SHA-256 và ID ba tập không giao nhau; chạy lại cùng seed cho cùng manifest.
- Imputer, encoder, scaler chỉ fit train; validation/test chỉ `transform`. Test thay dữ liệu validation không đổi thống kê đã fit.
- Với mỗi dataset, có một model version/artifact riêng; load lại artifact cho cùng xác suất trong dung sai; reject input sai dataset hoặc feature schema.
- Mọi metric test được tính sau khi khóa model và ngưỡng. Bảng kết quả ghi rõ thực đo, không trộn với số của bài báo Hlongwane.
- `predict()` trả đúng các key trong `docs/interface_contract.md`, để B tạo SHAP và C tích hợp UI.

## Prompt đưa cho agent của A

```text
Bạn là agent phụ trách vai trò A (dữ liệu và ML) của dự án Super Bells. Trước khi sửa code, đọc docs/ROLE_A_DATA_ML.md, docs/TEAM_3_PERSON_EXECUTION_GUIDE.md, docs/interface_contract.md, docs/data_contract.md, báo cáo Week 3 và kiểm tra git status. Chỉ sửa file thuộc quyền sở hữu A; với file chung hoặc giao diện cần thay, hãy mô tả đề xuất để B/C review trước. Thực hiện mốc gần nhất chưa đạt trong tài liệu A, kiểm thử chống rò rỉ và khả năng tái lập, bàn giao artifact/fixture theo giao diện v1. Không commit dữ liệu gốc, model artifact, SQLite hay bí mật. Kết thúc bằng: việc đã làm, lệnh chạy/test và kết quả, file đã sửa, API bàn giao, rủi ro còn lại và mốc deadline tiếp theo. Không gọi kết quả smoke là kết quả thí nghiệm E1 chính thức.
```

