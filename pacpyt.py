import curses
import random
import time

MAP = [
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o####.#####.##.#####.####o#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#.####.##.########.##.####.#",
    "#......##....##....##......#",
    "######.##### ## #####.######",
    "     #.##### ## #####.#     ",
    "     #.##          ##.#     ",
    "     #.## ###--### ##.#     ",
    "######.## #      # ##.######",
    "      .   #      #   .      ",
    "######.## #      # ##.######",
    "     #.## ######## ##.#     ",
    "     #.##          ##.#     ",
    "     #.## ######## ##.#     ",
    "######.## ######## ##.######",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o..##................##..o#",
    "###.##.##.########.##.##.###",
    "#......##....##....##......#",
    "#.##########.##.##########.#",
    "#.##########.##.##########.#",
    "#..........................#",
    "############################",
]

# Convert map to mutable list
HEIGHT = len(MAP)
WIDTH = max(len(row) for row in MAP)
grid = [list(row.ljust(WIDTH)) for row in MAP]

DIR_VECT = {
    curses.KEY_UP: (-1, 0),
    curses.KEY_DOWN: (1, 0),
    curses.KEY_LEFT: (0, -1),
    curses.KEY_RIGHT: (0, 1),
    ord('w'): (-1, 0),
    ord('s'): (1, 0),
    ord('a'): (0, -1),
    ord('d'): (0, 1),
}

def find_empty():
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] in ('.', 'o', ' '):
                return y, x
    return 1,1

def neighbors(y, x):
    for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
        ny, nx = y+dy, x+dx
        if 0 <= ny < HEIGHT and 0 <= nx < WIDTH and grid[ny][nx] != '#':
            yield ny, nx

class Ghost:
    def __init__(self, y, x, ch='G'):
        self.y = y
        self.x = x
        self.ch = ch
        self.spawn = (y, x)
    def step(self):
        opts = list(neighbors(self.y, self.x))
        if opts:
            self.y, self.x = random.choice(opts)
    def reset(self):
        self.y, self.x = self.spawn

# ...existing code...
def draw(stdscr, pac_y, pac_x, pac_dir, dots, ghosts, score):
    stdscr.clear()
    rows, cols = stdscr.getmaxyx()

    def safe_addstr(y, x, s, attr=0):
        if not (0 <= y < rows and x < cols):
            return
        # clip string to remaining columns to avoid addstr ERR
        try:
            stdscr.addstr(y, x, s[: max(0, cols - x)], attr)
        except curses.error:
            pass

    # if terminal is too small to show map + status, show warning
    if rows < HEIGHT + 2 or cols < WIDTH:
        msg = f"Terminal too small: need {WIDTH}x{HEIGHT+2}, have {cols}x{rows}"
        safe_addstr(rows // 2, max(0, (cols - len(msg)) // 2), msg, curses.A_BOLD)
        safe_addstr(rows - 1, 0, f"Score: {score}  (q to quit)")
        stdscr.refresh()
        return

    for y in range(HEIGHT):
        for x in range(WIDTH):
            ch = grid[y][x]
            if ch == '#':
                safe_addstr(y, x, '#', curses.color_pair(3))
            elif (y, x) in dots:
                safe_addstr(y, x, '.', curses.color_pair(2))
            elif ch == 'o':
                safe_addstr(y, x, 'o', curses.color_pair(2) | curses.A_BOLD)
            else:
                safe_addstr(y, x, ' ')

    # draw ghosts
    for g in ghosts:
        safe_addstr(g.y, g.x, g.ch, curses.color_pair(4) | curses.A_BOLD)

    # pac-man glyph by direction
    glyph = {'up': '^', 'down': 'v', 'left': '<', 'right': '>'}.get(pac_dir, 'C')
    safe_addstr(pac_y, pac_x, glyph, curses.color_pair(1) | curses.A_BOLD)

    # status on the first free line
    safe_addstr(HEIGHT, 0, f"Score: {score}  (q to quit)")
    stdscr.refresh()

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)  # Pac-Man
    curses.init_pair(2, curses.COLOR_WHITE, -1)   # Dots
    curses.init_pair(3, curses.COLOR_BLUE, -1)    # Walls
    curses.init_pair(4, curses.COLOR_RED, -1)     # Ghosts

    # collect dots and power pellets
    dots = set()
    power = set()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] == '.':
                dots.add((y,x))
            elif grid[y][x] == 'o':
                power.add((y,x))
                dots.add((y,x))

    # place Pac-Man
    pac_y, pac_x = 23, 13  # reasonable start inside map
    pac_dir = 'left'
    score = 0

    # ghosts
    ghosts = [
        Ghost(13, 12, 'B'),
        Ghost(13, 15, 'P'),
        Ghost(11, 12, 'I'),
        Ghost(11, 15, 'C'),
    ]

    tick = 0
    alive = True
    power_timer = 0

    while True:
        tick += 1
        # input
        try:
            key = stdscr.getch()
        except KeyboardInterrupt:
            break
        if key == ord('q'):
            break
        if key in DIR_VECT:
            dy, dx = DIR_VECT[key]
            ny, nx = pac_y + dy, pac_x + dx
            if 0 <= ny < HEIGHT and 0 <= nx < WIDTH and grid[ny][nx] != '#':
                pac_y, pac_x = ny, nx
                if (dy,dx) == (-1,0): pac_dir='up'
                elif (dy,dx) == (1,0): pac_dir='down'
                elif (dy,dx) == (0,-1): pac_dir='left'
                elif (dy,dx) == (0,1): pac_dir='right'

        # eat dots
        if (pac_y, pac_x) in dots:
            dots.remove((pac_y, pac_x))
            score += 10
        if (pac_y, pac_x) in power:
            power_timer = 50
            score += 50
            # remove pellet so it's not repeatedly triggered
            power.remove((pac_y,pac_x))

        # ghosts move every N ticks
        if tick % 2 == 0:
            for g in ghosts:
                g.step()

        # collisions
        for g in ghosts:
            if (g.y, g.x) == (pac_y, pac_x):
                if power_timer > 0:
                    score += 200
                    g.reset()
                else:
                    alive = False

        if not alive:
            draw(stdscr, pac_y, pac_x, pac_dir, dots, ghosts, score)
            stdscr.nodelay(False)
            stdscr.addstr(HEIGHT+1, 0, "GAME OVER. Press any key to exit.")
            stdscr.getch()
            break

        if not dots:
            draw(stdscr, pac_y, pac_x, pac_dir, dots, ghosts, score)
            stdscr.nodelay(False)
            stdscr.addstr(HEIGHT+1, 0, "YOU WIN! Press any key to exit.")
            stdscr.getch()
            break

        # decrement power
        if power_timer > 0:
            power_timer -= 1

        draw(stdscr, pac_y, pac_x, pac_dir, dots, ghosts, score)
        time.sleep(0.08)

if __name__ == "__main__":
    curses.wrapper(main)
