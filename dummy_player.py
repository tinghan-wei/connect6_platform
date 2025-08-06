#!/usr/bin/env python3
import sys
import random

class DummyGtpEngine:
    def __init__(self):
        self.size = 19
        self.komi = 0.0
        self.moves = []  # history of (color, vertex)
        # board[row][col] is '.', 'B', or 'W'
        self._init_board()

        self.commands = {
            "protocol_version": self.cmd_protocol_version,
            "name":             self.cmd_name,
            "version":          self.cmd_version,
            "list_commands":    self.cmd_list_commands,
            "boardsize":        self.cmd_boardsize,
            "clear_board":      self.cmd_clear_board,
            "komi":             self.cmd_komi,
            "play":             self.cmd_play,
            "genmove":          self.cmd_genmove,
            "quit":             self.cmd_quit,
        }
        self.running = True

    def _init_board(self):
        self.board = [['.' for _ in range(self.size)] for _ in range(self.size)]

    def run(self):
        while self.running:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if parts[0].isdigit():
                id_, cmd, args = parts[0], parts[1], parts[2:]
            else:
                id_, cmd, args = None, parts[0], parts[1:]

            handler = self.commands.get(cmd)
            if handler:
                try:
                    reply = handler(args)
                    self.respond(id_, reply)
                except Exception as e:
                    self.respond(id_, f"? {cmd} error: {e}")
            else:
                self.respond(id_, f"? unknown command: {cmd}")

    def respond(self, id_, message):
        prefix = f"{id_} " if id_ is not None else ""
        if not message.startswith("?"):
            print(f"={prefix}{message}\n")
        else:
            print(f"{message}\n")
        sys.stdout.flush()

    # --- GTP command handlers ---

    def cmd_protocol_version(self, args):
        return "2"

    def cmd_name(self, args):
        return "dummy-python-gtp"

    def cmd_version(self, args):
        return "0.2"

    def cmd_list_commands(self, args):
        return "\n".join(self.commands.keys())

    def cmd_boardsize(self, args):
        size = int(args[0])
        if size < 2 or size > 100:
            raise ValueError("unacceptable size")
        self.size = size
        self._init_board()
        return ""

    def cmd_clear_board(self, args):
        self.moves.clear()
        self._init_board()
        return ""

    def cmd_komi(self, args):
        self.komi = float(args[0])
        return ""

    def cmd_play(self, args):
        color, vertex = args[0].upper(), args[1].upper()
        if vertex != "PASS":
            row, col = self._vertex_to_coords(vertex)
            self.board[row][col] = color
        self.moves.append((color, vertex))
        return ""

    def cmd_genmove(self, args):
        color = args[0].upper()
        # build column labels (skip 'I') up to current board size
        all_cols = [c for c in "ABCDEFGHJKLMNOPQRST"]  # 19-letter palette
        cols = all_cols[: self.size]

        # collect all empty intersections
        empties = [
            (r, c)
            for r in range(self.size)
            for c in range(self.size)
            if self.board[r][c] == "."
        ]

        if not empties:
            move = "PASS"
        else:
            r, c = random.choice(empties)
            move = f"{cols[c]}{r+1}"
            self.board[r][c] = color
            self.moves.append((color, move))

        return move

    def cmd_quit(self, args):
        self.running = False
        return ""

    # --- utility ---

    def _vertex_to_coords(self, vertex):
        """Convert a GTP vertex like 'D4' to zero-based (row, col)."""
        letter = vertex[0]
        number = int(vertex[1:])
        all_cols = [c for c in "ABCDEFGHJKLMNOPQRST"]
        col = all_cols.index(letter)
        row = number - 1
        if not (0 <= row < self.size):
            raise ValueError("row out of range")
        return row, col

if __name__ == "__main__":
    engine = DummyGtpEngine()
    engine.run()
