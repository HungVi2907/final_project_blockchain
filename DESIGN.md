# Super Bells — Thiết kế dashboard kiểm toán tín dụng

## 1. Định hướng

Giao diện tiếng Việt cho người trình diễn và người xem đồ án IS355. Người xem cần nhận ra hồ sơ đang xem, hiểu mô hình dự đoán gì và kiểm tra bản ghi có khớp với cam kết trên chuỗi hay không. Dùng nền bạc hà pha xanh ngọc, bề mặt dữ liệu tông ngà và teal đậm cho hành động chính. Dành điểm nhấn cho xác suất dự đoán hoặc kết quả xác minh đang được xem.

## 2. Màu và token

| Vai trò | Màu | Cách dùng |
| --- | --- | --- |
| Nền ứng dụng | `#E4F3EC` | Nền bạc hà với chuyển sắc về `#CBF1F5` ở góc trên |
| Bề mặt dữ liệu | `#F8FBF4` | Khung giải thích, bảng và trường nhập |
| Nền tiêu đề bảng | `#E1EFE9` | Hàng tiêu đề bảng, rãnh biểu đồ và khối mã |
| Văn bản | `#15372F` | Tiêu đề, nhãn và nội dung chính |
| Văn bản phụ | `#3D5A50` | Mô tả và metadata |
| Đường viền | `#B1CEC2` / `#65867B` | Tách bề mặt và nhận diện trường nhập |
| Hành động chính | `#007669` | Nút chính với chữ trắng |
| Focus và tab đang chọn | `#00675C` | Viền bàn phím, chỉ báo điều hướng và liên kết |
| Xác suất rủi ro | `#005B4A` trên `#D5EFDF` | Số liệu chính trên nền bạc hà |
| Đóng góp SHAP | `#00816E` / `#3F6EA3` | Hướng tăng / giảm đầu ra, kèm dấu và giá trị |

Trạng thái đã xác minh dùng xanh lá `#267A52` trên nền `#E0F3E6`. Sai lệch hoặc giao dịch thất bại dùng đỏ san hô `#A7364F` trên nền `#FBE9EC`. Trạng thái chờ dùng hổ phách `#87570A` trên nền `#FFF1D1`. Trạng thái chưa thể xác minh hoặc không tìm thấy dùng bề mặt dữ liệu và viền trung tính. Luôn có nhãn chữ, ký hiệu và thông tin tiếp theo. Đồng bộ màu nền, chữ và hành động chính giữa `.streamlit/config.toml` và các biến `--audit-*` trong `src/credit_audit/audit.css`.

## 3. Kiểu chữ và số liệu

- Dùng sans-serif mặc định của Streamlit với đầy đủ dấu tiếng Việt. Dùng chữ đơn cách cho mã định danh, hash và mã trạng thái kỹ thuật.
- Văn bản chính khoảng `1rem`, nhãn phụ khoảng `0.875rem`. Tiêu đề dùng cỡ chữ co giãn. Dùng chữ số tabular cho xác suất, SHAP và số liệu đối chiếu.
- Hiển thị `P(Bad)` dưới dạng phần trăm với nhãn mô tả đúng dữ liệu. Đóng góp SHAP có dấu và ghi rõ đơn vị, ví dụ log-odds trong mô hình LR HELOC.

## 4. Thành phần và luồng thao tác

