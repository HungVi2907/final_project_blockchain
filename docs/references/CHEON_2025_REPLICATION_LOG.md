# Nhật ký tái thực nghiệm Cheon et al. (ICLR 2025)

**Nguồn số gốc:** [CHEON_2025_ORIGINAL_RESULTS.md](CHEON_2025_ORIGINAL_RESULTS.md). Không sửa bảng số gốc khi chạy lại. **Mã tác giả:** `ustunb/responsiveness`, nhánh `paper/iclr2025`, commit `4c68c73b34eef7c5e38847274048cb3ab66d702c`. Bản clone làm việc ở `artifacts/cheon_iclr2025/` và không được commit.

## Kiểm tra ban đầu — 19/11/2026

| Dataset | File nguồn trong repo tác giả | Dạng trước setup | Nhãn trong file | Giá trị thiếu trong file |
| --- | --- | ---: | --- | ---: |
| FICO HELOC | `research/iclr2025/data/fico/fico_data.csv` | 10.459 × 24 | `RiskPerformance`: `0=5.459`, `1=5.000` | 0 |
| German Credit | `research/iclr2025/data/german/german_data.csv` | 1.000 × 62 | `is_credit_risk_good`: `0=300`, `1=700` | 0 |
| Give Me Some Credit | `research/iclr2025/data/givemecredit/givemecredit_data.csv` | 150.000 × 11 | `NotSeriousDlqin2yrs`: `0=10.026`, `1=139.974` | 33.655 ô |

Đây là **file đầu vào của bước setup trong repo tác giả**, chưa phải dữ liệu sau xử lý 5.842 × 43 / 1.000 × 36 / 120.268 × 23 trong bài báo. SHA-256 theo thứ tự bảng trên: `65cf152304303b80c26c33808f7c2400e9b77f9222cc8160213d6893b11ee2a4`, `42a248f82f8fe2f914645dad92bf821a95e536ce7c3e0691ef359af79c098ee5`, `84e673ed862b69ccf2e75ad1572af029ff6a0d50a5014a77c91bc3bc1fec7da8`.

Sau khi chạy setup nguyên bản qua [launcher](../../scripts/replicate_cheon.py), kích thước và phân bố nhãn khớp số dòng/feature bài báo: FICO `5.842 × 43` (`Bad/-1=3.116`, `Good/+1=2.726`), German `1.000 × 36` (`Bad/-1=300`, `Good/+1=700`), Give Me Some Credit `120.268 × 23` (`Bad/-1=8.357`, `Good/+1=111.911`).

## Môi trường và sai khác cần theo dõi

- Windows, Python 3.10.11, `uv` 0.12.19. Bản clone đúng commit nêu trên.
- `uv sync --locked --no-default-groups --group ext` thất bại ở bước build package vì `hatch-vcs` không parse được tên nhánh/tag `paper/iclr2025` thành version. Cách chạy thử: `uv sync --locked --no-default-groups --group ext --no-install-project`, dùng import từ checkout tác giả; ghi rõ đây là **cách cài môi trường**, không thay đổi thuật toán.
- File `research/iclr2025/pyproject.toml` yêu cầu `scikit-learn==1.5.2`, `xgboost==2.1.4`; lockfile gốc ở thư mục repo hiện resolve 1.7.2/3.2.0 cho Python 3.10. Môi trường chạy lại đã ghim `scikit-learn==1.5.2`, `xgboost==2.1.4`, `imbalanced-learn==0.13.0`.
- Package `responsiveness==0.2.0a1` ghi trong pyproject của thư mục bài báo không còn tìm thấy trên registry. [Launcher](../../scripts/replicate_cheon.py) dùng mã package tại commit trên, ánh xạ `responsiveness.paths` và `responsiveness.ext.utils` tới bản trong `research/iclr2025/src`; các file `ext/training.py`, `ext/data.py`, `ext/fileutils.py`, `ext/cv.py`, `ext/metrics.py` trong package và thư mục nghiên cứu có checksum giống nhau.
- Mã `sample_processing` của tác giả resample cả test/validation khi `rebalance` được bật; `givemecredit` bật `rebalance='over'`. Điều này làm thay đổi tập đánh giá so với dữ liệu gốc và phải được ghi khi tái lập Table 11. Không tự sửa mã tác giả cho lần chạy đối chiếu đầu; nếu làm bản đánh giá không resample test, báo nó như thí nghiệm phụ riêng.
- Riêng `givemecredit`/XGBoost, `train_models.py` đặt `fold_num_validation=4`, `fold_num_test=5` và early stopping; train dùng 3/5 fold trước oversampling, khác mô tả tổng quát 80/20 của bài. LR/RF dùng 4/5 fold train. Đây là **sai khác giữa mã công khai và mô tả bài**, chưa đủ bằng chứng để kết luận nguyên nhân chênh lệch AUC.

### Lệnh dựng lại môi trường trên Windows

