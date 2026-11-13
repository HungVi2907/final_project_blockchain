# Phụ lục về mức độ sẵn sàng triển khai

## Mục đích

Báo cáo và đề xuất Tuần 3 xác định định hướng nghiên cứu, phạm vi, các ràng buộc chính, quy trình ở mức cao (S1-S11), các công nghệ được chọn và kế hoạch đánh giá của dự án. Những tài liệu này đủ để giải thích dự án *là gì* và vì sao I1 là cải tiến được đề xuất.

Tuy nhiên, chúng chưa phải là đặc tả triển khai hoàn chỉnh. Tài liệu này ghi nhận các quyết định và hiện vật cần được chốt trước khi bắt đầu phát triển, nhằm bảo đảm mọi thành viên triển khai cùng một hệ thống và các thí nghiệm có thể tái lập.

## Định hướng đã được xác nhận từ các tài liệu hiện có

- Hệ thống là nguyên mẫu phục vụ thí nghiệm, không phải sản phẩm phê duyệt khoản vay thực tế.
- Có hai pipeline ML độc lập: Home Credit Default Risk và UCI Taiwan Default of Credit Card Clients. Dữ liệu và mô hình đã huấn luyện tuyệt đối không được gộp hoặc chuyển giao giữa hai pipeline này.
- Mỗi tập dữ liệu dùng phép chia phân tầng 70/15/15 cho train/validation/test. Toàn bộ bước tiền xử lý có học tham số chỉ được dùng dữ liệu của tập train.
- Các mô hình ứng viên gồm Logistic Regression, Random Forest và XGBoost. Việc chọn mô hình dựa trên các chỉ số validation; mô hình được giữ lại chỉ được đánh giá một lần trên tập test tương ứng.
- Dự đoán và phần giải thích SHAP cục bộ được tạo off-chain.
- I1 lưu một bản ghi quyết định giả danh hoàn chỉnh `R` ở off-chain, chuẩn hóa nó, rồi tính `record_hash = SHA256(CanonicalSerialize(R))`.
- Registry Vyper chỉ lưu `decision_id`, `record_hash` và `model_version_hash`; nó phải giới hạn thao tác ghi cho các writer được ủy quyền.
- Quy trình xác minh tính lại cả hai hash từ bản ghi off-chain đã lưu và trả về `VERIFIED`, `MISMATCH`, `NOT_FOUND` hoặc `PENDING`.
- Đánh giá so sánh B0 (chỉ SQLite), B1 (SQLite cộng hash trong cùng cơ sở dữ liệu) và B2 (bản ghi off-chain cộng commitment on-chain), với các phép đo ML, SHAP, tính toàn vẹn, kiểm soát truy cập, gas và độ trễ.

## Các khoảng trống cản trở việc triển khai nhất quán

### 1. Môi trường tái lập và bố cục repository

Tên công nghệ đã được chỉ định, nhưng phiên bản chính xác và cấu trúc repository thì chưa.

Trước khi lập trình, cần tạo và commit:

- Một phiên bản Python được hỗ trợ và tệp dependency đã khóa (`pyproject.toml` kèm lockfile, hoặc `requirements.txt` với phiên bản được ghim).
- Phiên bản chính xác cho pandas, scikit-learn, XGBoost, SHAP, Web3.py, Vyper, Ape, pytest, Streamlit và công cụ Solidity/EVM mà Ape sử dụng.
- Phiên bản Node, Vyper, Ape; phiên bản Anvil; lựa chọn nhà cung cấp RPC Sepolia.
- Tệp `.env.example` chỉ chứa tên biến, không bao giờ chứa bí mật: `RPC_URL`, `PRIVATE_KEY`, `CHAIN_ID`, `CONTRACT_ADDRESS`, `SQLITE_PATH`.
- Bố cục repository tách biệt `data/` (ignored), `src/`, `contracts/`, `tests/`, `scripts/`, `artifacts/` (ignored) và `docs/`.
- Chính sách random seed cố định cho việc chia dữ liệu, huấn luyện mô hình và mọi dữ liệu nền SHAP được lấy mẫu.

### 2. Hợp đồng dữ liệu và kiểm soát rò rỉ

Nguồn dữ liệu và các ràng buộc tổng quát đã rõ, nhưng hợp đồng đặc trưng cụ thể vẫn chưa được cố định.

