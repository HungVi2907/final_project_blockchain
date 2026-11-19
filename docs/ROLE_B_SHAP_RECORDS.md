# Context người B — SHAP, bản ghi và SQLite

**Cập nhật 19/11/2026.** B phụ trách S7–S9, SQLite và thí nghiệm E2/E3. Tập chính của luồng A → B → C là **FICO HELOC** theo Cheon et al. (ICLR 2025). Nhóm dùng SHAP, một baseline giải thích trong bài, để tạo bản ghi kiểm toán off-chain. Phạm vi hiện tại gồm phần dự đoán Table 11 đã chạy lại và phần kiểm toán do nhóm phát triển. RESP và các thí nghiệm chất lượng giải thích của bài chưa được tái lập. [Bối cảnh nghiên cứu](PROJECT_CONTEXT.md) · [Nhật ký tái thực nghiệm](references/CHEON_2025_REPLICATION_LOG.md)

**Người phụ trách:** Chưa gán tên. **Hạn nộp:** 04/12/2026, giờ đóng Moodle chưa xác nhận. Các mốc nội bộ dùng giờ Việt Nam. [Kế hoạch nhóm](TEAM_3_PERSON_EXECUTION_GUIDE.md)

## Trạng thái ngày 19/11

| Hạng mục | Trạng thái |
| --- | --- |
| Bàn giao từ A | Nhật ký ghi nhận đã huấn luyện LR, XGBoost và RF trên HELOC, với 43 feature sau xử lý, train/test 4.674/1.168, fold `K05N01`, seed 2338. Tài liệu bàn giao có tên file, checksum và môi trường. Thư mục model trong `artifacts/` chưa có trong workspace tại thời điểm kiểm tra. B cần nhận file từ A hoặc dựng lại theo nhật ký và đối chiếu checksum với manifest tương ứng. [Bàn giao A → B](A_TO_B_HANDOFF_HELOC.md) |
| SHAP | Bản smoke Taiwan LR có công thức SHAP tuyến tính trong log-odds với 200 mẫu nền từ train, đặt ngay trong script smoke. Chưa có `explain.py`, SHAP HELOC hay kết quả E2. Tài liệu trước ghi nhận Windows Application Control chặn DLL Numba khi import `shap`; dùng môi trường tương thích nếu lỗi lặp lại. |
| Bản ghi và SQLite | Đã có `create_record()`, `canonical_serialize()`, `commitments()`, bảng `decisions` lưu JSON hiển thị và canonical bytes dạng BLOB, cùng hai unit test. Còn thiếu golden vectors cố định, migration có phiên bản, retry idempotent và ma trận E3. |
| Giao diện HELOC | Schema và validation v1 hiện chỉ nhận `taiwan_uci350` và `home_credit_2018`. ID mục tiêu là `fico_heloc_iclr2025`; cần A/B/C duyệt phiên bản schema/API và xác nhận tương thích trước khi lưu record HELOC. Dùng Taiwan làm fixture hồi quy v1. [Hợp đồng giao diện](interface_contract.md) |

## Đầu vào A → B

1. Xác minh SHA-256 của file model trước khi load từ nguồn tin cậy. Dùng đúng môi trường và pipeline của A. Lấy tên và thứ tự 43 feature từ action set `fico_complex_nD`. LR đóng gói scaler trong pipeline; RF/XGBoost dùng scaler đi kèm artifact. Áp dụng cùng cách tiền xử lý cho hồ sơ và tập nền, mỗi bước đúng một lần. [Bàn giao A → B](A_TO_B_HANDOFF_HELOC.md)
2. Trong CSV, `RiskPerformance` có `Good=1`, `Bad=0`. Dữ liệu sau setup trong nhật ký ghi `Good=+1`, `Bad=-1`. Kiểm tra `classes_` và mapping của từng estimator trong artifact rồi mới chọn cột xác suất. Giá trị trong record luôn là `risk_probability = P(Bad) = 1 - P(Good)`. [Hợp đồng dữ liệu](data_contract.md) · [Nhật ký tái thực nghiệm](references/CHEON_2025_REPLICATION_LOG.md)
3. Bắt đầu với LR để xác nhận mapping, additivity và tạo fixture; sau đó đánh giá explainer cho RF/XGBoost. Dùng tập nền chỉ lấy từ train, khóa cách lấy mẫu và seed. Ghi tên explainer, phiên bản thư viện, kích thước tập nền và `output_space` cho mỗi lần chạy.

## Tính SHAP và tạo bản ghi

- Với `output_space="probability"`, nếu explainer trả SHAP cho `P(Good)`, đổi `base_value` thành `1 - base_value`, đổi dấu từng contribution và dùng `P(Bad)` làm `model_output`. Kiểm tra `model_output` khớp với `risk_probability` trước khi làm tròn.
- Với LR trong `output_space="raw"`, nếu margin là log-odds Good, đổi dấu margin, base value và từng contribution để giải thích log-odds Bad. Kiểm tra additivity với margin Bad và kiểm tra sigmoid của margin Bad khớp `risk_probability`.
- Kiểm tra mọi giá trị hữu hạn và `abs(base_value + sum(contributions) - model_output) <= 1e-5` trước khi làm tròn, theo dung sai hiện có trong `create_record()`. Lưu đủ 43 contribution theo schema feature, kể cả giá trị bằng 0. Sai mapping, additivity hoặc schema phải chặn tạo bản ghi và đăng ký on-chain.
- Lưu `model_version`, `model_artifact_sha256`, SHAP và xác suất trong record. Tạo `input_reference` ngẫu nhiên theo hợp đồng. Chỉ gửi cho C fixture đã loại thông tin định danh, canonical UTF-8 bytes, `decision_id`, `record_hash` và `model_version_hash`. Hai hash được tính theo công thức trong [hợp đồng giao diện](interface_contract.md).

