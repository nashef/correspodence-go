"""Command-line interface for Correspodence Go."""

import json
import os
import sys
from pathlib import Path
from typing import Optional
import argparse

from .board import GoBoard, Stone, Move


DEFAULT_GAME_DIR = Path.home() / '.correspodence-go' / 'games'


def get_game_path(game_name: str) -> Path:
    """Get the path to a game file."""
    return DEFAULT_GAME_DIR / f"{game_name}.json"


def load_game(game_name: str) -> Optional[GoBoard]:
    """Load a game from disk."""
    game_path = get_game_path(game_name)
    if not game_path.exists():
        return None

    with open(game_path, 'r') as f:
        data = json.load(f)

    return GoBoard.load_from_dict(data)


def save_game(game_name: str, board: GoBoard) -> None:
    """Save a game to disk."""
    DEFAULT_GAME_DIR.mkdir(parents=True, exist_ok=True)
    game_path = get_game_path(game_name)

    with open(game_path, 'w') as f:
        json.dump(board.save_to_dict(), f, indent=2)


def cmd_new(args: argparse.Namespace) -> None:
    """Create a new game."""
    if load_game(args.name):
        print(f"Error: Game '{args.name}' already exists.", file=sys.stderr)
        sys.exit(1)

    board = GoBoard(args.size)
    save_game(args.name, board)
    print(f"Created new {args.size}x{args.size} game: {args.name}")


