import random
import time
import os

# Initializing variables
matrix_chars = "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()ΣΘΠΩαβγδεζηθικλμνξοπρστυφχψω"

try:
    terminal_size = os.get_terminal_size()
    width = terminal_size.columns
    height = terminal_size.lines
except OSError:
    # Default values for output piping
    width = 80
    height = 24

# Array to store the vertical position of each drop in columns
drops = [0] * width

# Infinite loop for the illusion
while True:
    line = ""
    # Iterate through columns
    for i in range(width):
        # Add character at current drop position
        if drops[i] > 0:
            char = random.choice(matrix_chars)
            # The tail is green, head is white
            if drops[i] <= 1:
                # White color
                line += "\033[1;37m" + char + "\033[0m"
            else:
                # Green color
                line += "\033[32m" + char + "\033[0m"
            drops[i] -= 1
        else:
            line += " "

        # Randomly start a new drop in columns
        if random.random() < 0.02:
            drops[i] = random.randint(1, height)

    print(line)
    # Control the speed
    time.sleep(0.05)
