"""Run five context-assembly examples for the HybridMemoryAgent bonus."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bonus.agent import HybridMemoryAgent  # noqa: E402


def main() -> int:
    user_id = "u_001"
    agent = HybridMemoryAgent(user_id=user_id)
    memories = [
        "Tôi đã đọc tài liệu về Kubernetes Deployment, health checks và autoscaling của pod.",
        "Tôi thích ví dụ ngắn bằng tiếng Việt, nhưng giữ nguyên tên công nghệ tiếng Anh.",
        "Gần đây tôi đang học cloud security, IAM least privilege và quản lý secret.",
        "Tôi muốn hiểu cách autoscaling hạ tầng phản ứng khi lưu lượng người dùng tăng.",
        "Tôi đọc về quan sát hệ thống, dashboard, log và cách xử lý incident trên cloud.",
    ]
    for memory in memories:
        agent.remember(memory, user_id)

    examples = [
        ("Vector memory — Kubernetes", "Tôi đã đọc gì về Kubernetes?"),
        ("Profile — recommendation", "Recommend đọc gì tiếp?"),
        ("Recent activity", "Tôi đang quan tâm gì gần đây?"),
        ("Paraphrase — autoscaling", "Tài liệu về tự động mở rộng hạ tầng?"),
        ("Hybrid — cloud security", "Cho tôi summary cloud security."),
    ]
    for title, query in examples:
        print(f"\n=== {title} ===")
        print(agent.recall(query, user_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
