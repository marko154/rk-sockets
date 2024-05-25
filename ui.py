import curses
from enum import Enum
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chatClient import Client


class Pane(Enum):
    CHAT_ROOMS = 1
    CURRENT_CHAT_ROOM = 2


screen_height = 0
screen_width = 0

active_pane = Pane.CHAT_ROOMS

ROOMS_WIDTH = 40


class ChatUI:
    client: "Client"
    active_pane: Pane
    stdscr: curses.window
    active_room_idx: int
    lock: Lock

    def __init__(self, client: "Client"):
        self.active_pane = Pane.CHAT_ROOMS
        self.current_input = ""
        self.client = client
        self.active_room_idx = 0
        self.lock = Lock()

    def start(self):
        curses.wrapper(self.draw)

    def draw(self, stdscr: curses.window):
        self.stdscr = stdscr
        k = 0

        # Clear and refresh the screen for a blank canvas
        stdscr.clear()
        stdscr.refresh()
        curses.curs_set(0)

        # Start colors in curses
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

        self.init_user()

        # Loop where k is the last character pressed
        while k != ord("q"):
            # Initialization
            self.redraw()
            # Wait for next input
            k = stdscr.getch()
            self.handle_input(k)

    def init_user(self) -> str:
        name = ""
        with self.lock:
            key = 0
            while True:
                self.stdscr.clear()
                self.stdscr.refresh()
                self.draw_init(name)
                key = self.stdscr.getch()
                name += chr(key)
                if key in (curses.KEY_ENTER, 10, 13):
                    break
                elif key in (127, curses.KEY_BACKSPACE):
                    name = name[:-2]
        self.client.init_user(name.strip())

    def draw_init(self, name):
        h, w = self.screen_dims()
        midh = h // 2
        midw = w // 2
        prompt = "Enter your username:"
        self.stdscr.addstr(
            midh - 1, midw - len(prompt) // 2, prompt, curses.color_pair(1)
        )
        self.stdscr.addstr(
            midh, midw - len(name) // 2, name, curses.color_pair(1) | curses.A_BOLD
        )

    def redraw(self):
        with self.lock:
            self.stdscr.clear()
            height, width = self.screen_dims()
            self.draw_status_bar()

            # Refresh the screen
            self.stdscr.refresh()

            chatrooms_pad = curses.newpad(height - 1, ROOMS_WIDTH)
            self.draw_chatrooms(chatrooms_pad)
            chatrooms_pad.refresh(0, 0, 0, 0, height - 1, ROOMS_WIDTH)

            current_room_pad = curses.newpad(height - 1, width - ROOMS_WIDTH)
            self.draw_current_chatroom(current_room_pad)
            current_room_pad.refresh(0, 0, 0, ROOMS_WIDTH, height - 1, width)

    def draw_status_bar(self):
        height, width = self.stdscr.getmaxyx()

        statusbarstr = "Press 'q' to exit | STATUS BAR"
        # Render status bar
        self.stdscr.attron(curses.color_pair(3))
        self.stdscr.addstr(height - 1, 0, statusbarstr)
        self.stdscr.addstr(
            height - 1, len(statusbarstr), " " * (width - len(statusbarstr) - 1)
        )

    def handle_user_disconnect(self, user: str):
        if self.curr_room() == user:
            self.active_room_idx = 0

    def curr_room(self):
        return list(self.client.rooms.keys())[self.active_room_idx]

    def draw_current_chatroom(self, pad: curses.window):
        color = curses.color_pair(1)
        if self.active_pane == Pane.CURRENT_CHAT_ROOM:
            pad.attron(curses.A_BOLD)
            color = curses.color_pair(2)
        pad.attrset(color)
        pad.border()

        pad.addstr(1, 2, f"CHATROOM: {self.curr_room()}", color | curses.A_BOLD)
        messages = self.client.rooms[self.curr_room()]
        screen_height, _ = self.screen_dims()

        for i, msg in enumerate(messages[-(screen_height - 5) :]):
            pad.addstr(3 + i, 2, f"{msg.username}: {msg.content}")

        pad.addstr(screen_height - 3, 2, f"> {self.current_input}", color)

    def draw_chatrooms(self, pad: curses.window):
        color = curses.color_pair(1)
        if self.active_pane == Pane.CHAT_ROOMS:
            color = curses.color_pair(2)
        pad.attrset(color)
        pad.border()

        pad.addstr(1, 2, "CHATROOMS", color | curses.A_BOLD)
        for i, room in enumerate(self.client.rooms):
            attrs = color
            if i == self.active_room_idx:
                attrs |= curses.A_BOLD
            pad.addstr(3 + i, 2, room, attrs)
        pad.addstr(
            3 + self.active_room_idx, ROOMS_WIDTH - 3, "<", color | curses.A_BOLD
        )
        pad.scrollok(True)

    def handle_input(self, key):
        if key in (curses.KEY_RIGHT, curses.KEY_LEFT):
            self.active_pane = (
                Pane.CHAT_ROOMS
                if self.active_pane == Pane.CURRENT_CHAT_ROOM
                else Pane.CURRENT_CHAT_ROOM
            )
        if self.active_pane == Pane.CHAT_ROOMS:
            n_rooms = len(self.client.rooms)
            if key == curses.KEY_UP:
                self.active_room_idx = (self.active_room_idx - 1) % n_rooms
            elif key == curses.KEY_DOWN:
                self.active_room_idx = (self.active_room_idx + 1) % n_rooms
            if key in (curses.KEY_ENTER, 10, 13):
                self.active_pane = Pane.CURRENT_CHAT_ROOM
        else:
            if key in (127, curses.KEY_BACKSPACE):
                if self.current_input:
                    self.current_input = self.current_input[:-2]
            elif key in (curses.KEY_ENTER, 10, 13):
                if self.current_input:
                    self.client.send_message(self.current_input, self.curr_room())
                    self.current_input = ""
            else:
                if key not in (curses.KEY_RIGHT, curses.KEY_LEFT):
                    self.current_input += chr(key)

    def screen_dims(self):
        return self.stdscr.getmaxyx()
