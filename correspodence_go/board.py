"""Go board representation and game logic."""

from typing import Optional, Set, Tuple, List
from enum import Enum
from dataclasses import dataclass
import json


class Stone(Enum):
    """Represents a stone on the board."""
    EMPTY = 0
    BLACK = 1
    WHITE = 2

    def opposite(self) -> 'Stone':
        """Return the opposite color stone."""
        if self == Stone.BLACK:
            return Stone.WHITE
        elif self == Stone.WHITE:
            return Stone.BLACK
        return Stone.EMPTY

    def __str__(self) -> str:
        """String representation for display."""
        if self == Stone.BLACK:
            return '○'  # Empty circle for black
        elif self == Stone.WHITE:
            return '●'  # Filled circle for white
        return '·'


@dataclass
class Move:
    """Represents a move in the game."""
    x: int
    y: int
    color: Stone

    def to_sgf_coords(self, board_size: int) -> str:
        """Convert to SGF coordinate format (aa to ss)."""
        # SGF uses letters a-s for coordinates
        x_char = chr(ord('a') + self.x)
        y_char = chr(ord('a') + self.y)
        return f"{x_char}{y_char}"

    @classmethod
    def from_sgf_coords(cls, coords: str, color: Stone) -> 'Move':
        """Create a Move from SGF coordinate format."""
        if len(coords) != 2:
            raise ValueError(f"Invalid SGF coordinates: {coords}")
        x = ord(coords[0]) - ord('a')
        y = ord(coords[1]) - ord('a')
        return cls(x, y, color)

    @classmethod
    def from_human_coords(cls, coords: str, color: Stone) -> 'Move':
        """Create a Move from human-readable coordinates (e.g., 'A1', 'D4')."""
        if len(coords) < 2 or len(coords) > 3:
            raise ValueError(f"Invalid coordinates: {coords}")

        col_char = coords[0].upper()
        if col_char == 'I':
            raise ValueError("'I' is not used in Go coordinates (use A-H, J-T)")

        # Adjust for skipped 'I' - J and beyond need to be shifted down by 1
        if col_char >= 'J':
            col = ord(col_char) - ord('A') - 1
        else:
            col = ord(col_char) - ord('A')

        row = int(coords[1:]) - 1
        return cls(col, row, color)

    def to_human_coords(self) -> str:
        """Convert to human-readable coordinates."""
        # Skip 'I' in Go coordinates
        if self.x < 8:
            col = chr(ord('A') + self.x)
        else:
            col = chr(ord('A') + self.x + 1)  # Skip 'I'
        row = str(self.y + 1)
        return f"{col}{row}"


