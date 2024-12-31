import curses
import logging
from typing import List, Tuple, Union, cast
import os
from sys import maxsize
from pathlib import Path

from ccolors import * # pyright: ignore[reportWildcardImportFromLibrary]



# Configure logging
logging.basicConfig(filename='debug.log', level=logging.DEBUG, filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


# Configure curses
stdscr = curses.initscr()
curses.start_color()
curses.use_default_colors()
init_16_colors()
BOX_COLOR       = WHITE
MESSAGE_COLOR   = BRIGHT_YELLOW
HINT_COLOR      = DIM_WHITE

# UI dimensions
SCREEN_HEIGHT, SCREEN_WIDTH = stdscr.getmaxyx()
COMMAND_WINDOW_HEIGHT   = 3
Y_PAD                   = COMMAND_WINDOW_HEIGHT - 2
X_PAD                   = 2

class CommandWindow:
    HELP, INPUT, ADD, DELETE, EDIT, SELECT  =   0,       1,         2,         3,           4,           5,
    HINT_STRINGS                            = ["Help:", "Input:", "Adding:", "Deleting:", "Changing:", "Selecting:"]

    INPUT_POS = 0

    APP_DATA_DIR = f"{os.path.expanduser('~')}/.local/share/projectarium"
    HISTORY_FILE = f"{os.path.expanduser('~')}/.local/share/projectarium/history"


    def __init__(self):
        self.h = COMMAND_WINDOW_HEIGHT
        self.w = SCREEN_WIDTH
        self.y = SCREEN_HEIGHT - COMMAND_WINDOW_HEIGHT
        self.x = 0
        self.win = curses.newwin(self.h, self.w, self.y, self.x)
        self.state = self.HELP

        self.history = self._read_history_file()

        curses.curs_set(0)
        curses.noecho()
        curses.set_escdelay(1)
        stdscr.keypad(True)


    def _draw_box(self, message="", commands: Union[List[str], List[Tuple[str, str]]]=[], default: Union[int, str]="") -> int:
        self.win.erase()
        self.win.attron(BOX_COLOR)
        self.win.box()
        self.win.attroff(BOX_COLOR)
        self.win.addstr(0, 1, self.HINT_STRINGS[self.state], HINT_COLOR)

        if message:
            message = message.strip()
            mlen = max(len(message) + 3 + 4, len(self.HINT_STRINGS[self.state]))
            self.win.addstr(Y_PAD, (1 * X_PAD), f"  {message}    ", BRIGHT_YELLOW | BOLD)
            self.win.addch(0, mlen, '┬', WHITE)
            for bar_index in range(Y_PAD, COMMAND_WINDOW_HEIGHT - 1):
                self.win.addch(bar_index, mlen, '│', WHITE)
            self.win.addch(COMMAND_WINDOW_HEIGHT - 1, mlen, '┴', WHITE)
        else:
            mlen = (2 * X_PAD) # off border then off edge

        if default:
            default_string = str(default).strip()
            self.win.addstr(0, mlen + 1, "Default:")
            dlen = max(len("Default: "), len(default_string) + 3 + 4 + 2)
            self.win.addch(0, mlen + dlen, '┬', WHITE)
            for bar_index in range(Y_PAD, COMMAND_WINDOW_HEIGHT - 1):
                self.win.addch(bar_index, mlen + dlen, '│', WHITE)
            self.win.addch(2, mlen + dlen, '┴', WHITE)
            if self.state == self.INPUT:
                default_prompt = f"   \"{default_string}\"  "
            else:
                default_prompt = f"    {default_string}   "
            self.win.addstr(1, mlen + 1, default_prompt, BRIGHT_YELLOW | BOLD)
            mlen += max(len("Default: "), len(default_string) + 3 + 4 + 2)

        if commands:
            shortcut_command_map = self.create_shortcuts(commands)
            if message: mlen += 5
            for mapped_shortcut in shortcut_command_map:
                self.win.addstr(Y_PAD, mlen, f"{mapped_shortcut[0]}: ", CYAN)
                self.win.addstr(Y_PAD, (mlen := mlen + 3), f"{mapped_shortcut[1]}", WHITE)
                mlen += len(mapped_shortcut[1]) + (2 * X_PAD)

        self.win.refresh()
        return mlen


    def create_shortcuts(self, commands: Union[List[str], List[Tuple[str, str]]]) -> List[Tuple[str, str]]:
        if commands and isinstance(commands[0], tuple):
            return cast(List[Tuple[str, str]], commands) # users can define their own shortcut tuples

        used_shortcuts, commands_map = [], []
        for command in commands:
            shortcut = next(((instruction, command) for instruction in command if instruction not in used_shortcuts), (" ⚠ ", "INVALID"))
            commands_map.append(shortcut)
            used_shortcuts.append(shortcut[0])
        return commands_map


    def help(self, commands: Union[List[str], List[Tuple[str, str]]]) -> None:
        self.state = self.HELP
        self._draw_box(message="", commands=commands)


    def make_selection(self, message, choices, default="", required=False):
        self.state = self.SELECT
        self._draw_box(message=message, commands=[(str(i+1), str(choice)) for i, choice in enumerate(choices)], default=default)

        selected_number = -1
        while selected_number not in range(1, len(choices)+1):
            try:
                key = self.win.getch()
                if (chr(key) == 'q' or key == 27) and not required:
                    return None
                if key in(curses.KEY_ENTER, 10, 13) and int(default) >= 0:
                    return choices[int(default)-1]
                selected_number = int(chr(key))
            except ValueError:
                selected_number = -1
        return choices[selected_number-1]


    def _draw_text_buffer(self, text_buffer, limit):
        if isinstance(text_buffer, list):
            text_buffer = "".join(text_buffer)
        # log.info(f"Drawing \"{text_buffer}\"")

        self.win.addstr(Y_PAD, self.INPUT_POS, '_' * limit)
        self.win.addstr(Y_PAD, self.INPUT_POS, text_buffer)
        self.win.move(Y_PAD, self.INPUT_POS + len(text_buffer))
        self.win.refresh()
        return len(text_buffer)
    

    def _read_history_file(self,):
        history = []
        os.makedirs(self.APP_DATA_DIR, exist_ok=True)

        if os.path.exists(self.HISTORY_FILE):
            with open(self.HISTORY_FILE, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    history.append(line.strip())
        return history

    def _add_history_line(self, line):
        with open(self.HISTORY_FILE, 'a') as file:
            file.write(f"{line}\n")


    def get_input(self, message, default="", limit=maxsize):
        self.state = self.INPUT
        mlen = self._draw_box(message, default=default)
        self.INPUT_POS = (1 * X_PAD) + mlen + X_PAD
        limit = min(SCREEN_WIDTH - self.INPUT_POS - (2 * X_PAD), limit)
        # log.info(limit)

        curses.noecho()
        curses.curs_set(1)
        self.win.keypad(True)

        text_buffer = []    # text the user has typed 
        i = 0               # index in text_buffer, for insertion
        end = 0             # end index of the current line (len(text_buffer)?)
        hist_ptr = len(self.history)    # where are we in history?
        temp_text_buffer = []           # temp space for saved but not visible text buffer

        self._draw_text_buffer(text_buffer, limit)

################################################################################
        while (key := self.win.getch()):
            log.info(key)
            if key in (10, 13): # enter
                self._add_history_line("".join(text_buffer))
                break
            elif key == 27: # escape
                text_buffer.clear()
                break
            elif key == curses.KEY_BACKSPACE:
                if i > 0:
                    i -= 1
                    end -= 1
                    if hist_ptr < len(self.history): # we are in history
                        text_buffer = list(self.history[hist_ptr])
                    log.info(f"right before backspace: i : {i}, end : {end}, limit : {limit}, text_buffer : {text_buffer}, temp_text_buffer : {temp_text_buffer}")
                    text_buffer.pop(i)
                    # asset text buffer as new temp
                    self._draw_text_buffer(text_buffer, limit)
                continue
            elif key == curses.KEY_DC:
                if i < end:
                    # i -= 1
                    end -= 1
                    text_buffer.pop(i)
                    self._draw_text_buffer(text_buffer, limit)
                continue
################################################################################
            elif key == curses.KEY_UP:
                if hist_ptr > 0:
                    if hist_ptr == len(self.history):
                        temp_text_buffer = text_buffer
                    hist_ptr -= 1
                    if hist_ptr < len(self.history) and len(text_buffer) < limit:
                        text_buffer = list(self.history[hist_ptr])
                    else:
                        text_buffer = list(temp_text_buffer)
                    log.info(f"new pos?? : {self.INPUT_POS + len(text_buffer)}")
                    i = self._draw_text_buffer(text_buffer, limit)
                continue
            elif key == curses.KEY_DOWN:
                if hist_ptr < len(self.history):
                    hist_ptr += 1
                    if hist_ptr < len(self.history) and len(text_buffer) < limit:
                        text_buffer = self.history[hist_ptr]
                    elif hist_ptr == len(self.history):
                        text_buffer = temp_text_buffer
                    i = self._draw_text_buffer(text_buffer, limit)
                continue
            elif key == curses.KEY_LEFT:
                if i > 0:
                    i -= 1
                continue
            elif key == curses.KEY_RIGHT:
                # if cpos < end:
                if i < limit and i < end:
                    i += 1
                continue
            elif key == curses.KEY_HOME:
                i = 0
                continue
            elif key == curses.KEY_END:
                i = end
                continue

            log.info(f"BEFORE: i : {i}, end : {end}, limit : {limit}")

            if hist_ptr <= len(self.history):
                temp_text_buffer = list(text_buffer)
                hist_ptr = len(self.history)
                end = len(temp_text_buffer)
                i = end


            text_buffer = list(text_buffer)
            if i < limit:
                if i == end: # we are appending to the end of the string
                    text_buffer.append(chr(key))
                    end += 1
                    i += 1
                elif i < end: # we are in the middle of a string
                    text_buffer.pop(i)
                    text_buffer.insert(i, chr(key))
                    i += 1
                elif i > end: # should not happen
                    end = i
            if end > limit: # should not happen
                end -= 1

            log.info(f"AFTER: i : {i}, end : {end}, limit : {limit}")
            self._draw_text_buffer(text_buffer, limit)



        finput = "".join(text_buffer)

        curses.curs_set(0)
        curses.noecho()
        
        if finput:
            self.history.append(finput)
            return finput
        self.history.append(default)
        return default
