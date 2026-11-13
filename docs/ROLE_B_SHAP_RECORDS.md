# Hướng dẫn cho người B — SHAP, bản ghi và SQLite

**Người phụ trách:** Chưa gán tên. **Hạn nộp chính thức:** 04/12/2026 (giờ Moodle chưa rõ). Lịch nội bộ ở [kế hoạch chung](TEAM_3_PERSON_EXECUTION_GUIDE.md), giờ UTC+7.

## Mục tiêu và phạm vi

Bạn sở hữu S7–S9, lưu trữ SQLite, E2/E3: giải thích local SHAP cho artifact của A, kiểm tra additivity trước làm tròn, tạo `R`, canonical UTF-8 bytes, hai SHA-256 commitment, golden vectors và kiểm thử sửa đổi. Cần hỗ trợ cả hai dataset nhưng không huấn luyện/chọn model. Theo [giao diện v1](interface_contract.md), `risk_probability` là `predict_proba` lớp 1; SHAP `model_output` có thể là raw margin hoặc probability nhưng phải ghi `output_space` và kiểm tra trong đúng không gian.

File sở hữu: `src/credit_audit/records.py`, `src/credit_audit/storage.py`, `schemas/`, `tests/test_records.py` và file `src/credit_audit/explain.py`, test/fixture mới của B. Không sửa data/ML, Vyper, Web3, UI. Thay đổi file chung cần review A/C.

## Trạng thái đang có

Đã có `canonical_serialize`, `create_record`, SQLite bảng `decisions`, JSON Schema v1 và hai unit test cơ bản. Bản smoke LR dùng công thức SHAP tuyến tính trong log-odds với 200 hàng nền train; residual đã kiểm tra gần 0. Thư viện `shap` cài được nhưng Windows Application Control chặn DLL Numba khi import; cần chuyển tác vụ đó sang WSL/Linux hoặc tìm cấu hình runtime hợp lệ. Chưa có golden vector cố định đủ chuẩn, migration có version, hỗ trợ đầy đủ RF/XGBoost hoặc ma trận E2/E3.

## Việc cần làm theo thứ tự

1. **Đến G0 — 16/11, 20:00:** Review `schemas/decision_record_v1.schema.json` với A/C. Chốt xử lý Unicode NFC, float → chuỗi 8 chữ số half-even, negative zero, timestamp/nonce, optional/null, duplicate feature và lỗi input. Tạo golden vectors với bytes/hash dự kiến và input invalid; hai người khác phải dùng cùng vectors.
2. **Đến G1 — 20/11, 20:00:** Đưa `explain(artifact, transformed_features)` vào module riêng. Với LR có thể đối chiếu công thức tuyến tính với SHAP package trên WSL; RF/XGBoost phải chọn explainer và `output_space` tương thích phiên bản khóa. Dùng background chỉ từ train và seed cố định. Giao fixture SHAP và record cho C; ghi cách ánh xạ feature đã biến đổi sang tên hiển thị.
3. **Đến G2 — 25/11, 20:00:** Hoàn thiện persistence: migration có version, unique ID, canonical BLOB/JSON nhất quán, audit fields (tx, chain, block, confirmation, lỗi), retry idempotent. Tạo bản ghi cho artifact Taiwan và Home Credit từ A. Mọi lỗi additivity hoặc schema phải chặn việc ghi chain.
4. **Đến G3 — 29/11, 20:00:** E2 đo residual và biểu đồ local/global. E3 tạo các tình huống sửa probability, contribution, model version, JSON hiển thị, canonical bytes, cả record và hash SQLite; chứng minh B2 phát hiện mọi sửa đổi sau anchor. Ghi detection count và false alerts trên fixture sạch.
5. **Đến G4 — 02/12, 20:00:** Chạy golden vectors, schema tests, migration tests và bàn giao biểu đồ/giới hạn SHAP cho báo cáo.

## Tiêu chí nghiệm thu

- `base_value + sum(contributions)` khớp `model_output` trong `output_space` đã khai báo trên số chưa làm tròn; record lỗi bị từ chối.
- Bản ghi lưu mọi local contribution, model version và hash bundle; canonical bytes giữ nguyên qua lưu/đọc/verify. Cùng R cho cùng bytes/hash.
- Đổi probability hoặc SHAP làm `record_hash` đổi; đổi model version hoặc artifact hash làm cả commitment tương ứng đổi. Golden vectors chạy trong CI.
- SQLite không để retry tạo ID mới cho cùng yêu cầu và không trả `VERIFIED` chỉ dựa vào hash local.
- Không lưu ID nguồn hoặc dữ liệu cá nhân thô trong R và không log profile đầu vào.

## Prompt đưa cho agent của B

```text
Bạn là agent phụ trách vai trò B (SHAP, bản ghi, SQLite) của dự án Super Bells. Đọc docs/ROLE_B_SHAP_RECORDS.md, docs/TEAM_3_PERSON_EXECUTION_GUIDE.md, docs/interface_contract.md, docs/IMPLEMENTATION_READINESS_VI.md và kiểm tra git status trước khi sửa. Chỉ sửa các file thuộc B. Nếu cần thay schema/giao diện chung, viết đề xuất rõ sự tương thích để A/C review. Hoàn thành mốc gần nhất chưa đạt, kiểm tra additivity trước làm tròn, chuẩn hóa bytes/hash bằng golden vectors và kiểm thử sửa đổi. Dùng artifact/fixture do A bàn giao; có thể dùng fixture giả lập trước khi artifact sẵn có. Không commit dữ liệu thô, SQLite, model artifact hoặc bí mật. Kết thúc bằng: kết quả, lệnh test, file đã sửa, API/fixture bàn giao cho C, blocker và deadline tiếp theo. Không diễn giải SHAP thành quan hệ nhân quả hoặc bằng chứng công bằng.
```

