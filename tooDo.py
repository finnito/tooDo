"""
Author: Finn Le Sueur
Website: https://github.com/Finnito/tooDo

This script is a fun weekend project
that finds all TODO/FIX/NOTE comments
inside directories and watches for
updates with fswatch.
"""

from fswatch import Monitor
import threading
import logging
import os
import queue
import re
import subprocess
import tkinter as tk
import toml


class TooDo:
    """ The business."""
    def __init__(self, window):
        # Load user defined directories
        self.config = self.load_config()

        # Create the tkinter window
        self.window = window
        self.window.geometry("1000x500")
        self.window.title("TooDo")
        self.window.wm_iconbitmap("icon.png")
        self.window.protocol("WM_DELETE_WINDOW", self.sigint_handler)
        self.window.after(0, self.check_queue)

        # Setup the text widget to be
        # updated over time.
        self.textWidget = tk.Text(
            self.window,
            width=15,
            height=15,
            wrap="word",
            padx=2,
            pady=2,
            font=(
                self.config["display"]["font_family"],
                self.config["display"]["font_size"]
            ),
            bg=self.config["display"]["background"],
            fg=self.config["display"]["text"],
            highlightthickness=0,
            spacing1=5,
            spacing3=5
        )
        self.textWidget.insert(tk.END, "Scanning...")
        self.textWidget.bind('<KeyPress-Return>', self.open_file)
        self.textWidget.bind('<KeyRelease-Up>', self.highlight_current_line)
        self.textWidget.bind('<KeyRelease-Down>', self.highlight_current_line)
        self.textWidget.bind('<ButtonRelease>', self.highlight_current_line)
        self.textWidget.pack(fill=tk.BOTH, expand=1)
        self.textWidget.focus_set()
        self.textWidget.tag_configure('bold', font=(
            self.config["display"]["font_family"],
            self.config["display"]["font_size"],
            'bold'))
        self.textWidget.tag_configure('italics', font=(
            self.config["display"]["font_family"],
            self.config["display"]["font_size"],
            'italic'))
        self.textWidget.tag_configure('big', font=(
            self.config["display"]["font_family"],
            self.config["display"]["font_size_big"],
            'bold'))
        self.textWidget.tag_configure("current_line", background=self.config["display"]["current_line"])

        # Setup the todos variable
        # where they are stored.
        self.todos = {}

        # Setup queue for inter-thread communication.
        self.queue = queue.Queue()

        # Search all files on start-up
        self.scan_all_files()

        # Create and start the monitor thread
        # to listen for file events.
        control_thread = threading.Thread(target=self.monitor, daemon=True)
        control_thread.start()

    def highlight_current_line(self, event):
        """
        This event adds a tag to the line
        where the insert cursor is placed.
        It is fired on key release UP/DOWN
        and when the mouse is clicked.

        The argument event is taken but not used.
        """
        logging.debug("Function: highlight current line")
        self.textWidget.tag_remove("current_line", 1.0, "end")
        self.textWidget.tag_add("current_line", "insert linestart", "insert lineend+1c")

    def open_file(self, event):
        """
        A user may push "RETURN" on a line
        to open that file for editing.
        This function figures out what line
        is selected, and figures out the
        absolute path of the file.
        """
        line = self.textWidget.get('insert linestart', 'insert lineend')
        line_split = line.split(" ")
        for i, item in enumerate(line_split):
            if item in [" ", ""]:
                line_split.pop(i)
        line_num = line_split[1].split(":")[1]
        relative_path = line_split[1].split(":")[0]
        logging.debug("Function: open_file " + relative_path)
        for directory, files in self.todos.items():
            for file, value in files.items():
                if file == relative_path:
                    logging.info(os.path.join(directory, file) + ":" + line_num)
                    subprocess.run(['/usr/local/bin/subl', os.path.join(directory, file) + ":" + line_num], check=True)
        return "break"

    @staticmethod
    def load_config():
        logging.debug("Function: load_config")
        with open('config.toml', 'r') as config_file:
            return toml.load(config_file, _dict=dict)

    def monitor(self):
        logging.debug("Function: monitor")
        monitor = Monitor()
        monitor.set_recursive()

        for name, directory in self.config["directories"].items():
            logging.debug("    Adding monitor: " + directory["path"])
            monitor.add_path(directory["path"])

        monitor.set_callback(self.callback)
        monitor.start()

    def callback(self, path, evt_time, flags, flags_num, event_num):
        logging.debug("Function: fsevent callback")
        path = path.decode()
        directory = self.match_directory(path)

        if directory is None:
            return

        if os.path.isdir(path):
            return

        relative_path = path.split(directory["path"])[1]
        if relative_path is None:
            return

        for ignore in directory["ignore_paths"]:
            if relative_path.startswith(ignore):
                return

        for fileType in directory["ignore_types"]:
            if relative_path.endswith(fileType):
                return

        tasks = self.look_for_todos(path, relative_path)
        
        if not directory["path"] in self.todos:
            self.todos[directory["path"]] = {}

        self.todos[directory["path"]][relative_path] = tasks
        self.output_todos()

    def scan_all_files(self):
        logging.debug("Function: scan_all_files")
        for name, directory in self.config["directories"].items():
            directory_has_todos = False
            for root, subdirectories, files in os.walk(directory['path']):
                current_dir = root.split(directory["path"])[1]
                # Check if directory should be ignored
                if current_dir.startswith(tuple(directory["ignore_paths"])):
                    break

                # if not currentDir.startswith(tuple(directory["ignore_paths"])):
                for filename in files:
                    # Check if file type is ignored
                    if filename.endswith(tuple(directory["ignore_types"])):
                        continue

                    file_path = os.path.join(root, filename)
                    relative_path = file_path.split(directory["path"])[1]
                    tasks = self.look_for_todos(file_path, relative_path)
                    if tasks:
                        if not directory_has_todos:
                            self.todos[directory["path"]] = {}
                            directory_has_todos = True
                        self.todos[directory["path"]][relative_path] = tasks
        self.output_todos()

    def look_for_todos(self, path, relative_path):
        logging.debug("Function: look_for_todos")
        file_tasks = {}
        if not os.path.exists(path):
            return file_tasks

        with open(path, "r") as file:
            try:
                lines = file.readlines()
            except UnicodeDecodeError: 
                return
            for i, line in enumerate(lines):
                for key, pattern in self.config["patterns"].items():
                    matches = re.finditer(rf"{pattern['regex']}", line, re.IGNORECASE)
                    for matchNum, match in enumerate(matches, start=1):
                        todo = self.strip_closing_comment_fences(path, match.group(1))

                        if key not in file_tasks:
                            file_tasks[key] = []

                        file_tasks[key].append({
                            "line": i+1,
                            "task": todo,
                            "path": relative_path
                        })
        return file_tasks

    def strip_closing_comment_fences(self, path, todo):
        logging.debug("Function: strip_closing_comment_fences")
        file_type = path.split(".")[-1]
        if file_type is None:
            return

        if file_type in self.config["comment_fences"]:
            todo = todo.removesuffix(self.config["comment_fences"][file_type]["fence"])
            todo = todo.strip()

        return todo

    def match_directory(self, path):
        logging.debug("Function: match_directory")
        for name, directory in self.config["directories"].items():
            if path.startswith(directory["path"]):
                return directory

    def find_longest_line(self):
        logging.debug("Function: find_longest_line")
        max_len = 0
        for directory, files in self.todos.items():
            for file, patterns in files.items():
                for pattern, tasks in patterns.items():
                    for task in tasks:
                        line_length = len(f"{file}:{task['line']}")
                        if line_length >= max_len:
                            max_len = line_length
        return max_len

    @staticmethod
    def get_spaces(max_len, line):
        logging.debug("Function: get_spaces")
        if len(line) != max_len:
            return " " * (max_len - len(line) + 4)
        else:
            return " " * 4

    @staticmethod
    def get_tasks_by_pattern(files, pattern):
        logging.debug("Function: get_tasks_by_pattern")
        out = []
        for filePath, tasks in files.items():
            if pattern in tasks:
                out += tasks[pattern]
        return out

    def output_todos(self):
        logging.debug("Function: output_todos")
        max_len = self.find_longest_line()
        for directory, files in self.todos.items():
            self.queue.put([f"DIRECTORY: {directory}\n", 'big'])
            for pattern, regex in self.config["patterns"].items():
                tasks = self.get_tasks_by_pattern(files, pattern)
                if len(tasks) != 0:
                    self.queue.put([f"{pattern}\n", 'bold'])
                    for i, task in enumerate(tasks):
                        i += 1
                        spaces = self.get_spaces(max_len, f"{task['path']}:{task['line']}")
                        if i < 10:
                            self.queue.put([f"{i}.  ", "bold"])
                        else:
                            self.queue.put([f"{i}. ", "bold"])
                        self.queue.put([f"{task['path']}:{task['line']}", "italics"])
                        self.queue.put([f"{spaces}{task['task']}\n", ""])
                    self.queue.put(["\n", ""])
            self.queue.put(["\n", ""])

    def check_queue(self):
        logging.debug("Function: check_queue")
        if not self.queue.empty():
            logging.debug("    Queue not empty")
            self.textWidget.delete("1.0", tk.END)
            logging.debug("        Removed labels")
            while not self.queue.empty():
                logging.debug("        Adding label")
                item = self.queue.get()
                self.textWidget.insert(tk.END, item[0], item[1])
        self.window.after(self.config["settings"]["tk_refresh_rate"], self.check_queue)

    def sigint_handler(self):
        self.window.destroy()
        exit(0)


def main():
    logging.basicConfig(level=logging.DEBUG, filename="out.log")
    window = tk.Tk()
    TooDo(window)
    window.mainloop()


if __name__ == "__main__":
    main()
