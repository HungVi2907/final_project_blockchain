# Bối cảnh nghiên cứu hiện hành — Super Bells

**Quyết định ngày 19/11/2026:** Bài tham khảo chính để tái thực nghiệm là Cheon, Wernerfelt, Friedler và Ustun, **“Feature Responsiveness Scores: Model-Agnostic Explanations for Recourse,” ICLR 2025**. [Bài báo chính thức](https://proceedings.iclr.cc/paper_files/paper/2025/hash/6662eaf34893d9827ddf60c29e9ad6af-Abstract-Conference.html), [PDF](references/Cheon_2025_ICLR_Feature_Responsiveness_Scores.pdf), [mã thí nghiệm của tác giả](https://github.com/ustunb/responsiveness/tree/paper/iclr2025/research/iclr2025). PDF tải từ proceedings có SHA-256 `898319f77c6291da28779f833ea33b29e24945002686891bbb2b70c62057a977`; nhánh mã tại thời điểm kiểm tra trỏ tới commit `4c68c73b34eef7c5e38847274048cb3ab66d702c`. Báo cáo Tuần 3, kế hoạch Taiwan/Home Credit và lịch sử git ghi lại hướng Hlongwane et al. (PLOS ONE 2024) để đối chiếu lý do đổi hướng; chúng không còn là giao thức thực nghiệm chính.

Các số gốc đã được trích và lưu tại [bảng kết quả chuẩn Cheon 2025](references/CHEON_2025_ORIGINAL_RESULTS.md); dùng tệp này để đối chiếu mọi lần chạy lại.

**Cập nhật thực nghiệm 19/11/2026:** đã chạy lại phần dự đoán của Table 11 trên cả ba dataset và ba mô hình bằng commit tác giả đã khóa. [Nhật ký và bảng so sánh](references/CHEON_2025_REPLICATION_LOG.md) ghi 9/9 test AUC; đây chưa phải tái lập các thí nghiệm RESP/SHAP về chất lượng giải thích hoặc tích hợp blockchain.

## Câu hỏi và trình tự thực hiện

1. **A — tái thực nghiệm bài ICLR 2025:** dùng dữ liệu, xử lý và mã tác giả để huấn luyện LR, XGBoost, Random Forest; đo AUC trên cùng phép chia của bài, đối chiếu bảng 11 và giải thích mọi sai khác. Chỉ sau khi có kết quả smoke và full được ghi lại mới đóng băng model, feature schema, preprocessing, seed, split và hash artifact.
2. **B — giải thích và bản ghi:** dùng đúng artifact của A để tính SHAP, kiểm tra additivity và lưu giải thích cùng prediction, model hash trong bản ghi off-chain. SHAP và LIME là baseline giải thích trong bài ICLR; RESP là phương pháp của tác giả. Nếu nhóm chỉ triển khai SHAP cho decision record, phải ghi rõ đây là phần mở rộng audit của nhóm, không tuyên bố đã tái lập toàn bộ thí nghiệm RESP.
3. **C — blockchain:** nhận canonical bytes và hai hash từ B, dùng web3.py gọi Vyper registry trên Anvil, xác minh và ghi kết quả theo cùng `decision_id`. So sánh B0/B1/B2 về phát hiện thay đổi, đo gas và độ trễ theo kế hoạch kiểm thử. Blockchain là phần kiểm toán do nhóm phát triển.

## Dữ liệu, kết quả đối chiếu và thứ tự ưu tiên

| Dataset theo tác giả | Vai trò | Test AUC LR | Test AUC XGBoost | Test AUC RF |
| --- | --- | ---: | ---: | ---: |
| FICO HELOC (`fico`, 5.842 dòng sau xử lý) | Tập chính để tích hợp A → B → C | 0,788 | 0,785 | 0,790 |
| German Credit (`german`, 1.000 dòng) | Tập nhỏ để smoke/tái lập độc lập | 0,760 | 0,794 | 0,766 |
| Give Me Some Credit (`givemecredit`, 120.268 dòng) | Kiểm tra tái lập trên tập lớn, đã chạy Table 11 | 0,844 | 0,793 | 0,835 |

Số trong bảng lấy từ **Table 11, Appendix B.4** của [PDF chính thức](https://proceedings.iclr.cc/paper_files/paper/2025/file/6662eaf34893d9827ddf60c29e9ad6af-Paper-Conference.pdf); đây chỉ là **kết quả tác giả**. [Bảng đối chiếu](references/CHEON_2025_REPLICATION_COMPARISON.csv) lưu riêng kết quả nhóm. Bài mô tả train/test 80/20 và tối ưu siêu tham số bằng randomized search; [script train tác giả](https://github.com/ustunb/responsiveness/blob/paper/iclr2025/research/iclr2025/experiment/train_models.py) đặt `random_seed=2338`, `fold_id=K05N01`. Nhóm đã smoke German rồi chạy HELOC và Give Me Some Credit; nhật ký nêu rõ sai khác giữa mô tả 80/20 và cách mã xử lý tập Give Me Some Credit.

**Quy ước nhãn cần xử lý trước khi nối giao diện:** mã [xử lý FICO của tác giả](https://github.com/ustunb/responsiveness/blob/paper/iclr2025/research/iclr2025/data/fico/process_fico.py) mã hóa `Good=1`, `Bad=0`, nghĩa là xác suất lớp 1 của tác giả là khả năng **trả nợ tốt**. Giao diện hiện tại của nhóm quy định `risk_probability` là xác suất **default/xấu**. A phải giữ nguyên chiều nhãn để đối chiếu AUC tác giả, rồi xuất `risk_probability = P(Bad) = 1 - P(Good)` ở adapter tích hợp; B giải thích đúng đầu ra risk đã công bố và kiểm tra additivity trong cùng output space. Kiểm tra mapping của German/Give Me Some Credit riêng, không suy từ FICO.

## Đặc tả tích hợp Tuần 4

Báo cáo giữ tên đề tài, thứ tự S1–S11 và cải tiến I1 ở S8–S11 từ Tuần 3. Giao thức dự đoán chuyển sang Cheon 2025. FICO HELOC là dữ liệu tích hợp chính, German Credit và Give Me Some Credit dùng để tái lập độc lập. Pilot Taiwan là bằng chứng kỹ thuật lịch sử. [Báo cáo Tuần 4](weekly_repo/week_4/IS355_Week4_Project_Report_Template.docx)

| Phụ trách | Đặc tả và đầu ra bàn giao | Điều kiện nghiệm thu |
| --- | --- | --- |
| **A · S1–S6** | Dùng thiết lập tác giả, fold `K05N01`, test fold 5, seed `2338`, 4.674 train và 1.168 test. Chọn LR từ các artifact đã tái lập cho lần tích hợp đầu. Bàn giao manifest gồm `dataset_id=fico_heloc_iclr2025`, `model_version`, SHA-256 của artifact, scaler, thứ tự 43 feature, ánh xạ `classes_` và chỉ số train cho SHAP background. Khi suy luận, trả `P(Bad)` và đúng vector đã đưa vào classifier. | Kiểm tra thứ tự feature, checksum, chiều xác suất và sự nhất quán giữa đầu ra adapter với pipeline đã lưu. Nếu cần nhãn nhị phân, chọn ngưỡng có F1 lớp Bad cao nhất trên dự đoán out-of-fold của tập train, chọn ngưỡng cao hơn khi hòa. Công bố ngưỡng sau khi đo. |
| **B · S7–S9** | Giải thích LR trong log-odds lớp Bad bằng linear interventional SHAP, dùng 100 dòng train với seed `2338`. Nếu margin của LR hướng về Good, đổi dấu margin, base và mọi đóng góp. Đích triển khai là `schema_version="2"` cho HELOC, giữ khả năng đọc v1. Gửi C bản ghi đã bỏ định danh nguồn, canonical bytes, `decision_id`, `record_hash`, `model_version_hash`, version schema và artifact. | Trước làm tròn, sai số additivity và chênh lệch giữa sigmoid của Bad margin với `P(Bad)` đều không quá `1e-6`. Có đủ 43 đóng góp. SQLite round-trip giữ nguyên canonical bytes và tái tạo được hai SHA-256. |
| **C · S10–S11** | Dùng `web3.py` gọi `DecisionRegistry.register_record` bằng tài khoản writer trên Anvil `31337`. Truyền đúng ba `bytes32` và giữ JSON/SHAP off-chain. Lưu `decision_id`, receipt, transaction hash, block, gas và kết quả hiển thị. | `VERIFIED` yêu cầu receipt thành công, một xác nhận trên Anvil và hai hash tính lại đều khớp registry. B0 lưu record trong SQLite, B1 lưu record cùng hash cục bộ, B2 xác minh dựa trên registry độc lập. |

Hai cam kết của S9 là `record_hash = SHA256(canonical_bytes)` và `model_version_hash = SHA256(UTF8(model_version + "|" + model_artifact_sha256))`. Mỗi lần bàn giao dùng cùng một `decision_id` để đối chiếu record, receipt và kết quả trên dashboard.

## Pilot đầu–cuối ngày 20/11/2026

- Chạy lại bước chuẩn bị từ CSV FICO gốc trên checkout tác giả đã ghim. Dùng đúng artifact LR của A, fold `K05N01`, test fold 5 và 100 dòng nền lấy từ train bằng seed `2338`. Ba lượt chọn ba vị trí đầu của tập held-out. Giá trị `P(Bad)` lần lượt là 0,75638247, 0,31828327 và 0,65212606.
- Cả 3 lượt có đủ 43 đóng góp SHAP và residual trước làm tròn bằng 0. Bản ghi HELOC dùng schema v2 và SQLite mới cho từng lượt. Mỗi lượt deploy registry mới trên cùng Anvil 1.9.0 local, chain ID 31337. Bản gốc `VERIFIED` 3/3, bản sao sửa xác suất `MISMATCH` 3/3. Mỗi giao dịch ghi dùng **93.507 gas**.
- Đăng ký thêm đúng fixture B (`eadc168f…`) trên một registry riêng. Giao dịch dùng 93.507 gas và trả `VERIFIED`. Cả bốn lượt kiểm tra giao diện Streamlit qua AppTest bằng RPC thật đều hiển thị đúng trạng thái, decision ID, transaction hash và gas. Mỗi thư mục con trong `artifacts/heloc_pilot/` có `summary.json`, `receipt.json`, canonical JSON và SQLite. `dashboard_checks.json` lưu bốn kết quả kiểm tra UI.
- Pilot dùng một artifact LR, một phép chia và Anvil automine. Các lượt thử nghiệm chính thức T1–T7 và đo độ trễ Sepolia vẫn thuộc kế hoạch kiểm thử.

### Chạy lại pilot

Mở Anvil local 1.9.0 ở cổng 18545, chain ID 31337. Trên Windows có thể dùng Anvil trong WSL với `--host 127.0.0.1 --port 18545 --chain-id 31337 --silent`. Dùng môi trường dự án để chạy blockchain và môi trường tác giả có scikit-learn 1.5.2 để nạp model. Tệp model phải khớp SHA-256 trong [bàn giao A](A_TO_B_HANDOFF_HELOC.md).

```powershell
.venv/Scripts/python.exe scripts/heloc_pilot.py --test-offset 0 --output artifacts/heloc_pilot/replay-01
.venv/Scripts/python.exe scripts/heloc_pilot.py --fixture-dir artifacts/role_b_smoke --output artifacts/heloc_pilot/replay-b
$env:CREDIT_AUDIT_PILOT_DIR = 'artifacts/heloc_pilot/replay-01'
.venv/Scripts/python.exe -m streamlit run scripts/heloc_pilot_dashboard.py --server.address 127.0.0.1
```

Đổi `--test-offset` thành 1 hoặc 2 và dùng thư mục đầu ra mới cho các lượt kế tiếp. Dashboard đọc SQLite và truy vấn registry trên phiên Anvil đang chạy. Sau khi reset Anvil, chạy lại pilot để tạo giao dịch và thư mục bằng chứng mới.

## Trạng thái triển khai và bằng chứng

- Schema v2 và dashboard đọc pilot hỗ trợ luồng HELOC LR → SHAP → SQLite → Anvil. Fixture Taiwan v1 vẫn đọc được và dùng để kiểm tra hồi quy.
- B đã chạy SHAP và SQLite trên fixture giả lập ngày 19/11/2026. Bộ bàn giao ban đầu vẫn giữ trạng thái `PENDING`; kết quả đăng ký ngày 20/11 được lưu ở thư mục pilot riêng. [Handoff B → C](https://github.com/HungVi2907/final_project_blockchain/blob/afa95ce38b86b9a8e738ae90872adc860011a2d6/docs/README_B_TO_C_SMOKE.md)
- Home Credit auxiliary tables không còn thuộc phạm vi chính của replication ICLR. Nếu vẫn dùng Taiwan/Home Credit, đặt là thí nghiệm mở rộng độc lập và không so AUC trực tiếp giữa các dataset để tuyên bố mô hình tốt hơn.
- Bảng phản hồi Tuần 3 trong báo cáo đang chờ nhận xét gốc của giảng viên và các mục ưu tiên cao còn mở từ đề cương.

## Bằng chứng cần lưu khi hoàn tất

Manifest nguồn (URL, commit SHA, checksum, điều khoản), EDA trên dữ liệu thực (phân bố lớp, missing, feature chính), lệnh và môi trường chạy, split/seed, AUC đo được so với Table 11, sai khác, model hash, SHAP additivity, record/hash golden vector, kiểm thử hợp đồng và kết quả B0/B1/B2. Chỉ kết quả đã chạy trên dữ liệu thật mới đưa vào bảng kết quả của nhóm.