def cmd_show(args: argparse.Namespace) -> None:
    """Show the current board state."""
    board = load_game(args.name)
    if not board:
        print(f"Error: Game '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)

    # If --move is specified, rebuild board up to that move
    if args.move is not None:
        if args.move < 0 or args.move > len(board.move_history):
            print(f"Error: Move {args.move} out of range (0-{len(board.move_history)})", file=sys.stderr)
            sys.exit(1)

        # Create a fresh board and replay moves up to the specified point
        temp_board = GoBoard(board.size)
        for i in range(args.move):
            move = board.move_history[i]
            if move.x >= 0 and move.y >= 0:  # Skip passes
                temp_board.place_stone(move.x, move.y, move.color)
        board = temp_board
        print(f"\nGame: {args.name} (at move {args.move})")
    else:
        print(f"\nGame: {args.name}")

    print("-" * 40)

    use_color = not getattr(args, 'no_color', False)
    print(board.to_ascii(show_coords=not args.no_coords, use_color=use_color))


def cmd_move(args: argparse.Namespace) -> None:
    """Make a move in the game."""
    board = load_game(args.name)
    if not board:
        print(f"Error: Game '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)

    # Determine whose turn it is
    if args.color:
        color = Stone.BLACK if args.color.lower() == 'black' else Stone.WHITE
    else:
        # Auto-detect based on move count
        if len(board.move_history) % 2 == 0:
            color = Stone.BLACK
        else:
            color = Stone.WHITE

    # Handle pass
    if args.position.lower() == 'pass':
        # Record pass in move history (using invalid coordinates as marker)
        pass_move = Move(-1, -1, color)
        board.move_history.append(pass_move)
        save_game(args.name, board)
        print(f"{color.name} passes.")
        return

    # Parse the move
    try:
        move = Move.from_human_coords(args.position, color)
    except ValueError as e:
        print(f"Error: Invalid move format: {e}", file=sys.stderr)
        sys.exit(1)

    # Make the move
    success, error_msg = board.place_stone(move.x, move.y, color)
    if not success:
        print(f"Error: Invalid move at {args.position} - {error_msg}", file=sys.stderr)
        sys.exit(1)

    save_game(args.name, board)
    print(f"{color.name} plays at {args.position}")

    # Show board if requested
    if args.show:
        print()
        use_color = not getattr(args, 'no_color', False)
        print(board.to_ascii(use_color=use_color))


def cmd_list(args: argparse.Namespace) -> None:
    """List all games."""
    if not DEFAULT_GAME_DIR.exists():
        print("No games found.")
        return

    games = list(DEFAULT_GAME_DIR.glob("*.json"))
    if not games:
        print("No games found.")
        return

    print("Available games:")
    for game_path in sorted(games):
        game_name = game_path.stem
        try:
            board = load_game(game_name)
            if board:
                next_player = "BLACK" if len(board.move_history) % 2 == 0 else "WHITE"
                print(f"  {game_name:20} - {board.size}x{board.size} board, "
                      f"{len(board.move_history)} moves, {next_player} to play")
        except Exception as e:
            print(f"  {game_name:20} - (error loading: {e})")


def cmd_delete(args: argparse.Namespace) -> None:
    """Delete a game."""
    game_path = get_game_path(args.name)
    if not game_path.exists():
        print(f"Error: Game '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)

    if not args.force:
        response = input(f"Are you sure you want to delete game '{args.name}'? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return

    game_path.unlink()
    print(f"Deleted game: {args.name}")


def cmd_history(args: argparse.Namespace) -> None:
    """Show game move history."""
    board = load_game(args.name)
    if not board:
        print(f"Error: Game '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)

    if not board.move_history:
        print("No moves played yet.")
        return

    print(f"Move history for game '{args.name}':")
    print("-" * 40)

    for i, move in enumerate(board.move_history):
        move_num = i + 1
        color = "Black" if i % 2 == 0 else "White"

        if move.x == -1 and move.y == -1:
            print(f"{move_num:3}. {color:5} passes")
        else:
            coords = move.to_human_coords()
            print(f"{move_num:3}. {color:5} {coords}")


def cmd_moves(args: argparse.Namespace) -> None:
    """Print all moves in order (compact format)."""
    board = load_game(args.name)
    if not board:
        print(f"Error: Game '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)

    if not board.move_history:
        print("No moves played yet.")
        return

    moves_list = []
    for i, move in enumerate(board.move_history):
        if move.x == -1 and move.y == -1:
            moves_list.append("pass")
        else:
            moves_list.append(move.to_human_coords())

    # Print moves in a compact format
    if args.one_per_line:
        for i, move_str in enumerate(moves_list):
            print(f"{i+1}. {move_str}")
    else:
        print(" ".join(moves_list))


def cmd_undo(args: argparse.Namespace) -> None:
    """Undo the last move in a game."""
    board = load_game(args.name)
    if not board:
        print(f"Error: Game '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)

    if not board.move_history:
        print(f"Error: No moves to undo in game '{args.name}'.", file=sys.stderr)
        sys.exit(1)

    # Get the last move for display
    last_move = board.move_history[-1]
    if last_move.x == -1 and last_move.y == -1:
        move_desc = "pass"
    else:
        move_desc = last_move.to_human_coords()

    move_num = len(board.move_history)
    color = "Black" if (move_num - 1) % 2 == 0 else "White"

    # Undo the move
    if board.undo_last_move():
        save_game(args.name, board)
        print(f"Undone: Move {move_num} - {color} {move_desc}")

        # Show board if requested
        if args.show:
            print()
            use_color = not getattr(args, 'no_color', False)
            print(board.to_ascii(use_color=use_color))
    else:
        print(f"Error: Failed to undo move.", file=sys.stderr)
        sys.exit(1)


def cmd_export(args: argparse.Namespace) -> None:
    """Export game to SGF format."""
    board = load_game(args.name)
    if not board:
        print(f"Error: Game '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)

    # Build SGF string
    sgf_lines = [
        "(;",
        f"GM[1]",  # Game type: Go
        f"FF[4]",  # File format version
        f"SZ[{board.size}]",  # Board size
        f"AP[Correspodence-Go:0.1.0]",  # Application
        f"PW[White]",  # White player name
        f"PB[Black]",  # Black player name
    ]

    # Add moves
    for i, move in enumerate(board.move_history):
        color = "B" if i % 2 == 0 else "W"
        if move.x == -1 and move.y == -1:
            sgf_lines.append(f";{color}[]")  # Pass
        else:
            coords = move.to_sgf_coords(board.size)
            sgf_lines.append(f";{color}[{coords}]")

    sgf_lines.append(")")
    sgf_content = "\n".join(sgf_lines)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(sgf_content)
        print(f"Exported game to: {args.output}")
    else:
        print(sgf_content)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog='corr-go',
        description='Command-line Go game manager'
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # New game command
    new_parser = subparsers.add_parser('new', help='Create a new game')
    new_parser.add_argument('name', help='Name for the game')
    new_parser.add_argument(
        '-s', '--size',
        type=int,
        default=19,
        choices=[9, 13, 19],
        help='Board size (default: 19)'
    )

    # Show board command
    show_parser = subparsers.add_parser('show', help='Show the current board')
    show_parser.add_argument('name', help='Game name')
    show_parser.add_argument(
        '--no-coords',
        action='store_true',
        help='Hide coordinate labels'
    )
    show_parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable dimmed dots (for terminals without ANSI support)'
    )
    show_parser.add_argument(
        '--move',
        type=int,
        help='Show board at a specific move number (0 for empty board)'
    )

    # Move command
    move_parser = subparsers.add_parser('move', help='Make a move')
    move_parser.add_argument('name', help='Game name')
    move_parser.add_argument(
        'position',
        help='Position (e.g., D4, K10) or "pass"'
    )
    move_parser.add_argument(
        '-c', '--color',
        choices=['black', 'white'],
        help='Stone color (auto-detected if not specified)'
    )
    move_parser.add_argument(
        '--show',
        action='store_true',
        help='Show board after move'
    )
    move_parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable dimmed dots (for terminals without ANSI support)'
    )

    # List games command
    list_parser = subparsers.add_parser('list', help='List all games')

    # Delete game command
    delete_parser = subparsers.add_parser('delete', help='Delete a game')
    delete_parser.add_argument('name', help='Game name')
    delete_parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Skip confirmation'
    )

    # History command
    history_parser = subparsers.add_parser('history', help='Show move history')
    history_parser.add_argument('name', help='Game name')

    # Moves command
    moves_parser = subparsers.add_parser('moves', help='Print all moves in order')
    moves_parser.add_argument('name', help='Game name')
    moves_parser.add_argument(
        '-l', '--one-per-line',
        action='store_true',
        help='Print one move per line with numbers'
    )

    # Undo command
    undo_parser = subparsers.add_parser('undo', help='Undo the last move')
    undo_parser.add_argument('name', help='Game name')
    undo_parser.add_argument(
        '--show',
        action='store_true',
        help='Show board after undo'
    )
    undo_parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable dimmed dots (for terminals without ANSI support)'
    )

    # Export command
    export_parser = subparsers.add_parser('export', help='Export game to SGF')
    export_parser.add_argument('name', help='Game name')
    export_parser.add_argument(
        '-o', '--output',
        help='Output file (prints to stdout if not specified)'
    )

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    commands = {
        'new': cmd_new,
        'show': cmd_show,
        'move': cmd_move,
        'list': cmd_list,
        'delete': cmd_delete,
        'history': cmd_history,
        'moves': cmd_moves,
        'undo': cmd_undo,
        'export': cmd_export,
    }

    commands[args.command](args)


if __name__ == '__main__':
    main()