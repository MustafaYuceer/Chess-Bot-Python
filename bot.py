import time
import re
import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from playwright.sync_api import sync_playwright
from stockfish import Stockfish
import chess

class ChessBot:
    def __init__(self, log_cb):
        sf_path = "stockfish/stockfish/stockfish-windows-x86-64-avx2.exe"
        self.log = log_cb
        self.log("Loading Stockfish engine...")
        self.stockfish = Stockfish(path=sf_path, depth=15, parameters={"Threads": 2, "Hash": 64})
        self.board = chess.Board()
        self.color = None 
        self.stop_event = threading.Event()
        self.consecutive_sync_count = 0
        self.last_move_time = 0
        
        # Watchdog / Performance
        self.last_attempted_move = None
        self.same_move_counter = 0

    def get_full_state(self, page):
        """Fetches all necessary DOM data in one single JS call (Batch Reading) for maximum speed."""
        try:
            # We use a short timeout and evaluate to avoid CDP round-trip overhead
            return page.evaluate("""() => {
                const pieces = Array.from(document.querySelectorAll('.piece')).map(p => p.className);
                const board = document.querySelector('wc-chess-board');
                const boardClass = board ? board.className : "";
                const bottomClock = document.querySelector('.clock-bottom');
                const topClock = document.querySelector('.clock-top');
                const bottomClockClass = bottomClock ? bottomClock.className : "";
                const topClockClass = topClock ? topClock.className : "";
                const isGameOver = !!document.querySelector('.game-over-modal');
                
                return {
                    pieces,
                    boardClass,
                    bottomClockClass,
                    topClockClass,
                    isGameOver
                };
            }""")
        except:
            return None

    def parse_pieces_to_dict(self, piece_classes):
        board_dict = {}
        piece_map = {
            'wp': 'P', 'wn': 'N', 'wb': 'B', 'wr': 'R', 'wq': 'Q', 'wk': 'K',
            'bp': 'p', 'bn': 'n', 'bb': 'b', 'br': 'r', 'bq': 'q', 'bk': 'k'
        }
        files = {1: 'a', 2: 'b', 3: 'c', 4: 'd', 5: 'e', 6: 'f', 7: 'g', 8: 'h'}
        
        for classes in piece_classes:
            piece_type = None
            for p_class in piece_map.keys():
                if p_class in classes:
                    piece_type = piece_map[p_class]
                    break
                    
            square_match = re.search(r'square-(\d)(\d)', classes)
            if square_match and piece_type:
                f_idx, r_idx = int(square_match.group(1)), int(square_match.group(2))
                sq_name = f"{files[f_idx]}{r_idx}"
                board_dict[sq_name] = piece_type
        return board_dict
        
    def board_to_dict(self, board):
        board_dict = {}
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                board_dict[chess.square_name(square)] = piece.symbol()
        return board_dict
        
    def dicts_match(self, d1, d2):
        if len(d1) != len(d2): return False
        for k, v in d1.items():
            if d2.get(k) != v: return False
        return True

    def find_move_played(self, board_dict):
        for move in self.board.legal_moves:
            self.board.push(move)
            expected_dict = self.board_to_dict(self.board)
            self.board.pop()
            if self.dicts_match(expected_dict, board_dict):
                return move
        return None

    def sync_board_from_dom(self, dom_dict, clock_turn):
        """Full board sync from DOM data context."""
        self.board.clear()
        for sq, sym in dom_dict.items():
            self.board.set_piece_at(chess.parse_square(sq), chess.Piece.from_symbol(sym))
        
        castling = ""
        if dom_dict.get('e1') == 'K':
            if dom_dict.get('h1') == 'R': castling += "K"
            if dom_dict.get('a1') == 'R': castling += "Q"
        if dom_dict.get('e8') == 'k':
            if dom_dict.get('h8') == 'r': castling += "k"
            if dom_dict.get('a8') == 'r': castling += "q"
        if not castling: castling = "-"
        
        # Determine turn
        if clock_turn is True:
            turn = 'w' if self.color == 'w' else 'b'
        elif clock_turn is False:
            turn = 'b' if self.color == 'w' else 'w'
        else:
            turn = 'w' if self.color == 'w' else 'b'
        
        fen_parts = self.board.fen().split(" ")
        fen_parts[1] = turn
        fen_parts[2] = castling
        fen_parts[3] = "-"
        fen_parts[4] = "0"
        fen_parts[5] = "1"
        self.board.set_fen(" ".join(fen_parts))

    def make_move_on_screen(self, page, move_str):
        from_sq = move_str[:2]
        to_sq = move_str[2:4]
        promotion = move_str[4:] if len(move_str) == 5 else ""
        
        file_map = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7}
        from_f, from_r = file_map[from_sq[0]], int(from_sq[1]) - 1
        to_f, to_r = file_map[to_sq[0]], int(to_sq[1]) - 1
        
        try:
            board_elem = page.locator("wc-chess-board")
            rect = board_elem.evaluate("(elem) => { let r = elem.getBoundingClientRect(); return {w: r.width, h: r.height, x: r.x, y: r.y}; }")
            
            if rect['w'] == 0: return False

            sq_w, sq_h = rect['w'] / 8, rect['h'] / 8
            def get_center_offsets(f, r):
                x_idx, y_idx = (f, 7-r) if self.color == "w" else (7-f, r)
                return {"x": (x_idx * sq_w) + (sq_w / 2), "y": (y_idx * sq_h) + (sq_h / 2)}

            from_pos, to_pos = get_center_offsets(from_f, from_r), get_center_offsets(to_f, to_r)

            board_elem.click(position=from_pos, force=True)
            time.sleep(0.1)
            board_elem.click(position=to_pos, force=True)
            
            if promotion:
                time.sleep(0.3)
                try: page.locator(".promotion-piece.wq, .promotion-piece.bq").first.click(force=True, timeout=500)
                except: pass
            return True
        except:
            return False

    def loop(self, page):
        self.log("Bot loop started! Fast detection active (v2).")
        # Reduced wait time since batch reading is very efficient
        turn_wait_time = 0.2 
        
        while not self.stop_event.is_set():
            try:
                state = self.get_full_state(page)
                if not state:
                    time.sleep(0.5)
                    continue

                if state['isGameOver']:
                    self.log("Game over detected!")
                    self.stop_event.set()
                    break
                    
                if not self.color:
                    if "flipped" in state['boardClass']:
                        self.color = "b"
                        self.log("Color Detected: BLACK")
                    else:
                        self.color = "w"
                        self.log("Color Detected: WHITE")

                dom_dict = self.parse_pieces_to_dict(state['pieces'])
                curr_dict = self.board_to_dict(self.board)
                
                # Determine clock turn from batched class data
                is_clock_ticking = False
                cl = state['bottomClockClass'].lower()
                if "clock-player-turn" in cl or "clock-active" in cl:
                    is_clock_ticking = True
                
                clock_turn_state = None # True: ours, False: theirs
                if is_clock_ticking:
                    clock_turn_state = True
                else:
                    tcl = state['topClockClass'].lower()
                    if "clock-player-turn" in tcl or "clock-active" in tcl:
                        clock_turn_state = False

                # STEP 1: Sync DOM changes
                if not self.dicts_match(curr_dict, dom_dict):
                    # Quick settle check
                    time.sleep(0.15)
                    state = self.get_full_state(page)
                    if not state: continue
                    dom_dict = self.parse_pieces_to_dict(state['pieces'])
                    
                    if not self.dicts_match(curr_dict, dom_dict):
                        move1 = self.find_move_played(dom_dict)
                        if move1:
                            self.log(f"Detected move: {move1}")
                            self.board.push(move1)
                            self.consecutive_sync_count = 0
                        else:
                            self.consecutive_sync_count += 1
                            if self.consecutive_sync_count > 6:
                                self.log("Too many sync failures. Resetting board.")
                                self.board.reset()
                                self.consecutive_sync_count = 0
                                continue
                            
                            self.log("Syncing board state...")
                            self.sync_board_from_dom(dom_dict, clock_turn_state)
                            self.consecutive_sync_count = 0

                # STEP 2: Logic and Watchdog
                is_our_turn_internal = (self.board.turn == chess.WHITE and self.color == "w") or \
                                       (self.board.turn == chess.BLACK and self.color == "b")

                # Force turn if clock says so
                if clock_turn_state is True and not is_our_turn_internal:
                    self.board.turn = chess.WHITE if self.color == "w" else chess.BLACK
                    is_our_turn_internal = True

                # STEP 3: Play
                if is_our_turn_internal and not self.stop_event.is_set():
                    # Throttle moves
                    if time.time() - self.last_move_time < 1.2:
                        time.sleep(0.1)
                        continue
                    
                    fen = self.board.fen()
                    if self.stockfish.is_fen_valid(fen): 
                        self.stockfish.set_fen_position(fen)
                        best_move = self.stockfish.get_best_move_time(800)
                        
                        if best_move:
                            if best_move == self.last_attempted_move:
                                self.same_move_counter += 1
                                if self.same_move_counter >= 3:
                                    self.log("Click watchdog: Forcing window focus.")
                                    try: page.bring_to_front() 
                                    except: pass
                            else:
                                self.last_attempted_move = best_move
                                self.same_move_counter = 0

                            self.log(f"[Stockfish] Best move: {best_move}")
                            if self.make_move_on_screen(page, best_move):
                                try:
                                    self.board.push(chess.Move.from_uci(best_move))
                                    self.last_move_time = time.time()
                                    # Verify move shortly after
                                    time.sleep(0.4)
                                    v_state = self.get_full_state(page)
                                    if v_state:
                                        v_dict = self.parse_pieces_to_dict(v_state['pieces'])
                                        if not self.dicts_match(self.board_to_dict(self.board), v_dict):
                                            self.log("Move failed to register on screen. Undoing.")
                                            try: self.board.pop()
                                            except: pass
                                        else:
                                            self.log("Move verified ✓")
                                except:
                                    pass
                
            except Exception as e:
                try:
                    if page.is_closed():
                        self.log("Browser closed.")
                        break
                except:
                    break
                
            time.sleep(turn_wait_time)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chess Bot Manager")
        self.geometry("450x480")
        self.resizable(False, False)
        self.lbl_title = ttk.Label(self, text="⚡ Automated Chess Bot ⚡", font=("Helvetica", 14, "bold")).pack(pady=10)
        self.lbl_info = ttk.Label(self, text="1. Start Chrome in Debug Mode.\n2. Open chess.com and start a game.\n3. Connect & Start the bot.", justify="center").pack(pady=5)
        self.btn_chrome = ttk.Button(self, text="1. Launch Chrome (Debug Mode)", command=self.open_chrome).pack(pady=5, ipadx=10, ipady=5)
        self.btn_start = ttk.Button(self, text="2. Connect & Start Bot", command=self.start_bot)
        self.btn_start.pack(pady=5, ipadx=10, ipady=5)
        self.btn_stop = ttk.Button(self, text="Stop Bot", command=self.stop_bot, state=tk.DISABLED)
        self.btn_stop.pack(pady=5)
        self.log_text = tk.Text(self, state=tk.DISABLED, height=15, width=55, bg="#1e1e1e", fg="white", font=("Consolas", 9))
        self.log_text.pack(pady=10)
        self.bot, self.bot_thread = None, None

    def log(self, msj):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msj + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def open_chrome(self):
        self.log("Launching Chrome...")
        try:
            user_data_dir = os.path.join(os.getcwd(), "chess_profile")
            command = f'"{r"C:\Program Files\Google\Chrome\Application\chrome.exe"}" --remote-debugging-port=9222 --user-data-dir="{user_data_dir}" "https://www.chess.com/"'
            subprocess.Popen(command, shell=True)
            self.log("✓ Chrome launched.")
        except:
            self.log("Failed to launch.")

    def start_bot(self):
        if self.bot: self.bot.stop_event.set()
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=2)
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.log("Connecting...")
        self.bot = ChessBot(log_cb=self.log)
        self.bot_thread = threading.Thread(target=self.run_bot_logic, daemon=True)
        self.bot_thread.start()

    def run_bot_logic(self):
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                chess_page = None
                for context in browser.contexts:
                    for page in context.pages:
                        if "chess.com" in page.url:
                            chess_page = page
                            break
                    if chess_page: break
                if not chess_page:
                    self.log("No chess.com tab found.")
                    return
                self.log("✓ Connected.")
                chess_page.wait_for_selector("wc-chess-board", timeout=10000)
                self.bot.loop(chess_page)
        except Exception as e:
            self.log(f"Error: {str(e)[:50]}")
        finally:
            self.stop_bot()
            self.log("Disconnected.")
            self.reset_ui()

    def stop_bot(self):
        if self.bot: self.bot.stop_event.set()
        self.reset_ui()
            
    def reset_ui(self):
        try:
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
        except: pass

if __name__ == "__main__":
    app = App()
    app.mainloop()
