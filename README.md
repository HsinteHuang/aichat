# AI Chat Bridge / AI 聊天橋樑

[![Stars](https://img.shields.io/github/stars/HsinteHuang/aichat?style=flat&color=yellow)](https://github.com/HsinteHuang/aichat/stargazers)
[![Forks](https://img.shields.io/github/forks/HsinteHuang/aichat?style=flat&color=blue)](https://github.com/HsinteHuang/aichat/network/members)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![OS](https://img.shields.io/badge/OS-Windows-success)
![AI](https://img.shields.io/badge/AI-Claude%20%7C%20Agy-blueviolet)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

A Python-based bridge that enables two AI assistants — **Claude** (Anthropic) and **Agy** (Antigravity) — to converse with each other autonomously.

兩個 AI 助手自動對話的橋接工具，支援 **Claude**（Anthropic）與 **Agy**（Antigravity）。

---

> ⚠️ **Warning / 警告**  
> Conducting multi-round AI-to-AI conversations will consume a significant amount of tokens, as the entire conversation history is sent in each turn. Please monitor your API usage and costs.  
> 進行多輪 AI 自動對話會消耗大量的 Token，因為每一輪呼叫都會傳遞累積的完整對話歷史。請密切注意您的 API 使用額度與費用。

## Features / 功能特色

- 🗣️ **Free Conversation Mode** (`ai_chat_bridge.py`) — Two AIs discuss any topic you choose  
  **自由對話模式** — 兩個 AI 針對你指定的主題自由討論

- ⏱️ Auto-advances every 5 seconds; intervene anytime  
  每輪自動倒數 5 秒繼續；隨時可介入切換主題

- 🧠 Full conversation memory passed each round  
  每輪完整傳遞對話歷史，AI 具備記憶脈絡

- 📝 All logs saved to `log/` directory (not tracked by git)  
  所有紀錄自動儲存至 `log/` 目錄（不推送至 git）

---

## Requirements / 環境需求 (⚠️ Windows Only / 僅支援 Windows)

- Windows 10 / 11 (由於使用 Windows 專有 API，目前不支援 macOS/Linux)
- Python 3.8+
- [Claude Code CLI](https://claude.ai/code) installed and authenticated  
  已安裝並登入 Claude Code CLI
- [Antigravity (agy) CLI](https://antigravity.dev) installed and authenticated  
  已安裝並登入 Antigravity CLI
- Required Python packages / 必要的 Python 套件：

  This project requires `pywinpty` for managing pseudo-terminals (PTY) on Windows.  
  本專案需要 `pywinpty` 套件以在 Windows 上管理虛擬終端機 (PTY)。

  You can install it by running the following command in your terminal:  
  您可以透過在終端機中執行以下指令來安裝：

  ```bash
  pip install pywinpty
  ```

---

## Installation / 安裝

```bash
git clone https://github.com/HsinteHuang/aichat.git
cd aichat
pip install pywinpty
```

---

## Usage / 使用方式

### Free Conversation Mode / 自由對話模式

```bash
python ai_chat_bridge.py
```

**Startup prompts / 啟動設定：**

```
對話輪數（直接按 Enter 使用預設值 5）：
對話主題（直接按 Enter 使用預設）：
```

**During conversation / 對話進行中：**

| Action / 操作 | Result / 效果 |
|---|---|
| Wait 5 seconds / 等待 5 秒 | Auto-advance to next round / 自動開始下一輪 |
| Type new topic + Enter / 輸入新主題 | Switch topic, clear history / 切換主題，清除歷史 |
| `q` + Enter | Quit / 結束程式 |

---

## Output / 輸出紀錄

All conversation and collaboration logs are saved in the `log/` directory:

所有對話紀錄儲存於 `log/` 目錄：

- `log/chat_log_YYYYMMDD_HHMMSS.txt` — Conversation logs / 對話紀錄

---

## Project Structure / 專案結構

```
aichat/
├── ai_chat_bridge.py   # Free conversation mode / 自由對話模式
├── log/                # Logs (git-ignored) / 紀錄目錄（不推送）
│   └── .gitkeep
├── .gitignore
├── LICENSE
└── README.md
```

---

## How It Works / 運作原理

1. `claude -p` is called via PowerShell with prompts written to temp files to handle multiline content correctly on Windows.  
   透過 PowerShell 搭配暫存檔呼叫 `claude -p`，正確處理 Windows 上的多行 prompt 傳遞。

2. `agy --print` is called via a pseudo-terminal (PTY) using `pywinpty`, since Agy requires a TTY to function.  
   透過 `pywinpty` 建立虛擬終端機 (PTY) 呼叫 `agy --print`，讓 Agy 以為連接了真實終端機。

3. Full conversation history is prepended to each prompt so both AIs maintain context across rounds.  
   每輪呼叫時附上完整對話歷史，讓兩個 AI 保有跨輪的記憶脈絡。

---

## License / 授權

MIT License — see [LICENSE](LICENSE) for details.  
MIT 授權條款 — 詳見 [LICENSE](LICENSE)。
