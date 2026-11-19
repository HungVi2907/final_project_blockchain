# Bàn giao A → B: FICO HELOC và model ICLR 2025

**Trạng thái:** dữ liệu và ba model đã chạy Table 11, sẵn sàng cho B dùng làm đầu vào SHAP. Nguồn code tác giả khóa tại commit `4c68c73b34eef7c5e38847274048cb3ab66d702c`, thư mục làm việc `artifacts/cheon_iclr2025/research/iclr2025/`. Bản clone/artifact được giữ trong `artifacts/`, không đưa vào Git.

## Dataset và quy ước đầu vào

- Dataset chính: FICO HELOC theo pipeline của tác giả, `data/fico/fico_data.csv`; SHA-256 `65cf152304303b80c26c33808f7c2400e9b77f9222cc8160213d6893b11ee2a4`. Bản đầu vào có 10.459 dòng × 24 cột (nhãn `RiskPerformance` + 23 biến), không có missing. File processed của tác giả sau setup: 5.842 dòng × 43 feature; train/test 4.674/1.168 theo fold `K05N01`.
- Dùng xử lý của tác giả trong `experiment/setup_dataset_actionset_fico.py` và feature schema của action set `fico_complex_nD`; không tự suy feature order từ 23 cột CSV vì pipeline tạo 43 feature sau xử lý.
- Chiều nhãn: `RiskPerformance=1` là Good, `0` là Bad. Khi B tạo record, `risk_probability` phải là `P(Bad) = 1 - P(Good)`. Xác suất lớp 1 của model tác giả là `P(Good)`; không ghi trực tiếp nó thành risk.
- Không đưa `RiskPerformance`, ID hồ sơ nguồn, hay thông tin định danh vào SHAP feature values hoặc decision record. Bản ghi chỉ cần input reference đã băm theo hợp đồng chung.

## Model artifacts A bàn giao

Các file là pickle/dill của mã tác giả, cần load trong môi trường đã khóa ở nhật ký tái lập; chỉ load artifact từ clone/commit tin cậy. Bảng dưới ghi SHA-256 để kiểm tra đúng file.

| Model | Artifact tương đối từ `research/iclr2025/` | Test AUC chạy lại | SHA-256 |
|---|---|---:|---|
| LR | `results/fico_complex_nD_logreg_processed.model` | 0,7775 | `b9b7a30f8afaec886c9255527c966c25e105af599f0835206c1e91b79b31e654` |
| XGBoost | `results/fico_complex_nD_xgb_processed.model` | 0,7903 | `59275ee1e51dd2c2cbd5834d9c330ed32b7f388ff4f1475d6a3dbf2ccc004e24` |
| RF | `results/fico_complex_nD_rf_processed.model` | 0,7866 | `37b1a5247efd4b879feb5aec865b92a1857b13e06dc82280a21cc7e37ea47718` |

Đề xuất B bắt đầu với **LR** để xác nhận output mapping, SHAP additivity và canonical record; sau khi pipeline ổn định có thể chạy thêm XGBoost/RF. Đây là thứ tự smoke cho phần B, không phải chọn model tốt nhất theo AUC. So sánh AUC với số gốc và sai khác được lưu trong [nhật ký tái lập](references/CHEON_2025_REPLICATION_LOG.md) và [CSV](references/CHEON_2025_REPLICATION_COMPARISON.csv).

## Điều B cần làm để tích hợp

1. Đọc ba model từ `artifacts/cheon_iclr2025/research/iclr2025/results/`; dùng đúng pipeline/scaler và thứ tự 43 feature từ action set của tác giả. LR lưu `Pipeline(scaler, clf)`; XGBoost/RF lưu estimator và scaler tách riêng trong object đã serialize.
2. Tính và ghi rõ SHAP trong output space nhất quán với `risk_probability=P(Bad)`. Kiểm tra additivity trước làm tròn. Nếu explainer tính SHAP cho `P(Good)`, phải chuyển toàn bộ output/background/contributions nhất quán sang `P(Bad)` hoặc giải thích trực tiếp lớp Bad.
3. Thêm `fico_heloc` vào enum/schema và API qua version/migration có review; hiện `decision_record_v1.schema.json` chỉ cho phép Taiwan/Home Credit nên chưa thể ghi record FICO bằng schema hiện tại.
4. Gửi fixture đã ẩn thông tin định danh cho C, kèm `dataset_id`, `model_version`, hash artifact, `risk_probability`, SHAP values và cách canonicalize. Không gửi toàn bộ hồ sơ cá nhân cho chain.

## Bằng chứng liên quan

- [Kết quả gốc được trích từ bài](references/CHEON_2025_ORIGINAL_RESULTS.md)
- [Nhật ký môi trường, dữ liệu và chênh lệch](references/CHEON_2025_REPLICATION_LOG.md)
- [Hợp đồng dữ liệu hiện hành](data_contract.md)
- [Hướng dẫn người B](ROLE_B_SHAP_RECORDS.md)
