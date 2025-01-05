import curses
import logging
from typing import List, Tuple, Union, cast
import os
from sys import maxsize
from pathlib import Path
from copy import deepcopy

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
    HELP, INPUT, ADD, DELETE, EDIT, SELECT  =   0,       1,        2,         3,           4,           5,
    HINT_STRINGS                            = ["Help:", "Input:", "Adding:", "Deleting:", "Changing:", "Selecting:"]

    def __init__(self):
        self.h = COMMAND_WINDOW_HEIGHT
        self.w = SCREEN_WIDTH
        self.y = SCREEN_HEIGHT - COMMAND_WINDOW_HEIGHT
        self.x = 0
        self.win = curses.newwin(self.h, self.w, self.y, self.x)
        self.state = self.HELP

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

    def get_input(self, message, default="", bound=maxsize, input_type="text"):
            self.state = self.INPUT
            mlen = self._draw_box(message, default=default)

            input_pos = (1 * X_PAD) + mlen + X_PAD
            bound = min(SCREEN_WIDTH - input_pos - (2 * X_PAD), bound)

            curses.noecho()
            curses.curs_set(1)
            self.win.keypad(True)

            if input_type == "text":
                ti = self.TextInput(self, default, input_pos, bound)
                finput = ti.get_input()
            else:
                pi = self.PathInput(self, default, input_pos, bound)
                finput = pi.get_input()

            curses.curs_set(0)
            curses.noecho()

            if bound <= 0:
                return ""

            if finput:
                return finput
            return default




    class Input:

        DATA_DIR = f"{os.path.expanduser('~')}/.local/share/projectarium"
        # HISTORY_FILE = f"{DATA_DIR}/history"


        def __init__(self, parent, default, input_pos, bound, history_file_name):
            self.parent = parent
            self.win = parent.win

            self.history_file_name = f"{self.DATA_DIR}/{history_file_name}"
            self.history = self._read_history_file()
            self.history_matches: List[List[str]] = []
            self.extended_matches: List[List[str]] = []
            self.matches: List[str] = []
            self.match_index = -1
            self.autocomplete_buffer = ""

            self.default = default
            self.input_pos = input_pos
            self.bound = bound

            self.text_buffer: List[str] = []        # text the user has typed 
            self.cursor_pos = 0                               # index in text_buffer, for insertion
            self.hist_ptr = len(self.history)       # where are we in history?
            self.saved_text_buffer: List[str] = []  # temp space for saved but not visible text buffer

            self._draw_text_buffer()

            curses.noecho()
            curses.curs_set(1)
            self.win.keypad(True)

        def _get_active_buffer_string(self):
            return "".join(self.history[self.hist_ptr]) if self.hist_ptr < len(self.history) else "".join(self.text_buffer)


        def _draw_text_buffer(self):
            self.win.addstr(Y_PAD, self.input_pos, '_' * self.bound)
            self.win.addstr(Y_PAD, self.input_pos, self._get_active_buffer_string())
            if self.autocomplete_buffer:
                self.win.addstr(Y_PAD, self.input_pos + self.cursor_pos, self.autocomplete_buffer[self.cursor_pos:], DARK_GREY)
            self.win.move(Y_PAD, self.input_pos + self.cursor_pos)
            self.win.refresh()
            return len(self.text_buffer)
        

        def _read_history_file(self):
            history = []
            os.makedirs(self.DATA_DIR, exist_ok=True)

            if os.path.exists(self.history_file_name):
                with open(self.history_file_name, 'r') as file:
                    lines = file.readlines()
                    for line in lines:
                        history.append(line.strip('\n'))
            return history

        def _add_history_line(self, line):
            with open(self.history_file_name, 'a') as file:
                file.write(f"{line}\n")

        def save(self):
            self._add_history_line("".join(self.text_buffer))

        def escape(self):
            self.text_buffer.clear()

        def backspace(self):
            self._pull_history_to_current()
            self.cursor_pos -= 1
            self.text_buffer.pop(self.cursor_pos)

        def delete(self):
            self._pull_history_to_current()
            self.text_buffer.pop(self.cursor_pos)
            if self.cursor_pos == len(self._get_active_buffer_string()) + 1:
                self.cursor_pos -= 1

        def up(self):
            if not self.saved_text_buffer: # existence means we have saved text
                self.saved_text_buffer = deepcopy(self.text_buffer)
            if self.hist_ptr > 0 and len(self.history[self.hist_ptr-1]) <= self.bound:
                self.hist_ptr -= 1
                self.cursor_pos = len(self._get_active_buffer_string())
            else:
                if self.hist_ptr > 0:
                    self.hist_ptr -= 1
                    self.up()
                else:
                    self.hist_ptr -= 1

        def down(self):
            if self.hist_ptr < len(self.history) - 1 and len(self.history[self.hist_ptr+1]) <= self.bound:
                self.hist_ptr += 1
            else:
                self.hist_ptr += 1
                if self.hist_ptr < len(self.history) - 1:
                    self.down()
            if self.saved_text_buffer and self.hist_ptr == len(self.history):
                self.text_buffer = deepcopy(self.saved_text_buffer)
                self.saved_text_buffer.clear()
            self.cursor_pos = len(self._get_active_buffer_string())

        def left(self):
            self.cursor_pos -= 1

        def right(self):
            if self.match_index > -1:
                self._accept_history_match()
            else:
                self.cursor_pos += 1

        def _load_history_matches(self):
            self.history_matches = [list(hist_entry) for hist_entry in self.history if hist_entry.startswith(self._get_active_buffer_string()) and len(hist_entry) <= self.bound]
            self.history_matches = self.history_matches[::-1] # most recent first

        def _next_history_match(self):
            if self.matches:
                self.match_index = (self.match_index + 1) % len(self.matches)
                self.autocomplete_buffer = self.matches[self.match_index]

        def _prev_history_match(self):
            if self.history_matches:
                self.match_index = (self.match_index - 1) % len(self.history_matches)
                self._pull_history_to_current()
                self.matches = self.history_matches[self.match_index][len(self.text_buffer):]

        def _accept_history_match(self):
            self.text_buffer.extend(list(self.autocomplete_buffer[self.cursor_pos:]))
            self.cursor_pos = len(self.text_buffer)

        def _clear_history_matches(self):
            self.match_index = -1
            self.matches.clear()
            self.history_matches.clear()

        def _clear_matches(self):
            self.autocomplete_buffer = ""
            self.matches.clear()
            self.match_index = -1

        def is_partial_match(self, partial_string):
            log.info(f"matches : {self.matches}")
            for match in self.matches:
                if match.startswith(partial_string):
                    return True
            return False

        def _filter_autocomplete(self):
            possible_matches = []
            if self.history_matches:
                possible_matches.extend(self.history_matches)
            if self.extended_matches:
                possible_matches.extend(self.extended_matches)
            for possible_match in possible_matches:
                possible_match_string = "".join(possible_match)
                if possible_match_string.startswith(self._get_active_buffer_string()):
                    self.matches.append(possible_match_string)


        def extend_autocomplete_pool(self, additions: List[str]):
            # if self.history_matches:
            for addition in additions[::-1]:
                # log.info(addition)
                if addition.startswith(self._get_active_buffer_string()):
                    self.extended_matches.insert(0, list(addition))
                    # self.history_matches.insert(0, list(addition))

        def delete_from_autocomplete_pool(self, addition):
            if list(addition) in self.extended_matches:
                self.extended_matches.remove(list(addition))

        def clear_extended_autocomplete_pool(self):
            self.extended_matches.clear()
            # if list(addition) in self.history_matches:
                # self.history_matches.remove(list(addition))

            
        def init_autocomplete(self):
            self._clear_history_matches()
            self._load_history_matches()

        def history_autocomplete(self, changed=False, direction=1):
            if self.history_matches:
                if changed:
                    self._clear_matches()
                    self._filter_autocomplete()
                # log.info(f"autocomplete buffer before : {self.autocomplete_buffer}")
                # log.info(f"match buffer : {self.matches}")
                self._next_history_match() if direction == 1 else self._prev_history_match()


        def _pull_history_to_current(self): # say "this is our new text buffer"
            if self.hist_ptr < len(self.history): # if we are in history
                self.saved_text_buffer.clear() # clear because we are now editting
                self.text_buffer = deepcopy(list(self.history[self.hist_ptr])) # text_buffer = current line in hist
                self.hist_ptr = len(self.history)


        def get_input(self):
            curses.noecho()
            curses.curs_set(1)
            self.win.keypad(True)

            self.init_autocomplete()

            while (key := self.win.getch()):
                log.info(key)
                if self.bound <= 0:
                    return ""

                if key in (10, 13): # enter
                    if self.hist_ptr != len(self.history) and self.saved_text_buffer: # we were not at a good location
                        self.hist_ptr = len(self.history)  # go to end of history (saved buffer)
                        self.cursor_pos = min(len(self.saved_text_buffer), self.bound)
                    else: # there was no saved buffer, so let's send selected buff string
                        self._pull_history_to_current() # load selected buff into sendable position
                        self.hist_ptr = len(self.history)  # go to end of history (saved buffer)
                        break
                elif key == 27: # escape
                    if self.matches:
                        self._clear_matches()
                    elif self.hist_ptr != len(self.history): # we were not at a good location
                        self.hist_ptr = len(self.history)  # hit end of history (saved buffer)
                        self.cursor_pos = 0
                    else:
                        return ""
                elif key == curses.KEY_BACKSPACE:
                    if self.cursor_pos > 0:
                        self.backspace()
                        self.history_autocomplete(changed=True)
                elif key == curses.KEY_DC:
                    if self.cursor_pos < len(self._get_active_buffer_string()):
                        self.delete()
                elif key == curses.KEY_UP:
                    if self.hist_ptr > 0:
                        self.up()
                elif key == curses.KEY_DOWN:
                    if self.hist_ptr < len(self.history):
                        self.down()
                elif key == curses.KEY_LEFT:
                    if self.cursor_pos > 0:
                        self.left()
                elif key == curses.KEY_RIGHT:
                    if (self.cursor_pos < self.bound and self.cursor_pos < len(self._get_active_buffer_string())) or self.matches:
                        self.right()
                elif key == curses.KEY_HOME:
                    self.cursor_pos = 0
                elif key == curses.KEY_END:
                    self.cursor_pos = min(len(self._get_active_buffer_string()), self.bound)
                elif key == 9: # tab
                    self.history_autocomplete(direction=1)
                elif key == curses.KEY_BTAB:
                    self.history_autocomplete(direction=-1)
                else: # regular character to print
                    self._pull_history_to_current()
                    if self.cursor_pos < self.bound:
                        self.text_buffer.insert(self.cursor_pos, chr(key))
                        self.cursor_pos += 1
                    self.history_autocomplete(changed=True)

                self._draw_text_buffer()

            finput = "".join(self.text_buffer)

            curses.curs_set(0)
            curses.noecho()
            
            if finput:
                self._add_history_line(finput)
                return finput
            self._add_history_line(self.default)
            return self.default

    class TextInput(Input):
        def __init__(self, parent, default, input_pos, bound):
            super().__init__(parent, default, input_pos, bound, "text_history")

    class PathInput(Input):
        def __init__(self, parent, default, input_pos, bound):
            super().__init__(parent, default, input_pos, bound, "path_history")

        def validate_path(self):
            if self._get_active_buffer_string():
                expanded = os.path.expanduser(self._get_active_buffer_string())
            else:
                return RED
            path_obj = Path(expanded)
            log.info(self.extended_matches)

            if path_obj.exists():
                self.clear_extended_autocomplete_pool()
                if path_obj.is_dir():
                    self.extend_autocomplete_pool([str(path_obj.absolute() / file.name)for file in path_obj.iterdir()])
                return GREEN
            elif self.is_partial_match(self._get_active_buffer_string()):
                log.info(self._get_active_buffer_string())
                # self.clear_extended_autocomplete_pool()
                self.extend_autocomplete_pool([str(path_obj.absolute() / file.name) for file in path_obj.parent.iterdir()])
                return BRIGHT_YELLOW
            else:
                return RED

        def _draw_text_buffer(self):
            self.win.addstr(Y_PAD, self.input_pos, '_' * self.bound)
            self.win.addstr(Y_PAD, self.input_pos, self._get_active_buffer_string(), self.validate_path())
            if self.autocomplete_buffer:
                self.win.addstr(Y_PAD, self.input_pos + self.cursor_pos, self.autocomplete_buffer[self.cursor_pos:], DARK_GREY)
            self.win.move(Y_PAD, self.input_pos + self.cursor_pos)
            self.win.refresh()
            return len(self.text_buffer)
