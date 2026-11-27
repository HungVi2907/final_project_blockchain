# Super Bells credit audit prototype

Super Bells là nguyên mẫu kiểm toán quyết định tín dụng trên dữ liệu FICO HELOC. A tái lập AUC của mô hình theo Cheon et al. (ICLR 2025), B tính SHAP và tạo bản ghi quyết định, C đăng ký cam kết lên registry và xác minh bản ghi. [Đề cương nghiên cứu](docs/07_SuperBells_IS355_Proposal.md) · [Nhật ký tái lập](docs/references/CHEON_2025_REPLICATION_LOG.md)

Dashboard hỗ trợ xem SHAP, đăng ký và xuất hồ sơ HELOC đã chuẩn bị, sau đó kiểm toán tệp JSON từ biên nhận trên Anvil. Repo có kết quả tổng hợp HELOC và chế độ mô phỏng chạy được ngay sau khi cài môi trường. [Hướng dẫn dashboard và phép đo Sepolia](docs/C_MVP_UI.md)

## Thiết lập và chạy thử

Từ bản clone mới, cài môi trường và mở dashboard mô phỏng. Chọn **Mô phỏng ngoại tuyến** để thử xác minh hồ sơ gốc và bản sao đã sửa.

```powershell
uv sync --locked
uv run streamlit run src/credit_audit/app.py --server.address 127.0.0.1
```

Để thử đường ống nguyên mẫu Taiwan và chạy bộ kiểm thử:

```powershell
uv run python scripts/download_taiwan.py
uv run python scripts/taiwan_smoke.py
uv run python -m pytest -q
```

Trong một terminal khác, chạy Anvil (chain ID 31337, RPC `http://127.0.0.1:8545`), rồi chạy:

```powershell
uv run python scripts/anvil_smoke.py
```

Trên máy Windows hiện tại, binary Anvil 1.9.0 dành cho Linux được chạy qua WSL; nó nằm trong `artifacts/tools/` và không được commit. Nguồn tải là [Foundry release v1.9.0](https://github.com/foundry-rs/foundry/releases/tag/v1.9.0), SHA-256 archive `8d17599b42e3139f1a9c171be3798c4ed8e743ae17b84cc3435e57bf2a51ae99`. Nếu đã có Anvil trong PATH của WSL, lệnh là `anvil --host 127.0.0.1 --port 8545 --chain-id 31337 --silent`.

Kết quả smoke lưu trong `artifacts/taiwan_smoke_summary.json` và `artifacts/anvil_smoke_summary.json`. Luồng dùng LR và công thức SHAP tuyến tính trong không gian log-odds; SHAP package hiện bị Windows Application Control chặn DLL của Numba trên máy này. Launcher `scripts/replicate_cheon.py` chạy mã tác giả ở commit cố định trong `artifacts/cheon_iclr2025/`; `scripts/compare_cheon_results.py` xuất bảng đối chiếu. Luồng HELOC, dashboard pilot và thực nghiệm đối chiếu B0/B1/B2 được mô tả bên dưới.

Dữ liệu nguồn và model artifact ở `data/` và `artifacts/`, không commit. RPC và key local nằm trong `.env` (xem `.env.example`). Không đưa private key của testnet hoặc dữ liệu cá nhân lên repo.

## Thực nghiệm HELOC

T1-01 dùng checkout của tác giả ở commit đã ghim, dữ liệu chuẩn bị bằng `scripts/replicate_cheon.py setup --dataset fico` và môi trường Python 3.10 của gói A. T1-02 dùng cùng mô hình LR cố định và cùng mẫu nền 100 dòng của B. Trong WSL, chạy các lệnh sau với các thư mục đầu ra mới. Biến `HELOC_PYTHON` trỏ đến Python 3.10 đã cài thư viện của gói A và checkout tác giả.

```bash
"$HELOC_PYTHON" scripts/heloc_training.py --output artifacts/heloc_training_t1
"$HELOC_PYTHON" scripts/heloc_e3.py prepare --output artifacts/heloc_e3/profiles.json
```

Mở Anvil local trên cổng 18545, chain ID 31337. Chạy nhóm đầu trước. Mỗi nhóm có một registry mới và 40 hồ sơ lấy mẫu không hoàn lại trong nhóm.

```bash
uv run python scripts/heloc_e3.py run --input artifacts/heloc_e3/profiles.json --output artifacts/heloc_e3 --rpc http://127.0.0.1:18545 --seeds 2338
uv run python scripts/heloc_e3.py run --input artifacts/heloc_e3/profiles.json --output artifacts/heloc_e3 --rpc http://127.0.0.1:18545 --seeds 2339 2340 2341 2342
```

Mỗi thư mục seed lưu SQLite của ba baseline, từng kết quả đối chiếu, giao dịch đăng ký và thống kê. Kịch bản sửa đổi cập nhật xác suất và canonical bytes ở cả ba baseline, kèm hai hash local ở B1. B2 đối chiếu với cam kết gốc trên Anvil. T1-01 lưu AUC và tham số theo từng lượt fit, cùng khoảng tin cậy theo seed. [Nhật ký tái lập](docs/references/CHEON_2025_REPLICATION_LOG.md)

Lượt chạy ngày 25/11/2026 neo 200 bản ghi thuộc 5 nhóm. Trong kịch bản này, B0 và B1 phát hiện 0/200, B2 phát hiện 200/200, cả ba baseline có 0/200 cảnh báo sai. Gas đăng ký trung vị là 93.507. Thời gian từ bắt đầu gửi đến receipt trên Anvil có trung vị 65,0 ms và p95 83,1 ms. Kết quả tổng hợp nằm ở `artifacts/heloc_e3/summary.json`.

Gói B cung cấp ba hồ sơ để kiểm toán và báo cáo độ nhạy SHAP. Lệnh tạo lại toàn bộ đầu ra T2-01 trong báo cáo cần `scripts/role_b_heloc.py` từ B. Script có sẵn `scripts/heloc_e3.py prepare` tính lại dự đoán và SHAP với mẫu nền cố định cho E3. [Báo cáo người B](docs/ROLE_B_HELOC_REPORT.md)

Dashboard chính cho phép chọn, đăng ký và xác minh ba hồ sơ HELOC của B. T5-02 có runner riêng và còn chờ kết quả trên Sepolia. [Hướng dẫn chạy dashboard và đo trên Sepolia](docs/C_MVP_UI.md)

Để demo một hồ sơ HELOC của B với phiên Anvil đang chạy, đăng ký fixture bằng `heloc_pilot.py` rồi mở dashboard pilot.

```bash
uv run python scripts/heloc_pilot.py --fixture-dir artifacts/role_b_heloc/handoff/position-0 --port 18545 --output artifacts/heloc_pilot/example-0
CREDIT_AUDIT_PILOT_DIR=artifacts/heloc_pilot/example-0 uv run streamlit run scripts/heloc_pilot_dashboard.py
```

