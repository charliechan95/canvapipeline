# Example: Style text in an existing design
import asyncio
from canva_designer import CanvaDesigner

async def style_existing_design():
    d = CanvaDesigner()
    await d.connect()
    
    # Open your design
    await d.open_design("https://www.canva.com/design/YOUR_DESIGN_ID/edit")
    
    # Style the quote text
    await d.style_text(
        text="Be the change",
        font="Lato",
        size=36,
        color="#8B7355",
        bold=True,
        alignment="Centre"
    )
    
    # Export
    await d.export_png("~/Documents/my_design.png")
    await d.disconnect()

asyncio.run(style_existing_design())
