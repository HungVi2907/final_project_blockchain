# Đặc tả phương pháp chi tiết và kế hoạch làm việc cho ba người

> **Bản kế hoạch Tuần 3 lưu trữ.** Phần dữ liệu/ML đã được thay bằng [bối cảnh ICLR 2025](PROJECT_CONTEXT.md) ngày 19/11/2026. Các bước Taiwan/Home Credit và seed 42 bên dưới chỉ phản ánh kế hoạch cũ; thiết kế SHAP, bản ghi và blockchain S7–S11 cần được áp dụng sau khi nâng dataset ID, schema và xử lý chiều nhãn FICO.

Tài liệu này triển khai quy trình S1–S11 của báo cáo Tuần 3 thành các bước có đầu vào, đầu ra, cách thực hiện và phép kiểm chứng. Hệ thống là nguyên mẫu nghiên cứu đánh giá rủi ro tín dụng có giải thích và bằng chứng toàn vẹn, không phải hệ thống phê duyệt khoản vay thực tế. Hai bộ Home Credit và Taiwan được xử lý độc lập từ chia dữ liệu đến đánh giá; chỉ bản ghi quyết định và cam kết của nó dùng chung một giao thức.

Các con số trong ví dụ dưới đây là **giả lập**. Ngưỡng, seed, dung sai và giao diện được nêu là **đề xuất triển khai** để nhóm có thể bắt đầu, không phải kết quả đã đo hoặc lựa chọn đã được báo cáo Tuần 3 xác nhận. Nhóm phải chốt chúng trong cấu hình và kiểm thử trước khi tạo kết quả chính thức.

## Quy ước và giao diện cần chốt trước

- `dataset_id` chỉ nhận `home_credit_2018` hoặc `taiwan_uci350`. Nhãn dương `y=1` là trường hợp vỡ nợ/khó khăn thanh toán theo nhãn tương ứng của từng nguồn.
- Dùng seed đề xuất `42` cho phép chia và huấn luyện có yếu tố ngẫu nhiên; lưu seed cùng checksum nguồn và danh sách ID của từng split. Chỉ lấy các hàng Home Credit có `TARGET`; không dùng `application_test.csv` không nhãn để đánh giá.
- Mỗi artifact gồm đúng một pipeline tiền xử lý đã fit, mô hình đã chọn, danh sách feature theo thứ tự, ngưỡng phân lớp, `dataset_id`, `model_version` và `model_artifact_sha256`. File manifest ràng buộc hash với chính bytes của gói pipeline/mô hình; tránh tự băm manifest có chứa chính hash của nó.
- Giao diện giữa các phần: `predict(dataset_id, feature_dict) -> {risk_probability, predicted_label, model_version, model_artifact_sha256, transformed_features}`; `explain(artifact, transformed_features) -> shap_explanation`; `create_record(prediction, explanation, input_reference) -> {R, canonical_bytes}`; `register(decision_id, record_hash, model_version_hash) -> tx_hash`; `verify(decision_id) -> status`.
- `decision_id` là 32 byte ngẫu nhiên biểu diễn dạng hex chữ thường 64 ký tự trong `R`, chuyển sang `bytes32` khi gọi contract. `input_reference` là mã ngẫu nhiên độc lập, không dùng ID hồ sơ gốc hoặc hash trực tiếp của ID gốc. `nonce` được tạo một lần bằng bộ sinh số ngẫu nhiên mật mã; đề xuất 16 byte dạng hex 32 ký tự.
- Đóng băng JSON Schema v1 và golden vectors trước khi ba nhánh triển khai song song. Mọi thay đổi schema/giao diện sau đó cần một PR riêng, có xác nhận của cả ba người.

## S1. Thu thập và kiểm kê dữ liệu

**Đầu vào:** Tệp `application_train.csv` của Home Credit từ Kaggle và bộ Default of Credit Card Clients từ UCI. Tệp `application_test.csv` của Kaggle không có nhãn nên không tham gia thí nghiệm có giám sát.

