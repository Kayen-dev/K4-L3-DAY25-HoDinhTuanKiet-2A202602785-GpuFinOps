# Bài viết ngắn — GPU FinOps

Với dữ liệu giả lập tháng 6/2026, chi phí inference giảm từ **$6.488 xuống $1.126 cho mỗi triệu token** (82,6%). Hiệu quả lớn nhất đến từ việc chuyển yêu cầu đơn giản sang model nhỏ: khoảng **$37.40/ngày**. Cache và batch tiết kiệm thêm lần lượt **$1.20** và **$1.79/ngày**. Các khoản này được tính theo thứ tự để không cộng trùng chiết khấu.

Trong cửa sổ 30 ngày, kịch bản tổng hợp giảm chi phí từ **$18,005 xuống $8,848**, tức **$9,157 (50,9%)**. Phần lớn đến từ chọn spot cho job có thể gián đoạn và reserved cho workload ổn định (**$6,690**). Hãy ưu tiên tắt GPU nhàn rỗi, áp dụng routing và batch, rồi kiểm tra hiệu suất thực tế trước khi đổi loại GPU. `gpu-h100-4` có GPU-Util khoảng 98% nhưng MFU chỉ 19,4%: GPU bận theo thời gian không có nghĩa đang tận dụng tốt năng lực tính toán.

Hai phần mở rộng đã được đo lường. Reasoning chiếm **8,4%** số request nhưng **94,0%** năng lượng inference ước tính. Trần 10% hiện không tác động; trần 5% cho kịch bản tiết kiệm **8,795.8 Wh/ngày** và **$0.03/ngày**, với điều kiện chất lượng câu trả lời vẫn đạt yêu cầu. Với 5 job có thể gián đoạn, chuyển lịch chạy từ `us-east-1` sang `europe-north1` giảm khoảng **626,2 kgCO2e** trong dữ liệu lưới điện giả lập. `us-east-wa` có giá điện thấp nhất; việc chọn vùng cần tính thêm giá thuê GPU, truyền dữ liệu và độ trễ.

Các nhóm chi phí inference API, workload GPU và telemetry chưa được đối soát theo cùng hóa đơn. Tổng savings là **ước tính lập kế hoạch**, vì khoản tắt GPU, right-size và cam kết thuê có thể chồng lấn. Xem [báo cáo chi tiết](report.md) và [biểu đồ savings](savings.png).
