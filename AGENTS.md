# Hướng dẫn làm việc trong repo Super Bells

Hướng dẫn này áp dụng cho toàn bộ repo. Với công việc liên quan đến giao diện web, nội dung hiển thị, biểu đồ hoặc luồng thao tác, hãy đọc [DESIGN.md](DESIGN.md) trước khi thiết kế hay sửa code.

## Thiết kế và triển khai giao diện

- Dùng skill [ui-ux-pro-max](.agents/skills/ui-ux-pro-max/SKILL.md) để nghiên cứu hoặc rà soát UX. Dùng thêm [design-system](.agents/skills/design-system/SKILL.md) khi thay đổi token, thành phần dùng chung hoặc trạng thái. Áp dụng các phần phù hợp với Streamlit, CSS và luồng kiểm toán của repo. `DESIGN.md` quyết định cách áp dụng các gợi ý chung vào giao diện Super Bells.
- Đọc [đặc tả MVP](docs/C_MVP_UI.md) để nắm luồng demo và [Proposal](docs/07_SuperBells_IS355_Proposal.md) khi thay đổi nội dung về mô hình, SHAP, blockchain hoặc phạm vi nghiên cứu. Đối chiếu trạng thái và khả năng đang có với mã và dữ liệu thực tế.
- Bắt đầu từ [dashboard Streamlit](src/credit_audit/app.py), [CSS hiện có](src/credit_audit/audit.css) và [theme Streamlit](.streamlit/config.toml). Ưu tiên widget Streamlit, token và thành phần hiện có. Khi đổi token hoặc quy ước dùng chung, cập nhật `DESIGN.md` và mã giao diện liên quan cùng lượt.
- Với thay đổi hiển thị, kiểm tra bố cục ở màn hình hẹp và rộng, thao tác bàn phím, focus, tương phản và các trạng thái liên quan. Dùng trình duyệt để kiểm tra phần hiển thị khi có thể và chạy kiểm thử sẵn có cho luồng bị thay đổi.

## Tra cứu bằng UI UX Pro Max

Chạy từ thư mục gốc. Ví dụ Windows dùng Python 3.11 đã kiểm tra tại workspace này. Có thể chọn phiên bản Python 3 khác đã cài. Trong WSL, macOS hoặc Linux, thay `py -3.11` bằng `python3`. Dùng kết quả làm gợi ý thiết kế cho tính năng đang làm.

```powershell
py -3.11 .agents/skills/ui-ux-pro-max/scripts/search.py "analytics dashboard institutional fintech audit light" --design-system -p "Super Bells" -f markdown
py -3.11 .agents/skills/ui-ux-pro-max/scripts/search.py "keyboard focus responsive forms status feedback" --domain ux -n 5
```

Hai skill được tạo từ [UI UX Pro Max 2.15.0](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/a38d04c3d5c298c851dbe5e6ee1965ee3de42cb5) bằng preset Codex của trình cài đặt chính thức. Xem [giấy phép MIT](.agents/skills/LICENSE.ui-ux-pro-max).
