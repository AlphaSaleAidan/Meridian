"""Extract lesson content from CanadaPortalTrainingPage.tsx into JSON for video pipeline."""
import json
import re
from pathlib import Path

TSX_PATH = Path(__file__).parent.parent.parent / "frontend/src/pages/canada/portal/CanadaPortalTrainingPage.tsx"
OUT_PATH = Path(__file__).parent / "lesson_content.json"

MODULE_ORDER = [
    ("onboarding", "New Rep Onboarding"),
    ("pitch", "Perfecting Your Pitch"),
    ("demo", "Running a Great Demo"),
    ("verticals", "Selling by Vertical"),
    ("advanced", "Advanced Closing Techniques"),
    ("compliance", "Compliance & Ethics"),
    ("camera", "Camera Intelligence Setup"),
    ("quicktips", "Quick Tips"),
    ("pos-guides", "POS Connection Guides"),
]

def extract():
    src = TSX_PATH.read_text()

    # Find all lesson blocks: { id: 'N', title: '...', completed: false, content: [...] }
    # Use a regex to find each lesson's id, title, and content array
    pattern = re.compile(
        r"\{\s*id:\s*'(\d+)'\s*,\s*title:\s*'([^']+)'\s*,\s*completed:\s*false\s*,\s*content:\s*\[(.*?)\]\s*\}",
        re.DOTALL,
    )

    lessons_by_tsx_id = {}
    for m in pattern.finditer(src):
        tsx_id = m.group(1)
        title = m.group(2)
        raw_content = m.group(3)

        # Extract strings from the content array
        paragraphs = []
        for sm in re.finditer(r"'((?:[^'\\]|\\.)*)'", raw_content):
            text = sm.group(1)
            text = text.replace("\\'", "'").replace("\\n", "\n")
            paragraphs.append(text)

        lessons_by_tsx_id[tsx_id] = {"title": title, "paragraphs": paragraphs}

    # Map sequential TSX IDs to pipeline module.lesson IDs
    module_sizes = [5, 4, 4, 5, 4, 3, 5, 4, 4]  # lessons per module
    result = {}
    tsx_id = 1

    for mod_idx, (mod_id, mod_name) in enumerate(MODULE_ORDER):
        mod_num = mod_idx + 1
        for lesson_idx in range(module_sizes[mod_idx]):
            lesson_num = lesson_idx + 1
            pipeline_id = f"{mod_num}.{lesson_num}"
            tsx_key = str(tsx_id)

            if tsx_key in lessons_by_tsx_id:
                data = lessons_by_tsx_id[tsx_key]
                result[pipeline_id] = {
                    "title": data["title"],
                    "module": mod_name,
                    "content": "\n\n".join(data["paragraphs"]),
                    "paragraph_count": len(data["paragraphs"]),
                }
            tsx_id += 1

    OUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Extracted {len(result)} lessons to {OUT_PATH}")
    for pid, info in sorted(result.items(), key=lambda x: [int(p) for p in x[0].split(".")]):
        print(f"  {pid:5s} | {info['paragraph_count']} paragraphs | {len(info['content']):5d} chars | {info['title']}")


if __name__ == "__main__":
    extract()
