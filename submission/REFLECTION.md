# Reflection — Lab 19

**Tên:** Trần Nguyễn Trí Dũng
**Cohort:** A20K4
**Path đã chạy:** lite

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Trên 50 query Lite, Hybrid đạt Precision@10 78,6%, hơn BM25 77,8% và vector 73,2%. Ở `exact`, BM25 và Hybrid cùng đạt 96,7%; ở `mixed`, Hybrid đạt 100%. Với `paraphrase`, vector đạt 24%, dưới BM25 (33,3%) và Hybrid (32%) vì bge-small thiên tiếng Anh. Dùng BM25 khi cần khớp mã hoặc tên chính xác; chỉ dùng vector sau khi kiểm chứng embedding đa ngữ trên corpus mục tiêu.

---

## Điều ngạc nhiên nhất khi làm lab này

Hybrid thắng tổng thể, nhưng Lite còn yếu với paraphrase tiếng Việt.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/`)
- [ ] Pair work với: 