**Thực hiện:** Tải theo điều khoản nguồn, ghi URL, ngày tải, tên tệp, số hàng/cột, checksum SHA-256 và quyền sử dụng. Kiểm tra có cột `TARGET` hoặc `default.payment.next.month`; nhận diện `SK_ID_CURR`/`ID` để theo dõi dòng, không dùng làm predictor. Ví dụ giả lập: hàng Home Credit có `SK_ID_CURR=100001`, `AMT_CREDIT=420000`, `TARGET=1` trở thành một dòng có khóa riêng trong manifest; ID không đi vào ma trận mô hình.

**Đầu ra:** Data inventory và tệp nguồn trong thư mục local bị Git ignore. Không commit dữ liệu cá nhân hoặc tệp nguồn thô.

**Tham số cần chốt:** Phiên bản nguồn, bảng Home Credit phụ được phép dùng. Bản đầu tiên nên chỉ dùng `application_train.csv`; bảng phụ chỉ thêm khi có quy tắc thời điểm dữ liệu sẵn có và phép tổng hợp rõ ràng.

**Kiểm chứng:** So checksum sau tải; kiểm tra cột nhãn, ID, kiểu dữ liệu, số dòng, tỷ lệ nhãn và các giá trị trùng/thiếu. Đối chiếu số liệu EDA với tệp đã tải, không lấy tỷ lệ lớp công bố trong bài báo làm số liệu đo của nhóm.

## S2. Khám phá dữ liệu và chia tập

**Đầu vào:** Các hàng có nhãn và ID ổn định từ S1, riêng cho từng `dataset_id`.

**Thực hiện:** Báo cáo tỷ lệ lớp, missingness, miền giá trị, trùng lặp và cột có nguy cơ rò rỉ. Chia phân tầng 70/15/15: trước tiên tách 15% test, rồi tách validation bằng `15/85` của 85% còn lại. Lưu ID train/validation/test cùng seed và checksum nguồn. Ví dụ giả lập với 100 dòng: khoảng 70/15/15 dòng; số lượng thực tế có thể lệch do làm tròn và phân tầng.

```text
for dataset in [home_credit_2018, taiwan_uci350]:
    labeled = load_and_validate(dataset)
    train_val, test = stratified_split(labeled, test_size=0.15, seed=42)
    train, val = stratified_split(train_val, test_size=15/85, seed=42)
    save_manifest(dataset, source_sha256, seed, IDs(train), IDs(val), IDs(test))
```

**Đầu ra:** Ba split và EDA report cho mỗi bộ dữ liệu; không có hàng chung giữa các split.

**Tham số:** Tỷ lệ 70/15/15 đã có trong Tuần 3; seed `42` là đề xuất. Quy tắc xử lý ID/hàng trùng phải được ghi trong data contract trước khi chia.

**Kiểm chứng:** Assert giao ba tập ID rỗng, hợp bằng toàn bộ ID hợp lệ, tỷ lệ lớp từng tập gần tỷ lệ nguồn và chạy lại cùng seed tạo manifest y hệt. Kiểm tra các cột chỉ xuất hiện sau thời điểm quyết định bị loại.

## S3. Tiền xử lý không rò rỉ

**Đầu vào:** Feature thô trong train/validation/test từ S2 và allow-list riêng cho mỗi dataset.

**Thực hiện:** Fit imputer và encoder trên train; chỉ `transform` validation/test. Với LR, chuẩn hóa biến số bằng scaler fit trên train. RF/XGBoost có thể dùng nhánh tiền xử lý thích hợp nhưng cùng hợp đồng feature. Ví dụ giả lập: median `AMT_INCOME_TOTAL` của train là `120000`; giá trị thiếu ở validation được điền `120000`, không tính lại median từ validation. Các cột ID/target không tham gia phép biến đổi. Nếu dùng bảng lịch sử Home Credit, chỉ tổng hợp sự kiện có sẵn trước thời điểm đánh giá.

```text
preprocessor = build_pipeline(feature_schema, model_family)
X_train = preprocessor.fit_transform(train_features)
X_val   = preprocessor.transform(val_features)
X_test  = preprocessor.transform(test_features)
```

**Đầu ra:** Ma trận số có thứ tự cột cố định và pipeline tiền xử lý đã fit cho từng dataset/model family.

**Tham số:** Chiến lược impute (đề xuất median cho số, nhãn `MISSING` cho category), quy tắc mã hóa category chưa thấy, scaling của LR, xử lý giá trị bất hợp lệ và ngoại lệ. Những lựa chọn này phải ghi trong `data_contract.md`.

