"""Build the long-context needle dataset programmatically (gold known by construction).

Each item: one support-note "needle" sentence with a known customer ask and damage flag,
inserted at the start / middle / end of neutral filler paragraphs, sized to a target
number of Laya-tokenizer tokens.
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.backends import make_backend  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "bench" / "data"

# (needle text, wants, mentions_damage)
NEEDLES = [
    ("Customer contact (ticket 4471): the customer reports the kettle arrived with a cracked lid and asks for a replacement unit to be sent out.", "replacement", True),
    ("Customer contact (ticket 4472): the customer says the headphones stopped charging after two days and wants a new pair instead of their money back.", "replacement", True),
    ("Customer contact (ticket 4473): the customer ordered the wrong size of gloves and would like a medium sent in exchange for the large.", "replacement", False),
    ("Customer contact (ticket 4474): the customer's parcel contained a blue mug rather than the green one ordered; they ask us to ship the green one.", "replacement", False),
    ("Customer contact (ticket 4475): the customer reports the tablet screen was shattered on arrival and requests a replacement device.", "replacement", True),
    ("Customer contact (ticket 4481): the customer says the blender arrived with a broken jug and asks for a full refund to their card.", "refund", True),
    ("Customer contact (ticket 4482): the customer changed their mind about the desk lamp before it shipped and would like the payment returned.", "refund", False),
    ("Customer contact (ticket 4483): the customer was charged twice for the same subscription month and asks for the duplicate payment to be refunded.", "refund", False),
    ("Customer contact (ticket 4484): the customer's jacket arrived with a torn sleeve; they do not want another one and ask for their money back.", "refund", True),
    ("Customer contact (ticket 4485): the customer says the course did not match its description and requests a refund of the enrolment fee.", "refund", False),
    ("Customer contact (ticket 4491): the customer's bicycle has a bent front wheel after delivery and they ask whether our workshop can straighten it.", "repair", True),
    ("Customer contact (ticket 4492): the customer's watch has stopped keeping time after a year of use and they ask to book it in for a service.", "repair", True),
    ("Customer contact (ticket 4493): the customer asks for the loose hinge on their cabinet to be fixed under the warranty.", "repair", True),
    ("Customer contact (ticket 4494): the customer reports the printer's paper tray jams constantly and asks for an engineer visit to fix it.", "repair", True),
    ("Customer contact (ticket 4495): the customer's e-bike display is dead on arrival and they want it repaired rather than replaced.", "repair", True),
    ("Customer contact (ticket 4501): the customer asks us to cancel their monthly meal-kit subscription starting next month.", "cancellation", False),
    ("Customer contact (ticket 4502): the customer would like their pending order for the garden furniture cancelled before it ships.", "cancellation", False),
    ("Customer contact (ticket 4503): the customer says the smart speaker arrived scratched and, rather than sorting it out, wants to cancel the whole account.", "cancellation", True),
    ("Customer contact (ticket 4504): the customer is moving abroad and asks to close their membership at the end of the current term.", "cancellation", False),
    ("Customer contact (ticket 4505): the customer asks for the auto-renewal on their domain registration to be cancelled.", "cancellation", False),
    ("Customer contact (ticket 4511): the customer called to confirm the delivery address on file and mentioned nothing else.", "not_stated", False),
    ("Customer contact (ticket 4512): the customer wrote to say the sofa arrived with a deep scratch on one arm; they have not yet said what they would like done.", "not_stated", True),
    ("Customer contact (ticket 4513): the customer asked what time the showroom opens on Saturdays.", "not_stated", False),
    ("Customer contact (ticket 4514): the customer mentioned their kettle's cord is frayed and asked whether that is normal for the model, without asking for anything.", "not_stated", True),
    ("Customer contact (ticket 4515): the customer thanked the team for a quick delivery last week.", "not_stated", False),
]

TARGETS = [100, 250, 500, 1000, 2000, 4000]
POSITIONS = ["start", "middle", "end"]


def main():
    filler = json.loads((DATA / "filler.json").read_text())
    paras = [p["text"] for p in filler]
    laya = make_backend("laya")
    count = lambda s: laya.count_state_tokens({"notes": s})  # noqa: E731
    rng = random.Random(42)
    items = []
    for ni, (needle, wants, damage) in enumerate(NEEDLES):
        for target in TARGETS:
            for pos in POSITIONS:
                order = paras[:]
                rng.shuffle(order)
                budget = target - count(needle) - 2
                chosen, used = [], 0
                for p in order:
                    n = count(p)
                    if used + n <= budget:
                        chosen.append(p)
                        used += n
                    elif budget - used > 25:
                        # trim a paragraph at word boundary to fill the remainder
                        words = p.split()
                        lo, hi = 0, len(words)
                        while lo < hi:
                            mid = (lo + hi + 1) // 2
                            if count(" ".join(words[:mid])) <= budget - used:
                                lo = mid
                            else:
                                hi = mid - 1
                        if lo > 5:
                            chosen.append(" ".join(words[:lo]) + ".")
                            used += count(chosen[-1])
                        break
                    else:
                        break
                k = {"start": 0, "middle": len(chosen) // 2, "end": len(chosen)}[pos]
                parts = chosen[:k] + [needle] + chosen[k:]
                notes = "\n\n".join(parts)
                items.append({
                    "id": f"needle-{ni:02d}-{target}-{pos}",
                    "notes": notes,
                    "wants": wants,
                    "mentions_damage": damage,
                    "length_target": target,
                    "laya_tokens": count(notes),
                    "position": pos,
                    "needle_index": ni,
                })
    with (DATA / "needle.jsonl").open("w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    by_len = {}
    for it in items:
        by_len.setdefault(it["length_target"], []).append(it["laya_tokens"])
    print({k: (min(v), max(v)) for k, v in by_len.items()})
    print(f"needle: {len(items)} items")


if __name__ == "__main__":
    main()