## Mốc thực hiện và nghiệm thu

| Mốc, 20:00 UTC+7 | Đầu ra của B |
| --- | --- |
| G0 · 20/11 | Chốt dataset ID, mapping risk và cách nâng schema với A/C. Chốt golden vector với timestamp, ID và nonce cố định, canonical bytes và hai hash dự kiến. Bao phủ NFC, làm tròn half-even, chuẩn hóa `-0.00000000`, feature trùng và input sai định dạng. |
| G1 · 25/11 | Chuẩn bị `explain(artifact, transformed_features)`, chạy smoke LR khi có artifact, kiểm tra canonicalization và SQLite. Gửi fixture nhân tạo cho C nếu artifact hoặc schema HELOC còn chờ. |
| G2 · 29/11 | Tạo bản ghi HELOC sau khi schema được duyệt. Kiểm tra round-trip JSON/BLOB, migration dữ liệu cũ, metadata giao dịch và retry giữ nguyên decision ID. Bàn giao fixture để C chạy HELOC → Anvil → verify. |
| G3 · 02/12 | E2 ghi số mẫu, số feature, output space, residual trước làm tròn và số mẫu vượt ngưỡng; xuất biểu đồ local/global. E3 phối hợp với C chạy B0 (SQLite), B1 (SQLite + hash local), B2 (cam kết on-chain). |
| G4 · 02/12 | Chạy lại golden vectors, test schema/migration và kiểm tra fixture Anvil. Bàn giao số đo cùng cấu hình chạy, phiên bản và giới hạn diễn giải SHAP. |

Trong E3, kiểm tra riêng thay đổi probability, contribution, model version, JSON hiển thị và canonical bytes. Kiểm tra cả trường hợp sửa record rồi tính lại hash local. Với B2 đã xác nhận, nội dung lệch cam kết phải trả `MISMATCH`; fixture sạch phải trả `VERIFIED` sau khi đủ xác nhận và khớp cả hai hash. Ghi số phát hiện và báo động sai theo từng phương án. [Thiết kế thực nghiệm](IMPLEMENTATION_READINESS_VI.md)

## Chạy thử với dữ liệu nhỏ và bàn giao cho C

1. **B tạo dữ liệu thử.** Dùng 4 dòng nền, 1 hồ sơ và 2 feature giả lập. Áp dụng mô hình logistic với hệ số cố định rồi tính SHAP tuyến tính trong log-odds. Đây là fixture tương thích schema v1 với ID `taiwan_uci350`. Trường `synthetic: true` trong summary đánh dấu nguồn dữ liệu giả lập.
2. **B xác minh và bàn giao.** Chạy từ thư mục gốc dự án. Kết quả dự kiến là `risk_probability=0.77729986`, đầu ra log-odds `1.25` và residual `0`. Script kiểm tra canonical bytes và hai commitment sau khi đọc lại từ SQLite.

   ```powershell
   uv run python scripts/role_b_smoke.py
   ```

   B gửi thư mục `artifacts/role_b_smoke/` cho C. Script Anvil đọc `audit.sqlite3` và `taiwan_smoke_summary.json` (chứa decision ID và hai hash). `decision_record.json` chứa canonical bytes và `model.json` chứa hệ số mô hình để đối chiếu hash artifact. Mỗi lần B chạy lại sẽ tạo decision ID và record hash mới. C dùng các file từ cùng một lần chạy để đối chiếu.

3. **C chạy Anvil.** Mở Anvil local ở chain ID `31337`, RPC `http://127.0.0.1:8545`, rồi chạy lệnh dưới. Nếu C chỉ cần một fixture mới, có thể tự chạy bước 2.

   ```powershell
   uv run python scripts/anvil_smoke.py --artifact-dir artifacts/role_b_smoke
   ```

   Kỳ vọng `VERIFIED` với bản ghi gốc, `MISMATCH` với bản sao bị sửa và tài khoản ngoài quyền writer bị từ chối. C gửi lại `artifacts/role_b_smoke/anvil_smoke_summary.json` có trạng thái xác minh, transaction hash và gas đã dùng.

## Phạm vi file và prompt cho agent của B

B phụ trách `src/credit_audit/explain.py`, `src/credit_audit/records.py`, `src/credit_audit/storage.py`, `schemas/` và test/fixture SHAP, record, storage. Phối hợp A/C khi thay đổi giao diện chung.

```text
Bạn phụ trách vai trò B (SHAP, bản ghi, SQLite) của dự án Super Bells. Đọc docs/ROLE_B_SHAP_RECORDS.md, docs/A_TO_B_HANDOFF_HELOC.md, docs/interface_contract.md và docs/TEAM_3_PERSON_EXECUTION_GUIDE.md. Kiểm tra git status và sự hiện diện của artifact trước khi làm mốc gần nhất chưa đạt. Bắt đầu với HELOC LR theo fold K05N01. Xác minh checksum, feature order và mapping của estimator. Kiểm tra additivity trước làm tròn trong đúng output space. Gửi đề xuất schema/API cho A/C review trước khi tích hợp HELOC. Dùng fixture nhân tạo để kiểm tra phần độc lập nếu artifact còn chờ. Giữ dữ liệu gốc, model, SQLite và bí mật ngoài Git. Khi bàn giao, ghi file đã sửa, lệnh test, số đo, fixture/API cho C, phần còn vướng và mốc tiếp theo. Diễn giải SHAP theo đầu ra mô hình và tập nền đã dùng.
```
