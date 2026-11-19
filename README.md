# Super Bells credit audit prototype

**Bài tham khảo chính từ 19/11/2026:** Cheon et al., *Feature Responsiveness Scores: Model-Agnostic Explanations for Recourse* (ICLR 2025). Đọc [bối cảnh nghiên cứu hiện hành](docs/PROJECT_CONTEXT.md) trước khi triển khai. Thứ tự là A tái lập mô hình và AUC của tác giả trên dữ liệu tín dụng thật → B tính SHAP và tạo bản ghi quyết định → C ghi và xác minh commitment trên blockchain.

Ứng dụng hiện tại vẫn là nguyên mẫu Taiwan LR → bản ghi → Anvil. Phần dự đoán của ICLR 2025 đã được chạy lại độc lập theo [nhật ký tái lập](docs/references/CHEON_2025_REPLICATION_LOG.md); [giao diện v1](docs/interface_contract.md) và [phương pháp S1–S11 cũ](docs/DETAILED_METHOD_AND_3_PERSON_PLAN_VI.md) cần được chuyển sang dữ liệu ICLR trước khi dùng cho luồng đầy đủ.

## Thiết lập và chạy thử

```powershell
uv sync --locked
uv run python scripts/download_taiwan.py
uv run python scripts/taiwan_smoke.py
uv run python -m pytest -q
```

Trong một terminal khác, chạy Anvil (chain ID 31337, RPC `http://127.0.0.1:8545`), rồi chạy:

```powershell
uv run python scripts/anvil_smoke.py
```

Trên máy Windows hiện tại, binary Anvil 1.9.0 dành cho Linux được chạy qua WSL; nó nằm trong `artifacts/tools/` và không được commit. Nguồn tải là [Foundry release v1.9.0](https://github.com/foundry-rs/foundry/releases/tag/v1.9.0), SHA-256 archive `8d17599b42e3139f1a9c171be3798c4ed8e743ae17b84cc3435e57bf2a51ae99`. Nếu đã có Anvil trong PATH của WSL, lệnh là `anvil --host 127.0.0.1 --port 8545 --chain-id 31337 --silent`.

Kết quả smoke lưu trong `artifacts/taiwan_smoke_summary.json` và `artifacts/anvil_smoke_summary.json`. Luồng dùng LR và công thức SHAP tuyến tính trong không gian log-odds; SHAP package hiện bị Windows Application Control chặn DLL của Numba trên máy này. Launcher `scripts/replicate_cheon.py` chạy mã tác giả ở commit cố định trong `artifacts/cheon_iclr2025/`; `scripts/compare_cheon_results.py` xuất bảng đối chiếu. SHAP/RESP đầy đủ, UI Streamlit và baseline B0/B1/B2 là các bước tiếp theo.

Dữ liệu nguồn và model artifact ở `data/` và `artifacts/`, không commit. RPC và key local nằm trong `.env` (xem `.env.example`). Không đưa private key của testnet hoặc dữ liệu cá nhân lên repo.