Chạy từ thư mục gốc project. Bản clone nằm trong `artifacts/` nên không đưa dữ liệu/model vào Git. Launcher từ chối commit khác commit đã khóa.

```powershell
git clone --branch paper/iclr2025 --single-branch https://github.com/ustunb/responsiveness.git artifacts/cheon_iclr2025
git -C artifacts/cheon_iclr2025 checkout 4c68c73b34eef7c5e38847274048cb3ab66d702c
Push-Location artifacts/cheon_iclr2025
uv sync --locked --no-default-groups --group ext --no-install-project
uv pip install --python .venv/Scripts/python.exe scikit-learn==1.5.2 xgboost==2.1.4 imbalanced-learn==0.13.0 psutil rich tabulate
uv pip install --python .venv/Scripts/python.exe ipython
Pop-Location
artifacts/cheon_iclr2025/.venv/Scripts/python.exe scripts/replicate_cheon.py setup --dataset german
artifacts/cheon_iclr2025/.venv/Scripts/python.exe scripts/replicate_cheon.py train --dataset german --model logreg
```

Sau smoke, đổi `--dataset` thành `fico`/`givemecredit`, chạy setup trước và lặp `--model logreg`, `xgb`, `rf`; cuối cùng chạy `artifacts/cheon_iclr2025/.venv/Scripts/python.exe scripts/compare_cheon_results.py`.

## AUC lưu trong artifact của lần tái lập — Table 11

Lệnh setup: `artifacts/cheon_iclr2025/.venv/Scripts/python.exe scripts/replicate_cheon.py setup --dataset <german|fico|givemecredit>`. Lệnh train: `artifacts/cheon_iclr2025/.venv/Scripts/python.exe scripts/replicate_cheon.py train --dataset <...> --model <logreg|xgb|rf>`. Chạy German/LR trước làm smoke, sau đó chạy đủ 9 tổ hợp. Tất cả dùng seed `2338`, fold `K05N01`, test fold `5`, action set `complex_nD` và mã tại commit nêu trên. [CSV so sánh đầy đủ](CHEON_2025_REPLICATION_COMPARISON.csv) có thời gian lưu, cỡ train/test, phiên bản thư viện và SHA-256 từng artifact.

| Dataset | Model | Train AUC lưu | Test AUC bài | Test AUC lưu | Chênh lệch |
| --- | --- | ---: | ---: | ---: | ---: |
| HELOC | LR | 0,7657 | 0,788 | 0,7775 | −0,0105 |
| HELOC | XGBoost | 0,7723 | 0,785 | 0,7903 | +0,0053 |
| HELOC | RF | 0,7819 | 0,790 | 0,7866 | −0,0034 |
| German | LR | 0,8067 | 0,760 | 0,7675 | +0,0075 |
| German | XGBoost | 0,9215 | 0,794 | 0,7802 | −0,0138 |
| German | RF | 0,8828 | 0,766 | 0,7745 | +0,0085 |
| Give Me Some Credit | LR | 0,8400 | 0,844 | 0,8424 | −0,0016 |
| Give Me Some Credit | XGBoost | 0,8659 | 0,793 | 0,8357 | +0,0427 |
| Give Me Some Credit | RF | 0,8643 | 0,835 | 0,8353 | +0,0003 |

**Diễn giải có giới hạn:** 8/9 test AUC lệch nhiều nhất 0,0138; XGBoost/Give Me Some Credit lệch +0,0427 và cần điều tra thêm trước khi gọi là tái lập gần kết quả gốc. Với HELOC, train/test thực tế là 4.674/1.168; German 800/200. Give Me Some Credit có test **44.764 sau oversampling**, LR/RF train 179.058 sau oversampling, còn XGBoost train 134.294 do dành fold validation riêng; không diễn giải chúng như số hồ sơ gốc. Nguồn của khác biệt XGBoost chưa được chứng minh; split/validation, sampling và lịch sử mã tác giả là các giả thuyết cần kiểm tra. Các kết quả trên mới tái lập **Table 11**, chưa chạy reachable-set/RESP của Tables 3–5/12 hoặc đánh giá SHAP của B.

Train AUC cũng chưa khớp đều: HELOC/XGBoost `0,859` (bài) so với `0,7723` (chạy lại), German/XGBoost `0,971` so với `0,9215`, German/RF `0,828` so với `0,8828`. Test AUC gần nhau không xóa được các chênh lệch này. Cần đối chiếu cấu hình tìm siêu tham số, checkpoint/model mà tác giả dùng cho Table 11 và cách tính train AUC trước khi khẳng định tái lập toàn bộ bảng.

## Kiểm chứng gói bàn giao HELOC của A — 25/11/2026

