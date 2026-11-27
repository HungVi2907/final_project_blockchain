# Huấn luyện và bàn giao XAI FICO HELOC

Lượt chạy này huấn luyện lại Logistic Regression, Random Forest và XGBoost trên FICO HELOC. Dữ liệu có 43 đặc trưng đã qua bước tạo biến của Cheon et al. Giữ tập test fold 5 của lượt tái lập để đối chiếu. Fold này đã được dùng trong nghiên cứu của nhóm trước đó, nên số liệu là kết quả trên tập test đã có của dự án.

## Giao thức đánh giá

- Tách 20% của 4.674 hồ sơ phát triển làm validation, phân tầng theo nhãn với seed 2338. Tập test gồm 1.168 hồ sơ và được giữ riêng trong lượt chạy này.
- Tìm siêu tham số bằng CV phân tầng 4 fold trên phần train. Chấm bằng Average Precision của lớp Bad. Scaler của LR nằm trong pipeline và được fit riêng trong từng fold. Dữ liệu giữ tỷ lệ lớp gốc.
- Chọn mô hình theo Average Precision trên validation. Khi bằng nhau, ưu tiên ROC-AUC cao hơn, sau đó dùng tên mô hình để có thứ tự xác định.
- Với từng mô hình, chọn ngưỡng làm F1 của lớp Bad cao nhất trên validation. Khi nhiều ngưỡng cho cùng F1, lấy ngưỡng cao nhất. Cố định mô hình và ngưỡng khi chạy test.
- Lưu ROC-AUC, Average Precision, log loss, Brier score, Precision, Recall, F1 và ma trận nhầm lẫn. Khoảng tin cậy bootstrap phân tầng 95% trên test cho ROC-AUC và AP dùng 1.000 mẫu lặp. Khoảng này phản ánh độ bất định do lấy mẫu hồ sơ test với mô hình đã fit cố định.

## Kết quả lượt chạy v1

Tập train có 3.739 hồ sơ. Validation có 935 hồ sơ. Test có 1.168 hồ sơ, gồm 623 nhãn Bad.

| Mô hình | AP validation | ROC-AUC test | AP test | Precision test | Recall test | F1 test |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Logistic Regression | 0,7635 | 0,7871 | 0,7990 | 0,6622 | 0,8716 | 0,7526 |
| Random Forest | 0,7615 | 0,7864 | 0,7981 | 0,6238 | 0,9342 | 0,7481 |
| XGBoost | 0,7667 | 0,7864 | 0,7995 | 0,6867 | 0,8266 | 0,7502 |

## Nhận xét kết quả cho báo cáo cuối kỳ

**Lựa chọn mô hình cho XAI.** Nhóm chọn XGBoost vì mô hình đạt AP cao nhất trên validation (0,7667), hơn Logistic Regression khoảng 0,0032. Ngưỡng 0,4325 được chọn để tối đa hóa F1 của lớp Bad trên validation và được giữ cố định khi đánh giá test. AP test của XGBoost chỉ cao hơn Logistic Regression khoảng 0,0006. Mức chênh lệch quan sát được còn nhỏ và bằng chứng hiện có chưa đủ để khẳng định lợi thế rõ rệt của XGBoost.

**Đánh đổi tại các ngưỡng đã chốt.** Trên 1.168 hồ sơ test, có 623 hồ sơ Bad và 545 hồ sơ Good.

| Mô hình | Hồ sơ Good bị báo nhầm | Hồ sơ Bad bị bỏ sót | Nhận xét |
| --- | ---: | ---: | --- |
| Logistic Regression | 277 | 80 | Đạt ROC-AUC và F1 test cao nhất trong ba mô hình. Log loss (0,5569) và Brier score (0,1877) cũng thấp nhất. So với XGBoost, phát hiện thêm 28 hồ sơ Bad và báo nhầm thêm 42 hồ sơ Good. |
| Random Forest | 351 | 41 | Đạt Recall cao nhất (93,4%). Số hồ sơ Good bị báo nhầm cũng cao nhất. |
| XGBoost | 235 | 108 | Đạt Precision cao nhất (68,7%) và có ít hồ sơ Good bị báo nhầm nhất. Số hồ sơ Bad bị bỏ sót cao nhất tại các ngưỡng đã chốt. |