**Kiểm chứng:** Test đổi toàn bộ giá trị validation/test mà trạng thái imputer/scaler/encoder không thay đổi; số cột và thứ tự cột của ba split bằng nhau; không còn NaN hoặc giá trị vô hạn khi mô hình yêu cầu đầu vào hữu hạn.

## S4. Huấn luyện ứng viên

**Đầu vào:** `X_train`, `y_train` và pipeline riêng của mỗi dataset từ S3.

**Thực hiện:** Huấn luyện Logistic Regression, Random Forest và XGBoost. Đề xuất dùng stratified 5-fold CV **chỉ trong train** để chọn siêu tham số theo PR-AUC; validation vẫn giữ nguyên cho chọn mô hình và ngưỡng. Có thể đặt grid nhỏ để phù hợp tài nguyên: LR `C ∈ {0.1,1,10}`; RF `n_estimators ∈ {200,400}`, `max_depth ∈ {None,10}`; XGBoost `n_estimators ∈ {200,400}`, `max_depth ∈ {3,6}`, `learning_rate ∈ {0.05,0.1}`. Điều chỉnh grid sau thử nghiệm tài nguyên phải được ghi lại. Nếu resampling, nó phải nằm bên trong từng fold train, không áp dụng trước khi chia hoặc lên validation/test.

**Đầu ra:** Ba ứng viên cùng hyperparameter và điểm CV cho từng dataset.

**Tham số:** Seed `42`, `class_weight`/`scale_pos_weight` hoặc không cân bằng lớp; metric CV là average precision (PR-AUC); phiên bản dependency khóa trong lockfile.

**Kiểm chứng:** Huấn luyện lại cùng dữ liệu/seed/phiên bản cho cùng cấu hình và so metric trong dung sai đã ghi; assert không fit dữ liệu validation/test; báo cáo số mẫu từng fold và tỷ lệ lớp. Nếu thuật toán không hoàn toàn xác định trên phần cứng đang dùng, ghi dung sai thay vì hứa hash artifact giống nhau tuyệt đối.

## S5. Chọn mô hình, ngưỡng và đóng băng artifact

**Đầu vào:** Ứng viên S4 và validation chưa dùng trong fit; test được giữ kín tới cuối.

**Thực hiện:** Tính PR-AUC và ROC-AUC trên validation. Quy tắc đề xuất: chọn PR-AUC cao nhất, phá hòa bằng ROC-AUC rồi mô hình đơn giản hơn. Chọn ngưỡng `t` trên validation bằng F1 lớp dương; nếu F1 hòa, chọn ngưỡng có Recall cao hơn rồi ngưỡng nhỏ hơn. Cố định mô hình, tiền xử lý và `t`, sau đó chạy test **một lần**. Với `p = 0.72`, `t = 0.40`, nhãn dự đoán là `1`.

```text
winner = argmax(candidates, key=(val_PR_AUC, val_ROC_AUC, simplicity))
t = argmax_threshold(val_probabilities, metric=F1_for_y1)
test_probabilities = winner.predict_proba(X_test)[:, 1]
save_bundle(winner, preprocessor, feature_schema, t, metadata)
model_artifact_sha256 = SHA256(exact_saved_bundle_bytes)
```

**Đầu ra:** Một artifact được chọn cho mỗi dataset; manifest phiên bản, hash, ngưỡng, confusion matrix và ROC-AUC, PR-AUC, Recall, F1 trên test tương ứng.

**Tham số:** Dải threshold lấy từ các xác suất validation hoặc grid cố định `[0,1]` bước `0.01` (cần chọn một cách trước khi chạy); định nghĩa Recall `TP/(TP+FN)`, Precision `TP/(TP+FP)`, F1 `2PR/(P+R)`, đều cho `y=1`. Nếu báo cáo khoảng tin cậy, đề xuất bootstrap phân tầng test 1000 lần, seed `42`, nhưng không dùng bootstrap để chọn lại mô hình.

**Kiểm chứng:** Assert artifact tải lại cho cùng xác suất (trong dung sai số); hash bytes khớp manifest; test chỉ được đánh giá sau khi lựa chọn và ngưỡng đã khóa. Báo cáo kết quả riêng từng dataset; không suy luận chuyển giao từ chênh lệch AUC giữa hai bộ.

