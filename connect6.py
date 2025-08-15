#!/usr/bin/env python3
import sys
import random

EMPTY, BLACK, WHITE = '.', 'X', 'O'
BLACK1, BLACK2, WHITE1, WHITE2 = 0, 1, 2, 3

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
            "gogui-rules_game_id":          self.cmd_game_id,
            "gogui-rules_board":            self.cmd_board,
            "gogui-rules_board_gfx":        self.cmd_board_gfx,
            "gogui-rules_captured_count":   self.cmd_captured_count,
            "gogui-rules_board_size":       self.cmd_board_size,
            "gogui-rules_legal_moves":      self.cmd_legal_moves,
            "gogui-rules_side_to_move":     self.cmd_side_to_move,
            "gogui-rules_final_result":     self.cmd_final_result,
        }
        self.running = True
        self.to_play = BLACK2
        self.winner = EMPTY


    def _init_board(self):
        self.board = [['.' for _ in range(self.size)] for _ in range(self.size)]
        self.to_play = BLACK2

    def run(self):
        while self.running:
            line = sys.stdin.readline()
            print(line, file=sys.stderr)
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
            print(f"= {prefix}{message}\n")
        else:
            print(f" {message}\n")
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
        colour, vertex = args[0].upper(), args[1].upper()
        if args[0].upper() == 'B':
            colour = BLACK
        elif args[0].upper() == 'W':
            colour = WHITE
        self._play(vertex, colour)
        return ""

    def cmd_genmove(self, args):
        if(len(args) > 0):
            if args[0].upper() == 'B':
                colour = BLACK
            elif args[0].upper() == 'W':
                colour = WHITE
        else:
            if self.to_play in (BLACK1, BLACK2):
                colour = BLACK
            else:
                colour = WHITE
        # collect all empty intersections
        empties = self._empties()

        if not empties:
            vertex = "PASS"
        else:
            r, c = random.choice(empties)
            vertex = self._coords_to_vertex((r,c))
        self._play(vertex, colour)

        return vertex

    def cmd_quit(self, args):
        self.running = False
        return ""
    
    def cmd_game_id(self, args):
        return "Connect6"
    
    def cmd_board(self, args):
        board_str = ""
        for i in range(self.size):
            for j in range(self.size):
                board_str += self.board[i][j]
                board_str += ' '
            board_str += '\n'
        return board_str
    
    def cmd_board_gfx(self, args):
        return ""
    
    def cmd_captured_count(self, args):
        return "0 0"
    
    def cmd_board_size(self, args):
        return f"{self.size}"

    def cmd_legal_moves(self, args):
        print("legal moves", file=sys.stderr)
        vertices = ""
        runs = self._find_six_in_a_row()
        if runs:
            r = runs[0]
            self.winner = r['player']
        else:
            empties = self._empties()
            for e in empties:
                r, c = e
                vertices += self._coords_to_vertex((r,c)) + " "
        return vertices
    
    def cmd_side_to_move(self, args):
        if(self.to_play == BLACK1 or self.to_play == BLACK2):
            return "black"
        else:
            return "white"
    
    def cmd_final_result(self, args):
        return f"{self.winner} wins."

    # --- utility ---

    def _vertex_to_coords(self, vertex):
        """Convert a GTP vertex like 'D4' to zero-based (row, col)."""
        letter = vertex[0]
        number = int(vertex[1:])
        all_cols = [c for c in "ABCDEFGHJKLMNOPQRST"]
        col = all_cols.index(letter)
        row = self.size - number
        if not (0 <= row < self.size):
            raise ValueError("row out of range")
        return row, col
    
    def _coords_to_vertex(self, coords):
        """Convert a coord (r,c) to a GTP vertex like 'D4'"""
        # build column labels (skip 'I') up to current board size
        all_cols = [c for c in "ABCDEFGHJKLMNOPQRST"]  # 19-letter palette
        cols = all_cols[: self.size]
        r, c = coords
        return f"{cols[c]}{self.size - r}"
    
    def _empties(self):
        return [
            (r, c)
            for r in range(self.size)
            for c in range(self.size)
            if self.board[r][c] == "."
        ]
    
    def _play(self, vertex, colour):
        # todo: check if colour is consistent with to_play
        if vertex != "PASS":
            row, col = self._vertex_to_coords(vertex)
            self.board[row][col] = colour
        self.moves.append((colour, vertex))
        self.to_play = (self.to_play + 1) % 4

    def _find_six_in_a_row(self):
        """
        Returns a list of runs with length >= 6:
        [{'player': 'X'/'O',
            'start': (r, c),
            'end': (r, c),
            'length': L,
            'direction': (dr, dc),
            'cells': [(r,c), ...]}]
        """
        dirs = [(0, 1), (1, 0), (1, 1), (1, -1)]  # →, ↓, ↘, ↙
        results = []

        for r in range(self.size):
            for c in range(self.size):
                s = self.board[r][c]
                if s not in (BLACK, WHITE):
                    continue
                for dr, dc in dirs:
                    # ensure (r,c) is the START of this run in this direction
                    pr, pc = r - dr, c - dc
                    if 0 <= pr < self.size and 0 <= pc < self.size and self.board[pr][pc] == s:
                        continue

                    # walk forward
                    cells = []
                    rr, cc = r, c
                    while 0 <= rr < self.size and 0 <= cc < self.size and self.board[rr][cc] == s:
                        cells.append((rr, cc))
                        rr += dr
                        cc += dc

                    if len(cells) >= 6:
                        results.append({
                            'player': s,
                            'start': cells[0],
                            'end': cells[-1],
                            'length': len(cells),
                            'direction': (dr, dc),
                            'cells': cells
                        })
        return results

    # def has_winner(board):
    #     """
    #     Convenience helper: returns (player, cells) for the first found winning run,
    #     or None if there is no 6+ in a row.
    #     """
    #     runs = find_six_in_a_row(board)
    #     if runs:
    #         r = runs[0]
    #         return r['player'], r['cells']
    #     return None



if __name__ == "__main__":
    engine = DummyGtpEngine()
    engine.run()
