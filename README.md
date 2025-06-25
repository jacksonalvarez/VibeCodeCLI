# AI COMMAND LINE APP

![AI CLI Demo](https://github.com/user-attachments/assets/660e6b9d-22c6-4413-823d-1c75c030cbae)

A smart, terminal-based AI assistant that helps you write, compile, and run code in many programming languages — all from your command line with a sleek and interactive interface.

---

## What It Does

- Rich, responsive terminal UI powered by [Textual](https://github.com/Textualize/textual)
- Uses OpenAI’s API to help you write and improve code
- Supports compiling and running multiple languages
- Real-time feedback and logs
- Handles threading, subprocesses, and runtime quirks
- Makes terminal coding faster and more intuitive

---

## 🚀 Getting Started

### What You Need

- Python 3.9 or newer
- Required libraries:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install textual rich openai python-dotenv
```

### API Key Setup

Create a `.env` file in your project folder:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

---

## Supported Languages

This app supports a wide variety of file types and languages:

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

> ⚠️ **Heads up:** If you plan to run code in compiled languages (like Java, C++, Rust, etc.), you’ll need to have those compilers/runtimes installed yourself. This app helps you use them — it doesn’t install them for you.

---

## How to Run It

From the root directory, launch the app with:

```bash
python app.py
```

Enjoy the magic. 

---

##  requirements.txt

```txt
textual
rich
openai
python-dotenv
```

---

## 💖 Leave a Tip

Support a broke solo developer ;D
[![[Donate](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/pool/9g1cB8WseO?sr=wccr](https://www.paypal.com/donate/?business=AS3PVPZSJHS84&no_recurring=0&item_name=Support+a+solo+guy+who+makes+free+accessible+tools+for+everyone.+Even+1%24+helps%21&currency_code=USD))]

Or just send a thank-you — that works too. 🙏

---

## 📜 License

MIT License — free to use, share, and modify. Happy coding!
