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
        self.is_playing = False
        self.stop_event = threading.Event()
        
        # Watchdog variables
        self.last_attempted_move = None
        self.same_move_counter = 0
        
    def get_board_state_from_dom(self, page):
        piece_elements = page.locator(".piece").all()
        board_dict = {}
        piece_map = {
            'wp': 'P', 'wn': 'N', 'wb': 'B', 'wr': 'R', 'wq': 'Q', 'wk': 'K',
            'bp': 'p', 'bn': 'n', 'bb': 'b', 'br': 'r', 'bq': 'q', 'bk': 'k'
        }
        files = {1: 'a', 2: 'b', 3: 'c', 4: 'd', 5: 'e', 6: 'f', 7: 'g', 8: 'h'}
        
        for p in piece_elements:
            classes = p.get_attribute('class')
            if not classes: continue
            
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

    def make_move_on_screen(self, page, move_str):
        from_sq = move_str[:2]
        to_sq = move_str[2:4]
        promotion = move_str[4:] if len(move_str) == 5 else ""
        
        file_map = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7}
        
        from_f = file_map[from_sq[0]]
        from_r = int(from_sq[1]) - 1
        to_f = file_map[to_sq[0]]
        to_r = int(to_sq[1]) - 1
        
        self.log(f"Playing move: {move_str}")
        try:
            board_elem = page.locator("wc-chess-board")
            rect = board_elem.evaluate("(elem) => { let r = elem.getBoundingClientRect(); return {w: r.width, h: r.height}; }")
            
            if rect['w'] == 0:
                self.log("ERROR: Chrome is completely minimized. Cannot click.")
                return

            sq_w = rect['w'] / 8
            sq_h = rect['h'] / 8

            def get_center_offsets(f, r):
                if self.color == "w": 
                    x_idx = f
                    y_idx = 7 - r
                else: 
                    x_idx = 7 - f
                    y_idx = r
                return {"x": (x_idx * sq_w) + (sq_w / 2), "y": (y_idx * sq_h) + (sq_h / 2)}

            from_pos = get_center_offsets(from_f, from_r)
            to_pos = get_center_offsets(to_f, to_r)

            board_elem.click(position=from_pos, force=True)
            time.sleep(0.1)
            board_elem.click(position=to_pos, force=True)
            
            if promotion:
                time.sleep(0.2)
                try:
                    page.locator(".promotion-piece.wq, .promotion-piece.bq").first.click(force=True, timeout=500)
                except:
                    pass
                
            time.sleep(0.3)
        except Exception as e:
            self.log(f"Failed to play ({move_str}): {e}")

    def loop(self, page):
        self.log("Bot loop started! Listening for moves...")
        turn_wait_time = 0.5
        
        while not self.stop_event.is_set():
            try:
                board_elem = page.locator("wc-chess-board")
                if page.locator(".game-over-modal").is_visible(timeout=100):
                    self.log("Game over screen detected!")
                    self.stop_event.set()
                    break
                    
                if not self.color:
                    classes = board_elem.get_attribute("class", timeout=1000)
                    if classes:
                        if "flipped" in classes:
                            self.color = "b"
                            self.log("Color Detected: BLACK")
                        else:
                            self.color = "w"
                            self.log("Color Detected: WHITE")

                dom_dict = self.get_board_state_from_dom(page)
                curr_dict = self.board_to_dict(self.board)
                
                # 1. PROCESS OPPORTUNISTIC DOM CHANGES FIRST
                # Bu bölüm Watchdog'dan önce olmalıdır. Çünkü rakip hamle yaptıysa önce tahtada karşılığını işlemeliyiz.
                if not self.dicts_match(curr_dict, dom_dict):
                    time.sleep(0.15)
                    dom_dict = self.get_board_state_from_dom(page)
                    
                    if not self.dicts_match(curr_dict, dom_dict):
                        move = self.find_move_played(dom_dict)
                        if move:
                            self.log(f"Detected move: {move}")
                            self.board.push(move)
                            self.same_move_counter = 0 # Sıfırla
                        else:
                            self.log("Board desync detected! Syncing...")
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
                            
                            turn = 'w' if self.color == 'w' else 'b' 
                            fen_parts = self.board.fen().split(" ")
                            fen_parts[1] = turn # Resetlemede başlangıç sırası bizimkisi farz edilir
                            fen_parts[2] = castling
                            fen_parts[3] = "-"
                            self.board.set_fen(" ".join(fen_parts))
                            self.log("Sync Complete.")

                # 2. WATCHDOG: TURN STATE VERIFICATION
                is_our_turn_internally = (self.board.turn == chess.WHITE and self.color == "w") or \
                                         (self.board.turn == chess.BLACK and self.color == "b")

                is_clock_ticking = False
                try:
                    clock_elem = page.locator(".clock-bottom").first
                    if clock_elem.is_visible(timeout=100):
                        c_class = clock_elem.get_attribute("class") or ""
                        if "turn" in c_class.lower() or "active" in c_class.lower() or "playing" in c_class.lower():
                            is_clock_ticking = True
                except:
                    pass

                if is_clock_ticking and not is_our_turn_internally:
                    # Rakibin hamlesini işlediğimiz halde sıra bize geçmediyse iç yapıyı düzelt
                    self.log("Watchdog: Clock indicates it's our turn, but bot internal state is asleep. Forcing wake up!")
                    self.board.turn = chess.WHITE if self.color == "w" else chess.BLACK
                    is_our_turn_internally = True

                # 3. STOCKFISH PLAYING
                if is_our_turn_internally and not self.stop_event.is_set():
                    fen = self.board.fen()
                    if self.stockfish.is_fen_valid(fen): 
                        self.stockfish.set_fen_position(fen)
                        best_move = self.stockfish.get_best_move_time(800)
                        
                        if best_move:
                            if best_move == self.last_attempted_move:
                                self.same_move_counter += 1
                                if self.same_move_counter >= 3:
                                    self.log("Watchdog: Move failed 3 times! Forcing full window layer sync...")
                                    try: page.bring_to_front() 
                                    except: pass
                            else:
                                self.last_attempted_move = best_move
                                self.same_move_counter = 0

                            self.log(f"[Stockfish] Best move: {best_move}")
                            self.make_move_on_screen(page, best_move)
                            try:
                                self.board.push(chess.Move.from_uci(best_move))
                            except:
                                self.log("Warning: Internal move push failed.")
                        else:
                            self.log("Stockfish found no moves.")
                            
            except Exception as e:
                err_text = str(e)
                if "closed" in err_text.lower() or "disconnected" in err_text.lower():
                    self.log("Browser disconnected! Stopping...")
                    self.stop_event.set()
                    break
                
            time.sleep(turn_wait_time)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chess Bot Manager")
        self.geometry("450x450")
        self.resizable(False, False)
        
        self.lbl_title = ttk.Label(self, text="⚡ Automated Chess Bot ⚡", font=("Helvetica", 14, "bold"))
        self.lbl_title.pack(pady=10)
        
        self.lbl_info = ttk.Label(self, text="1. Start Chrome in Debug Mode.\n2. Open chess.com and start a game.\n3. Connect & Start the bot.", justify="center")
        self.lbl_info.pack(pady=5)
        
        self.btn_chrome = ttk.Button(self, text="1. Launch Chrome (Debug Mode)", command=self.open_chrome)
        self.btn_chrome.pack(pady=5, ipadx=10, ipady=5)
        
        self.btn_start = ttk.Button(self, text="2. Connect & Start Bot", command=self.start_bot)
        self.btn_start.pack(pady=5, ipadx=10, ipady=5)
        
        self.btn_stop = ttk.Button(self, text="Stop Bot", command=self.stop_bot, state=tk.DISABLED)
        self.btn_stop.pack(pady=5)
        
        self.log_text = tk.Text(self, state=tk.DISABLED, height=14, width=50, bg="#1e1e1e", fg="white", font=("Consolas", 9))
        self.log_text.pack(pady=10)
        
        self.bot = None
        self.bot_thread = None

    def log(self, msj):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msj + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def open_chrome(self):
        self.log("Launching Chrome...")
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        try:
            user_data_dir = os.path.join(os.getcwd(), "chess_profile")
            command = f'"{chrome_path}" --remote-debugging-port=9222 --user-data-dir="{user_data_dir}" "https://www.chess.com/"'
            subprocess.Popen(command, shell=True)
            self.log("✓ Chrome launched successfully.")
        except Exception as e:
            self.log(f"Failed to launch Chrome: {e}")

    def start_bot(self):
        if self.bot_thread and self.bot_thread.is_alive():
            return
            
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.log("------------------------")
        self.log("Connecting bot to browser...")
        
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
                    if chess_page:
                        break
                        
                if not chess_page:
                    self.log("ERROR: No active chess.com tab found!")
                    return
                
                self.log("✓ Connected to chess.com tab.")
                chess_page.wait_for_selector("wc-chess-board", timeout=10000)
                
                self.bot.loop(chess_page)
                
        except Exception as e:
            self.log(f"Connection Error: {str(e)[:50]}...")
            self.log("Ensure Chrome was started using the button.")
        finally:
            self.stop_bot()
            self.log("Bot disconnected cleanly.")
            self.reset_ui()

    def stop_bot(self):
        if self.bot:
            self.bot.stop_event.set()
        self.reset_ui()
            
    def reset_ui(self):
        try:
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
        except:
            pass

if __name__ == "__main__":
    app = App()
    app.mainloop()