## S6. Suy luận một hồ sơ

**Đầu vào:** `dataset_id`, dictionary feature thô đúng schema và artifact tương ứng. Ví dụ giả lập: `{"dataset_id":"taiwan_uci350","LIMIT_BAL":50000,"AGE":27,"PAY_0":2,...}`; dấu `...` là các feature bắt buộc còn lại, không phải input hợp lệ để chạy thật.

**Thực hiện:** Kiểm tra kiểu, miền giá trị, cột bắt buộc và version; chạy đúng pipeline đã lưu; lấy `risk_probability = predict_proba(x)[1]` và `predicted_label = 1[p >= t]`. Sinh `input_reference` ngẫu nhiên không chứa `ID` gốc. Không chọn artifact Home Credit cho hồ sơ Taiwan.

**Đầu ra:** Xác suất, nhãn, tham chiếu giả danh và feature sau biến đổi cho S7. Ví dụ giả lập: `p=0.72000000`, `t=0.40`, `label=1`.

**Tham số:** Schema feature và ngưỡng từ artifact; giới hạn giá trị hợp lệ từ data contract. Không tự điền các feature bắt buộc còn thiếu ngoài quy tắc imputation đã khóa.

**Kiểm chứng:** Test dataset ID sai hoặc thiếu feature trả lỗi có cấu trúc; cùng input/artifact cho cùng xác suất; prediction qua service khớp lời gọi trực tiếp artifact; không rò rỉ ID gốc vào output.

## S7. Giải thích SHAP

**Đầu vào:** Artifact đã chọn, vector đã transform và xác suất từ S6.

**Thực hiện:** Dùng explainer tương thích với model family (ví dụ `LinearExplainer` cho LR, `TreeExplainer` cho RF/XGBoost). Mỗi artifact khai báo `method`, `output_space`, feature names và cách chọn background train. Đề xuất background tối đa 200 hàng train, lấy mẫu bằng seed `42`; xác định `output_space` theo API thực tế của explainer đã khóa. Kiểm tra trước khi làm tròn:

`abs(base_value + Σ feature_contributions − model_output) <= tolerance`.

Ví dụ **giải thích đồ chơi** có hai feature trong không gian xác suất: `base_value=0.20`, đóng góp `+0.40` và `+0.12`, nên `model_output=0.72`. Bản ghi thực phải chứa **mọi** đóng góp cho đầy đủ feature sau biến đổi; ví dụ hai feature này không đại diện cho schema Home Credit/Taiwan. Nếu dùng raw margin/log-odds, `model_output` là margin, còn `risk_probability` vẫn là `predict_proba`, không cộng SHAP margin trực tiếp vào xác suất.

**Đầu ra:** `shap_explanation={method,output_space,base_value,model_output,feature_contributions}` cho một hồ sơ; biểu đồ SHAP toàn cục được tính riêng từ mẫu đánh giá, không nhét vào `R`.

**Tham số:** Explainer, giới hạn background, phiên bản SHAP, dung sai đề xuất `1e-5` trên giá trị chưa làm tròn (kiểm chứng lại với model thực), quy tắc tên feature one-hot và aggregation.

**Kiểm chứng:** Kiểm tra additivity, số feature contribution bằng số feature đã transform, thứ tự và tên đúng schema, mọi giá trị hữu hạn. Nếu thất bại, dừng tạo bản ghi và ghi lỗi; không gửi cam kết on-chain cho lời giải thích chưa đạt.

## S8. Tạo và lưu bản ghi quyết định I1

**Đầu vào:** S6, S7, `model_version`, `model_artifact_sha256`, `dataset_id`.

**Thực hiện:** Tạo `R` với `schema_version="1"`, `dataset_id`, `decision_id`, `input_reference`, `model_version`, `model_artifact_sha256`, `risk_probability`, `shap_explanation`, `timestamp_utc`, `nonce`. Sinh timestamp UTC chính xác tới giây và nonce **một lần**. Chuyển các số thực sang chuỗi thập phân 8 chữ số theo chế độ làm tròn đã chốt (đề xuất decimal half-even), không dùng float JSON cho các trường này. Lưu JSON hiển thị và canonical bytes dạng BLOB trong SQLite; nếu giữ hai bản, so canonical hóa JSON với BLOB khi đọc.

