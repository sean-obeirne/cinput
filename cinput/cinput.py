import curses
import logging
from typing import List, Tuple, Union, cast

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

    def __init__(self):
        self.h = COMMAND_WINDOW_HEIGHT
        self.w = SCREEN_WIDTH
        self.y = SCREEN_HEIGHT - COMMAND_WINDOW_HEIGHT
        self.x = 0
        self.win = curses.newwin(self.h, self.w, self.y, self.x)
        self.state = self.HELP

    def init(self):
        stdscr.clear()

        curses.curs_set(0)
        curses.noecho()
        curses.set_escdelay(1)
        stdscr.keypad(True)

        stdscr.refresh()



    def draw_box(self, message="", commands: Union[List[str], List[Tuple[str, str]]]=[], default: Union[int, str]="") -> int:
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
        self.draw_box(message="", commands=commands)

    def make_selection(self, message, choices, default="", required=False):
        self.state = self.SELECT
        self.draw_box(message=message, commands=[(str(i+1), str(choice)) for i, choice in enumerate(choices)], default=default)

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


    def get_input(self, message, default="", placeholder_len=0):
        self.state = self.INPUT
        mlen = self.draw_box(message, default=default)

        curses.echo()
        curses.curs_set(1)

        input_pos = (1 * X_PAD) + mlen + 3
        input, i = [], -1
        self.win.keypad(True)
        while (key := self.win.getch(1, input_pos + i)):
            if key in (10, 13):
                break
            elif key == 27:
                input.clear()
                break
            elif key == curses.KEY_BACKSPACE:
                if len(input) > 0:
                    input.pop(i)
                    i -= 1
                self.win.addstr(1, input_pos + i, ('_' if placeholder_len > 0 else ' '))
                self.win.move(1, input_pos + i - 1)
                self.win.refresh()
                continue
            # elif key == curses.KEY_LEFT:
            #     i -= 1
            #     self.win.move(1, input_pos + i - 1)
            #     self.win.refresh()
            #     continue
            input.append(chr(key))
            i += 1

        finput = "".join(input)
            
        curses.curs_set(0)
        curses.noecho()


        return default if finput == "" else finput
        


def init():
    cw = CommandWindow()
        
    return cw
