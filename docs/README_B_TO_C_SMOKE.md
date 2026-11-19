# Bàn giao kết quả chạy thử từ B cho C

B đã tạo một bản ghi mẫu để C thử đăng ký và xác minh hai commitment trên Anvil. Fixture dùng **4 dòng nền, 1 hồ sơ và 2 feature giả lập**, với mô hình logistic có hệ số cố định. Bản ghi dùng schema v1 và ID `taiwan_uci350` để tương thích với script hiện tại. Summary đánh dấu `synthetic: true`. Tích hợp FICO HELOC sẽ dùng artifact của A và schema được nhóm duyệt.

## Kết quả B đã kiểm tra

| Phép kiểm tra | Kết quả |
| --- | --- |
| Xác suất rủi ro `P(Bad)` | `0.77729986` |
| SHAP trong không gian log-odds | Base `−0.25`, `feature_a = +1.00`, `feature_b = +0.50` |
| Tổng SHAP cộng base và đầu ra mô hình | Cùng bằng `1.25`, residual trước khi làm tròn bằng `0` |
| Đọc lại từ SQLite | Canonical bytes giữ nguyên, `record_hash` và `model_version_hash` đều khớp |

Ba giá trị C cần để đăng ký bản ghi nằm trong `taiwan_smoke_summary.json`. Các giá trị dưới đây thuộc gói bàn giao ngày 19/11/2026.

```text
decision_id        eadc168fd75a3ba9100f0850bebae792a3e0d047ec0cb30e4de37d6e512ef5ab
record_hash        2e52f1ecc77b729b13633bf5433fe5afb7cb109901dabc6cc5ef8af87c2a6c09
model_version_hash 7d784b76f970bd7b78f58b8de10a21604ef78ad629dd48a469cab67e2d38e09e
```

## Cách chạy cho C

1. Dùng bản `scripts/anvil_smoke.py` có tùy chọn `--artifact-dir`. Giải nén `role_b_smoke.zip` vào `artifacts/role_b_smoke/`. Script đọc `audit.sqlite3` và `taiwan_smoke_summary.json`. Gói còn có `decision_record.json` chứa đúng canonical bytes và `model.json` để đối chiếu SHA-256 của model.
2. Mở Anvil local tại `http://127.0.0.1:8545`, chain ID `31337`. Chạy lệnh dưới đây từ thư mục gốc dự án.

   ```powershell
   uv run python scripts/anvil_smoke.py --artifact-dir artifacts/role_b_smoke
   ```

3. Kết quả kỳ vọng là `VERIFIED` sau khi đăng ký bản ghi gốc, `MISMATCH` khi sửa bản sao off-chain, kể cả khi tính lại canonical bytes, và giao dịch từ tài khoản thiếu quyền writer bị từ chối. B đã chạy phần SHAP, SQLite và hash. Phần Anvil đang chờ C chạy và gửi lại `artifacts/role_b_smoke/anvil_smoke_summary.json` có trạng thái xác minh, transaction hash và gas đã dùng.

Có thể tạo fixture mới bằng `uv run python scripts/role_b_smoke.py`. Khi tạo lại, dùng SQLite và summary từ cùng lần chạy vì decision ID và record hash sẽ thay đổi.
