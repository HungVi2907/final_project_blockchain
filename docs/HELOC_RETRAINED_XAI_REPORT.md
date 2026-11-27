# XAI và kiểm toán XGBoost HELOC huấn luyện lại

## Phạm vi và nguồn

Kết quả dùng gói `artifacts/SuperBells_HELOC_XAI_v1_Retrained.zip`, model `models/XGB.joblib`, SHA-256 `301e7b873bedf8e4f932f72a04d2c2f40bfbdb9ae5347b8dfc7d1d26297bc5fd`. Không huấn luyện lại mô hình. Tất cả 17 checksum có trong manifest của gói khớp khi kiểm tra. Nhãn Bad = 1; ngưỡng đã chọn trên validation là 0,43248084. Test fold 5 gồm 1.168 hồ sơ, đã được dùng trong lần tái thực nghiệm trước của dự án.

## Phương pháp và kết quả XAI

Dùng XGBoost 2.1.4, `Booster.predict(pred_contribs=True, approx_contribs=False)`: TreeSHAP chính xác theo tree-path-dependent. Giá trị nền được tính từ thống kê độ bao phủ các nhánh trong mô hình; **không dùng 100 dòng `xai_background.csv`** trong phương pháp này. Giải thích đầu ra raw log-odds của lớp Bad, không phải xác suất; sigmoid của đầu ra raw cho xác suất Bad.

Đã tính đóng góp của 43 đặc trưng cho toàn bộ 1.168 hồ sơ test. Sai số lớn nhất giữa tổng SHAP cộng giá trị nền và đầu ra raw là 5,96 × 10⁻⁷; sai số lớn nhất giữa sigmoid và xác suất mô hình là 0; chênh lệch tối đa so với xác suất test đã lưu là 5,56 × 10⁻¹⁷.

Năm đặc trưng có trung bình trị tuyệt đối đóng góp SHAP lớn nhất trên tập test:

| Đặc trưng | Mean absolute SHAP (log-odds) |
| --- | ---: |
| ExternalRiskEstimate_geq_70 | 0,4568 |
| NetFractionRevolvingBurden_geq_50 | 0,1791 |
| NoDelqEver | 0,1357 |
| ExternalRiskEstimate_geq_80 | 0,1286 |
| AvgYearsInFile_geq_7 | 0,0991 |

Đây là độ lớn ảnh hưởng trung bình theo mô hình và phương pháp nền đã chọn, không biểu thị chiều ảnh hưởng chung hay quan hệ nhân quả. Các đặc trưng ngưỡng có thể phụ thuộc nhau; diễn giải cần thận trọng.

## Pilot kiểm toán Anvil

Chọn hồ sơ đầu tiên theo thứ tự test ở mỗi nhóm sau; đây là ví dụ kiểm thử, không phải mẫu đại diện thống kê. Mỗi hồ sơ được ghi vào SQLite, neo hai commitment lên một hợp đồng Anvil riêng và đối chiếu lại. Bản sao bị thay đổi xác suất và tính lại canonical bytes nhưng không thay đổi commitment on-chain.

| Nhóm | source_position | P(Bad) | Gốc | Bản sao sửa | Gas | Xác nhận local |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| Bad dự đoán đúng | 0 | 0,70445 | VERIFIED | MISMATCH | 93.507 | 469,155 ms |
| Bad bị bỏ sót | 1 | 0,33900 | VERIFIED | MISMATCH | 93.507 | 464,604 ms |
| Good bị báo nhầm | 4 | 0,50162 | VERIFIED | MISMATCH | 93.495 | 460,668 ms |

Gas và thời gian chỉ thuộc các giao dịch thử nghiệm cục bộ này. Kiểm tra hash chỉ xác minh bản ghi khớp commitment; không chứng minh dữ liệu, mô hình hay giải thích là đúng. Các phép thử B0/B1/B2 có đối chứng, phân quyền có hệ thống và Sepolia chưa được thực hiện ở đây.

## Tệp kết quả

- `artifacts/heloc_retrained_xai/summary.json`: phương pháp, checksum và sai số kiểm tra.
- `artifacts/heloc_retrained_xai/global_importance.csv`: mức độ đóng góp trung bình tuyệt đối của 43 biến.
- `artifacts/heloc_retrained_xai/test_shap.csv`: đóng góp, nhãn và dự đoán của từng hồ sơ test.
- `artifacts/heloc_retrained_xai/examples.json`: ba ví dụ chi tiết để tạo bản ghi.
- `artifacts/heloc_retrained_audit/`: bản ghi JSON, SQLite, receipt và summary của ba thử nghiệm. Anvil là chuỗi tạm thời; nếu phiên node kết thúc, cần chạy lại để xác minh trực tuyến, không chỉ dùng receipt cũ.

Các tệp trong `artifacts/` bị Git ignore và cần được bàn giao riêng nếu muốn chia sẻ. Thứ tự biến và `source_position` chỉ có ý nghĩa trong tập test nguồn. Không chia sẻ các tệp cấp hồ sơ nếu không phù hợp với chính sách dữ liệu của nhóm.

## Tái lập

Giải nén ZIP vào một thư mục mới. Tạo môi trường Python 3.10 và cài `requirements.txt` trong gói. Dùng các đường dẫn mới chưa tồn tại cho output:

```powershell
uv venv tmp/xai_retrained_env --python 3.10
uv pip install --python tmp/xai_retrained_env/Scripts/python.exe -r tmp/review_retrained_20261127/heloc_standard_v1/requirements.txt
tmp/xai_retrained_env/Scripts/python.exe scripts/explain_retrained_heloc.py --bundle tmp/review_retrained_20261127/heloc_standard_v1 --output artifacts/heloc_retrained_xai_rerun
```

Khởi động Anvil local chain ID 31337 tại port 18545, rồi dùng môi trường dự án chính:

```powershell
.venv/Scripts/python.exe scripts/audit_retrained_heloc.py --examples artifacts/heloc_retrained_xai_rerun/examples.json --output artifacts/heloc_retrained_audit_rerun --port 18545
```

Khi node còn chạy, có thể xem một bản ghi với dashboard hiện có bằng cách đặt `CREDIT_AUDIT_PILOT_DIR` trỏ đến thư mục con tương ứng và chạy `streamlit run scripts/heloc_pilot_dashboard.py`. Mỗi lần chạy mới tạo ID, nonce, giao dịch và thời gian mới; các giá trị này không cố định.