**Đầu ra:** `R`, canonical UTF-8 bytes và trạng thái bản ghi `PENDING`; chưa được gọi là `VERIFIED`.

**Tham số:** JSON Schema v1, độ dài ID/nonce, chính sách làm tròn, các trường bắt buộc và kiểu. Ví dụ rút gọn: `{"schema_version":"1","dataset_id":"taiwan_uci350","risk_probability":"0.72000000",...}` chỉ minh họa trường, không phải golden vector đầy đủ.

**Kiểm chứng:** Validate JSON Schema; round-trip canonical bytes; unique `decision_id`; kiểm tra không có ID nguồn hoặc dữ liệu cá nhân thô trong `R`; thử tạo lại cùng bản ghi không sinh timestamp/nonce mới trong quá trình verify. Test SQLite transaction rollback và retry theo `decision_id`.

## S9. Chuẩn hóa và tính hai cam kết I1

**Đầu vào:** `R` và canonical bytes được lưu từ S8.

**Thực hiện:** NFC hóa chuỗi; sort key JSON đệ quy; sort `feature_contributions` theo tên feature; dùng số thực là chuỗi 8 chữ số thập phân, JSON không khoảng trắng thừa và UTF-8. Từ chối NaN/Infinity, tên feature trùng, kiểu hoặc chuỗi Unicode không hợp lệ. Tính:

`record_hash = SHA256(canonical_bytes)`

`model_version_hash = SHA256(UTF8(model_version + "|" + model_artifact_sha256))`.

Đổi hai digest 32 byte và `decision_id` 32 byte thành `bytes32` cho contract. Ví dụ giả lập: đổi `risk_probability` từ `"0.72000000"` sang `"0.73000000"` làm `record_hash` thay đổi; đổi `model_version` làm cả `record_hash` và `model_version_hash` thay đổi.

**Đầu ra:** Ba giá trị `bytes32` (`decision_id`, `record_hash`, `model_version_hash`) và golden vectors xác định.

**Tham số:** Đặc tả chính xác cho negative zero, số mũ, `null`, mảng khác, escaping, Unicode lỗi và cách biểu diễn hex cần chốt trong schema/golden vectors trước khi tính hash chính thức.

**Kiểm chứng:** Hai lần serialize cùng `R` tạo cùng bytes và digest; đổi xác suất/SHAP/version làm hash thích hợp đổi; invalid input bị từ chối. Golden vectors gồm canonical bytes và hai hash dự kiến, dùng chung cho mọi bên cài đặt.

## S10. Ghi cam kết vào Vyper registry I1

**Đầu vào:** Ba `bytes32` từ S9, tài khoản writer và RPC của Anvil (Sepolia chỉ dùng khi cấu hình được và cần demo).

**Thực hiện:** Admin triển khai contract và `grant_writer`. Writer gọi `register_record(decision_id,record_hash,model_version_hash)`; contract từ chối writer không được cấp quyền, ID trùng và hash bằng không; lưu cam kết bất biến và phát `RecordRegistered`. Backend ghi `tx_hash`, `chain_id`, receipt, block, gas và số xác nhận vào SQLite. Retry cùng `decision_id` phải tra receipt/chain trước khi gửi lại, tránh tạo giao dịch trùng.

**Đầu ra:** Commitment on-chain và audit log; trạng thái vẫn `PENDING` cho đến khi đủ số xác nhận và xác minh S11.

**Tham số:** ABI, compiler/bytecode version, RPC, chain ID, địa chỉ contract, số xác nhận tối thiểu (đề xuất 1 trên Anvil; quy tắc Sepolia cần chốt theo mục tiêu demo), gas policy và timeout.

**Kiểm chứng:** Contract test cho grant/revoke, writer không hợp lệ, ID trùng, zero hash, bất biến, event, getter và view verification. Đối chiếu receipt thành công với đúng chain/contract và ba tham số đăng ký.

## S11. Xác minh và hiển thị kết quả I1

**Đầu vào:** `decision_id`, bản ghi/bytes trong SQLite, receipt và cam kết trên chain.

