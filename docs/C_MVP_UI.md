# Super Bells · MVP kiểm toán trên Anvil

Dashboard xem ba hồ sơ FICO HELOC schema v2 người B đã bàn giao, đăng ký hai hash lên Anvil và xác minh theo Decision ID.

## Chạy demo

1. Cài môi trường tại thư mục gốc bằng `uv sync --locked`. Trên Windows có thể chạy các lệnh trong WSL.
2. Giải nén gói bàn giao HELOC của B sao cho ba thư mục `position-0`, `position-1` và `position-2` nằm trong `artifacts/role_b_heloc/handoff/`. Mỗi thư mục cần `audit.sqlite3`, `decision_record.json` và `taiwan_smoke_summary.json` từ cùng lượt chạy.
3. Mở Anvil trong terminal riêng. Ví dụ từ PowerShell khi Anvil nằm trong PATH của Ubuntu:

   ```powershell
   wsl.exe -d Ubuntu -- bash -lc 'anvil --host 127.0.0.1 --port 8545 --chain-id 31337 --silent'
   ```

   Nếu đang ở trong Ubuntu, chạy `~/.local/bin/anvil`. Nếu Anvil đã có trong PATH của terminal hiện tại, dùng:

   ```bash
   anvil --host 127.0.0.1 --port 8545 --chain-id 31337 --silent
   ```

4. Từ thư mục gốc, mở terminal thứ hai để triển khai contract và chạy dashboard. Nếu PowerShell cũng không nhận `uv`, chạy `wsl.exe -d Ubuntu` từ thư mục repo rồi dùng `~/.local/bin/uv` thay cho `uv`.

   ```bash
   uv run python scripts/deploy_anvil.py
   uv run streamlit run src/credit_audit/app.py --server.address 127.0.0.1
   ```

5. Chọn một trong ba nguồn **FICO HELOC · Hồ sơ 0–2**. Trong tab **Hồ sơ**, xem P(Bad) và SHAP rồi bấm **Đăng ký trên Anvil**. Trong tab **Xác minh**, dùng Decision ID có sẵn và bấm **Xác minh bản ghi**. Khi giao dịch đủ số xác nhận và cả hai hash đều khớp, dashboard hiển thị `VERIFIED` cùng biên nhận.
6. Bấm **Thử trên bản sao đã sửa** để đổi xác suất và tính lại canonical bytes trong một bản sao trong bộ nhớ. Kết quả `MISMATCH` cho thấy hash bản ghi sai lệch và hash phiên bản mô hình vẫn khớp. Bấm **Xác minh bản ghi** để kiểm tra lại bản ghi gốc.

Dashboard đọc gói B ở chế độ chỉ đọc. Metadata giao dịch nằm trong `artifacts/role_c_mvp/audit.sqlite3`; manifest nằm cùng thư mục. Khi bắt đầu lại với Anvil mới, đổi tên thư mục `artifacts/role_c_mvp` cũ rồi chạy lại script triển khai.

Nếu dùng thư mục demo hoặc cổng khác, truyền `--output <thư-mục-demo>/deployment.json` và `--rpc <URL>` cho script triển khai. Đặt `ROLE_C_MVP_DIR` và `RPC_URL` tương ứng khi chạy Streamlit. `ROLE_B_HELOC_DIR` trỏ đến thư mục chứa ba nguồn HELOC khi dùng đường dẫn khác.

## Kiểm toán từ tệp JSON

1. Từ một hồ sơ đã đăng ký trên Anvil, mở **Hồ sơ** → **Bản ghi và hai hash off-chain** → **Tải JSON canonical**.
2. Trong **Nguồn hồ sơ**, chọn **Nạp JSON để kiểm toán** và chọn tệp nhận được. Luồng này nhận bản ghi JSON chuẩn hóa v1 hoặc v2, tối đa 1 MB.
3. Mở tab **Xác minh** và bấm **Xác minh bản ghi**. Dashboard lấy Decision ID từ tệp, tìm giao dịch đăng ký trên registry Anvil đang dùng và đối chiếu hai cam kết. Kết quả có biên nhận, số xác nhận và từng cặp hash khi tìm được giao dịch hợp lệ.

