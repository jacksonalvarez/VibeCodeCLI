# AI CLI App

A terminal-based AI assistant for writing, compiling, and executing code across multiple languages — directly from your terminal using a rich Textual UI.

---

## 🧠 Features

- Terminal UI with input fields, logs, buttons, and more (via [textual](https://github.com/Textualize/textual))
- OpenAI-powered code assistant
- Supports code generation and execution for many languages
- Handles compilation and runtime execution
- Multithreading and subprocess support
- Rich logging and formatting via `rich`

---

## 📦 Requirements

### Python Version

- **Python 3.9+** is required.

### Python Dependencies

Install with:

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install textual rich openai python-dotenv
```

#### Required Packages

- [textual](https://pypi.org/project/textual/)
- [rich](https://pypi.org/project/rich/)
- [openai](https://pypi.org/project/openai/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

---

## 🔐 Environment Variables

Create a `.env` file in the root directory with your OpenAI API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

---

## 🖥️ Supported Languages

This app supports the following file types and languages:

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

> ⚠️ **Bring your own compiler**:  
> For compiled or interpreted languages (like C, Java, TypeScript, Go, etc.), you **must have the necessary compiler or runtime installed** on your system.  
> This app does not include or install them for you.

---

## 🚀 Running the App

Once dependencies are installed and your `.env` file is set up, run:

```bash
python app.py
```

---

## 📁 Project Structure

```
.
├── app.py                # Main Textual application
├── agent.py              # AI agent logic
├── llm_utils.py          # LLM helper utilities
├── .env                  # API key config
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## 📄 requirements.txt

```txt
textual>=0.54.1
rich>=13.7.0
openai>=1.3.7
python-dotenv>=1.0.0
```

---

## 🪪 License

MIT License (or insert your preferred license here)