Quyết định và lập tài liệu cho từng tập dữ liệu:

- Quy trình tải về, URL nguồn, ngày truy xuất, tên tệp nguồn và checksum SHA-256.
- Cột target, các cột ID, allow-list đặc trưng thô cuối cùng và các trường bị loại trừ rõ ràng.
- Với Home Credit: các bảng phụ chính xác sẽ dùng (nếu có), định nghĩa phép tổng hợp và quy tắc về thời điểm dữ liệu có mặt để ngăn rò rỉ sau quyết định.
- Chính sách xử lý bản ghi trùng lặp, giá trị thiếu, giá trị không hợp lệ, mã hóa biến phân loại, chuẩn hóa biến số và xử lý ngoại lệ.
- Cách xử lý mất cân bằng lớp, bao gồm việc có dùng `class_weight`, resampling hay giữ nguyên phân phối lớp. Mọi resampling chỉ được diễn ra trong quy trình huấn luyện.
- Seed để chia dữ liệu, định dạng split manifest và các định danh dòng được lưu cho train/validation/test.

Sản phẩm bàn giao: `docs/data_contract.md` cùng các split manifest đã được version. Không đưa dữ liệu cá nhân hoặc dữ liệu nguồn thô vào Git.

### 3. Đặc tả thí nghiệm ML

Báo cáo đã nêu mô hình ứng viên và các metric, nhưng chưa cố định một giao thức huấn luyện có thể chạy được.

Cần chỉ rõ:

- Khoảng tìm kiếm siêu tham số, metric tối ưu hóa, số fold CV (nếu dùng), quy trình validation và quy tắc phá hòa khi chọn mô hình.
- Định nghĩa chính xác của Recall và F1, bao gồm lớp dương và quy tắc chọn ngưỡng vận hành. Ngưỡng chỉ có thể được chọn trên validation.
- Phương pháp khoảng tin cậy, số lần resampling và random seed nếu có báo cáo khoảng tin cậy.
- Định dạng artifact (`joblib` hoặc tương đương), quy ước thư mục artifact, tệp metadata và nội dung dùng để tính `model_artifact_sha256`.
- Lệnh `train` có thể tái lập và lệnh `evaluate` xuất ra các metric, confusion matrix, ngưỡng được chọn và metadata artifact.

### 4. Hợp đồng SHAP

Các bản ghi yêu cầu đầu ra SHAP, nhưng cần cố định chi tiết tương thích để tránh các giải thích không tương thích.

Cần chỉ rõ:

- Explainer cho từng mô hình hỗ trợ (`LinearExplainer`, `TreeExplainer` hoặc một phương án thay thế được hỗ trợ khác), phiên bản, cách chọn dữ liệu nền và giới hạn cỡ mẫu.
- Một `output_space` được khai báo cho mỗi loại mô hình: `probability` hoặc raw margin. Giá trị này phải được lưu trong `R` và dùng nhất quán trong phép kiểm tra tính cộng.
- Tên đặc trưng SHAP tham chiếu đến đặc trưng thô hay đặc trưng sau biến đổi, cũng như cách ánh xạ đặc trưng one-hot hoặc đặc trưng tổng hợp để hiển thị.
- Dung sai số học cho `base_value + sum(feature_contributions) ~= model_output`, được tính trước khi định dạng thập phân.
- Chính sách khi thất bại: từ chối tạo bản ghi, đánh dấu bản ghi, hoặc lưu trạng thái xác thực rõ ràng nếu kiểm tra tính cộng không đạt.

### 5. Đặc tả JSON chuẩn hóa có thể thực thi

Báo cáo đưa ra các quy tắc mạnh cho việc chuẩn hóa, nhưng vẫn cần một hợp đồng có thể thực thi và kiểm thử.

Chốt các điểm sau trước khi tính hash cho môi trường production:

- JSON Schema cho `R` với các trường bắt buộc, kiểu dữ liệu, dataset ID được phép, giới hạn độ dài và chính sách versioning.
- Mọi giá trị số hữu hạn có được chuyển thành chuỗi trước khi serialization hay không, bao gồm giá trị SHAP và `risk_probability`; xác định chính xác chế độ làm tròn (ví dụ decimal half-even hoặc half-up).
- Cách xử lý chính xác số âm không, ký pháp số mũ, trường tùy chọn, `null`, boolean, các mảng ngoài `feature_contributions`, escape và lỗi chuẩn hóa Unicode.
- Biểu diễn chính xác của `decision_id` (32 byte ngẫu nhiên biểu diễn bằng hexadecimal chữ thường gồm 64 ký tự, hoặc bytes32) và độ dài/cách mã hóa `nonce`.
- Chuỗi byte nguồn chân lý: lưu UTF-8 bytes đã chuẩn hóa khi tạo bản ghi và hash lại chính các byte ấy lúc xác minh; không tạo lại time hoặc nonce.