Gói `SuperBells_HELOC_XAI.zip` có SHA-256 `613823f7f6f82db9b8e1c77da941e5c47b7a8141cc9ffbc4c1198e05a3ba4663`. Bản giải nén nằm ở `artifacts/SuperBells_HELOC_XAI/`, gồm dữ liệu nguồn, 4.674 hồ sơ train, 1.168 hồ sơ test với 43 đặc trưng, ba mô hình, dự đoán test và 100 vị trí mẫu nền LR. Cả 20 checksum trong manifest đều khớp. Ba mã băm mô hình khớp bảng tái lập trong repo.

Chạy `verify_models.py` trong gói với Python 3.10.22 và đúng phiên bản thư viện trong `requirements.txt`. Dự đoán P(Bad) trên tập test khớp CSV bàn giao ở cả ba mô hình, với sai lệch tuyệt đối lớn nhất `2,22e-16`. Các số dưới đây được tính từ các pipeline đã huấn luyện và dữ liệu trong gói.

| Mô hình | AUC test lưu trong artifact | AUC test tính lại bằng scikit-learn |
| --- | ---: | ---: |
| LR | 0,7775 | 0,7882 |
| RF | 0,7866 | 0,7866 |
| XGBoost | 0,7903 | 0,7902 |

**Nguyên nhân chênh lệch LR.** Trình huấn luyện ở commit đã ghim chuẩn hóa train và test trong `sample_processing`, sau đó gắn cùng bộ chuẩn hóa vào pipeline LR. Khi lưu chỉ số, `_build_output` đưa dữ liệu đã chuẩn hóa vào pipeline, nên bộ chuẩn hóa chạy lần thứ hai. [Mã đánh giá của tác giả](https://github.com/ustunb/responsiveness/blob/4c68c73b34eef7c5e38847274048cb3ab66d702c/research/iclr2025/src/ext/training.py#L115-L227)

Chạy lại hàm `get_clf_stats` của tác giả trên cùng dữ liệu cho AUC test LR `0,7882` khi pipeline nhận đặc trưng trước chuẩn hóa. Khi đặc trưng được chuẩn hóa trước khi đưa vào pipeline, hàm tái lập AUC train `0,7657`, test `0,7775` và toàn bộ chỉ số LR lưu trong hai tập. Với XGBoost, hàm của tác giả tái lập `0,7903` trên đầu vào đúng và scikit-learn cho `0,7902` do cách xử lý điểm đồng hạng. Kết quả từng đường đánh giá nằm trong `artifacts/heloc_auc_trace.json`. [Hàm tính AUC của tác giả](https://github.com/ustunb/responsiveness/blob/4c68c73b34eef7c5e38847274048cb3ab66d702c/research/iclr2025/src/ext/metrics.py#L57-L74)

Proposal và báo cáo Tuần 4 dùng cột AUC tính lại bằng scikit-learn cho cả ba mô hình HELOC. Khi chạy thêm seed, dùng `roc_auc_score(label == -1, p_bad)` trên dự đoán của pipeline nhận đặc trưng trước chuẩn hóa.

## T1-01 trên bảy seed huấn luyện HELOC — 25/11/2026

Chạy 21 lượt fit với seed 2338–2344 trên cùng fold 5 của `K05N01`. Dữ liệu tái dựng từ mã tác giả khớp toàn bộ đặc trưng và nhãn của 4.674 hồ sơ train và 1.168 hồ sơ test trong gói A. AUC dùng `P(Bad)` tính từ pipeline trên đầu vào trước chuẩn hóa. Khoảng tin cậy t 95% phản ánh biến thiên giữa seed huấn luyện trên phép chia cố định.

| Mô hình | AUC test trung bình | Khoảng tin cậy 95% | AUC test Table 11 | Đạt biên ±0,02 |
| --- | ---: | ---: | ---: | --- |
| LR | 0,7882 | 0,7882–0,7882 | 0,788 | Có |
| RF | 0,7871 | 0,7859–0,7884 | 0,790 | Có |
| XGBoost | 0,7893 | 0,7886–0,7901 | 0,785 | Có |

Không gian tìm kiếm XGBoost của tác giả tạo 9 ứng viên có `subsample > 1` qua bảy seed. Các ứng viên này thất bại trong cross-validation. Cả bảy lượt huấn luyện XGBoost hoàn tất với các ứng viên hợp lệ. Lưu AUC và siêu tham số từng lượt trong `artifacts/heloc_training_t1/`.

Tính lại SHAP trên cả 1.168 hồ sơ cho sai số cộng lớn nhất `1,33e-15`. Xác suất, giá trị nền, log-odds và 43 đóng góp khớp cả ba hồ sơ B sau khi làm tròn 8 chữ số. Tái lập phép thử mẫu nền lồng nhau trên 40 hồ sơ và 5 seed cho trung vị trùng top 5 là `1,00`, khoảng `0,80–1,00` khi so 100 với 200 dòng. Kết quả chi tiết nằm trong `artifacts/role_a_heloc_verification.json`. [Báo cáo bàn giao của B](../ROLE_B_HELOC_REPORT.md)