class GoBoard:
    """Represents a Go board and handles game logic."""

    def __init__(self, size: int = 19):
        """Initialize a Go board.

        Args:
            size: Board size (typically 9, 13, or 19)
        """
        if size not in [9, 13, 19]:
            raise ValueError(f"Board size must be 9, 13, or 19, got {size}")

        self.size = size
        self.board = [[Stone.EMPTY for _ in range(size)] for _ in range(size)]
        self.captured_black = 0
        self.captured_white = 0
        self.move_history: List[Move] = []
        self.ko_point: Optional[Tuple[int, int]] = None

    def get(self, x: int, y: int) -> Stone:
        """Get the stone at position (x, y)."""
        if not self._is_valid_position(x, y):
            raise ValueError(f"Position ({x}, {y}) is out of bounds")
        return self.board[y][x]

    def set(self, x: int, y: int, stone: Stone) -> None:
        """Set a stone at position (x, y)."""
        if not self._is_valid_position(x, y):
            raise ValueError(f"Position ({x}, {y}) is out of bounds")
        self.board[y][x] = stone

    def _is_valid_position(self, x: int, y: int) -> bool:
        """Check if a position is within board bounds."""
        return 0 <= x < self.size and 0 <= y < self.size

    def _get_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Get valid neighboring positions."""
        neighbors = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if self._is_valid_position(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    def _get_group(self, x: int, y: int) -> Set[Tuple[int, int]]:
        """Get all stones in the same group as the stone at (x, y)."""
        if self.get(x, y) == Stone.EMPTY:
            return set()

        color = self.get(x, y)
        group = set()
        to_check = [(x, y)]

        while to_check:
            cx, cy = to_check.pop()
            if (cx, cy) in group:
                continue
            group.add((cx, cy))

            for nx, ny in self._get_neighbors(cx, cy):
                if self.get(nx, ny) == color and (nx, ny) not in group:
                    to_check.append((nx, ny))

        return group

    def _has_liberties(self, group: Set[Tuple[int, int]]) -> bool:
        """Check if a group has any liberties."""
        for x, y in group:
            for nx, ny in self._get_neighbors(x, y):
                if self.get(nx, ny) == Stone.EMPTY:
                    return True
        return False

    def _remove_group(self, group: Set[Tuple[int, int]]) -> int:
        """Remove a group of stones from the board."""
        if not group:
            return 0

        # Determine color being captured
        sample_x, sample_y = next(iter(group))
        color = self.get(sample_x, sample_y)

        # Remove stones
        for x, y in group:
            self.set(x, y, Stone.EMPTY)

        return len(group)

    def _capture_stones(self, x: int, y: int, color: Stone) -> int:
        """Capture enemy stones around the given position."""
        captured = 0
        enemy_color = color.opposite()

        for nx, ny in self._get_neighbors(x, y):
            if self.get(nx, ny) == enemy_color:
                group = self._get_group(nx, ny)
                if not self._has_liberties(group):
                    captured += self._remove_group(group)

        return captured

    def is_valid_move(self, x: int, y: int, color: Stone) -> tuple[bool, str]:
        """Check if a move is valid.

        Returns:
            (is_valid, error_message) - error_message is empty string if valid
        """
        # Check if position is on board
        if not self._is_valid_position(x, y):
            return False, f"Position ({x}, {y}) is outside the board"

        # Check if position is empty
        if self.get(x, y) != Stone.EMPTY:
            current_stone = "black" if self.get(x, y) == Stone.BLACK else "white"
            return False, f"Position already occupied by {current_stone} stone"

        # Check ko rule
        if self.ko_point == (x, y):
            return False, "Move violates ko rule (immediate recapture)"

        # Save board state
        saved_board = [row[:] for row in self.board]

        # Temporarily place the stone
        self.set(x, y, color)

        # Check for captures
        captured = self._capture_stones(x, y, color)

        # Check for suicide (placing a stone with no liberties and no captures)
        own_group = self._get_group(x, y)
        is_suicide = not self._has_liberties(own_group) and captured == 0

        # Restore the board completely
        self.board = saved_board

        if is_suicide:
            return False, "Suicide move (stone/group would have no liberties)"

        return True, ""

    def place_stone(self, x: int, y: int, color: Stone) -> tuple[bool, str]:
        """Place a stone on the board.

        Returns:
            (success, error_message) - error_message is empty string if successful
        """
        is_valid, error_msg = self.is_valid_move(x, y, color)
        if not is_valid:
            return False, error_msg

        # Place the stone
        self.set(x, y, color)

        # Capture enemy stones
        captured = self._capture_stones(x, y, color)

        # Update captured counts
        if color == Stone.BLACK:
            self.captured_white += captured
        else:
            self.captured_black += captured

        # Update ko point (simple ko detection)
        # Ko occurs when exactly one stone is captured and the capturing stone
        # would be immediately capturable
        self.ko_point = None
        if captured == 1:
            # Find the captured position
            for nx, ny in self._get_neighbors(x, y):
                if self.get(nx, ny) == Stone.EMPTY:
                    # Check if this was just captured
                    temp_board = [row[:] for row in self.board]
                    self.set(nx, ny, color.opposite())
                    enemy_group = self._get_group(nx, ny)
                    self.board = temp_board

                    if len(enemy_group) == 1:
                        # Check if placing enemy stone here would capture our stone
                        self.set(nx, ny, color.opposite())
                        our_group = self._get_group(x, y)
                        if not self._has_liberties(our_group):
                            self.ko_point = (nx, ny)
                        self.set(nx, ny, Stone.EMPTY)
                        break

        # Record the move
        move = Move(x, y, color)
        self.move_history.append(move)

        return True, ""

    def to_ascii(self, show_coords: bool = True, use_color: bool = True) -> str:
        """Convert board to ASCII representation."""
        lines = []

        # ANSI codes for dimming the dots
        if use_color:
            DIM = '\033[2m'       # Dim text
            RESET = '\033[0m'     # Reset to normal
        else:
            DIM = RESET = ''

        # Column labels
        if show_coords:
            col_labels = "   " + " ".join(chr(ord('A') + i) if i < 8 else chr(ord('A') + i + 1)
                                         for i in range(self.size))
            lines.append(col_labels)

        # Board rows
        for y in range(self.size):
            row_num = self.size - y
            row = []

            if show_coords:
                row.append(f"{row_num:2} ")

            for x in range(self.size):
                stone = self.get(x, self.size - 1 - y)  # Flip Y for display

                # Add special markers for star points (hoshi)
                if stone == Stone.EMPTY:
                    if self._is_star_point(x, self.size - 1 - y):
                        row.append(f'{DIM}+{RESET}')
                    else:
                        row.append(f'{DIM}·{RESET}')
                else:
                    row.append(str(stone))
                row.append(' ')

            if show_coords:
                row.append(f"{row_num:2}")

            lines.append(''.join(row))

        # Column labels again
        if show_coords:
            lines.append(col_labels)

        # Add game info
        lines.append("")
        lines.append(f"Black captured: {self.captured_black}")
        lines.append(f"White captured: {self.captured_white}")
        lines.append(f"Moves played: {len(self.move_history)}")
        if self.ko_point:
            ko_move = Move(self.ko_point[0], self.ko_point[1], Stone.EMPTY)
            lines.append(f"Ko at: {ko_move.to_human_coords()}")

        return '\n'.join(lines)

    def _is_star_point(self, x: int, y: int) -> bool:
        """Check if a position is a star point (hoshi)."""
        star_points = {
            9: [(2, 2), (6, 2), (4, 4), (2, 6), (6, 6)],
            13: [(3, 3), (9, 3), (6, 6), (3, 9), (9, 9)],
            19: [(3, 3), (9, 3), (15, 3), (3, 9), (9, 9), (15, 9),
                 (3, 15), (9, 15), (15, 15)]
        }
        return (x, y) in star_points.get(self.size, [])

    def undo_last_move(self) -> bool:
        """Remove the last move and restore the board state.

        Returns:
            True if a move was undone, False if there are no moves to undo.
        """
        if not self.move_history:
            return False

        # Remove the last move
        self.move_history.pop()

        # Rebuild the board from scratch by replaying all remaining moves
        # This ensures captures and ko state are correctly restored
        temp_board = GoBoard(self.size)

        for move in self.move_history:
            # Skip pass moves (marked with -1, -1)
            if move.x >= 0 and move.y >= 0:
                temp_board.place_stone(move.x, move.y, move.color)

        # Copy the rebuilt state back
        self.board = temp_board.board
        self.captured_black = temp_board.captured_black
        self.captured_white = temp_board.captured_white
        self.ko_point = temp_board.ko_point

        return True

    def save_to_dict(self) -> dict:
        """Save board state to a dictionary."""
        return {
            'size': self.size,
            'board': [[stone.value for stone in row] for row in self.board],
            'captured_black': self.captured_black,
            'captured_white': self.captured_white,
            'moves': [(m.x, m.y, m.color.value) for m in self.move_history],
            'ko_point': self.ko_point
        }

    @classmethod
    def load_from_dict(cls, data: dict) -> 'GoBoard':
        """Load board state from a dictionary."""
        board = cls(data['size'])

        # Restore board state
        for y in range(board.size):
            for x in range(board.size):
                board.board[y][x] = Stone(data['board'][y][x])

        board.captured_black = data['captured_black']
        board.captured_white = data['captured_white']
        board.move_history = [Move(x, y, Stone(color)) for x, y, color in data['moves']]
        board.ko_point = tuple(data['ko_point']) if data['ko_point'] else None

        return board