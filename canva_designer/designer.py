#!/usr/bin/env python3
"""
Canva Designer — Complete Browser Automation Tool
==================================================
Full Canva editor automation via CDP (Chrome DevTools Protocol).
Works with Canva Free plan. Uses ARIA labels for all interactions.

Author: Charlie Chan / OWL
License: MIT
Repo: https://github.com/charlie-mindfulness/canva-designer
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from playwright.async_api import async_playwright, Page, Browser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("canva_designer")


# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

class Config:
    """Central configuration."""
    CDP_URL = "http://localhost:9222"
    SCREENSHOT_DIR = Path("/tmp/canva_exports")
    EXPORT_DIR = Path.home() / "Documents" / "Canva Exports"
    DEFAULT_WAIT = 2.0
    SHORT_WAIT = 0.5
    LONG_WAIT = 5.0

    # Charlie's brand defaults
    BRAND_FONT = "Lato"
    BRAND_SIZE = 36
    BRAND_COLOR = "#8B7355"  # Warm brown
    BOLD = True
    ITALIC = False
    ALIGNMENT = "Centre"


# ═══════════════════════════════════════════════════════════════════
# MAIN CLASS
# ═══════════════════════════════════════════════════════════════════

class CanvaDesigner:
    """
    Complete Canva editor automation.
    
    Usage:
        designer = CanvaDesigner()
        await designer.connect()
        await designer.open_design("https://canva.com/design/...")
        await designer.style_text("Be the change", font="Lato", size=36, bold=True)
        await designer.replace_image(old_x=500, old_y=300, new_image_path="/path/to/img.jpg")
        await designer.export_png("/tmp/design.png")
        await designer.disconnect()
    """

    def __init__(self, cdp_url: str = Config.CDP_URL):
        self.cdp_url = cdp_url
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    # ── Connection ─────────────────────────────────────────────────

    async def connect(self) -> bool:
        """Connect to Chrome via CDP."""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)
            for ctx in self.browser.contexts:
                for page in ctx.pages:
                    self.page = page
                    logger.info(f"Connected to: {self.page.url[:80]}")
                    return True
            logger.error("No pages found")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def disconnect(self):
        if self.playwright:
            await self.playwright.stop()

    # ── Navigation ─────────────────────────────────────────────────

    async def open_design(self, url: str, wait: float = Config.LONG_WAIT):
        """Navigate to a Canva design editor URL."""
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(wait)
        logger.info(f"Opened design: {self.page.url[:80]}")

    # ── Text Selection ─────────────────────────────────────────────

    async def select_text(self, text: str) -> bool:
        """Find and click on a text element by its content."""
        result = await self.page.evaluate(f"""
        () => {{
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node;
            while (node = walker.nextNode()) {{
                const t = node.textContent.trim();
                if (t.includes('{text}') && t.length < 200) {{
                    const parent = node.parentElement;
                    if (parent) {{
                        const rect = parent.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {{
                            return {{ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) }};
                        }}
                    }}
                }}
            }}
            return null;
        }}
        """)
        if result:
            # Use real mouse click (JS click doesn't trigger Canva's selection)
            await self.page.mouse.click(result['x'], result['y'])
            await asyncio.sleep(Config.SHORT_WAIT)
            logger.info(f"Selected text '{text}' at ({result['x']}, {result['y']})")
            return True
        logger.warning(f"Text '{text}' not found")
        return False

    async def select_text_at(self, x: int, y: int):
        """Click at coordinates to select a text element."""
        await self.page.mouse.click(x, y)
        await asyncio.sleep(Config.SHORT_WAIT)

    # ── Font Operations (via ARIA labels) ─────────────────────────

    async def get_font(self) -> str:
        """Get current font family."""
        el = self.page.locator('[aria-label*="Toggle font selector"]')
        if await el.count() > 0:
            label = await el.get_attribute("aria-label") or ""
            if "current font:" in label:
                return label.split("current font:")[-1].strip()
        return ""

    async def set_font(self, font_name: str) -> bool:
        """Set font family by opening dropdown and searching."""
        # Wait for toolbar to appear
        font_btn = self.page.locator('[aria-label*="Toggle font selector"]')
        await font_btn.wait_for(state="visible", timeout=10000)
        # Click font button
        await font_btn.click()
        await asyncio.sleep(1.5)

        # Search
        search = self.page.locator('input[type="search"]')
        if await search.count() > 0:
            await search.click()
            await search.fill(font_name)
            await asyncio.sleep(2)

            # Click first result (LI > IMG pattern)
            result = await self.page.evaluate("""
            () => {
                const lis = document.querySelectorAll('li');
                for (const li of lis) {
                    const rect = li.getBoundingClientRect();
                    if (rect.x >= 0 && rect.x <= 350 && rect.y >= 250 && rect.y <= 700) {
                        const img = li.querySelector('img');
                        if (img) { img.click(); return 'clicked_img'; }
                        li.click(); return 'clicked_li';
                    }
                }
                return 'not_found';
            }
            """)
            await asyncio.sleep(1)
            return result in ('clicked_img', 'clicked_li')
        return False

    async def get_font_size(self) -> int:
        el = self.page.locator('input[aria-label="Font size"]')
        if await el.count() > 0:
            val = await el.input_value()
            try:
                return int(val)
            except ValueError:
                pass
        return 0

    async def set_font_size(self, size: int):
        el = self.page.locator('input[aria-label="Font size"]')
        if await el.count() > 0:
            await el.click()
            await el.fill(str(size))
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(Config.SHORT_WAIT)

    # ── Text Formatting (via ARIA labels) ─────────────────────────

    async def toggle_bold(self):
        await self.page.locator('[aria-label="Bold"]').click()
        await asyncio.sleep(0.3)

    async def toggle_italic(self):
        await self.page.locator('[aria-label="Italics"]').click()
        await asyncio.sleep(0.3)

    async def toggle_underline(self):
        await self.page.locator('[aria-label="Underline"]').click()
        await asyncio.sleep(0.3)

    async def toggle_strikethrough(self):
        await self.page.locator('[aria-label="Strikethrough"]').click()
        await asyncio.sleep(0.3)

    async def toggle_uppercase(self):
        await self.page.locator('[aria-label="Uppercase"]').click()
        await asyncio.sleep(0.3)

    # ── Color (via ARIA labels) ───────────────────────────────────

    async def get_color(self) -> str:
        el = self.page.locator('[aria-label*="Current text colour"]')
        if await el.count() > 0:
            label = await el.get_attribute("aria-label") or ""
            if "colour " in label:
                return label.split("colour ")[-1].strip()
        return ""

    async def set_color_hex(self, hex_color: str) -> bool:
        """Set text color via hex code."""
        await self.page.locator('[aria-label*="Current text colour"]').click()
        await asyncio.sleep(1.5)

        # Try hex input
        hex_input = self.page.locator('input[placeholder*="#"], input[placeholder*="hex"], input[type="text"]')
        if await hex_input.count() > 0:
            await hex_input.first.click()
            await hex_input.first.fill(hex_color)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(0.5)
            return True

        # Fallback: close and return False
        await self.page.keyboard.press("Escape")
        return False

    # ── Alignment (via ARIA labels) ───────────────────────────────

    async def get_alignment(self) -> str:
        el = self.page.locator('[aria-label*="Toggle text alignment"]')
        if await el.count() > 0:
            label = await el.get_attribute("aria-label") or ""
            if "alignment:" in label:
                return label.split("alignment:")[-1].strip()
        return ""

    async def cycle_alignment(self):
        await self.page.locator('[aria-label*="Toggle text alignment"]').click()
        await asyncio.sleep(0.3)

    async def set_alignment(self, target: str):
        """Set alignment to 'Left', 'Centre', or 'Right'."""
        for _ in range(5):
            current = await self.get_alignment()
            if current == target:
                return
            await self.cycle_alignment()
            await asyncio.sleep(0.3)

    # ── Style Text (combined) ─────────────────────────────────────

    async def style_text(
        self,
        text: str,
        font: Optional[str] = None,
        size: Optional[int] = None,
        color: Optional[str] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        alignment: Optional[str] = None,
    ) -> bool:
        """
        Full text styling in one call.
        
        Args:
            text: Text content to find and style
            font: Font family name (e.g., "Lato", "Playfair Display")
            size: Font size (e.g., 36)
            color: Hex color (e.g., "#8B7355")
            bold: True/False/None (None = don't change)
            italic: True/False/None
            underline: True/False/None
            alignment: "Left", "Centre", "Right", or None
        """
        if not await self.select_text(text):
            return False

        # Wait for toolbar to appear after text selection
        await self.page.locator('[aria-label*="Toggle font selector"]').wait_for(state="visible", timeout=10000)

        if font:
            await self.set_font(font)
        if size:
            await self.set_font_size(size)
        if color:
            await self.set_color_hex(color)
        if bold is not None:
            if bold:
                await self.toggle_bold()
        if italic is not None:
            if italic:
                await self.toggle_italic()
        if underline is not None:
            if underline:
                await self.toggle_underline()
        if alignment:
            await self.set_alignment(alignment)

        logger.info(f"Styled text '{text}': font={font}, size={size}, color={color}")
        return True

    # ── Image Replacement ──────────────────────────────────────────

    async def find_images_on_canvas(self) -> List[Dict]:
        """Find all image elements on the canvas."""
        return await self.page.evaluate("""
        () => {
            const imgs = document.querySelectorAll('img');
            const results = [];
            for (const img of imgs) {
                const rect = img.getBoundingClientRect();
                // Canvas area: x > 200, y > 80, reasonable size
                if (rect.x > 200 && rect.x < 1200 && rect.y > 80 && rect.y < 700 &&
                    rect.width > 50 && rect.height > 50) {
                    results.push({
                        src: (img.src || '').substring(0, 100),
                        cls: (img.className || '').toString().substring(0, 40),
                        x: Math.round(rect.x + rect.width / 2),
                        y: Math.round(rect.y + rect.height / 2),
                        w: Math.round(rect.width),
                        h: Math.round(rect.height)
                    });
                }
            }
            return results;
        }
        """)

    async def select_image_at(self, x: int, y: int):
        """Click on an image at given coordinates to select it."""
        await self.page.mouse.click(x, y)
        await asyncio.sleep(Config.SHORT_WAIT)

    async def replace_image(self, x: int, y: int, new_image_path: str) -> bool:
        """
        Replace an image on the canvas.
        
        Strategy: Select image → click "Replace" or use Upload panel.
        """
        # Click on the image to select it
        await self.select_image_at(x, y)
        await asyncio.sleep(1)

        # Look for "Replace" button in floating toolbar or right-click menu
        # Canva shows a floating toolbar when image is selected
        replace_btn = self.page.locator('[aria-label*="Replace"], button:has-text("Replace")')
        if await replace_btn.count() > 0:
            await replace_btn.click()
            await asyncio.sleep(1)
        else:
            # Try right-click context menu
            await self.page.mouse.click(x, y, button="right")
            await asyncio.sleep(1)
            replace_option = self.page.locator('text="Replace", text="Replace image"]')
            if await replace_option.count() > 0:
                await replace_option.click()
                await asyncio.sleep(1)
            else:
                await self.page.keyboard.press("Escape")
                logger.warning("Could not find 'Replace' option")
                return False

        # Now handle the upload dialog
        return await self._upload_image_file(new_image_path)

    async def upload_image(self, image_path: str) -> bool:
        """Upload an image to the design via the Uploads panel."""
        # Click "Uploads" in sidebar
        uploads_btn = self.page.locator('text="Uploads"')
        if await uploads_btn.count() > 0:
            await uploads_btn.click()
            await asyncio.sleep(1)

            # Click "Upload files"
            upload_files_btn = self.page.locator('button:has-text("Upload files"), button:has-text("Upload media")')
            if await upload_files_btn.count() > 0:
                await upload_files_btn.click()
                await asyncio.sleep(0.5)

        return await self._upload_image_file(image_path)

    async def _upload_image_file(self, image_path: str) -> bool:
        """Set file on hidden input and wait for upload."""
        file_inputs = await self.page.query_selector_all('input[type="file"]')
        for inp in file_inputs:
            try:
                await inp.set_input_files(image_path)
                await asyncio.sleep(3)
                logger.info(f"Uploaded: {image_path}")
                return True
            except Exception:
                continue
        logger.warning("No file input found for upload")
        return False

    async def place_image_on_canvas(self, x: int = 540, y: int = 540):
        """Click on canvas to place a recently uploaded image."""
        await self.page.mouse.click(x, y)
        await asyncio.sleep(1)

    # ── Element Manipulation ───────────────────────────────────────

    async def get_all_elements(self) -> List[Dict]:
        """Get all selectable elements on the canvas."""
        return await self.page.evaluate("""
        () => {
            const results = [];
            
            // Text elements (via TreeWalker)
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            const seen = new Set();
            let node;
            while (node = walker.nextNode()) {
                const text = node.textContent.trim();
                if (text.length > 2 && text.length < 100 && !seen.has(text)) {
                    const parent = node.parentElement;
                    if (parent) {
                        const rect = parent.getBoundingClientRect();
                        if (rect.x > 200 && rect.x < 1200 && rect.y > 80 && rect.y < 700 && rect.width > 10) {
                            seen.add(text);
                            results.push({
                                type: 'text',
                                text: text.substring(0, 50),
                                x: Math.round(rect.x + rect.width / 2),
                                y: Math.round(rect.y + rect.height / 2),
                                w: Math.round(rect.width),
                                h: Math.round(rect.height)
                            });
                        }
                    }
                }
            }
            
            // Image elements
            const imgs = document.querySelectorAll('img');
            for (const img of imgs) {
                const rect = img.getBoundingClientRect();
                if (rect.x > 200 && rect.x < 1200 && rect.y > 80 && rect.y < 700 &&
                    rect.width > 50 && rect.height > 50) {
                    results.push({
                        type: 'image',
                        src: (img.src || '').substring(0, 60),
                        x: Math.round(rect.x + rect.width / 2),
                        y: Math.round(rect.y + rect.height / 2),
                        w: Math.round(rect.width),
                        h: Math.round(rect.height)
                    });
                }
            }
            
            return results;
        }
        """)

    async def delete_element_at(self, x: int, y: int):
        """Select and delete an element at coordinates."""
        await self.page.mouse.click(x, y)
        await asyncio.sleep(0.5)
        # Press Delete key
        await self.page.keyboard.press("Delete")
        await asyncio.sleep(0.5)

    async def move_element(self, from_x: int, from_y: int, to_x: int, to_y: int):
        """Drag an element from one position to another."""
        await self.page.mouse.move(from_x, from_y)
        await self.page.mouse.down()
        await asyncio.sleep(0.3)
        await self.page.mouse.move(to_x, to_y)
        await asyncio.sleep(0.3)
        await self.page.mouse.up()
        await asyncio.sleep(0.5)

    async def resize_element(self, x: int, y: int, direction: str = "se", amount: int = 100):
        """
        Resize an element by dragging its handles.
        direction: 'nw', 'ne', 'sw', 'se' (corner handles)
        """
        await self.page.mouse.click(x, y)
        await asyncio.sleep(0.5)

        # Find resize handle
        handle = await self.page.evaluate(f"""
        () => {{
            const handles = document.querySelectorAll('[class*="handle"], [class*="resize"], [class*="corner"]');
            for (const h of handles) {{
                const rect = h.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {{
                    return {{ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) }};
                }}
            }}
            return null;
        }}
        """)

        if handle:
            await self.page.mouse.move(handle['x'], handle['y'])
            await self.page.mouse.down()
            dx = amount if 'e' in direction else -amount
            dy = amount if 's' in direction else -amount
            await self.page.mouse.move(handle['x'] + dx, handle['y'] + dy)
            await self.page.mouse.up()

    async def duplicate_element(self, x: int, y: int):
        """Select and duplicate an element."""
        await self.page.mouse.click(x, y)
        await asyncio.sleep(0.5)
        # Cmd+D to duplicate
        await self.page.keyboard.press("Meta+d")
        await asyncio.sleep(0.5)

    # ── Template Selection ────────────────────────────────────────

    async def search_templates(self, query: str) -> List[Dict]:
        """Search Canva templates."""
        # Navigate to templates page
        await self.page.goto(f"https://www.canva.com/templates/?query={query}",
                             wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        return await self.page.evaluate("""
        () => {
            const results = [];
            // Template thumbnails
            const thumbs = document.querySelectorAll('a[href*="/design/"], a[href*="/templates/"]');
            for (const thumb of thumbs) {
                const rect = thumb.getBoundingClientRect();
                if (rect.width > 50 && rect.height > 50) {
                    const img = thumb.querySelector('img');
                    results.push({
                        href: thumb.href || '',
                        title: (thumb.getAttribute('aria-label') || thumb.textContent || '').trim().substring(0, 50),
                        img: img ? (img.src || '').substring(0, 80) : '',
                        x: Math.round(rect.x + rect.width / 2),
                        y: Math.round(rect.y + rect.height / 2)
                    });
                }
            }
            return results;
        }
        """)

    async def select_template(self, index: int = 0) -> Optional[str]:
        """Click on a template by index and return the design URL."""
        templates = await self.page.evaluate("""
        () => {
            const thumbs = document.querySelectorAll('a[href*="/design/"], a[href*="/templates/"]');
            const results = [];
            for (const thumb of thumbs) {
                const rect = thumb.getBoundingClientRect();
                if (rect.width > 50 && rect.height > 50) {
                    results.push({ href: thumb.href, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                }
            }
            return results;
        }
        """)

        if index < len(templates):
            t = templates[index]
            await self.page.mouse.click(t['x'], t['y'])
            await asyncio.sleep(3)

            # Look for "Customize this template" button
            customize = self.page.locator('button:has-text("Customize"), a:has-text("Customize")')
            if await customize.count() > 0:
                await customize.click()
                await asyncio.sleep(5)
                return self.page.url

        return None

    # ── Export ─────────────────────────────────────────────────────

    async def export_png(self, output_path: Optional[str] = None) -> Optional[str]:
        """Export design as PNG."""
        return await self._export("png", output_path)

    async def export_pdf(self, output_path: Optional[str] = None) -> Optional[str]:
        """Export design as PDF."""
        return await self._export("pdf", output_path)

    async def export_jpg(self, output_path: Optional[str] = None) -> Optional[str]:
        """Export design as JPG."""
        return await self._export("jpg", output_path)

    async def _export(self, format: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Export design via Canva's download dialog.
        
        Flow: Share → Download → Select format → Download
        """
        if not output_path:
            Config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = int(time.time())
            output_path = str(Config.EXPORT_DIR / f"design_{timestamp}.{format}")

        # Click "Share" button
        share_btn = self.page.locator('[aria-label="Share"], button:has-text("Share")')
        if await share_btn.count() > 0:
            await share_btn.click()
            await asyncio.sleep(1)

            # Click "Download"
            download_btn = self.page.locator('button:has-text("Download"), [aria-label*="Download"]')
            if await download_btn.count() > 0:
                await download_btn.click()
                await asyncio.sleep(1)

                # Select format
                format_option = self.page.locator(f'text="{format.upper()}", [aria-label*="{format}"]')
                if await format_option.count() > 0:
                    await format_option.click()
                    await asyncio.sleep(0.5)

                # Click final download button
                final_download = self.page.locator('button:has-text("Download").VgvqkQ, button:has-text("Download")[class*="primary"]')
                if await final_download.count() == 0:
                    final_download = self.page.locator('button:has-text("Download")')

                if await final_download.count() > 0:
                    # Set up download handler
                    async with self.page.expect_download(timeout=30000) as download_info:
                        await final_download.click()

                    download = await download_info.value
                    await download.save_as(output_path)
                    logger.info(f"Exported to: {output_path}")
                    return output_path

        logger.error("Export failed")
        return None

    async def screenshot(self, path: Optional[str] = None) -> str:
        """Take a screenshot of the current state."""
        if not path:
            Config.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = int(time.time())
            path = str(Config.SCREENSHOT_DIR / f"screenshot_{timestamp}.png")

        await self.page.screenshot(path=path)
        logger.info(f"Screenshot: {path}")
        return path

    # ── State ──────────────────────────────────────────────────────

    async def get_state(self) -> Dict:
        """Get full formatting state of selected text."""
        return await self.page.evaluate("""
        () => {
            const getAria = (sel) => {
                const el = document.querySelector(sel);
                return el ? (el.getAttribute('aria-label') || '').toString() : '';
            };
            const getPressed = (sel) => {
                const el = document.querySelector(sel);
                return el ? el.getAttribute('aria-pressed') === 'true' : null;
            };
            const getVal = (sel) => {
                const el = document.querySelector(sel);
                return el ? el.value : '';
            };

            return {
                font: getAria('[aria-label*="Toggle font selector"]').replace('Toggle font selector, current font: ', ''),
                size: getVal('input[aria-label="Font size"]'),
                bold: getPressed('[aria-label="Bold"]'),
                italic: getPressed('[aria-label="Italics"]'),
                underline: getPressed('[aria-label="Underline"]'),
                strikethrough: getPressed('[aria-label="Strikethrough"]'),
                color: getAria('[aria-label*="Current text colour"]').replace('Current text colour ', ''),
                alignment: getAria('[aria-label*="Toggle text alignment"]').replace('Toggle text alignment, current alignment: ', ''),
                url: window.location.href
            };
        }
        """)

    # ── High-Level Workflows ───────────────────────────────────────

    async def create_quote_post(
        self,
        quote: str,
        author: str = "",
        template_query: str = "minimalist quote instagram",
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Full workflow: Search template → Customize → Style text → Export.
        
        Args:
            quote: The quote text
            author: Author attribution (optional)
            template_query: Search term for templates
            output_path: Export path (auto-generated if None)
            
        Returns:
            Path to exported file, or None on failure
        """
        logger.info(f"Creating quote post: '{quote[:30]}...'")

        # 1. Search templates
        templates = await self.search_templates(template_query)
        if not templates:
            logger.error("No templates found")
            return None
        logger.info(f"Found {len(templates)} templates")

        # 2. Select first template
        design_url = await self.select_template(0)
        if not design_url:
            logger.error("Could not open template")
            return None
        logger.info(f"Opened template: {design_url[:80]}")

        # 3. Find and replace text
        # Try to find existing text and replace it
        elements = await self.get_all_images_on_canvas()
        logger.info(f"Found {len(elements)} elements on canvas")

        # 4. Style the quote text
        await self.style_text(
            text=quote[:20],  # Partial match
            font=Config.BRAND_FONT,
            size=Config.BRAND_SIZE,
            color=Config.BRAND_COLOR,
            bold=Config.BOLD,
            italic=Config.ITALIC,
            alignment=Config.ALIGNMENT,
        )

        # 5. Export
        result = await self.export_png(output_path)
        if result:
            logger.info(f"✅ Quote post created: {result}")
        return result

    async def get_all_images_on_canvas(self) -> List[Dict]:
        """Alias for find_images_on_canvas."""
        return await self.find_images_on_canvas()


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Canva Designer — Browser Automation Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Style command
    style_parser = subparsers.add_parser("style", help="Style text in a design")
    style_parser.add_argument("--design", required=True, help="Design URL")
    style_parser.add_argument("--text", required=True, help="Text to find and style")
    style_parser.add_argument("--font", default=Config.BRAND_FONT, help="Font family")
    style_parser.add_argument("--size", type=int, default=Config.BRAND_SIZE, help="Font size")
    style_parser.add_argument("--color", default=Config.BRAND_COLOR, help="Hex color")
    style_parser.add_argument("--bold", action="store_true", help="Make bold")
    style_parser.add_argument("--italic", action="store_true", help="Make italic")
    style_parser.add_argument("--align", default=Config.ALIGNMENT, help="Alignment")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export a design")
    export_parser.add_argument("--design", required=True, help="Design URL")
    export_parser.add_argument("--format", default="png", choices=["png", "pdf", "jpg"])
    export_parser.add_argument("--output", help="Output file path")

    # Quote command
    quote_parser = subparsers.add_parser("quote", help="Create a quote post")
    quote_parser.add_argument("--quote", required=True, help="Quote text")
    quote_parser.add_argument("--author", default="", help="Author name")
    quote_parser.add_argument("--template", default="minimalist quote instagram", help="Template search")
    quote_parser.add_argument("--output", help="Output file path")

    # State command
    state_parser = subparsers.add_parser("state", help="Get current design state")
    state_parser.add_argument("--design", required=True, help="Design URL")

    # Elements command
    elements_parser = subparsers.add_parser("elements", help="List all elements on canvas")
    elements_parser.add_argument("--design", required=True, help="Design URL")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    designer = CanvaDesigner()
    if not await designer.connect():
        print("ERROR: Could not connect to Chrome. Make sure Chrome is running with --remote-debugging-port=9222")
        return

    try:
        if args.command == "style":
            await designer.open_design(args.design)
            await designer.style_text(
                text=args.text,
                font=args.font,
                size=args.size,
                color=args.color,
                bold=args.bold,
                italic=args.italic,
                alignment=args.align,
            )
            state = await designer.get_state()
            print(json.dumps(state, indent=2))

        elif args.command == "export":
            await designer.open_design(args.design)
            if args.format == "png":
                result = await designer.export_png(args.output)
            elif args.format == "pdf":
                result = await designer.export_pdf(args.output)
            else:
                result = await designer.export_jpg(args.output)
            if result:
                print(f"Exported to: {result}")
            else:
                print("Export failed")

        elif args.command == "quote":
            result = await designer.create_quote_post(
                quote=args.quote,
                author=args.author,
                template_query=args.template,
                output_path=args.output,
            )
            if result:
                print(f"Created: {result}")
            else:
                print("Failed to create quote post")

        elif args.command == "state":
            await designer.open_design(args.design)
            state = await designer.get_state()
            print(json.dumps(state, indent=2))

        elif args.command == "elements":
            await designer.open_design(args.design)
            elements = await designer.get_all_elements()
            for i, el in enumerate(elements):
                print(f"[{i}] {el['type']}: {el.get('text', el.get('src', ''))[:40]} at ({el['x']}, {el['y']})")

    finally:
        await designer.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