- **Đầu trang** — Hiển thị Super Bells, tên trang và nguồn hồ sơ đang chọn. Ưu tiên hồ sơ test FICO HELOC bàn giao khi sẵn có. Ghi rõ hồ sơ giả lập, lượt pilot chỉ đọc và mô phỏng ngoại tuyến.
- **Hồ sơ** — Đặt dataset và schema gần xác suất lớp Bad, rồi hiển thị phiên bản mô hình và giải thích SHAP. Biểu đồ dùng mốc 0 và giá trị có dấu, ưu tiên tối đa 10 đặc trưng có độ lớn tuyệt đối cao nhất. Đặt Decision ID, hai hash off-chain và bản tải JSON canonical trong mục bằng chứng.
- **Xác minh** — Dùng trường Decision ID có nhãn và nút “Xác minh bản ghi”. Hiển thị trạng thái sau thao tác, kèm thời điểm kiểm tra. Đặt mỗi cặp hash cạnh nhau và ghi khớp hoặc sai lệch. Với kết quả có giao dịch, cho xem mã giao dịch, block, gas và số xác nhận tùy dữ liệu có sẵn.
- **Nạp JSON để kiểm toán** — Dùng trường tải tệp Streamlit có nhãn và hướng dẫn lấy JSON chuẩn hóa từ tab Hồ sơ. Báo lỗi định dạng cạnh trường tải tệp. Hiển thị Decision ID đọc từ tệp và dùng cùng trạng thái, đối chiếu hash và biên nhận trên tab Xác minh.
- **Trạng thái** — Dùng nhãn tiếng Việt bên cạnh mã kỹ thuật. Phân biệt chưa kiểm tra, chờ xác nhận, lỗi kết nối và sai lệch. Khi đổi Decision ID hoặc nguồn hồ sơ, đặt lại kết quả hiển thị nếu ngữ cảnh thay đổi. Gắn nhãn mô phỏng bên cạnh mã trạng thái khi kết quả được tính trong bộ nhớ.
- **Kết quả nghiên cứu** — Hiển thị AUC pilot và trung bình bảy seed của HELOC. Bảng E3 dùng số đếm phát hiện và cảnh báo sai, kèm gas và thời gian đến biên nhận của đăng ký B2. Ghi rõ mạng và cỡ mẫu. Gắn nhãn kết quả pilot đã lưu và dẫn người dùng đến tab Xác minh để lấy kết quả mới.
- Dùng nút chính cho hành động ưu tiên của từng khu vực. Dùng nhãn nêu hành động cụ thể. Đặt chi tiết kỹ thuật dưới phần tóm tắt và cho phép sao chép đầy đủ mã định danh hoặc hash.

## 5. Bố cục và bề mặt

Giới hạn vùng nội dung rộng khoảng `76rem`. Trên màn hình rộng, bố trí xác suất cạnh giải thích và đặt chi tiết bản ghi gần hành động kiểm toán. Tách khu vực bằng khoảng cách, độ sáng bề mặt và đường viền mảnh. Ưu tiên bán kính `8–14px` tùy thành phần. Dùng lưới mờ ở đầu trang để tạo nhận diện cho khu vực tiêu đề.

## 6. Màn hình hẹp và khả năng tiếp cận

- Ở khoảng `720px` trở xuống, ưu tiên một cột, giữ thứ tự đọc và cho phép ID/hash xuống dòng hoặc cuộn trong chính vùng mã. Kiểm tra ở khoảng `375px`, `768px` và `1440px`.
- Dùng nhãn thực cho trường nhập, thứ tự tab theo luồng thao tác và focus dễ thấy. Kiểm tra tỷ lệ tương phản tối thiểu 4,5:1 cho chữ thường. Dùng chữ, dấu hoặc hình dạng cùng với màu cho trạng thái và biểu đồ.
- Ưu tiên vùng bấm thoải mái trên thiết bị cảm ứng. Tôn trọng `prefers-reduced-motion` khi thêm chuyển động.

## 7. Ngôn ngữ và phạm vi nghiên cứu

Ghi rõ nguồn hồ sơ và nhãn giả lập khi có. Mô tả SHAP là đóng góp vào đầu ra mô hình. Mô tả `VERIFIED` là bản ghi khớp với cam kết trên chuỗi theo điều kiện xác minh hiện hành. Mọi giao diện thuộc phạm vi nguyên mẫu nghiên cứu. Giữ dữ liệu cá nhân ngoài giao diện demo và blockchain. Dùng số liệu và trạng thái thực từ luồng đang chạy.

## 8. Tham chiếu thiết kế

Palette xanh ngọc sáng của Color Hunt là điểm xuất phát. Super Bells dùng `#CBF1F5` ở nền và `#A6E3E9` ở đầu trang, rồi bổ sung sắc bạc hà và các màu đậm cho chữ, nút và biểu đồ. [Palette Color Hunt](https://colorhunt.co/palette/e3fdfdcbf1f5a6e3e971c9ce)

Cách dùng độ sáng bề mặt và đường viền mảnh lấy cảm hứng từ hệ phân cấp thị giác của Linear. [Linear](https://linear.app/now/behind-the-latest-design-refresh)

Tài liệu Coinbase từ VoltAgent cung cấp tham chiếu cho cách nhấn một hành động chính và trình bày thông tin tài chính. [Bản tham chiếu trong repo](docs/design-references/coinbase/DESIGN.md) · [Bản nguồn đã ghim](https://github.com/VoltAgent/awesome-design-md/blob/fcc70284932276d085f01ef9f83edde90b1258cb/design-md/coinbase/DESIGN.md) · [Giấy phép MIT](docs/design-references/coinbase/LICENSE)