**Thực hiện:** Nếu giao dịch chưa đủ xác nhận, trả `PENDING`. Nếu không có bản ghi hoặc commitment, trả `NOT_FOUND` với nguồn thiếu được ghi rõ; giao dịch thất bại có trạng thái lỗi riêng, không gộp thành `VERIFIED`. Khi đủ xác nhận, kiểm tra JSON và canonical bytes khớp nhau; hash lại bytes đã lưu; tính lại `model_version_hash` từ `R`; đọc chain và so cả hai hash. Trả `VERIFIED` chỉ khi tất cả bằng nhau; sai bất kỳ phần nào trả `MISMATCH`. Giao diện hiển thị xác suất, giải thích, version, trạng thái, transaction/block/gas và lý do lỗi thích hợp.

```text
verify(id):
    local = sqlite.get(id)
    chain = registry.get_record(id)
    if local is missing or chain is missing: return NOT_FOUND
    if tx_failed(local): return TRANSACTION_FAILED
    if not sufficiently_confirmed(local): return PENDING
    if canonical_serialize(local.display_json) != local.canonical_bytes: return MISMATCH
    if SHA256(local.canonical_bytes) != chain.record_hash: return MISMATCH
    if SHA256(UTF8(local.R.model_version + "|" + local.R.model_artifact_sha256)) != chain.model_version_hash: return MISMATCH
    return VERIFIED
```

**Đầu ra:** `VERIFIED`, `MISMATCH`, `NOT_FOUND`, `PENDING` hoặc lỗi giao dịch/RPC riêng; màn hình chi tiết và audit.

**Tham số:** Số xác nhận, timeout RPC, chính sách chain reorganization, mapping lỗi UI. Khi RPC không khả dụng, hiển thị `UNAVAILABLE` hoặc lỗi xác minh, không suy đoán trạng thái từ SQLite.

**Kiểm chứng:** End-to-end test cho B0 (bản ghi SQLite), B1 (bản ghi + hash cùng SQLite) và B2 (cam kết on-chain). Sau khi B2 confirmed, sửa riêng probability, SHAP contribution, model version; cả ba phải `MISMATCH`. Sửa đồng thời bản ghi và hash local của B1 vẫn không vượt qua B2. Test pending, thiếu bản ghi, giao dịch lỗi, RPC lỗi và chain reorganization giả lập.

## Đo lường E1–E7

| Thí nghiệm | Dữ liệu cần lưu và tiêu chí kiểm tra |
| --- | --- |
| E1: mô hình | ROC-AUC, PR-AUC, Recall, F1, confusion matrix, threshold, CI nếu tính; so sánh LR/RF/XGB chỉ trong cùng dataset/split. |
| E2: SHAP | Residual additivity chưa làm tròn, `output_space`, số feature và biểu đồ local/global; bản ghi không được tạo khi residual vượt dung sai. |
| E3: sửa dữ liệu | Ma trận kịch bản sửa probability, SHAP, version, record + local hash; báo cáo số lần phát hiện và báo động sai cho B0/B1/B2. |
| E4: phân quyền | Test writer, non-writer, revoke, ID trùng, hash zero; mọi thao tác bị cấm phải revert. |
| E5: chi phí | Gas mỗi lần ghi, phí ước tính/thực trả, thời gian xác nhận; ghi môi trường phần cứng, mạng, số lần lặp và thống kê median/p95. Tách Anvil và Sepolia. |
| E6: toàn trình | Độ trễ tạo bản ghi -> confirmed -> VERIFIED và các trạng thái lỗi; không bao giờ `VERIFIED` khi pending. |
| E7: độ nhạy dữ liệu | Báo cáo E1/E2 riêng Home Credit và Taiwan; không gộp dữ liệu hay chuyển artifact giữa chúng. |

## Kế hoạch ba người không xung đột

Phân theo **quyền sở hữu file và đầu ra**, không phân theo hai dataset: một người duy trì cả hai pipeline ML để tránh hai schema/metric lệch nhau; hai người còn lại làm lõi kiểm toán và tích hợp blockchain/UI. Có thể gán tên sau; kế hoạch dùng vai trò A/B/C vì nhóm Tuần 3 có sáu thành viên nhưng yêu cầu hiện tại là ba người.

