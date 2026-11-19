# Hợp đồng dữ liệu — hướng ICLR 2025

**Nguồn phương pháp chính:** [Cheon et al., ICLR 2025](PROJECT_CONTEXT.md). Hợp đồng dữ liệu cho kết quả chính sẽ theo ba dataset của tác giả, ưu tiên FICO HELOC cho luồng A → B → C. Các mục Taiwan/Home Credit bên dưới chỉ mô tả nguyên mẫu và kế hoạch cũ; chúng không phải dữ liệu tái lập ICLR.

## FICO HELOC — nguồn chính, chưa tái lập tại repo nhóm

Nguồn thực nghiệm: [thư mục FICO trong mã tác giả](https://github.com/ustunb/responsiveness/tree/paper/iclr2025/research/iclr2025/data/fico), gồm dữ liệu và script xử lý. Bài báo báo cáo 5.842 dòng, 43 feature sau xử lý; test AUC LR/XGBoost/RF = 0,788/0,785/0,790 với train/test 80/20. Cần kiểm chứng lại trên file thực, lưu commit SHA, checksum, quyền sử dụng, tỷ lệ lớp, missing/special values, feature list và split manifest. Script tác giả đặt seed 2338 và `fold_id=K05N01`; xác nhận fold thực tế trước khi công bố kết quả nhóm.

**Nhãn:** `RiskPerformance` được mã hóa `Good=1`, `Bad=0` trong script FICO. Giữ chiều nhãn đó khi đối chiếu AUC bài báo. Adapter xuất bản ghi nhóm phải tính `risk_probability=P(Bad)=1-P(Good)`; B giải thích đúng đầu ra này và kiểm tra additivity. Không dùng `predict_proba[:,1]` trực tiếp làm risk.

## German Credit và Give Me Some Credit — kiểm tra độc lập

[German](https://github.com/ustunb/responsiveness/tree/paper/iclr2025/research/iclr2025/data/german) là tập nhỏ để smoke, [Give Me Some Credit](https://github.com/ustunb/responsiveness/tree/paper/iclr2025/research/iclr2025/data/givemecredit) là tập lớn để mở rộng. Bài báo nêu lần lượt 1.000 và 120.268 dòng sau xử lý. Mỗi tập có preprocessing, split, artifact và mapping nhãn riêng; không chuyển mô hình giữa các tập. Chưa có EDA hoặc kết quả tái lập của nhóm trên hai tập này.

## Hồ sơ dữ liệu cũ — chỉ dùng cho smoke và lịch sử

## Taiwan UCI 350 — đã kiểm tra trên tệp gốc

Nguồn chính thức: https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients (DOI 10.24432/C55S3H, CC BY 4.0). Script `scripts/download_taiwan.py` tải ZIP chính thức và lưu checksum trong `data/raw/taiwan_source_manifest.json`. Tệp XLS hiện có SHA-256 `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`.

Đọc sheet `Data` với header ở hàng thứ hai. Tệp có 30.000 dòng, 23 predictors, cột `ID` và nhãn `default payment next month`. Phân bố nhãn thực đo: `0=23.364`, `1=6.636` (22,12% dương). Không có ô NaN; 56 hàng trùng toàn bộ 23 predictor nhưng có ID khác. Bản smoke giữ các hàng đó, chỉ loại `ID` khỏi mô hình. Cần đánh giá chính sách hàng trùng trước thí nghiệm chính thức.

Allow-list predictor: `LIMIT_BAL`, `SEX`, `EDUCATION`, `MARRIAGE`, `AGE`, `PAY_0`, `PAY_2`–`PAY_6`, `BILL_AMT1`–`BILL_AMT6`, `PAY_AMT1`–`PAY_AMT6`. Các mã `EDUCATION` 0/5/6, `MARRIAGE` 0 và `PAY_0` -2/0 có mặt trong dữ liệu; smoke giữ dạng số gốc, không tự diễn giải hay remap. Trước E1 chính thức cần chốt xử lý các mã này và kiểm tra tính nhạy cảm của nhân khẩu học.

Chia phân tầng 70/15/15 với seed 42 thành 21.000/4.500/4.500 dòng. `artifacts/taiwan_split.json` lưu ID từng tập và checksum nguồn. Imputer median và scaler của bản smoke chỉ fit trên train. Mô hình demo LR dùng validation để chọn ngưỡng; test được đánh giá một lần. Đây chưa phải tìm kiếm và so sánh LR/RF/XGBoost của E1.

## Home Credit — chưa tải và chưa kiểm chứng thực nghiệm

Nguồn dự kiến: https://www.kaggle.com/competitions/home-credit-default-risk/data, theo điều khoản Kaggle. Dự kiến chỉ dùng `application_train.csv` có nhãn `TARGET` cho split và evaluation; `application_test.csv` không có nhãn. `SK_ID_CURR` chỉ dùng ID/join, không làm predictor. Bảng phụ và quy tắc tránh rò rỉ theo thời gian chưa chốt; pipeline này chưa được triển khai. Không gộp dữ liệu hoặc chuyển model giữa Home Credit và Taiwan.

