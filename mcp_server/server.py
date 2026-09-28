from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Procurement Decision Copilot")

RFA_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "rfa_reference"
)


@mcp.tool()
def list_rfa_guidance() -> str:
    """List available procurement RFA guidance documents."""
    return "\n".join(
        file.name
        for file in sorted(RFA_DIR.glob("*.md"))
    )


@mcp.tool()
def get_rfa_guidance(category: str) -> str:
    """Retrieve procurement guidance relevant to an RFA category."""
    category = category.strip().upper()

    matches = []

    for file in sorted(RFA_DIR.glob("*.md")):
        text = file.read_text(encoding="utf-8")

        if category in text.upper():
            matches.append(
                f"--- {file.name} ---\n{text}"
            )

    if not matches:
        return f"No guidance found for category: {category}"

    return "\n\n".join(matches)


if __name__ == "__main__":
    mcp.run()
