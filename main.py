import curses
import time
import psutil
import threading
from datetime import datetime

class TuiApp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.running = True
        self.mouse_x = 0
        self.mouse_y = 0
        self.widgets = []

        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_GREEN, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.mousemask(curses.ALL_MOUSE_EVENTS)

        self.height, self.width = self.stdscr.getmaxyx()

        self.init_widgets()
        self.update_thread = threading.Thread(target=self.update_widgets)
        self.update_thread.daemon = True
        self.update_thread.start()

    def init_widgets(self):
        self.widgets.append(ClockWidget(1, 1, 20, 3))

        self.widgets.append(CpuMonitorWidget(1, 5, 20, 5))

        self.widgets.append(MemoryWidget(23, 5, 20, 5))

        self.widgets.append(ButtonWidget(23, 1, 20, 3, "Exit", self.quit))

    def update_widgets(self):
        while self.running:
            for widget in self.widgets:
                widget.update()
            time.sleep(0.5)

    def draw(self):
        self.stdscr.clear()

        self.stdscr.border()

        for widget in self.widgets:
            widget.draw(self.stdscr)

        self.stdscr.addstr(self.mouse_y, self.mouse_x, "X", curses.A_REVERSE)

        status = f" Mouse: ({self.mouse_x},{self.mouse_y}) | Press q to quit "
        self.stdscr.addstr(self.height-1, 0, status, curses.color_pair(1))

        self.stdscr.refresh()

    def handle_mouse(self, event):
        _, mx, my, _, button = event
        self.mouse_x = mx
        self.mouse_y = my

        if button & curses.BUTTON1_CLICKED:
            for widget in self.widgets:
                if widget.is_inside(mx, my):
                    widget.on_click()

    def quit(self):
        self.running = False

    def run(self):
        while self.running:
            self.draw()

            try:
                self.stdscr.timeout(100)
                key = self.stdscr.getch()

                if key == ord('q'):
                    self.quit()
                elif key == curses.KEY_MOUSE:
                    try:
                        mouse_event = curses.getmouse()
                        self.handle_mouse(mouse_event)
                    except:
                        pass
                elif key == curses.KEY_RESIZE:
                    self.height, self.width = self.stdscr.getmaxyx()
            except KeyboardInterrupt:
                self.quit()


class Widget:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def is_inside(self, mx, my):
        return (self.x <= mx < self.x + self.width and
                self.y <= my < self.y + self.height)

    def draw(self, screen):
        for i in range(self.width):
            screen.addstr(self.y, self.x + i, "─")
            screen.addstr(self.y + self.height - 1, self.x + i, "─")

        for i in range(self.height):
            screen.addstr(self.y + i, self.x, "│")
            screen.addstr(self.y + i, self.x + self.width - 1, "│")

        screen.addstr(self.y, self.x, "┌")
        screen.addstr(self.y, self.x + self.width - 1, "┐")
        screen.addstr(self.y + self.height - 1, self.x, "└")
        screen.addstr(self.y + self.height - 1, self.x + self.width - 1, "┘")

    def update(self):
        pass

    def on_click(self):
        pass


class ClockWidget(Widget):
    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height)
        self.time = ""
        self.update()

    def update(self):
        self.time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def draw(self, screen):
        super().draw(screen)
        screen.addstr(self.y, self.x + 2, " Clock ")
        screen.addstr(self.y + 1, self.x + 2, self.time)


class CpuMonitorWidget(Widget):
    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height)
        self.cpu_percent = 0

    def update(self):
        self.cpu_percent = psutil.cpu_percent(interval=0.1)

    def draw(self, screen):
        super().draw(screen)
        screen.addstr(self.y, self.x + 2, " CPU ")

        bar_width = self.width - 6
        filled = int(bar_width * self.cpu_percent / 100)

        bar = "█" * filled + "░" * (bar_width - filled)

        if self.cpu_percent < 70:
            color = curses.color_pair(3)  # Green
        else:
            color = curses.color_pair(4)  # Red

        screen.addstr(self.y + 1, self.x + 2, f"{self.cpu_percent:5.1f}%")
        screen.addstr(self.y + 2, self.x + 2, bar, color)


class MemoryWidget(Widget):
    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height)
        self.memory_percent = 0
        self.memory_used = 0
        self.memory_total = 0

    def update(self):
        memory = psutil.virtual_memory()
        self.memory_percent = memory.percent
        self.memory_used = memory.used // (1024 * 1024)
        self.memory_total = memory.total // (1024 * 1024)

    def draw(self, screen):
        super().draw(screen)
        screen.addstr(self.y, self.x + 2, " Memory ")

        bar_width = self.width - 6
        filled = int(bar_width * self.memory_percent / 100)

        # Draw progress bar
        bar = "█" * filled + "░" * (bar_width - filled)

        if self.memory_percent < 70:
            color = curses.color_pair(3)  # Green
        else:
            color = curses.color_pair(4)  # Red

        screen.addstr(self.y + 1, self.x + 2, f"{self.memory_percent:5.1f}%")
        screen.addstr(self.y + 2, self.x + 2, bar, color)
        screen.addstr(self.y + 3, self.x + 2, f"{self.memory_used}M/{self.memory_total}M")


class ButtonWidget(Widget):
    def __init__(self, x, y, width, height, label, callback):
        super().__init__(x, y, width, height)
        self.label = label
        self.callback = callback
        self.pressed = False

    def draw(self, screen):
        super().draw(screen)

        if self.pressed:
            attr = curses.color_pair(2)
        else:
            attr = 0

        label_x = self.x + (self.width - len(self.label)) // 2
        label_y = self.y + self.height // 2

        screen.addstr(label_y, label_x, self.label, attr)

    def on_click(self):
        self.pressed = True
        self.callback()


def main(stdscr):
    app = TuiApp(stdscr)
    app.run()


if __name__ == "__main__":
    curses.wrapper(main)
