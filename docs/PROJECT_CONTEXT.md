# Bối cảnh nghiên cứu hiện hành — Super Bells

**Quyết định ngày 19/11/2026:** Bài tham khảo chính để tái thực nghiệm là Cheon, Wernerfelt, Friedler và Ustun, **“Feature Responsiveness Scores: Model-Agnostic Explanations for Recourse,” ICLR 2025**. [Bài báo chính thức](https://proceedings.iclr.cc/paper_files/paper/2025/hash/6662eaf34893d9827ddf60c29e9ad6af-Abstract-Conference.html), [PDF](references/Cheon_2025_ICLR_Feature_Responsiveness_Scores.pdf), [mã thí nghiệm của tác giả](https://github.com/ustunb/responsiveness/tree/paper/iclr2025/research/iclr2025). PDF tải từ proceedings có SHA-256 `898319f77c6291da28779f833ea33b29e24945002686891bbb2b70c62057a977`; nhánh mã tại thời điểm kiểm tra trỏ tới commit `4c68c73b34eef7c5e38847274048cb3ab66d702c`. Báo cáo Tuần 3, kế hoạch Taiwan/Home Credit và lịch sử git ghi lại hướng Hlongwane et al. (PLOS ONE 2024) để đối chiếu lý do đổi hướng; chúng không còn là giao thức thực nghiệm chính.

Các số gốc đã được trích và lưu tại [bảng kết quả chuẩn Cheon 2025](references/CHEON_2025_ORIGINAL_RESULTS.md); dùng tệp này để đối chiếu mọi lần chạy lại.

**Cập nhật thực nghiệm 19/11/2026:** đã chạy lại phần dự đoán của Table 11 trên cả ba dataset và ba mô hình bằng commit tác giả đã khóa. [Nhật ký và bảng so sánh](references/CHEON_2025_REPLICATION_LOG.md) ghi 9/9 test AUC; đây chưa phải tái lập các thí nghiệm RESP/SHAP về chất lượng giải thích hoặc tích hợp blockchain.

## Câu hỏi và trình tự thực hiện

1. **A — tái thực nghiệm bài ICLR 2025:** dùng dữ liệu, xử lý và mã tác giả để huấn luyện LR, XGBoost, Random Forest; đo AUC trên cùng phép chia của bài, đối chiếu bảng 11 và giải thích mọi sai khác. Chỉ sau khi có kết quả smoke và full được ghi lại mới đóng băng model, feature schema, preprocessing, seed, split và hash artifact.
2. **B — giải thích và bản ghi:** dùng đúng artifact của A để tính SHAP, kiểm tra additivity và lưu giải thích cùng prediction, model hash trong bản ghi off-chain. SHAP và LIME là baseline giải thích trong bài ICLR; RESP là phương pháp của tác giả. Nếu nhóm chỉ triển khai SHAP cho decision record, phải ghi rõ đây là phần mở rộng audit của nhóm, không tuyên bố đã tái lập toàn bộ thí nghiệm RESP.
3. **C — blockchain:** nhận canonical bytes và hai hash từ B, đăng ký bằng Vyper + Ape, xác minh, chạy B0/B1/B2 và đo gas/latency/tình huống chỉnh sửa. Phần blockchain là đóng góp của nhóm, không thuộc phương pháp của Cheon et al.

## Dữ liệu, kết quả đối chiếu và thứ tự ưu tiên

| Dataset theo tác giả | Vai trò | Test AUC LR | Test AUC XGBoost | Test AUC RF |
| --- | --- | ---: | ---: | ---: |
| FICO HELOC (`fico`, 5.842 dòng sau xử lý) | Tập chính để tích hợp A → B → C | 0,788 | 0,785 | 0,790 |
| German Credit (`german`, 1.000 dòng) | Tập nhỏ để smoke/tái lập độc lập | 0,760 | 0,794 | 0,766 |
| Give Me Some Credit (`givemecredit`, 120.268 dòng) | Kiểm tra tái lập trên tập lớn, đã chạy Table 11 | 0,844 | 0,793 | 0,835 |

Số trong bảng lấy từ **Table 11, Appendix B.4** của [PDF chính thức](https://proceedings.iclr.cc/paper_files/paper/2025/file/6662eaf34893d9827ddf60c29e9ad6af-Paper-Conference.pdf); đây chỉ là **kết quả tác giả**. [Bảng đối chiếu](references/CHEON_2025_REPLICATION_COMPARISON.csv) lưu riêng kết quả nhóm. Bài mô tả train/test 80/20 và tối ưu siêu tham số bằng randomized search; [script train tác giả](https://github.com/ustunb/responsiveness/blob/paper/iclr2025/research/iclr2025/experiment/train_models.py) đặt `random_seed=2338`, `fold_id=K05N01`. Nhóm đã smoke German rồi chạy HELOC và Give Me Some Credit; nhật ký nêu rõ sai khác giữa mô tả 80/20 và cách mã xử lý tập Give Me Some Credit.

**Quy ước nhãn cần xử lý trước khi nối giao diện:** mã [xử lý FICO của tác giả](https://github.com/ustunb/responsiveness/blob/paper/iclr2025/research/iclr2025/data/fico/process_fico.py) mã hóa `Good=1`, `Bad=0`, nghĩa là xác suất lớp 1 của tác giả là khả năng **trả nợ tốt**. Giao diện hiện tại của nhóm quy định `risk_probability` là xác suất **default/xấu**. A phải giữ nguyên chiều nhãn để đối chiếu AUC tác giả, rồi xuất `risk_probability = P(Bad) = 1 - P(Good)` ở adapter tích hợp; B giải thích đúng đầu ra risk đã công bố và kiểm tra additivity trong cùng output space. Kiểm tra mapping của German/Give Me Some Credit riêng, không suy từ FICO.

## Ranh giới thay đổi và trạng thái hiện tại

- Đã có launcher và các model/kết quả tái lập ICLR trong `artifacts/` (không commit). **Ứng dụng chính** vẫn chỉ có Taiwan LR smoke; schema v1 chỉ nhận `taiwan_uci350`/`home_credit_2018`, chưa nhận artifact ICLR, chưa có SHAP full hoặc luồng HELOC → blockchain. Không gọi các kết quả Taiwan smoke là replication của ICLR.
- Cần sửa data contract, enum `dataset_id`, record schema/API và test một cách đồng bộ trước khi ghi record HELOC; không chỉ đổi tên dataset trong JSON. Nếu thay đổi phá tương thích, dùng schema version mới hoặc migration rõ ràng. Giữ fixture Taiwan cũ để kiểm tra hồi quy cho đến khi chuyển xong.
- Home Credit auxiliary tables không còn thuộc phạm vi chính của replication ICLR. Nếu vẫn dùng Taiwan/Home Credit, đặt là thí nghiệm mở rộng độc lập và không so AUC trực tiếp giữa các dataset để tuyên bố mô hình tốt hơn.
- Ghi thay đổi so với đề cương/báo cáo Tuần 3: đổi bài nền từ Hlongwane 2024 sang Cheon 2025 vì bài ICLR có mã tác giả, dữ liệu, split/seed và kết quả AUC đối chiếu; phần SHAP + blockchain audit vẫn giữ mục tiêu chủ đề hiện tại.

## Bằng chứng cần lưu khi hoàn tất

Manifest nguồn (URL, commit SHA, checksum, điều khoản), EDA trên dữ liệu thực (phân bố lớp, missing, feature chính), lệnh và môi trường chạy, split/seed, AUC đo được so với Table 11, sai khác, model hash, SHAP additivity, record/hash golden vector, kiểm thử hợp đồng và kết quả B0/B1/B2. Chỉ kết quả đã chạy trên dữ liệu thật mới đưa vào bảng kết quả của nhóm.
