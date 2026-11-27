# Báo cáo người B về SHAP và bản ghi FICO HELOC

Người B thực hiện S7–S9 trên mô hình Logistic Regression FICO HELOC đã chốt của A. Kết quả dùng cho báo cáo Tuần 4 gồm kiểm tra SHAP trên toàn bộ tập test, thử độ nhạy với mẫu nền, đối chiếu hai cam kết khi bản ghi thay đổi và ba fixture để C đăng ký trên Anvil. [Đề cương](07_SuperBells_IS355_Proposal.md)

## Đầu vào từ A

Gói `artifacts/SuperBells_HELOC_XAI/` cung cấp mô hình LR, scaler đã fit, manifest, 4.674 hồ sơ train và 1.168 hồ sơ test theo fold `K05N01`, test fold 5, seed 2338. Mỗi hồ sơ có 43 đặc trưng sau bước tạo đặc trưng của tác giả. Hai cột `label` và `split_position` dùng để đối chiếu dữ liệu. Phiên bản mô hình là `cheon2025-fico-complex-nd-logreg-2338`, với SHA-256 `b9b7a30f8afaec886c9255527c966c25e105af599f0835206c1e91b79b31e654`. Script kiểm tra checksum, dữ liệu và thứ tự đặc trưng trước khi suy luận.

## S7 Tính và kiểm tra SHAP

Môi trường giữ scikit-learn 1.5.2 theo gói bàn giao. Script dùng cột xác suất của `Bad=-1` sau khi xác nhận thứ tự lớp `(-1, 1)`. Với LR nhị phân, margin mặc định hướng về lớp Good. Script đổi dấu hệ số, intercept và margin để giải thích Bad. Mẫu nền chính là đúng 100 vị trí lấy từ tập train do A cung cấp. Scaler đã fit được áp dụng cho cả mẫu nền và hồ sơ cần giải thích.

Với mỗi đặc trưng đã chuẩn hóa, đóng góp SHAP bằng hệ số của lớp Bad nhân với chênh lệch giữa đặc trưng của hồ sơ và giá trị trung bình của đặc trưng đó trong mẫu nền. Script kiểm tra `base_value + sum(SHAP)` khớp log-odds Bad và sigmoid của log-odds khớp `P(Bad)`, cùng dung sai `1e-6` trước khi làm tròn. Xác suất trên mọi dòng được đối chiếu với `p_bad_LR` của A. Hồ sơ test vị trí 0 còn được đối chiếu từng đóng góp với JSON mẫu.

Phép thử T2-01 chọn 40 hồ sơ test đầu và tạo các mẫu nền lồng nhau có kích thước 25, 50, 100 và 200 cho mỗi seed từ 2338 đến 2342. Phép thử xếp hạng theo trị tuyệt đối của SHAP, dùng tên đặc trưng để xử lý đồng hạng, rồi tính mức trùng của top 5 so với mẫu nền 200 dòng. SHAP ở đây mô tả đóng góp cục bộ trong mô hình LR, với mẫu nền cố định và trên thang log-odds Bad.

## S8 Tạo bản ghi và lưu SQLite

Mỗi hồ sơ tạo một bản ghi `fico_heloc_iclr2025` phiên bản 2, gồm xác suất, 43 đóng góp SHAP, giá trị nền, log-odds, phiên bản và checksum của mô hình, ID ngẫu nhiên và timestamp. Script kiểm tra bằng JSON Schema v2, lưu JSON hiển thị cùng canonical bytes dạng BLOB rồi đọc lại để kiểm tra cả nội dung lẫn hai hash. Bản ghi dùng tham chiếu đầu vào ngẫu nhiên. Vị trí test chỉ nằm trong đầu ra đối chiếu của lần chạy.

## S9 Tính cam kết và bàn giao

- `record_hash = SHA256(canonical_bytes)`
- `model_version_hash = SHA256(UTF8(model_version + "|" + model_artifact_sha256))`

B kiểm tra ba hồ sơ trước các kịch bản sửa xác suất, sửa một đóng góp SHAP, sửa phiên bản mô hình, sửa riêng JSON hiển thị, sửa riêng canonical bytes và sửa đồng thời bản ghi với hash local. Mỗi hồ sơ có một ca gốc làm đối chứng. B0 mô phỏng không có cam kết, B1 so với hash local và B2 đối chiếu với cam kết gốc giữ độc lập. Kết quả này đo logic đối chiếu off-chain. C chạy giao dịch và ghi kết quả xác minh trên Anvil.

## Kết quả thực đo