Sản phẩm bàn giao:

- `schemas/decision_record_v1.schema.json`
- Một cài đặt duy nhất `canonical_serialize(record) -> bytes`
- Golden vectors chứa các bản ghi hợp lệ, canonical bytes, `record_hash` dự kiến, `model_version_hash` dự kiến và các trường hợp input không hợp lệ

### 6. Hợp đồng lưu trữ SQLite

SQLite đã được chọn, nhưng schema và hành vi vận hành chưa được xác định.

Cần định nghĩa:

- Các bảng, primary key, unique constraint, index, công cụ migration và lịch sử migration.
- Canonical bytes có được lưu dưới dạng BLOB và JSON có được giữ riêng để hiển thị hay không; chỉ giữ cả hai nếu có kiểm tra tính nhất quán giữa chúng.
- Các trường audit log: thời điểm tạo, transaction hash, chain ID, block number, trạng thái xác nhận, kết quả xác minh và lý do lỗi.
- Cách xử lý `decision_id` trùng lặp và hành vi idempotency khi client thử lại sau lỗi mạng.
- Vị trí tệp cục bộ, chính sách backup/lưu giữ và các artifact phải bị loại khỏi Git.

### 7. Đặc tả và triển khai Vyper contract

Tên hàm dự kiến đã được liệt kê, nhưng hành vi contract cần được hoàn thiện để có thể triển khai và kiểm thử.

Hoàn tất README và test cho contract với:

- Cấu trúc lưu trữ và mapping, mô hình vai trò, constructor/admin ban đầu, `grant_writer`, `revoke_writer` và chính sách chuyển vai trò.
- Toàn bộ chữ ký, visibility, kiểu trả về, trường event và trường được indexed cho `register_record`, `get_record` và `verify_record_hash`.
- Điều kiện revert và thông báo lỗi/custom error cho thao tác ghi không được ủy quyền, hash bằng không, ID trùng lặp và bản ghi không tồn tại.
- Quy tắc bất biến: commitment đã đăng ký không được ghi đè. Nếu sau này cần thay thế, phải định nghĩa quy tắc quyết định/phiên bản mới rõ ràng thay vì ghi đè lịch sử.
- Cấu hình mạng cho Anvil và Sepolia, lệnh triển khai, phiên bản bytecode/compiler, bản ghi địa chỉ đã triển khai và số xác nhận tối thiểu trước khi coi giao dịch đã được xác nhận.
- Unit test cho phân quyền, hành vi revoke, trùng lặp, giá trị bằng không, truy xuất, xác minh, event phát ra và việc từ chối non-writer.

### 8. Hợp đồng giao diện Backend và Streamlit

Tài liệu nêu Streamlit và Web3.py nhưng không xác định ranh giới giữa UI, backend, cơ sở dữ liệu và blockchain.

Định nghĩa các luồng và hợp đồng dữ liệu sau:

- Xác thực input cho một assessment mới và lựa chọn `dataset_id`/model artifact được phép.
- Chuỗi prediction -> SHAP -> record -> persist -> submit transaction -> confirmation -> verify, bao gồm hành vi retry.
- Các phương thức API/service hoặc hàm Python tương đương, schema request/response và ánh xạ trạng thái cho `PENDING`, `VERIFIED`, `MISMATCH`, `NOT_FOUND` và lỗi giao dịch.
- Các màn hình UI: tạo assessment, chi tiết assessment, trạng thái giao dịch, xác minh bản ghi hiện có, và màn hình audit/lỗi.
- Quy tắc: UI không bao giờ được gắn nhãn bản ghi là `VERIFIED` trước khi đủ xác nhận on-chain và cả hai hash đều khớp.

### 9. Bảo mật, quyền riêng tư và vận hành

Dự án đã loại dữ liệu cá nhân thô khỏi blockchain, nhưng các biện pháp kiểm soát triển khai vẫn chưa cụ thể.

