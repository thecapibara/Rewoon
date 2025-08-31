# Rewoon - The Random Scare Generator

Ever wanted to add a little unexpected excitement to your streams, gaming or coding sessions? **Rewoon** is a simple, lightweight, cross-platform app that randomly plays a sound of your choice to keep you on your toes.

Perfect for scaring yourself, your friends, or your stream audience when they least expect it. Set it, forget it, and wait for the screams!

 <!-- Optional: Replace with a screenshot of your app -->

## Features

-   **Cross-Platform**: Works flawlessly on Windows and major Linux distributions (Arch, Ubuntu, Fedora).
-   **System Tray Icon**: Hides in your system tray after setup, staying out of your way while it waits for the perfect moment to strike.
-   **Customizable Icon**: Easily add your own `icon.png` to the `assets` folder to personalize the tray icon.
-   **Low Memory Usage**: Built with Python's standard libraries to ensure a minimal impact on your system's performance.
-   **User-Friendly Configuration**: Easily change timings in the `config.ini` file without touching the code.
-   **Randomized Scares**: Plays the selected sound at completely random intervals. You'll never know when it's coming!

## Installation

First, clone the repository to your local machine:

```bash
git clone https://github.com/thecapibara/rewoon.git
cd rewoon
```

Next, you need to install the necessary Python libraries. A `requirements.txt` file is included to make this easy.

```bash
pip install -r requirements.txt
```

## How to Use

The process is simple: run the script, choose a sound, and start the application. It will then run in the background from the system tray.

### On Windows

1.  Open PowerShell or Command Prompt.
2.  Navigate to the `rewoon` directory.
3.  Run the application with the following command:
    ```powershell
    python rewoon.py
    ```

### On Linux (Arch / Ubuntu / Fedora)

1.  Open your terminal.
2.  Navigate to the `rewoon` directory.
3.  Run the application with the following command:
    ```bash
    python3 rewoon.py
    ```

After starting, select a sound file, click "Start", and the application window will hide, leaving only an icon in your system tray. To stop the application completely, right-click the tray icon and select "Exit".

## Running Detached from the Terminal

Once the application's GUI window is open, you can safely close the terminal/PowerShell window that launched it. However, for a cleaner start, you can launch the script so it never attaches to a terminal at all.

Any output the script would normally print to the terminal (like our `print()` statements for debugging) will be redirected to a file named `nohup.out` when using the Linux method.

| Method | When to Use It | How It Works |
| :--- | :--- | :--- |
| **Just close the terminal** | Works fine for this GUI app. | The OS treats the GUI window as its own independent process. |
| `pythonw.exe rewoon.py` | **The best way on Windows.** | Runs the script as a windowed application from the start, never opening a console. |
| `nohup python3 rewoon.py &` | **The standard way on Linux for any long-running process.** | Detaches the process from the terminal, preventing it from being closed. |

## Configuration

You can easily change the minimum and maximum time (in seconds) between scares without editing any code.

1.  Open the `config.ini` file in a text editor.
2.  Change the values of `min_delay` and `max_delay`.
3.  Save the file. The changes will apply the next time you start Rewoon.

```ini
[Settings]
min_delay = 10
max_delay = 600
```

## Project Structure

The project is organized into logical modules for easy maintenance and contribution.

```
rewoon/
├── assets/
│   └── icon.png           # Customizable tray icon
├── .gitignore             # Tells Git what files to ignore
├── config.ini             # User-facing settings
├── config.py              # Loads settings and holds app state
├── LICENSE                # MIT License
├── README.md              # You are here!
├── requirements.txt       # Project dependencies
├── rewoon.py              # Main entry point for the application
├── sound_player.py        # Core logic for playing sounds
└── ui.py                  # All GUI and system tray code
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
