# Hợp đồng giao diện bản ghi

V1 dùng cho Taiwan/Home Credit và các fixture cũ. [V2](../schemas/decision_record_v2.schema.json) dùng cho FICO HELOC trong pilot Anvil. Hai phiên bản dùng cùng quy tắc chuẩn hóa byte và tham số registry. German Credit và Give Me Some Credit hiện chỉ dùng trong phần tái lập kết quả dự đoán.

## Định danh và dữ liệu

- V1 nhận `taiwan_uci350` hoặc `home_credit_2018`. V2 nhận `fico_heloc_iclr2025`. Mỗi ID ánh xạ một pipeline và artifact riêng.
- `decision_id`: 32 byte ngẫu nhiên, biểu diễn trong JSON bằng 64 ký tự hex chữ thường, truyền vào Vyper dưới dạng `bytes32`.
- `input_reference`: 16 byte ngẫu nhiên biểu diễn hex, độc lập với ID gốc.
- `nonce`: 16 byte ngẫu nhiên biểu diễn hex; `timestamp_utc` ở độ chính xác giây, dạng `YYYY-MM-DDTHH:MM:SSZ`.
- `risk_probability` trong bản ghi nhóm luôn là xác suất Bad/default. Riêng mã FICO của Cheon et al. huấn luyện với `Good=1`, `Bad=0`, nên adapter phải dùng `P(Bad)=1-predict_proba(Good)`; không suy rằng cột `predict_proba[:,1]` luôn là rủi ro. B kiểm tra SHAP additivity với đúng đầu ra risk đã ghi.

## Các hàm giữa ba phần

```text
predict(dataset_id, feature_dict) -> {
  risk_probability: float, predicted_label: 0|1,
  model_version: str, model_artifact_sha256: str,
  transformed_features: ordered numeric vector
}
explain(artifact, transformed_features) -> {
  method: str, output_space: "raw"|"probability",
  base_value: float, model_output: float,
  feature_contributions: [{feature: str, value: float}, ...]
}
create_record(prediction, explanation, input_reference) -> (R, canonical_bytes)
register(decision_id: bytes32, record_hash: bytes32, model_version_hash: bytes32) -> tx_hash
verify(decision_id) -> VERIFIED|MISMATCH|NOT_FOUND|PENDING|TRANSACTION_FAILED|UNAVAILABLE
```

`R` bắt buộc có `schema_version`, `dataset_id`, `decision_id`, `input_reference`, `model_version`, `model_artifact_sha256`, `risk_probability`, `shap_explanation`, `timestamp_utc`, `nonce`. `shap_explanation` có đủ các trường như `explain()` và đủ đóng góp cho mọi feature sau biến đổi. Không lưu ID nguồn hoặc dữ liệu cá nhân thô trong R.

## Byte và hash

Giá trị số thực của probability và SHAP được đổi sang chuỗi thập phân đúng 8 chữ số sau dấu chấm bằng Decimal ROUND_HALF_EVEN; `-0.00000000` chuẩn hóa thành `0.00000000`. Từ chối NaN/Infinity, tên feature trùng và Unicode surrogate lỗi. Chuỗi được NFC hóa, key JSON sort đệ quy, `feature_contributions` sort theo `feature`, không có khoảng trắng thừa, UTF-8 (`ensure_ascii=False`). Bản ghi lưu chính canonical bytes tại lúc tạo; xác minh phải đối chiếu bản JSON hiển thị với bytes này và hash lại bytes đã lưu.

```text
record_hash = SHA256(canonical_bytes)
model_version_hash = SHA256(UTF8(model_version + "|" + model_artifact_sha256))
```

On-chain chỉ có ba `bytes32` trên. `VERIFIED` cần receipt đủ xác nhận và cả hai hash khớp. Registry từ chối ghi đè decision ID ở cả hai phiên bản.

## Phân quyền sửa file

- A: `src/credit_audit/data.py`, `src/credit_audit/ml.py`, `tests/test_data_ml.py`, `docs/data_contract.md`.
- B: `src/credit_audit/records.py`, `src/credit_audit/storage.py`, `schemas/`, golden vectors và test tương ứng.
- C: `contracts/`, `src/credit_audit/chain.py`, `src/credit_audit/app.py`, `tests/test_contract.py`, `tests/test_e2e.py`.
- File chung (`pyproject.toml`, `uv.lock`, `.env.example`, `.gitignore`, tài liệu này) đổi qua PR được cả ba review.