| Người | Sở hữu chính | File/thư mục được sửa | Bàn giao và tiêu chí hoàn thành |
| --- | --- | --- | --- |
| A — Dữ liệu và ML | S1–S6, E1/E7 | `src/data/`, `src/ml/`, `tests/data/`, `tests/ml/`, `docs/data_contract.md`, split manifest | Hai artifact độc lập, `predict()` theo giao diện đã khóa, báo cáo EDA/metric/test không rò rỉ. |
| B — SHAP và bản ghi | S7–S9, SQLite, E2/E3 | `src/explain/`, `src/records/`, `src/storage/`, `schemas/`, `tests/explain/`, `tests/records/`, `tests/storage/` | `explain()`, `create_record()`, `canonical_serialize()`, golden vectors, migration SQLite và kiểm thử sửa đổi local. |
| C — Chain và ứng dụng | S10–S11, E4–E6 | `contracts/`, `src/chain/`, `src/app/`, `tests/contracts/`, `tests/e2e/`, `scripts/deploy/` | Vyper registry, Web3 adapter, Streamlit, trạng thái xác minh, test end-to-end B0/B1/B2. |

**Quy tắc file chung:** Một người điều phối tạo `pyproject.toml`/lockfile, `.env.example`, `README.md`, CI và file giao diện `docs/interface_contract.md` trong giai đoạn khởi động; sau khi khóa, các thay đổi vào chúng phải qua PR riêng được cả ba review. Không để cả ba cùng sửa một file trong một sprint. A/B/C tạo test dưới nhánh thư mục của mình; C sở hữu test tích hợp, A và B cung cấp fixtures, golden vectors và artifact test. Dữ liệu nguồn, model artifact, database và secret nằm trong `.gitignore`.

### Mốc phối hợp và phụ thuộc

| Mốc | A | B | C | Cổng tích hợp |
| --- | --- | --- | --- | --- |
| 0 — Khóa giao diện | Chốt feature schema và dạng artifact | Chốt JSON Schema, số thập phân, bytes và golden vectors | Chốt ABI, trạng thái, request/response | Cả ba duyệt `interface_contract.md`; chưa tích hợp qua lời gọi giả định. |
| 1 — Làm song song | S1–S5 trên Taiwan trước, rồi Home Credit | S7–S9 với prediction fixture giả lập, SQLite | Contract trên Anvil với hash golden vector, UI mock | Unit/contract test từng nhánh xanh. |
| 2 — Nối dây | Xuất `predict()` và hai artifact | Nối `explain()`/`create_record()` với A | Nối registry và dashboard với B | Một hồ sơ Taiwan hoàn tất S6–S11 trên Anvil, có thể VERIFY. |
| 3 — Hoàn thiện | Home Credit và E1/E7 | E2/E3, kiểm thử lỗi | E4–E6, test B0/B1/B2 | CI xanh; kết quả thực đo được lưu riêng với kỳ vọng; demo trạng thái pending/mismatch. |

Nếu thời gian ngắn, ưu tiên chạy toàn trình trên Taiwan và Anvil để kiểm tra giao diện trước, rồi bổ sung Home Credit khi nguồn Kaggle và tài nguyên huấn luyện sẵn có. Đây là thứ tự thực hiện; báo cáo cuối chỉ công bố kết quả của các thí nghiệm thực sự đã chạy.

## Điều kiện hoàn thành

- [ ] Hai dataset có source checksum, split manifest và kiểm thử chống rò rỉ; không có test-set tuning.
- [ ] Mỗi dataset có một artifact versioned và metric test riêng; model/feature không dùng chéo.
- [ ] Mọi bản ghi có SHAP đầy đủ, vượt qua kiểm tra additivity trước làm tròn, schema v1 và canonical bytes ổn định.
- [ ] Contract từ chối ghi trái quyền/trùng ID, phát event và giữ commitment bất biến.
- [ ] Xác minh so cả `record_hash` lẫn `model_version_hash` sau xác nhận; các thay đổi giả lập trả `MISMATCH`.
- [ ] E1–E7 có kết quả đo, cấu hình chạy và log tái lập; giới hạn về tính đúng của dữ liệu, tính công bằng, quan hệ nhân quả SHAP và tính sẵn có off-chain được nêu trong demo/báo cáo.