Kiểm toán từ tệp dùng dữ liệu trong bộ nhớ và đọc registry. Dùng cùng triển khai Anvil mà bên tạo hồ sơ đã đăng ký. Nếu Decision ID chưa có cam kết trên registry đó, dashboard hiển thị `NOT_FOUND`.

## Kết quả nghiên cứu

Dashboard đọc bản tổng hợp đo ngày 25/11/2026 từ [HELOC_RESEARCH_SUMMARY.json](references/HELOC_RESEARCH_SUMMARY.json). Bản tổng hợp lấy AUC pilot từ `artifacts/role_a_heloc_verification.json`, AUC trung bình bảy seed từ `artifacts/heloc_training_t1/summary.json` và E3 từ `artifacts/heloc_e3/summary.json`. Thời gian đến biên nhận và gas được đo cho đăng ký B2 trên Anvil.

## Nguồn hồ sơ khác

- **Gói bàn giao B · dữ liệu giả lập** dùng `artifacts/role_b_smoke/`. Có thể đặt `ROLE_B_FIXTURE_DIR` để chọn thư mục riêng chứa `audit.sqlite3`, `decision_record.json`, `model.json` và `taiwan_smoke_summary.json`.
- **Mô phỏng ngoại tuyến** chạy phép đối chiếu trên hồ sơ minh họa trong bộ nhớ. Kết quả có tiền tố **Mô phỏng** và chạy được khi thiếu gói B hoặc Anvil.
- **Lượt pilot** đọc `summary.json` và `audit.sqlite3` của từng lượt. Mặc định dashboard tìm các thư mục con trong `artifacts/heloc_pilot/`. Có thể đặt `CREDIT_AUDIT_PILOT_DIR` đến một lượt hoặc thư mục chứa các lượt. Dashboard chỉ đọc registry của lượt đã chọn và xác minh qua Anvil khi bấm nút. Phần kết quả đã lưu tiếp tục đọc được khi Anvil dừng.

## Kiểm thử

Chạy `uv run python -m pytest -q` với Anvil trên PATH hoặc đặt `ANVIL_BIN` trỏ tới executable. Test tự dùng một Anvil riêng. Có thể chạy smoke CLI với `scripts/anvil_smoke.py --artifact-dir <bản-sao-gói-B>`.

UI kiểm tra trường hợp Decision ID sai định dạng, bản ghi không tồn tại, giao dịch chờ xác nhận, bản gốc khớp, bản sao sai lệch và Anvil mất kết nối.

## Đo độ trễ trên Sepolia

T5-02 đang chờ ETH thử nghiệm để thực hiện hai cửa sổ đo trên Sepolia. Các số độ trễ trong dashboard là kết quả từ Anvil.

T5-02 dùng hai tài khoản testnet riêng cho admin và writer. Cấp ETH Sepolia cho cả hai và đặt `SEPOLIA_RPC_URL`, `SEPOLIA_ADMIN_KEY`, `SEPOLIA_WRITER_KEY` trong môi trường chạy. Dùng cùng nhà cung cấp, tài khoản và mức phí trong hai cửa sổ. Các cờ phí dưới đây là ví dụ.

```bash
uv run python scripts/sepolia_latency.py --output artifacts/sepolia_t5 --window 1 --max-fee-gwei 10 --priority-fee-gwei 1
# Chạy cửa sổ 2 từ ít nhất sáu giờ sau khi cửa sổ 1 kết thúc.
uv run python scripts/sepolia_latency.py --output artifacts/sepolia_t5 --window 2 --max-fee-gwei 10 --priority-fee-gwei 1
```

Runner kiểm tra chain ID 11155111 và số dư theo trần phí trước khi gửi giao dịch. Mỗi cửa sổ đo 15 lượt cấp quyền, đăng ký và thu hồi quyền với mã băm thử nghiệm. `transactions.jsonl` lưu mã giao dịch, thời điểm gửi, thời điểm nhận biên nhận, gas, phí và trạng thái lỗi. Nếu quá 120 giây, runner ghi timeout và chỉ tiếp tục khi giao dịch đó đã xác nhận thành công trong thời gian chờ bổ sung. Nếu runner dừng, kiểm tra mã giao dịch đã lưu trước khi bắt đầu lượt mới. Bảng tổng hợp ghi số timeout và để trống p95 nếu các giá trị quan sát được chưa đủ để xác định phân vị.
