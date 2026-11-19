# Person C · Kiểm thử và demo Anvil

Luồng này dùng bản ghi giả lập theo giao diện v1. Nó dùng các hàm tạo bản ghi và SQLite đã có trong repo. Bạn có thể chạy contract, Web3, màn hình kiểm toán và phép đo B2 trước khi A/B bàn giao artifact hoặc fixture chính thức.

## Chạy local

Cài dependencies bằng `uv sync --locked`. Khởi động Anvil từ terminal riêng, ưu tiên WSL trên Windows.

```bash
anvil --host 127.0.0.1 --port 8545 --chain-id 31337 --silent
```

Chạy các lệnh sau từ thư mục repo.

```bash
uv run python scripts/anvil_smoke.py --runs 20 --warmup 3
uv run streamlit run src/credit_audit/app.py --server.address 127.0.0.1
```

Trong Streamlit, chọn **Dữ liệu giả lập**. Dán `decision_id` mà script in ra hoặc bấm **Tạo và đăng ký bản ghi giả lập** để chạy luồng từ giao diện. Giữ Anvil chạy trong lúc xác minh. Sau khi khởi động lại Anvil, hãy chạy lại script để triển khai registry và tạo bản ghi mới.

- Script tạo `artifacts/anvil_demo.sqlite3`, manifest `artifacts/anvil_demo_deployment.json` và kết quả `artifacts/anvil_smoke_summary.json`.
- Có thể triển khai riêng registry bằng `uv run python scripts/deploy_anvil.py`. Muốn kiểm toán một bản ghi Taiwan đã tạo bằng script của A, dùng `uv run python scripts/anvil_smoke.py --taiwan` rồi chọn **Taiwan** trong dashboard.
- Script mặc định dùng RPC `http://127.0.0.1:8545`. Nếu đổi cổng, truyền `--rpc` cho script và đặt `RPC_URL` khi chạy Streamlit.

## Kiểm thử và đọc kết quả

Chạy `uv run python -m pytest -q` trong môi trường có `anvil` trên PATH hoặc đặt `ANVIL_BIN` trỏ tới binary. Pytest tự khởi động một Anvil riêng. Kết quả E4 nằm trong các test phân quyền, event và điều kiện revert. Benchmark B2 ghi gas, phí, thời gian submit đến receipt và thời gian tạo bản ghi đến `VERIFIED`, kèm median và p95 của các mẫu sau warm-up.

Nếu RPC gián đoạn đúng lúc gửi giao dịch và SQLite chưa có tx hash, luồng giữ trạng thái `SUBMITTING`. Kiểm tra giao dịch hoặc event của decision trên đúng registry trước khi xử lý tiếp, vì node có thể đã nhận lệnh gửi.

## Phần cần đầu ra của A/B

- A bàn giao model artifact, schema đầu vào, `predict()` và hồ sơ demo Taiwan.
- B bàn giao `explain()`, golden vector v1 và fixture để đối chiếu B0, B1, B2.
- Khi các đầu ra sẵn sàng, nối form tạo assessment đến A/B và đo lại luồng tích hợp trên artifact của nhóm.
