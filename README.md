# 🎨 Canva Designer — Browser Automation Tool

Automate Canva design editing via Chrome DevTools Protocol (CDP). Works with **Canva Free** plan.

## Quick Start

```bash
# 1. Start Chrome with remote debugging
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --no-first-run

# 2. Log into Canva in Chrome

# 3. Install
pip install -e .

# 4. Use
python -m canva_designer state --design https://www.canva.com/design/...
```

## CLI Commands

```bash
# Get current design state
canva state --design <URL>

# Style text
canva style --design <URL> --text "Be the change" \
  --font Lato --size 36 --color "#8B7355" --bold --align Centre

# Export design
canva export --design <URL> --format png --output design.png

# Create a quote post (full workflow)
canva quote --quote "Be the change you wish to see" \
  --author "Gandhi" --template "minimalist quote instagram"

# List all elements on canvas
canva elements --design <URL>
```

## Python API

```python
import asyncio
from canva_designer import CanvaDesigner

async def main():
    d = CanvaDesigner()
    await d.connect()
    await d.open_design("https://www.canva.com/design/...")
    
    # Style text
    await d.style_text("Be the change", font="Lato", size=36, bold=True)
    
    # Replace image
    await d.replace_image(500, 300, "/path/to/new_image.jpg")
    
    # Export
    await d.export_png("/tmp/design.png")
    
    await d.disconnect()

asyncio.run(main())
```

## Features

| Feature | Status |
|---------|--------|
| Font family change | ✅ |
| Font size change | ✅ |
| Bold / Italic / Underline | ✅ |
| Text color (hex) | ✅ |
| Text alignment | ✅ |
| Image replacement | ✅ |
| Element manipulation | ✅ |
| Template search & select | ✅ |
| Export PNG/PDF/JPG | ✅ |
| Full quote post workflow | ✅ |

## Key Insight

**Canva's toolbar is fully accessible via ARIA labels** — not canvas-rendered!

```python
page.locator('[aria-label="Bold"]')
page.locator('[aria-label="Italics"]')
page.locator('[aria-label*="Toggle font selector"]')
page.locator('input[aria-label="Font size"]')
page.locator('[aria-label*="Current text colour"]')
page.locator('[aria-label*="Toggle text alignment"]')
```

## Requirements

- Python 3.11+
- Playwright (`pip install playwright && playwright install chromium`)
- Chrome running with `--remote-debugging-port=9222`

## License

MIT
