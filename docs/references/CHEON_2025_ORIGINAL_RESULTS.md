# Kết quả gốc để đối chiếu — Cheon et al., ICLR 2025

**Trạng thái:** tài liệu này chỉ chứa số do tác giả công bố, không trộn số tái thực nghiệm của nhóm. Nguồn là [PDF ICLR chính thức](Cheon_2025_ICLR_Feature_Responsiveness_Scores.pdf), tải từ [trang proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/6662eaf34893d9827ddf60c29e9ad6af-Abstract-Conference.html). SHA-256 PDF: `898319f77c6291da28779f833ea33b29e24945002686891bbb2b70c62057a977`. Mã tác giả: [nhánh `paper/iclr2025`](https://github.com/ustunb/responsiveness/tree/paper/iclr2025), commit được kiểm tra ngày 19/11/2026: `4c68c73b34eef7c5e38847274048cb3ab66d702c`.

Kết quả nhóm đã chạy lại được lưu **riêng** tại [nhật ký tái lập](CHEON_2025_REPLICATION_LOG.md) và [CSV đối chiếu](CHEON_2025_REPLICATION_COMPARISON.csv); không thay các giá trị gốc trong tài liệu này.

Ba bảng CSV trong cùng thư mục giữ **giá trị từng ô** và số bảng/trang PDF: [AUC Table 11](CHEON_2025_TABLE11_AUC.csv), [recourse Table 3](CHEON_2025_TABLE3_RECOURSE.csv), [explanation Tables 4/12](CHEON_2025_TABLE4_12_EXPLANATIONS.csv). Dùng chúng làm mốc bất biến; lưu kết quả chạy lại của nhóm trong tệp khác với tên, ngày chạy, commit và cấu hình rõ ràng.

## 1. Giao thức công bố của tác giả

- **Phần thực nghiệm chính, Section 4:** ba tập tín dụng công khai ở dạng đặc trưng rời rạc, chia train/test **80/20**. Huấn luyện LR, XGBoost, RF; chỉnh siêu tham số bằng randomized search. Bài báo dùng tối đa **4 đặc trưng** trong mỗi giải thích. [PDF tr. 7 và tr. 26](Cheon_2025_ICLR_Feature_Responsiveness_Scores.pdf).
- **Mã tham chiếu:** [pipeline](https://github.com/ustunb/responsiveness/blob/paper/iclr2025/research/iclr2025/experiment/run_experiment_pipeline.py) có các bước `setup`, `db`, `train`, `explain`, `audit`, `score`; [script train](https://github.com/ustunb/responsiveness/blob/paper/iclr2025/research/iclr2025/experiment/train_models.py) ghi seed mặc định `2338`, fold `K05N01`, mô hình `logreg`/`rf`/`xgb`. Khi chạy phải khóa commit, đối chiếu phiên bản và lưu split thực tế, không suy rằng mọi bản chạy mặc định tạo cùng phép chia.
- **Nhãn FICO:** [script xử lý](https://github.com/ustunb/responsiveness/blob/paper/iclr2025/research/iclr2025/data/fico/process_fico.py) mã hóa `Good=1`, `Bad=0`. AUC để đối chiếu tác giả phải dùng đúng chiều nhãn và xác suất Good. Khi nhóm tạo `risk_probability` cho record, đổi thành `P(Bad)=1-P(Good)` và giải thích SHAP trên đầu ra tương ứng. Cần xác minh mapping từng tập khác riêng.
- **Đơn vị phần trăm:** Table 3 `% Denied` có mẫu số là toàn bộ hồ sơ của dataset; ba tỉ lệ recourse sau đó có mẫu số là các hồ sơ **bị từ chối**. Tables 4/12 báo kết quả giải thích trên nhóm được trình bày giải thích trong các hồ sơ bị từ chối; `RESP` chỉ trình bày cho một phần nhóm này. Không so trực tiếp hai tỉ lệ có mẫu số khác nhau.

## 2. Kết quả dự đoán dùng cho người A — Table 11, PDF tr. 26

| Dataset (n, d) | Model | Train AUC | Test AUC |
| --- | --- | ---: | ---: |
| HELOC (5.842, 43) | LR | 0,772 | **0,788** |
| HELOC (5.842, 43) | XGBoost | 0,859 | **0,785** |
| HELOC (5.842, 43) | RF | 0,780 | **0,790** |
| German (1.000, 36) | LR | 0,819 | **0,760** |
| German (1.000, 36) | XGBoost | 0,971 | **0,794** |
| German (1.000, 36) | RF | 0,828 | **0,766** |
| Give Me Some Credit (120.268, 23) | LR | 0,841 | **0,844** |
| Give Me Some Credit (120.268, 23) | XGBoost | 0,875 | **0,793** |
| Give Me Some Credit (120.268, 23) | RF | 0,864 | **0,835** |

Các số trên là **một bảng kết quả của tác giả**, không phải mục tiêu bắt buộc phải khớp tuyệt đối hoặc trung bình nhiều seed. Khi đối chiếu, ghi cả chênh lệch tuyệt đối `AUC_nhóm - AUC_tác_giả` lẫn nguyên nhân khả dĩ (dữ liệu, feature engineering, split, tuning, thư viện), không sửa phương pháp sau khi xem test để ép khớp số.

## 3. Kết quả recourse — Table 3, PDF tr. 7

| Dataset | Model | Bị từ chối / toàn bộ | Không thể cải thiện / bị từ chối | Cải thiện bằng 1 feature / bị từ chối | Cần từ 2 feature / bị từ chối |
| --- | --- | ---: | ---: | ---: | ---: |
| HELOC | LR | 56,1% | 22,2% | 41,0% | 36,8% |
| HELOC | RF | 58,3% | 31,3% | 31,7% | 37,0% |
| HELOC | XGBoost | 57,0% | 53,1% | 25,3% | 21,6% |
| German | LR | 22,9% | 7,4% | 74,2% | 18,3% |
| German | RF | 17,5% | 28,6% | 48,0% | 23,4% |
| German | XGBoost | 22,0% | 11,8% | 68,2% | 20,0% |
| Give Me Some Credit | LR | 24,6% | 15,6% | 72,4% | 12,0% |
| Give Me Some Credit | RF | 24,7% | 0,2% | 93,2% | 6,6% |
| Give Me Some Credit | XGBoost | 24,8% | 11,5% | 76,0% | 12,5% |

Đây là thí nghiệm **RESP/recourse** của bài báo. Chạy lại AUC và SHAP additivity **không đủ** để khẳng định đã tái lập Table 3; cần thêm actionability constraints, reachable sets và audit như mã tác giả.

## 4. Kết quả giải thích dùng cho người B — Tables 4 và 12

CSV đầy đủ gồm LIME, SHAP, LIME-AW, SHAP-AW và RESP cho 3 dataset × 3 model. Hai mốc HELOC quan trọng:

| Nguồn | Model | Cách giải thích | Có ít nhất 1 feature responsive | Mọi feature responsive | Tỷ lệ được giải thích |
| --- | --- | --- | ---: | ---: | ---: |
| Table 4, tr. 8 | LR | SHAP | 22,7% | 0,0% | 100,0% |
| Table 4, tr. 8 | LR | SHAP-AW | 29,7% | 0,2% | 100,0% |
| Table 4, tr. 8 | LR | RESP | 100,0% | 100,0% | 41,0% |
| Table 4, tr. 8 | XGBoost | SHAP | 17,7% | 0,0% | 100,0% |
| Table 4, tr. 8 | XGBoost | RESP | 100,0% | 100,0% | 25,3% |
| Table 12, tr. 26 | RF | SHAP | 21,8% | 0,0% | 100,0% |
| Table 12, tr. 26 | RF | RESP | 100,0% | 100,0% | 31,7% |

Tác giả báo rằng với HELOC/LR, **77,3%** giải thích SHAP không nêu được feature responsive nào (Table 4). Đây là thước đo **khả năng hỗ trợ thay đổi quyết định**, không phải kiểm tra SHAP additivity. Phần B của nhóm cần báo riêng hai phép đo nếu có: (i) additivity của bản ghi, (ii) responsiveness nếu chạy lại reachable-set audit.

## 5. Thí nghiệm mở rộng của tác giả — Section 5, Tables 5/14

Section 5 dùng **Give Me Some Credit giữ feature liên tục**, huấn luyện XGBoost và lấy mẫu reachable set với `N=500` cho mỗi feature có thể thay đổi. PDF tr. 9–10 nêu 23.459 người bị dự đoán bất lợi và kết luận **dưới 7%** giải thích SHAP/LIME có ít nhất một feature vừa responsive, vừa monotonic, vừa intuitive; không có giải thích nào mà toàn bộ feature đồng thời thỏa cả ba điều kiện. **Table 14, PDF tr. 32:** XGBoost trên bản liên tục (n=120.268, d=11) có train AUC **0,937**, test AUC **0,830**. Không trộn kết quả này với Table 11 (bản rời rạc d=23).

## 6. Mẫu đối chiếu khi nhóm chạy lại

Tạo tệp kết quả riêng chứa ít nhất: `paper_commit`, `run_timestamp_utc`, `dataset`, `source_checksum`, `processed_checksum`, `n_rows`, `n_features`, `label_mapping`, `split_id`, `seed`, `train_n`, `test_n`, `model`, `hyperparameters`, `train_auc`, `test_auc`, `paper_test_auc`, `delta_test_auc`, `environment`, `notes`. Chỉ ghi số vào bảng sau khi chạy thật. Thứ tự: smoke German → full HELOC và so Table 11 → SHAP/recourse nếu triển khai → gắn audit blockchain; các kết quả B/C là phần mở rộng của nhóm và phải báo riêng.
