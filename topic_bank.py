"""
topic_bank.py — Voquo v2.0
----------------------------
Manages the topic bank JSON file.
- Add topics
- Get next unused topic
- Mark topics as used
- Never repeats a topic
"""

import json
from pathlib import Path
from datetime import datetime

TOPIC_BANK_PATH = Path("topic_bank.json")


def load_bank() -> list:
    if not TOPIC_BANK_PATH.exists():
        return []
    with open(TOPIC_BANK_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_bank(topics: list):
    with open(TOPIC_BANK_PATH, "w", encoding="utf-8") as f:
        json.dump(topics, f, indent=2, ensure_ascii=False)


def add_topics(new_topics: list):
    """
    Add topics to the bank.
    Each topic can be a string or a dict.
    Strings are converted to full topic objects.
    """
    bank = load_bank()
    existing = {t["topic"].lower() for t in bank}

    next_id = max((t["id"] for t in bank), default=0) + 1
    added = 0

    for item in new_topics:
        if isinstance(item, str):
            topic_obj = {
                "id": next_id,
                "topic": item,
                "category": "general",
                "channel": "lloydambition",
                "mode": "flashcard",
                "used": False,
                "added_at": datetime.now().isoformat()
            }
        else:
            topic_obj = item
            topic_obj["id"] = next_id
            topic_obj.setdefault("used", False)
            topic_obj.setdefault("added_at", datetime.now().isoformat())

        if topic_obj["topic"].lower() not in existing:
            bank.append(topic_obj)
            existing.add(topic_obj["topic"].lower())
            next_id += 1
            added += 1

    save_bank(bank)
    print(f"✅ Added {added} topics. Bank total: {len(bank)}")
    return added


def get_next_topic(channel: str = None, mode: str = None) -> dict:
    """Get next unused topic. Optionally filter by channel or mode."""
    bank = load_bank()
    unused = [t for t in bank if not t.get("used", False)]

    if channel:
        filtered = [t for t in unused if t.get("channel") == channel]
        if filtered:
            unused = filtered

    if mode:
        filtered = [t for t in unused if t.get("mode") == mode]
        if filtered:
            unused = filtered

    if not unused:
        raise ValueError(
            "❌ Topic bank is empty or all topics used.\n"
            "Add more topics with: python topic_bank.py --add"
        )

    return unused[0]


def mark_used(topic_id: int):
    """Mark a topic as used after video is produced."""
    bank = load_bank()
    for t in bank:
        if t["id"] == topic_id:
            t["used"] = True
            t["used_at"] = datetime.now().isoformat()
            break
    save_bank(bank)
    print(f"✅ Topic {topic_id} marked as used")


def show_status():
    """Print bank status."""
    bank = load_bank()
    total  = len(bank)
    used   = sum(1 for t in bank if t.get("used"))
    unused = total - used

    print(f"\n{'='*50}")
    print(f"  TOPIC BANK STATUS")
    print(f"{'='*50}")
    print(f"  Total:  {total}")
    print(f"  Used:   {used}")
    print(f"  Unused: {unused}")
    print(f"{'='*50}")

    if unused > 0:
        print(f"\n  Next up:")
        for t in [t for t in bank if not t.get("used")][:3]:
            print(f"  [{t['id']}] {t['topic']} ({t.get('mode','flashcard')})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--add", nargs="+", help="Add topic(s) to bank")
    parser.add_argument("--next", action="store_true", help="Show next topic")
    parser.add_argument("--status", action="store_true", help="Show bank status")
    parser.add_argument("--mark-used", type=int, help="Mark topic ID as used")
    args = parser.parse_args()

    if args.add:
        add_topics(args.add)
    elif args.next:
        topic = get_next_topic()
        print(f"\nNext topic: [{topic['id']}] {topic['topic']}")
    elif args.status:
        show_status()
    elif args.mark_used:
        mark_used(args.mark_used)
    else:
        show_status()