Cần chỉ rõ:

- Cách private key và RPC URL chỉ được tải từ biến môi trường local/secret storage; tuyệt đối không commit chúng.
- Quy tắc redaction log cho profile đầu vào, giá trị SHAP, hash và metadata giao dịch.
- Cách xây dựng `input_reference` giả danh; nó không được là định danh cá nhân có thể đảo ngược hoặc applicant ID thuần.
- Giả định kiểm soát truy cập đối với tệp SQLite và dashboard.
- Hành vi lỗi và phục hồi khi SQLite không khả dụng, RPC không khả dụng, giao dịch thất bại, chain reorganization hoặc thiếu bản ghi off-chain.

### 10. Ma trận kiểm thử và định nghĩa hoàn thành

Các thí nghiệm E1-E7 dự kiến có phạm vi tốt nhưng cần các ca kiểm thử và tiêu chí đạt cụ thể.

Triển khai:

- Unit test cho ranh giới rò rỉ trong tiền xử lý, khả năng tái lập phép chia, hashing model artifact, tính cộng SHAP, serialization chuẩn hóa và lưu trữ cơ sở dữ liệu.
- Các smart-contract test mô tả ở mục 7.
- End-to-end test cho B0, B1 và B2, bao gồm việc cố ý thay đổi probability, đóng góp SHAP và phiên bản mô hình sau commit. Mỗi thay đổi phải khiến xác minh B2 trả về `MISMATCH`.
- Một test chứng minh rằng việc thay đổi đồng thời bản ghi và hash cục bộ trong SQLite không thể qua mặt xác minh B2.
- Golden-vector test dùng chung cho Python và mọi cài đặt chuẩn hóa khác.
- Giao thức đo hiệu năng: bối cảnh phần cứng/mạng, số lần lặp, chính sách warm-up, chỉ số báo cáo (khuyến nghị median và percentile), và việc báo cáo riêng kết quả Anvil với Sepolia.
- CI chạy formatting, unit test, contract test và golden vectors mà không dùng bí mật production.

## Trình tự triển khai đề xuất

1. Chốt các mục 1-5 và tạo khung repository, schema, dependency lockfile và golden vectors.
2. Cài đặt tải dữ liệu, split manifest, tiền xử lý, huấn luyện mô hình, đánh giá và artifact hashing cho một tập dữ liệu trước.
3. Cài đặt SHAP và bản ghi quyết định off-chain đầy đủ, lưu trữ SQLite và xác minh cục bộ.
4. Cài đặt và kiểm thử Vyper registry trên Anvil.
5. Tích hợp Web3.py và Streamlit; chạy B0/B1/B2 end to end.
6. Lặp lại pipeline ML độc lập cho tập dữ liệu thứ hai.
7. Chạy E1-E7, ghi nhận kết quả thực tế tách biệt với kết quả kỳ vọng, sau đó triển khai demonstration contract lên Sepolia nếu cần.

## Cổng sẵn sàng triển khai tối thiểu

Chỉ nên bắt đầu phát triển khi các hạng mục sau đã có và được rà soát:

- [ ] Môi trường đã khóa và `.env.example`
- [ ] Hợp đồng dữ liệu và split manifest
- [ ] Quy tắc đặc trưng/tiền xử lý và chống rò rỉ
- [ ] Giao thức huấn luyện, chọn ngưỡng và đánh giá
- [ ] Chính sách output-space và tính cộng SHAP
- [ ] JSON Schema, cài đặt chuẩn hóa và golden vectors
- [ ] SQLite schema và migrations
- [ ] Giao diện Vyper, mô hình vai trò, event, revert và test
- [ ] Hợp đồng trạng thái/lỗi của Backend/UI
- [ ] Xử lý bảo mật và kế hoạch kiểm thử tự động

## Lưu ý quan trọng về phạm vi

Commitment on-chain giúp bản ghi quyết định đã lưu trở nên có thể phát hiện chỉnh sửa sau khi được xác nhận. Nó không chứng minh dữ liệu đầu vào là trung thực, dự đoán mô hình là đúng đắn hoặc công bằng, SHAP có tính nhân quả, hay kho lưu trữ off-chain sẽ luôn sẵn có. Các giới hạn này cần tiếp tục được thể hiện rõ trong báo cáo cuối cùng và dashboard.
