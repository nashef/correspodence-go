"""Image rendering for Go boards with terminal display support."""

import os
import sys
import base64
import tempfile
from typing import Optional, Tuple
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from .board import GoBoard, Stone


class BoardImageRenderer:
    """Renders Go boards as images."""

    def __init__(self, board_size: int = 19):
        """Initialize the renderer.

        Args:
            board_size: Size of the Go board (9, 13, or 19)
        """
        self.board_size = board_size

        # Image dimensions
        self.cell_size = 40
        self.margin = 60
        self.board_pixel_size = self.cell_size * (board_size - 1)
        self.image_size = self.board_pixel_size + 2 * self.margin

        # Colors
        self.board_color = (220, 180, 140)  # Wood-like color
        self.grid_color = (0, 0, 0)
        self.black_stone_color = (20, 20, 20)
        self.white_stone_color = (240, 240, 240)
        self.star_point_color = (0, 0, 0)
        self.label_color = (50, 50, 50)

        # Stone rendering
        self.stone_radius = int(self.cell_size * 0.45)

    def render(self, board: GoBoard, show_coords: bool = True) -> Image.Image:
        """Render a Go board as a PIL Image.

        Args:
            board: The GoBoard to render
            show_coords: Whether to show coordinate labels

        Returns:
            PIL Image object
        """
        # Create image with board color background
        img = Image.new('RGB', (self.image_size, self.image_size), self.board_color)
        draw = ImageDraw.Draw(img)

        # Draw grid lines
        for i in range(self.board_size):
            # Calculate position
            pos = self.margin + i * self.cell_size

            # Vertical lines
            draw.line(
                [(pos, self.margin), (pos, self.margin + self.board_pixel_size)],
                fill=self.grid_color,
                width=1
            )

            # Horizontal lines
            draw.line(
                [(self.margin, pos), (self.margin + self.board_pixel_size, pos)],
                fill=self.grid_color,
                width=1
            )

        # Draw thicker border
        border_rect = [
            (self.margin, self.margin),
            (self.margin + self.board_pixel_size, self.margin + self.board_pixel_size)
        ]
        draw.rectangle(border_rect, outline=self.grid_color, width=2)

        # Draw star points
        star_points = self._get_star_points()
        for x, y in star_points:
            pixel_x = self.margin + x * self.cell_size
            pixel_y = self.margin + y * self.cell_size
            radius = 4
            draw.ellipse(
                [pixel_x - radius, pixel_y - radius, pixel_x + radius, pixel_y + radius],
                fill=self.star_point_color
            )

        # Draw stones
        for x in range(self.board_size):
            for y in range(self.board_size):
                stone = board.get(x, y)
                if stone != Stone.EMPTY:
                    self._draw_stone(draw, x, y, stone)

        # Draw coordinate labels if requested
        if show_coords:
            self._draw_coordinates(draw)

        return img

    def _draw_stone(self, draw: ImageDraw.Draw, x: int, y: int, stone: Stone) -> None:
        """Draw a stone on the board.

        Args:
            draw: PIL ImageDraw object
            x: Board x coordinate
            y: Board y coordinate
            stone: Stone type (BLACK or WHITE)
        """
        pixel_x = self.margin + x * self.cell_size
        pixel_y = self.margin + y * self.cell_size

        # Main stone circle
        if stone == Stone.BLACK:
            color = self.black_stone_color
            outline_color = self.black_stone_color
        else:
            color = self.white_stone_color
            outline_color = (100, 100, 100)  # Gray outline for white stones

        # Draw stone with gradient effect (simple version)
        draw.ellipse(
            [pixel_x - self.stone_radius, pixel_y - self.stone_radius,
             pixel_x + self.stone_radius, pixel_y + self.stone_radius],
            fill=color,
            outline=outline_color,
            width=1
        )

        # Add a highlight for 3D effect
        if stone == Stone.BLACK:
            highlight_color = (60, 60, 60)
            highlight_offset = -self.stone_radius // 3
        else:
            highlight_color = (255, 255, 255)
            highlight_offset = -self.stone_radius // 3

        highlight_radius = self.stone_radius // 4
        draw.ellipse(
            [pixel_x + highlight_offset - highlight_radius,
             pixel_y + highlight_offset - highlight_radius,
             pixel_x + highlight_offset + highlight_radius,
             pixel_y + highlight_offset + highlight_radius],
            fill=highlight_color
        )

    def _draw_coordinates(self, draw: ImageDraw.Draw) -> None:
        """Draw coordinate labels around the board.

        Args:
            draw: PIL ImageDraw object
        """
        try:
            # Try to use a better font if available
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            font = ImageFont.load_default()

        for i in range(self.board_size):
            # Column labels (A-T, skipping I)
            col_label = chr(ord('A') + i) if i < 8 else chr(ord('A') + i + 1)
            x = self.margin + i * self.cell_size

            # Top labels
            draw.text((x - 5, self.margin - 25), col_label, fill=self.label_color, font=font)
            # Bottom labels
            draw.text((x - 5, self.margin + self.board_pixel_size + 10), col_label, fill=self.label_color, font=font)

            # Row labels (1-19)
            row_label = str(self.board_size - i)
            y = self.margin + i * self.cell_size

            # Left labels
            draw.text((self.margin - 30, y - 10), row_label, fill=self.label_color, font=font)
            # Right labels
            draw.text((self.margin + self.board_pixel_size + 15, y - 10), row_label, fill=self.label_color, font=font)

    def _get_star_points(self) -> list:
        """Get star point coordinates for the current board size.

        Returns:
            List of (x, y) tuples for star points
        """
        star_points = {
            9: [(2, 2), (6, 2), (4, 4), (2, 6), (6, 6)],
            13: [(3, 3), (9, 3), (6, 6), (3, 9), (9, 9)],
            19: [(3, 3), (9, 3), (15, 3), (3, 9), (9, 9), (15, 9),
                 (3, 15), (9, 15), (15, 15)]
        }
        return star_points.get(self.board_size, [])

    def save_image(self, board: GoBoard, filename: str, show_coords: bool = True) -> None:
        """Save board as an image file.

        Args:
            board: The GoBoard to render
            filename: Output filename
            show_coords: Whether to show coordinate labels
        """
        img = self.render(board, show_coords)
        img.save(filename)

    def to_sixel(self, board: GoBoard, show_coords: bool = True) -> str:
        """Convert board to Sixel format for terminal display.

        Sixel is supported by terminals like xterm, mlterm, mintty.

        Args:
            board: The GoBoard to render
            show_coords: Whether to show coordinate labels

        Returns:
            Sixel escape sequence string
        """
        img = self.render(board, show_coords)

        # Resize for terminal display
        max_width = 800
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to Sixel (requires libsixel-bin package)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            img.save(tmp.name)
            try:
                import subprocess
                result = subprocess.run(
                    ['img2sixel', tmp.name],
                    capture_output=True,
                    text=True
                )
                return result.stdout
            except FileNotFoundError:
                return "Error: img2sixel not found. Install with: apt-get install libsixel-bin"
            finally:
                os.unlink(tmp.name)

    def to_iterm2(self, board: GoBoard, show_coords: bool = True) -> str:
        """Convert board to iTerm2 inline image format.

        Args:
            board: The GoBoard to render
            show_coords: Whether to show coordinate labels

        Returns:
            iTerm2 inline image escape sequence
        """
        img = self.render(board, show_coords)

        # Resize for terminal display
        max_width = 800
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_data = base64.b64encode(buffer.getvalue()).decode('ascii')

        # iTerm2 proprietary escape sequence
        return f'\033]1337;File=inline=1;width=auto;height=auto:{img_data}\007'

    def to_kitty(self, board: GoBoard, show_coords: bool = True) -> str:
        """Convert board to Kitty graphics protocol format.

        Args:
            board: The GoBoard to render
            show_coords: Whether to show coordinate labels

        Returns:
            Kitty graphics protocol commands
        """
        img = self.render(board, show_coords)

        # Resize for terminal display
        max_width = 800
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_data = base64.b64encode(buffer.getvalue()).decode('ascii')

        # Kitty graphics protocol
        # a=T: transmit image, f=100: PNG format, t=d: direct transmission
        return f'\033_Ga=T,f=100,t=d;{img_data}\033\\'

    def to_ascii_art(self, board: GoBoard, show_coords: bool = True) -> str:
        """Convert board image to ASCII art using block characters.

        This creates a very compact representation using Unicode block characters.

        Args:
            board: The GoBoard to render
            show_coords: Whether to show coordinate labels

        Returns:
            ASCII art representation using block characters
        """
        img = self.render(board, show_coords)

        # Resize to reasonable terminal size (each character is ~2:1 aspect ratio)
        width = 80
        height = int(width * img.height / img.width / 2)
        img = img.resize((width, height), Image.Resampling.LANCZOS)

        # Convert to grayscale
        img = img.convert('L')

        # Convert to ASCII using block characters
        chars = ' ░▒▓█'
        result = []

        for y in range(height):
            line = []
            for x in range(width):
                pixel = img.getpixel((x, y))
                char_idx = int(pixel / 256 * len(chars))
                if char_idx >= len(chars):
                    char_idx = len(chars) - 1
                line.append(chars[char_idx])
            result.append(''.join(line))

        return '\n'.join(result)