| Kiểm tra | Kết quả |
| --- | --- |
| Xác minh đầu vào và mẫu A | 20/20 checksum khớp. Kết quả tính lại của 43 đóng góp ở vị trí 0 khớp mẫu của A trong dung sai `1e-10`. |
| SHAP trên tập test | 1.168 hồ sơ × 43 đóng góp. Sai số cộng lớn nhất `1.3323e-15` và sai số sigmoid lớn nhất `1.6653e-16`. Tất cả dưới `1e-6`. |
| Đối chiếu dự đoán của A | Chênh lệch tuyệt đối lớn nhất `3.0531e-16` trên toàn bộ tập test. |
| SQLite và schema | 1.168/1.168 bản ghi đạt schema v2, đọc lại đúng canonical bytes và tái tính đúng hai mã băm. Cơ sở dữ liệu có 1.168 decision ID riêng, trạng thái ban đầu `PENDING`. |
| T2-01 độ nhạy mẫu nền | 20 cấu hình và 800 lượt giải thích. Với 100 so với 200 dòng, trung vị top-5 overlap là **1,00** và khoảng quan sát **0,80–1,00**, đạt ngưỡng trung vị 0,60. Sai số cộng lớn nhất trong 800 lượt là `1.7764e-15`. |
| E3 mô phỏng off-chain | B0 phát hiện 0/18 ca sửa, B1 phát hiện 15/18, đối chiếu với cam kết độc lập phát hiện 18/18. Cả ba phương án có 0/3 cảnh báo sai. Ba ca B1 bỏ sót là khi cả bản ghi và hash local được cập nhật cùng nhau. |
| Hồi quy | 4/4 unit test đạt, gồm test byte chuẩn hóa cố định cho HELOC v2 và test tương thích Taiwan v1. |

| Vị trí test | P(Bad) | Log-odds Bad |
| ---: | ---: | ---: |
| 0 | 0,75638247 | 1,13294768 |
| 1 | 0,31828327 | −0,76167245 |
| 2 | 0,65212606 | 0,62839770 |

Ở vị trí 0, hai đóng góp dương lớn nhất lần lượt là `AvgYearsInFile_geq_5` và `ExternalRiskEstimate_geq_70`. Trên cả tập test, ba tên đứng đầu theo trung bình trị tuyệt đối SHAP là `ExternalRiskEstimate_geq_70` (0,2671), `NetFractionRevolvingBurden_geq_50` (0,2192) và `AvgYearsInFile_geq_7` (0,1824). Kết quả phản ánh mô hình, phép chia và mẫu nền đã dùng.

## File đầu ra

Các kết quả của lần chạy nằm trong `artifacts/role_b_heloc/`.

| File | Nội dung |
| --- | --- |
| `summary.json` và `shap_metrics.csv` | Cấu hình, sai số và cam kết để đối chiếu theo từng hồ sơ. |
| `audit.sqlite3` | Toàn bộ 1.168 bản ghi với canonical bytes. |
| `shap_local_position_0.png`, `shap_global.png` và `shap_global.csv` | Biểu đồ mẫu cục bộ và thống kê tổng hợp trên tập test. |
| `background_sensitivity.csv` và `background_sensitivity_summary.csv` | Kết quả chi tiết cho 800 lượt giải thích và thống kê theo seed, kích thước mẫu nền. |
| `integrity_checks.csv` | Kết quả đối chiếu sáu ca sửa và một ca sạch trên mỗi fixture. |
| `handoff/position-0` đến `handoff/position-2` | Ba fixture thực đã kiểm tra theo định dạng đầu vào của script Anvil. Gói `artifacts/role_b_heloc_handoff.zip` chứa ba fixture và báo cáo này. |

## Cách chạy lại

Chạy từ thư mục gốc dự án và chọn một thư mục đầu ra mới cho mỗi lần chạy. Mỗi lần tạo các decision ID mới. Sau khi có môi trường Python 3.10, chạy:

```powershell
python -m venv artifacts/.venv-role-b
artifacts/.venv-role-b/Scripts/python.exe -m pip install -r artifacts/SuperBells_HELOC_XAI/requirements.txt jsonschema==4.26.0 matplotlib==3.10.9
$env:PYTHONPATH = 'src'
$env:MPLCONFIGDIR = (Join-Path (Resolve-Path artifacts) '.matplotlib-role-b')
artifacts/.venv-role-b/Scripts/python.exe scripts/role_b_heloc.py --output artifacts/role_b_heloc
python -m pytest -q
```

Khi chuyển cho C, dùng các thư mục `handoff/position-0`, `position-1` và `position-2` từ cùng lần chạy. Mỗi thư mục có SQLite, canonical JSON và summary chứa decision ID cùng hai mã băm. Tên `taiwan_smoke_summary.json` được giữ để tương thích với script Anvil có sẵn. Trường dataset bên trong dùng ID HELOC.

C mở Anvil local ở cổng 8545, chain ID 31337, rồi chạy với từng fixture:

```powershell
uv run python scripts/anvil_smoke.py --artifact-dir artifacts/role_b_heloc/handoff/position-0
```

Kỳ vọng bản gốc `VERIFIED` và bản sao bị sửa `MISMATCH`. Mỗi lượt lưu `anvil_smoke_summary.json` trong thư mục fixture. Nếu giải nén gói bàn giao vào vị trí khác, truyền đường dẫn tương ứng vào `--artifact-dir`.
