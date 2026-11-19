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

## Kết quả chạy lại phần dự đoán — Table 11

Lệnh setup: `artifacts/cheon_iclr2025/.venv/Scripts/python.exe scripts/replicate_cheon.py setup --dataset <german|fico|givemecredit>`. Lệnh train: `artifacts/cheon_iclr2025/.venv/Scripts/python.exe scripts/replicate_cheon.py train --dataset <...> --model <logreg|xgb|rf>`. Chạy German/LR trước làm smoke, sau đó chạy đủ 9 tổ hợp. Tất cả dùng seed `2338`, fold `K05N01`, test fold `5`, action set `complex_nD` và mã tại commit nêu trên. [CSV so sánh đầy đủ](CHEON_2025_REPLICATION_COMPARISON.csv) có thời gian lưu, cỡ train/test, phiên bản thư viện và SHA-256 từng artifact.

| Dataset | Model | Train AUC nhóm | Test AUC bài | Test AUC nhóm | Chênh lệch |
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
