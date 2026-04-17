# ⚡ Automated Chess Bot

### ⚠️ Disclaimer
> Please use this program strictly for educational purposes and only in "Player vs. Computer (PVE)" training modes on the site. Using this bot against real human players violates Fair-Play rules and platform Terms of Service, which may lead to the permanent suspension of your account.

### What is it?
This project is an autonomous robot that tracks the chess matches you play on **Chess.com** using native DOM reading. Powered by **Stockfish 16.1**—one of the world's strongest open-source chess engines—it automatically calculates and executes the best moves on your behalf. Thanks to its GUI, it can be seamlessly controlled and managed.

### Features
* **Fully Autonomous Execution:** Supported by Playwright's background interactions, it doesn't seize your physical mouse; it sends invisible pointer events. It can continue playing efficiently even if the browser tab remains in the background (as long as it isn't fully minimized).
* **Smart Sync & Watchdog Recovery:** Even if you start the bot in the middle of an on-going game or experience slight network drops/animations bugs, the bot scans the entire board layout in split-seconds and resumes flawlessly from where it left off, courtesy of its Auto-Recovery (Watchdog) mechanism.
* **0 Configuration, 1-Click Setup:** As soon as you launch it, the launcher checks for missing Python libraries and fetches the latest Stockfish engine from its official repository, compiling the local environment entirely on its own.

### Installation Steps
1. Download this repository to your computer (by clicking `Download ZIP` or using `git clone`).
2. Double-click the **`Run_Bot.bat`** file located inside the folder.
3. No manual installations or complex `pip` commands are required on your end. The bot will quietly fetch the necessary dependencies and the chess engine in the background. Once everything is done, an `IT IS READY` prompt will appear and the bot's interface will launch automatically.

### Usage Guide
Due to browser security constraints, the bot cannot connect to an ordinary window. It must attach to a browser launched with a special debugging port.
1. Execute `Run_Bot.bat` to launch the bot manager.
2. In the interface, click the **"1. Launch Chrome (Debug Mode)"** button. (This launches an internal Chrome instance bound to the `--remote-debugging-port=9222` argument while keeping your login sessions safe inside the newly created local `chess_profile` folder).
3. In the new Chrome window that opens, log in to Chess.com for the first time and start a "Play vs Computer" game to test.
4. Go back to the Bot UI and click **"2. Connect & Start Bot"**. The bot will immediately capture the current pieces and your turn, then consecutively play the most accurate engine moves whenever it is your right to move.

Enjoy your training!
