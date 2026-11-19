# Hướng dẫn cho người C — Blockchain, Web3 và giao diện

> **Cập nhật 19/11/2026:** Theo [bối cảnh hiện hành](PROJECT_CONTEXT.md), luồng kết quả chính sẽ dùng artifact FICO HELOC của A và record SHAP của B. Phần Vyper + Ape, B0/B1/B2 và xác minh hai hash vẫn giữ; các mốc Taiwan/Home Credit bên dưới là kế hoạch cũ. C chỉ tích hợp hồ sơ HELOC sau khi B bàn giao record/schema version phù hợp. Blockchain là phần mở rộng của nhóm, không được quy cho bài ICLR.

**Người phụ trách:** Chưa gán tên. **Hạn nộp chính thức:** 04/12/2026 (giờ Moodle chưa rõ). Mốc nội bộ trong [kế hoạch chung](TEAM_3_PERSON_EXECUTION_GUIDE.md), giờ UTC+7.

## Mục tiêu và phạm vi

Bạn sở hữu S10–S11, E4–E6: Vyper registry, phân quyền, triển khai Anvil, Web3 adapter, xác minh hai commitment, trạng thái giao dịch và dashboard Streamlit. UI chỉ hiển thị `VERIFIED` sau khi receipt đủ xác nhận và `record_hash` **cùng** `model_version_hash` khớp. Không huấn luyện model, không thay canonical bytes hoặc cách sinh SHAP. Dùng [giao diện v1](interface_contract.md) và artifact/fixture của A/B.

File sở hữu: `contracts/`, `src/credit_audit/chain.py`, `src/credit_audit/app.py`, `scripts/anvil_smoke.py`, test contract/e2e và script deploy mới. Không sửa pipeline ML, `records.py`, `storage.py` hoặc schema nếu chưa review chung.

## Trạng thái đang có

`DecisionRegistry.vy` đã compile với Vyper 0.4.3; smoke deploy trên Anvil 1.9.0 qua WSL, non-writer bị từ chối, record xác minh `VERIFIED`, sửa record và hash local vẫn `MISMATCH`. Anvil là chain tạm, không còn chạy sau smoke; contract address trong artifact không phải địa chỉ triển khai lâu dài. Chưa có test đầy đủ cho grant/revoke/duplicate/zero/event, UI Streamlit, xử lý reorg/RPC outage, phép đo lặp E4–E6. Ape đã khóa cho Linux/WSL; cài dev group Windows bị vướng `safe-pysha3` nên không dùng Ape trực tiếp trên Windows hiện tại.

## Việc cần làm theo thứ tự

1. **Đến G0 — 16/11, 20:00:** Review ABI, event, quyền admin/writer, quy tắc record bất biến và status map với B. Chốt số xác nhận cho Anvil/testnet và hình thức deployment manifest. Không dùng private key testnet trong repo.
2. **Đến G1 — 20/11, 20:00:** Viết contract tests cho unauthorized write, grant/revoke, duplicate ID, zero hash, getter, hash verification và event. Dùng golden vector B để kiểm tra ba `bytes32`. Cài Ape trong WSL nếu khả thi; Web3/pytest là fallback test tối thiểu đã có.
3. **Đến G2 — 29/11, 20:00:** Hoàn thiện backend state machine và Streamlit: tạo assessment, chi tiết, trạng thái transaction, xác minh theo ID, audit/error. Gắn A `predict()` và B `explain()/create_record()` theo giao diện đã nâng cho ICLR. Một hồ sơ FICO HELOC phải đi từ input UI đến `VERIFIED`; thử sửa record trên bản sao trả `MISMATCH`. Taiwan smoke cũ chỉ là test hồi quy.
4. **Đến G3 — 29/11, 20:00:** Chạy B0/B1/B2 cho E4–E6, đo gas/write, latency và lỗi giả lập. Lưu môi trường, số lần lặp, warm-up, median/p95; tách Anvil và Sepolia nếu nhóm chạy Sepolia. Test pending, receipt thất bại, RPC unavailable, duplicate retry, reorg/mất record. Không suy ra VERIFIED khi chain không đọc được.
5. **Đến G4 — 02/12, 20:00:** Demo từ môi trường sạch, README triển khai, test e2e và bảng gas/latency; phối hợp kiểm tra báo cáo. Xác nhận giờ Moodle và người nộp trước 04/12.

## Tiêu chí nghiệm thu

- Contract chỉ writer được cấp quyền mới đăng ký; revoke có hiệu lực; duplicate/zero bị từ chối; commitment đã ghi không thay thế được.
- Backend kiểm tra chain ID, contract address, receipt, block, số xác nhận và cả hai hash. Các trạng thái `PENDING`, `NOT_FOUND`, `MISMATCH`, `VERIFIED`, `TRANSACTION_FAILED`, `UNAVAILABLE` có UI và lý do rõ.
- Thao tác retry không tạo bản ghi quyết định mới hay gửi lại giao dịch bừa bãi khi receipt đang pending.
- E4–E6 có dữ liệu đo thực, test tự động và script tái lập trên Anvil. Dashboard không hiển thị raw personal data hoặc private key.

## Prompt đưa cho agent của C

```text
Bạn là agent phụ trách vai trò C (Vyper, Web3, UI) của dự án Super Bells. Đọc docs/ROLE_C_CHAIN_UI.md, docs/TEAM_3_PERSON_EXECUTION_GUIDE.md, docs/interface_contract.md, README.md và kiểm tra git status trước khi sửa. Chỉ sửa file thuộc C; đề xuất mọi thay đổi ABI/schema/API chung để A/B review trước. Hoàn thành mốc gần nhất chưa đạt. Dùng artifact/fixture A/B, hoặc fixture giả lập tạm thời nếu chưa có. Kiểm thử role, duplicate, zero hash, receipt/confirmation và cả hai commitment; UI không bao giờ báo VERIFIED khi pending, RPC lỗi hoặc hash sai. Không commit private key, .env, SQLite, dữ liệu hoặc artifact. Kết thúc bằng: việc hoàn thành, lệnh chạy/test, file đã sửa, API cần A/B bàn giao, blocker và deadline tiếp theo. Địa chỉ Anvil là tạm thời, không gọi là triển khai Sepolia.
```
