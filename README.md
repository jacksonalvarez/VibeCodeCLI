# AI-CLI APP

A smart, terminal-based AI assistant that helps you write, compile, and run code in many programming languages — all from your command line with a sleek and interactive interface.

---

## What It Does

- Provides a rich, user-friendly terminal UI powered by [Textual](https://github.com/Textualize/textual)
- Uses OpenAI’s API to assist with coding tasks
- Supports writing, compiling, and running code in multiple languages
- Shows logs and feedback in real-time for smooth workflows
- Handles multi-threading and subprocesses behind the scenes
- Makes working with code from the terminal fun and productive

---

## Getting Started

### What You Need

- Python 3.9 or newer
- The following Python libraries (install with pip):

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install textual rich openai python-dotenv
```

### Your OpenAI API Key

To connect to OpenAI’s service, create a `.env` file in the project folder with this line:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

---

## Supported Languages

This app supports working with code files in these languages:

| Extension | Language            |
|-----------|---------------------|
| `.py`     | Python              |
| `.js`     | JavaScript (Node.js)|
| `.ts`     | TypeScript          |
| `.java`   | Java                |
| `.cpp`    | C++                 |
| `.c`      | C                   |
| `.cs`     | C#                  |
| `.go`     | Go                  |
| `.rs`     | Rust                |
| `.rb`     | Ruby                |
| `.php`    | PHP                 |
| `.html`   | HTML                |
| `.css`    | CSS                 |
| `.json`   | JSON                |
| `.md`     | Markdown            |
| `.txt`    | Plain Text          |
| `.xml`    | XML                 |
| `.yml`    | YAML                |
| `.yaml`   | YAML                |

**Important:**  
For languages that require compiling or a runtime (like Java, C++, Go, etc.), please make sure you have the necessary tools installed on your computer. This app doesn’t install them for you — it just helps you use what you already have.

---

## How To Run

Once everything is set up, just run:

```bash
python app.py
```

and start coding smarter from your terminal.

---

## Project Files Overview

```
.
├── app.py                # The main app UI and logic
├── agent.py              # AI coding assistant backend
├── llm_utils.py          # Helper utilities for language model interaction
├── .env                  # Your OpenAI API key (not included)
├── requirements.txt      # Python dependencies list
└── README.md             # This guide
```

---

## Dependencies (`requirements.txt`)

```txt
textual>=0.54.1
rich>=13.7.0
openai>=1.3.7
python-dotenv>=1.0.0
```

---

## License

MIT License — free to use and modify!
