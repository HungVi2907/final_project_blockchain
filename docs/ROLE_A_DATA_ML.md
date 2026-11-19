# Người A — dữ liệu, tái thực nghiệm ICLR 2025 và mô hình

**Người thực hiện hiện tại:** người dùng. **Bài tham khảo chính:** Cheon et al., *Feature Responsiveness Scores: Model-Agnostic Explanations for Recourse* (ICLR 2025). Đọc [bối cảnh hiện hành](PROJECT_CONTEXT.md), [data contract](data_contract.md), [giao diện](interface_contract.md) và [kế hoạch ba người](TEAM_3_PERSON_EXECUTION_GUIDE.md). Hạn nộp nhóm được ghi là 04/12/2026; các mốc nội bộ cần điều chỉnh theo tiến độ thực tế.

## Mục tiêu

Tái lập **phần dự đoán tín dụng của tác giả trước**, rồi mới bàn giao model cho B tính SHAP và C tích hợp chain. Dữ liệu chính cho luồng tích hợp là FICO HELOC; German Credit dùng để smoke, Give Me Some Credit để kiểm tra trên tập lớn. Mô hình cần đối chiếu là Logistic Regression, XGBoost và Random Forest. Kết quả chuẩn là **Table 11, Appendix B.4** của [PDF ICLR](references/Cheon_2025_ICLR_Feature_Responsiveness_Scores.pdf), không phải số liệu Taiwan/Home Credit của bài PLOS cũ.

**Tiến độ 19/11/2026:** đã lưu [số liệu gốc](references/CHEON_2025_ORIGINAL_RESULTS.md), smoke German/LR và chạy đủ 9 tổ hợp của Table 11 trên ba dataset; [nhật ký và bảng so sánh](references/CHEON_2025_REPLICATION_LOG.md) ghi AUC, chênh lệch và điểm bất thường Give Me Some Credit/XGBoost. Các bước 1–3 dưới đây đã có kết quả; việc tiếp theo là điều tra sai khác đó và bàn giao artifact HELOC cho B theo bước 4–5.

## Việc cần làm theo thứ tự

1. Ghi commit SHA của [repo tác giả, nhánh `paper/iclr2025`](https://github.com/ustunb/responsiveness/tree/paper/iclr2025), phiên bản phụ thuộc, URL/checksum dữ liệu và quyền sử dụng. Kiểm tra EDA trên dữ liệu thật: số dòng, phân bố lớp, missing, giá trị đặc biệt, đặc trưng đầu vào; đối chiếu 5.842/1.000/120.268 dòng sau xử lý mà bài báo nêu. Không dùng dữ liệu giả lập để báo kết quả chính.
2. Chạy smoke **German Credit** theo script `setup_dataset_actionset_german.py` và `train_models.py`; kiểm tra split 80/20, `fold_id=K05N01`, seed 2338 và hướng nhãn trong mã. Ghi lệnh, thời gian, lỗi phiên bản và AUC thực đo. Smoke chỉ xác nhận pipeline chạy, chưa phải bảng tái lập đầy đủ.
3. Chạy full **FICO HELOC** cho LR/XGBoost/RF theo mã và cấu hình tác giả, không tự đổi feature engineering hoặc tuning trong lần so sánh đầu. Đối chiếu test AUC lần lượt **0,788 / 0,785 / 0,790**; ghi chênh lệch, số dòng, split, preprocessing và hyperparameters. Nếu cần điều chỉnh để chạy trên môi trường hiện tại, ghi rõ từng thay đổi trước khi diễn giải sai khác.
4. Khóa artifact HELOC được chọn cho luồng nhóm: preprocessing, thứ tự feature, model, phiên bản, nguồn/split manifest và SHA-256. Bàn giao API `predict()` cùng ít nhất một fixture HELOC hợp lệ cho B/C. Sau đó mới thực hiện SHAP/B và chain/C. Give Me Some Credit đã được chạy lại trong bảng đối chiếu độc lập.
5. Đối với bản ghi nhóm, giữ đúng quy ước `risk_probability=P(Bad/default)`. **Mã FICO tác giả dùng `Good=1`, `Bad=0`**; vì vậy adapter phải đổi `P(Bad)=1-P(Good)` sau khi đã đo AUC theo đúng nhãn tác giả. B phải giải thích đúng xác suất risk được ghi trong record; kiểm tra mapping nhãn từng dataset riêng.

## Tiêu chí bàn giao

- EDA, checksum, commit SHA, seed/fold và lệnh chạy được ghi, split train/test không giao nhau; transform có học tham số chỉ fit trên train.
- Bảng so **AUC tác giả / AUC nhóm / chênh lệch**, không gộp số liệu các tập dữ liệu; số chưa chạy ghi “chưa chạy”.
- Artifact load lại cho cùng prediction; `risk_probability` và chiều nhãn đã được kiểm tra bằng ví dụ Good/Bad. Model version và hash artifact đi vào bản ghi qua B.
- Hợp đồng `dataset_id`/schema được nâng nhất quán trước khi tạo record HELOC. Mã hiện có chỉ hỗ trợ Taiwan LR smoke; không đổi tên dataset để giả làm replication ICLR.

## File phụ trách

`src/credit_audit/data.py`, `src/credit_audit/ml.py`, script dữ liệu/train/evaluate mới, `docs/data_contract.md`, `tests/test_data_ml.py` và ghi chú tái lập ICLR. `records.py`, `storage.py`, `chain.py`, `contracts/`, `schemas/` và UI là phần B/C hoặc file chung, cần phối hợp khi sửa API. Không commit dữ liệu gốc, artifact, SQLite hay khóa bí mật.
