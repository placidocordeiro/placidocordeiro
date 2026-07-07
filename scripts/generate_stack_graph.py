import os
import base64
import mimetypes
import re
import subprocess
import tempfile
from pathlib import Path

import graphviz

ICONS_DIR = Path("stack-icons")
OUTPUT_NAME = "stack-graph"
FONT_NAME = "JetBrains Mono, Fira Code, DejaVu Sans Mono, Consolas, monospace"
ICON_NODE_SIZE = "1.0"
ICON_PNG_SIZE = "256x256"

CATEGORY_COLORS = [
    "#38bdf8",
    "#a78bfa",
    "#0ea5e9",
    "#7c3aed",
    "#22d3ee",
    "#c084fc",
]


def inline_svg_images(svg_path):
    svg_path = Path(svg_path)
    svg = svg_path.read_text(encoding="utf-8")

    def replace_href(match):
        quote = match.group("quote")
        href = match.group("href")

        if href.startswith(("data:", "http://", "https://")):
            return match.group(0)

        image_path = Path(href)
        if not image_path.is_absolute():
            image_path = svg_path.parent / image_path

        if not image_path.exists():
            return match.group(0)

        mime_type, _ = mimetypes.guess_type(image_path)
        if mime_type is None:
            mime_type = "application/octet-stream"

        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f'{match.group("attr")}={quote}data:{mime_type};base64,{encoded}{quote}'

    svg = re.sub(
        r'(?P<attr>(?:xlink:)?href)=(?P<quote>["\'])(?P<href>[^"\']+)(?P=quote)',
        replace_href,
        svg,
    )
    svg_path.write_text(svg, encoding="utf-8")


def safe_filename(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def prepare_icon(icon_path, output_dir, node_id):
    output_path = output_dir / f"{safe_filename(node_id)}.png"
    command = [
        "magick",
        "-background",
        "none",
        "-density",
        "384",
        str(icon_path),
        "-resize",
        ICON_PNG_SIZE,
        "-gravity",
        "center",
        "-extent",
        ICON_PNG_SIZE,
        "-strip",
        f"png32:{output_path}",
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        print(f"Aviso: nao foi possivel normalizar {icon_path}: {error}")
        return icon_path

    return output_path


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        icon_output_dir = Path(temp_dir)
        g = graphviz.Graph(engine="twopi", format="svg")
        g.attr(
            bgcolor="transparent",
            overlap="false",
            splines="curved",
            root="STACK",
            pad="0.4",
            nodesep="0.6",
            ranksep="1.4 equally",
        )
        g.attr("node", fontname=FONT_NAME, fontcolor="#e2e8f0")
        g.attr("edge", penwidth="1.3")

        g.node(
            "STACK",
            shape="circle",
            style="filled",
            fillcolor="#0f172a",
            color="#38bdf8",
            fontsize="22",
            fontcolor="white",
            width="1.3",
            fixedsize="true",
        )

        categories = sorted(
            d for d in os.listdir(ICONS_DIR)
            if os.path.isdir(ICONS_DIR / d)
        )

        for i, category in enumerate(categories):
            color = CATEGORY_COLORS[i % len(CATEGORY_COLORS)]
            cat_path = ICONS_DIR / category
            cat_label = category.replace("-", " ").replace("_", " ")

            g.node(
                category,
                label=cat_label,
                shape="box",
                style="rounded,filled",
                fillcolor="#0f172a",
                color=color,
                fontcolor=color,
                fontsize="16",
                penwidth="1.8",
                margin="0.25,0.15",
            )
            g.edge("STACK", category, color=color)

            icon_files = sorted(
                f for f in os.listdir(cat_path)
                if f.lower().endswith((".png", ".svg", ".jpg", ".jpeg"))
            )

            for icon_file in icon_files:
                icon_path = cat_path / icon_file
                icon_name = os.path.splitext(icon_file)[0]
                node_id = f"{category}__{icon_name}"
                prepared_icon_path = prepare_icon(icon_path, icon_output_dir, node_id)

                g.node(
                    node_id,
                    label="",
                    image=str(prepared_icon_path),
                    shape="none",
                    imagescale="true",
                    width=ICON_NODE_SIZE,
                    height=ICON_NODE_SIZE,
                    fixedsize="true",
                    fontcolor="#94a3b8",
                )
                g.edge(category, node_id, color=color)

        output_path = g.render(OUTPUT_NAME, cleanup=True)
        inline_svg_images(output_path)
        print(f"Gerado: {output_path}")


if __name__ == "__main__":
    main()