**Phạm vi kết luận.** Các khoảng tin cậy bootstrap hiện có mô tả ROC-AUC và AP của từng mô hình. Để đánh giá mức độ chắc chắn của chênh lệch, cần tính khoảng tin cậy cho hiệu số trên các mẫu bootstrap ghép cặp từ cùng tập test. Tập test này là fold 5 của HELOC đã được sử dụng trong lượt tái lập, nên kết luận giới hạn ở phép chia của dự án.

**Hệ quả cho demo.** Dùng XGBoost đã lưu và ngưỡng 0,4325 để tái hiện kết quả v1. Nếu nhóm ưu tiên phát hiện nhiều hồ sơ Bad hơn, có thể đặt mục tiêu Recall trên validation, chọn ngưỡng phù hợp và ghi lại đánh đổi về báo nhầm. Việc đổi ngưỡng giữ nguyên tham số của mô hình đã huấn luyện.

## Dùng các tệp đã bàn giao

| Tệp | Nội dung |
| --- | --- |
| `manifest.json` | Thứ tự 43 đặc trưng, nguồn và checksum, mô hình được chọn, ngưỡng và phiên bản Python |
| `selection.json` | Metric validation, tiêu chí chọn mô hình và siêu tham số đã chốt |
| `models/*.joblib` | Ba mô hình đã fit. Tệp dùng cho XAI được trỏ từ `selected_model_path` |
| `data/` | Train, validation, test, các fold CV và 100 dòng train dành cho mẫu nền XAI |
| `results/metrics.csv` | Chỉ số, số đếm ma trận nhầm lẫn và khoảng tin cậy |
| `results/predictions.csv` | Nhãn, xác suất Bad và nhãn dự đoán của từng mô hình trên từng tập |
| `results/cv_*.csv` | Kết quả từng cấu hình và từng fold CV |
| `requirements.txt` | Phiên bản thư viện của môi trường đã chạy |

Trong gói này, nhãn `1 = Bad` và `0 = Good` cho cả ba mô hình. `source_position` là vị trí trong tập nguồn. Train và validation cùng lấy từ tập phát triển. Test dùng hệ vị trí riêng. Khi ghép dự đoán, dùng cặp `split` và `source_position`.

Ví dụ nạp mô hình đã chốt và tính xác suất lớp Bad từ thư mục giải nén. Chỉ nạp tệp joblib từ nguồn tin cậy.

```python
import json
from pathlib import Path

import joblib
import pandas as pd

manifest = json.loads(Path("manifest.json").read_text(encoding="utf-8"))
model = joblib.load(manifest["selected_model_path"])
features = manifest["feature_order"]
test = pd.read_csv("data/test.csv")[features]
background = pd.read_csv("data/xai_background.csv")[features]
p_bad = model.predict_proba(test.iloc[[0]])[0, list(model.classes_).index(1)]
predicted_bad = p_bad >= manifest["selected_threshold"]
```

Khi viết phần XAI, ghi rõ phiên bản mô hình, lớp Bad, tập nền và không gian đầu ra. Nếu giải thích logit, kiểm tra tính cộng của đóng góp trên logit. Nếu giải thích xác suất, kiểm tra trên xác suất. Giữ checksum của đúng tệp mô hình khi tích hợp web.

## Chạy lại trong repo

Đặt gói HELOC dùng làm nguồn tại `artifacts/SuperBells_HELOC_XAI.zip`. Cài các phiên bản trong `requirements.txt` của gói bàn giao mới và chạy ở thư mục gốc repo.

```powershell
python scripts/train_heloc_standard.py --output artifacts/heloc_standard_rerun
```
