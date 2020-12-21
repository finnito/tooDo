# TooDo

> Find the tasks in your source files!

This is a fun weekend project for me, but I am all for learning, so [let me know](https://github.com/Finnito/tooDo/issues) if things don't work, or you have a feature request.

## How to Use

1. Clone this repository
2. Install requirements (`fswatch`, `toml`)
    - `python3 -m pip install -r requirements.txt`
3. Open `config.toml` and define the directories you want to watch, like this:

```toml
[directories]
    [directories.tooDo]
        path = "/Users/finnlesueur/Git/tooDo/"
        ignore_paths = [
            "venv"
        ]
        ignore_types = [
            ".html",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".gpx",
            ".min.js",
        ]
```

4. Run the script!
    - `python tooDo.py`
    - I personally made an [Automator](https://support.apple.com/en-au/guide/automator/welcome/mac) app which simply calls this script so I can boot it from [Alfred](https://www.alfredapp.com).

### Customisation

You may wish to customise the FIX/TODO/NOTE/whateveryouwant patterns being searched for. You can do this in `config.toml`

```toml
[patterns]
    [patterns.FIX]
        regex = "FIX:\\s*(.*)"
    [patterns.TODO]
        regex = "TODO:\\s*(.*)"
    [patterns.NOTE]
        regex = "NOTE:\\s*(.*)"
```

You can also change the font family, font size, font colour, background colour and colour of the currently selected line.

---

### Dependencies

- [pyfswatch](https://github.com/paul-nameless/pyfswatch)
    + MIT License
- [toml](https://github.com/uiri/toml)
    + MIT License 