# Kế hoạch thực hiện cho ba người đến hạn nộp 04/12/2026

Tài liệu này là lịch nội bộ để ba thành viên và các agent họ sử dụng phối hợp trên cùng repository. Hạn nộp chính thức do nhóm cung cấp là **04/12/2026**; giờ đóng cổng nộp chưa được xác nhận. Mọi mốc có giờ trong tài liệu này là giờ Việt Nam (UTC+7). Nhóm cần xác nhận giờ nộp trên Moodle và chọn người nộp bản cuối.

## Trạng thái khởi đầu ngày 13/11/2026

Đã có báo cáo Tuần 3, đề cương, phương pháp S1–S11, [hợp đồng giao diện v1](interface_contract.md), khung `src/`, Vyper registry, SQLite, dữ liệu UCI Taiwan và một luồng smoke Taiwan LR → giải thích tuyến tính → bản ghi → Anvil → xác minh. Luồng smoke trả `VERIFIED`, bản ghi bị sửa trả `MISMATCH`; đây không phải kết quả E1–E7 chính thức. Home Credit, so sánh LR/RF/XGBoost, Streamlit, golden vectors đầy đủ và thí nghiệm B0/B1/B2 còn thiếu. File mới hiện chưa được commit; cần đưa bộ khung vào Git trước khi các thành viên tách nhánh.

## Phân công và file sở hữu

| Vai trò | Người phụ trách | File/thư mục sở hữu | Đầu ra chính |
| --- | --- | --- | --- |
| A — Dữ liệu và ML | Chưa gán tên | `src/credit_audit/data.py`, `src/credit_audit/ml.py`, `scripts/download_taiwan.py`, `scripts/taiwan_smoke.py`, `docs/data_contract.md`, `tests/test_data_ml.py` và script dữ liệu/ML mới | Hai pipeline độc lập, model artifact, metrics E1/E7, hàm `predict()` |
| B — Giải thích và bản ghi | Chưa gán tên | `src/credit_audit/records.py`, `src/credit_audit/storage.py`, `schemas/`, `tests/test_records.py` và test/storage/SHAP mới | `explain()`, `create_record()`, canonical bytes, golden vectors, SQLite, E2/E3 |
| C — Blockchain và UI | Chưa gán tên | `contracts/`, `src/credit_audit/chain.py`, `src/credit_audit/app.py`, `scripts/anvil_smoke.py`, test contract/e2e mới | Registry, Web3, Streamlit, verify và E4–E6 |

File chung `pyproject.toml`, `uv.lock`, `.gitignore`, `.env.example`, `README.md`, `docs/interface_contract.md` và báo cáo cuối chỉ được sửa qua một PR riêng với review của cả ba. Mỗi người làm trên nhánh riêng; không để nhiều agent sửa cùng một file. Agent được giao việc phải đọc hướng dẫn của vai trò mình và `docs/interface_contract.md` trước khi sửa code.

## Lịch và cổng nghiệm thu nội bộ

| Mốc | Hạn nội bộ | A | B | C | Điều kiện qua cổng |
| --- | --- | --- | --- | --- | --- |
| G0 — Chuẩn bị | 16/11, 20:00 | Kiểm kê schema/dữ liệu Taiwan, đề xuất đặc trưng Home Credit | Chốt JSON Schema, numeric rules, golden vector mẫu | Chốt ABI và mapping trạng thái | Ba người review giao diện v1; commit khung repo; CI cơ bản chạy được |
| G1 — Thành phần Taiwan | 20/11, 20:00 | LR/RF/XGBoost, validation và artifact Taiwan | SHAP tương thích artifact, SQLite và canonicalization tests | Contract role/revert/event tests, Web3 adapter | API của A/B/C nhận fixture chung; không cần UI hoàn chỉnh |
| G2 — Tích hợp | 25/11, 20:00 | Home Credit dữ liệu, split, mô hình ứng viên | Bản ghi và giải thích trên hai artifact; tamper tests | Streamlit, trạng thái PENDING/VERIFIED/MISMATCH/NOT_FOUND, luồng Anvil | Hồ sơ Taiwan chạy input → UI → chain → verify; Home Credit tối thiểu chạy inference độc lập |
| G3 — Thực nghiệm | 29/11, 20:00 | E1/E7 test metrics và phân tích lỗi | E2/E3 SHAP và sửa đổi B0/B1/B2 | E4/E5/E6 phân quyền, gas, latency, lỗi mạng | Kết quả thực đo, cấu hình và seed được lưu; không dùng số kỳ vọng thay số đo |
| G4 — Đóng gói | 02/12, 20:00 | Kiểm tra bảng/biểu đồ mô hình | Kiểm tra schema, hash, giới hạn diễn giải SHAP | Demo, README, triển khai local, tổng hợp báo cáo | CI xanh, demo từ môi trường sạch, báo cáo được cả ba đọc lại |
| Dự phòng và nộp | 03–04/12 | Sửa lỗi cuối | Sửa lỗi cuối | Chạy demo cuối và nộp | Xác nhận giờ đóng Moodle; nộp trước hạn 04/12 |

Nếu một mốc trễ, người phụ trách báo cho hai người còn lại ngay trong ngày: tên API/file bị ảnh hưởng, đầu ra vẫn dùng được, thời gian dự kiến và fixture tạm. Chỉ đổi hợp đồng giao diện sau khi cả ba đồng ý; nếu không, giữ v1 và đưa phần mở rộng sang version mới.

## Cách làm việc với agent

1. Mỗi người mở một cuộc trò chuyện agent riêng và dán prompt trong tài liệu vai trò tương ứng: [A](ROLE_A_DATA_ML.md), [B](ROLE_B_SHAP_RECORDS.md), [C](ROLE_C_CHAIN_UI.md).
2. Yêu cầu agent kiểm tra `git status` và đọc file được giao trước khi thay đổi. Không cho agent tự sửa phần của người khác; nếu cần, agent đề xuất một thay đổi giao diện bằng mô tả/PR riêng.
3. Mỗi lần bàn giao nêu commit/nhánh, lệnh chạy, test đạt/chưa đạt, artifact hoặc fixture được tạo, và vấn đề còn mở. Không commit dữ liệu gốc, model artifact, SQLite, `.env` hoặc private key.
4. Cùng dùng một manifest split và checksum nguồn cho mỗi dataset. A cung cấp artifact và schema feature; B cung cấp golden vectors và record fixture; C dùng các fixture đó trong e2e. Không tạo bản sao thủ công khác nhau của cùng một hợp đồng dữ liệu.

## Ranh giới báo cáo

Bản smoke hiện tại chỉ chứng minh luồng tích hợp kỹ thuật. Báo cáo cuối phải tách kết quả đã đo của nhóm khỏi kết quả tác giả khác và kỳ vọng trong đề cương; ghi rõ mẫu, split, seed, phiên bản, môi trường, số lần chạy và giới hạn của hash on-chain. Blockchain chỉ chứng minh tính nhất quán của bản ghi với cam kết, không chứng minh input đúng, mô hình công bằng hoặc SHAP có tính nhân quả.

