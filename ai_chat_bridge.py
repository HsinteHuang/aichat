import subprocess
import os
import sys
import re
import time
import tempfile  # 由 Claude 修改：用暫存檔傳遞多行 prompt，避免 cmd.exe 截斷換行
import msvcrt   # 由 Claude 修改：用於倒數計時中偵測鍵盤輸入（Windows 專用）
from datetime import datetime
from winpty import PtyProcess  # 由 Claude 修改：新增 pywinpty，讓 agy 以為有真實終端機

# 由 Claude 修改：完全改寫為輪流呼叫模式，使用 -p/--print 非互動旗標

DEFAULT_TOPIC = "如果用 AI 統治世界，第一步該做什麼？"
AUTO_CONTINUE_SECONDS = 5  # 由 Claude 修改：每輪結束後自動繼續的等待秒數


def make_env():
    """由 Claude 修改：建立關閉顏色輸出的環境變數"""
    env = os.environ.copy()
    env['NO_COLOR'] = '1'
    env['TERM'] = 'dumb'
    env['FORCE_COLOR'] = '0'
    return env


def strip_ansi(text):
    """由 Claude 修改：清除 ANSI 控制碼與多餘的終端機控制字元"""
    # 移除標準 ANSI escape sequences（含 ? 修飾符，如 [?1004h [?9001h）
    text = re.sub(r'\x1b\[[\?0-9;]*[a-zA-Z]', '', text)
    # 移除其他 ESC 序列（如 \x1b[c \x1b[1t）
    text = re.sub(r'\x1b[^a-zA-Z\[]?.', '', text)
    # 移除其他控制字元（保留換行與 tab）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text


HISTORY_WINDOW = 10  # 傳入 prompt 的最近幾筆對話（每輪 2 筆，預設保留最近 5 輪）


def build_prompt_for_claude(history):
    """將對話歷史整合成 prompt，最後一筆一定是 Agy 說的話。
    只取最近 HISTORY_WINDOW 筆，避免 prompt 隨輪數無限增長。"""
    window = history[-HISTORY_WINDOW:]
    omitted = len(history) - len(window)
    lines = ['以下是你（Claude）與 Agy 目前的完整對話紀錄，最後是 Agy 說的話，請直接回應：', '']
    if omitted:
        lines.append(f'（更早的 {omitted} 筆對話已省略）')
        lines.append('')
    for speaker, msg in window:
        prefix = '你（Claude）' if speaker == 'Claude' else speaker
        lines.append(f'[{prefix}]：{msg}')
        lines.append('')
    lines.append('請根據以上脈絡繼續對話，不要重新自我介紹。')
    return '\n'.join(lines)


def build_prompt_for_agy(history):
    """將對話歷史整合成 prompt，最後一筆一定是 Claude 說的話。
    只取最近 HISTORY_WINDOW 筆，避免 prompt 隨輪數無限增長。"""
    window = history[-HISTORY_WINDOW:]
    omitted = len(history) - len(window)
    lines = ['以下是你（Agy）與 Claude 目前的完整對話紀錄，最後是 Claude 說的話，請直接回應：', '']
    if omitted:
        lines.append(f'（更早的 {omitted} 筆對話已省略）')
        lines.append('')
    for speaker, msg in window:
        prefix = '你（Agy）' if speaker == 'Agy' else speaker
        lines.append(f'[{prefix}]：{msg}')
        lines.append('')
    lines.append('請根據以上脈絡繼續對話，不要重新自我介紹。')
    return '\n'.join(lines)


CLAUDE_ROLE_PROMPT = (
    "你現在是一個對話參與者，正在與另一個 AI（名為 Agy）進行即興對話討論。"
    "請直接回應對方說的話，進行真實的對話交流，不要以軟體工程助手的身份處理請求，"
    "也不要詢問對方需要什麼幫助。"
)


def call_claude(prompt, env):
    """由 Claude 修改：以非互動模式呼叫 claude，回傳回應文字。
    prompt 和 system prompt 皆寫入暫存檔後由 PowerShell 讀取，
    避免多行內容透過 cmd.exe 傳遞時換行被截斷的問題。"""
    prompt_path = sp_path = None
    try:
        fd1, prompt_path = tempfile.mkstemp(suffix='.txt', prefix='claude_p_')
        with os.fdopen(fd1, 'w', encoding='utf-8') as f:
            f.write(prompt)

        fd2, sp_path = tempfile.mkstemp(suffix='.txt', prefix='claude_sp_')
        with os.fdopen(fd2, 'w', encoding='utf-8') as f:
            f.write(CLAUDE_ROLE_PROMPT)

        ps_cmd = (
            f'$p = [IO.File]::ReadAllText("{prompt_path}", [Text.Encoding]::UTF8); '
            f'$sp = [IO.File]::ReadAllText("{sp_path}", [Text.Encoding]::UTF8); '
            f'claude -p $p --append-system-prompt $sp'
        )
        result = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps_cmd],
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=env
        )
        return result.stdout.strip()
    finally:
        for p in filter(None, [prompt_path, sp_path]):
            try:
                os.unlink(p)
            except OSError:
                pass


def call_agy(prompt, env):
    """由 Claude 修改：透過 PTY 呼叫 agy，讓它以為有真實終端機以避免卡住"""
    try:
        proc = PtyProcess.spawn(
            ['agy', '--print', prompt],
            env=env,
            dimensions=(50, 220)  # 寬度設大，避免 agy 的 UI 換行截斷內容
        )

        chunks = []
        while True:
            try:
                chunk = proc.read(4096)
                if chunk:
                    chunks.append(chunk)
            except EOFError:
                break

        proc.close()
        raw = ''.join(chunks)
        cleaned = strip_ansi(raw)

        # 過濾掉空行和只含符號的 UI 行，保留有意義的文字
        lines = []
        for line in cleaned.splitlines():
            stripped = line.strip()
            if len(stripped) > 3 and not re.fullmatch(r'[\─\━\═\─\|╭╮╰╯┌┐└┘\s\-=_*#]+', stripped):
                lines.append(stripped)

        return '\n'.join(lines).strip()

    except Exception as e:
        print(f"[System] PTY 呼叫失敗：{e}")
        return ''


def save_log(history, topic):
    """由 Claude 修改：將對話紀錄存成 txt 檔，儲存於 log 目錄"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"chat_log_{timestamp}.txt"
    log_dir = os.path.join(os.path.dirname(__file__), 'log')
    os.makedirs(log_dir, exist_ok=True)
    filepath = os.path.join(log_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"主題：{topic}\n")
        f.write(f"時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        for speaker, message in history:
            f.write(f"[{speaker}]\n{message}\n\n")
    return filepath


def wait_with_countdown(seconds=AUTO_CONTINUE_SECONDS, auto_msg="自動繼續下一輪"):
    """由 Claude 修改：倒數計時，期間可輸入新主題或 q 離開。
    回傳：None=自動繼續、False=離開、str=新主題
    若使用者開始輸入，停止倒數並等待 Enter。
    """
    print(f"\n{'─' * 60}")
    print(f"  {seconds} 秒後{auto_msg}")
    print("  輸入新主題 + Enter → 開啟新主題（清除對話紀錄）")
    print("  q + Enter          → 結束程式")
    print('─' * 60)

    chars = []
    deadline = time.time() + seconds

    while True:
        now = time.time()
        user_typing = len(chars) > 0

        if not user_typing and now >= deadline:
            # 倒數結束且使用者未輸入 → 自動繼續
            print(f"\r自動繼續下一輪...                              ")
            return None

        remaining = max(0, int(deadline - now) + 1)
        display = ''.join(chars)
        if user_typing:
            print(f"\r輸入中 > {display}   ", end='', flush=True)
        else:
            print(f"\r倒數 {remaining}s | 輸入新主題或 q > {display}  ", end='', flush=True)

        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ('\r', '\n'):  # Enter 確認
                print()
                text = ''.join(chars).strip()
                if text.lower() == 'q':
                    return False
                elif text:
                    return text  # 新主題
                else:
                    return None  # 空 Enter = 立即繼續
            elif ch == '\x08':  # Backspace
                if chars:
                    chars.pop()
            elif ch == '\x03':  # Ctrl+C
                raise KeyboardInterrupt
            elif ch in ('\x00', '\xe0'):  # 特殊鍵前綴，跳過下一個字元
                if msvcrt.kbhit():
                    msvcrt.getwch()
            elif ord(ch) >= 32:  # 一般可列印字元
                chars.append(ch)

        time.sleep(0.05)


def get_settings():
    """由 Claude 修改：啟動時詢問對話輪數與主題，回傳 (rounds, topic, initial_prompt)"""
    print("=" * 60)
    print("AI 聊天橋樑設定")
    print("=" * 60)

    # 詢問輪數
    while True:
        try:
            val = input(f"對話輪數（直接按 Enter 使用預設值 5）：").strip()
            if val == '':
                rounds = 5
                break
            rounds = int(val)
            if rounds < 1:
                raise ValueError
            break
        except ValueError:
            print("請輸入正整數。")
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)

    # 詢問主題
    try:
        topic = input(f"對話主題（直接按 Enter 使用預設：{DEFAULT_TOPIC}）：").strip()
        if not topic:
            topic = DEFAULT_TOPIC
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)

    return rounds, topic


def run_topic(rounds, topic, env, history=None):
    """由 Claude 修改：執行單一主題的對話。
    history=None 表示全新開始；傳入舊 history 則延續對話。
    回傳 (status, history)：
      status = 'quit'        → 使用者結束程式
      status = 'new:<主題>'  → 使用者輸入新主題
      status = 'done'        → 全部輪次正常完成
    """
    is_continuation = history is not None
    if history is None:
        history = []

    print("\n" + "=" * 60)
    print(f"主題：{topic}{'（延續）' if is_continuation else ''}")
    print(f"輪數：{rounds} 輪")
    print("=" * 60)

    for round_num in range(1, rounds + 1):
        print(f"\n--- 第 {round_num} / {rounds} 輪 ---")

        # 由 Claude 修改：history 為空時用開場白，否則直接傳完整歷史（最後一筆是 Agy）
        if not history:
            claude_prompt = f"請向 Antigravity (agy) 打招呼，並開始討論以下主題：{topic}"
        else:
            claude_prompt = build_prompt_for_claude(history)

        print(f"\n[Claude] 思考中...")
        claude_response = call_claude(claude_prompt, env)
        if not claude_response:
            print("[System] Claude 無回應，中止對話。")
            break
        print(f"[Claude] {claude_response}")
        history.append(('Claude', claude_response))

        # 由 Claude 修改：history 最後一筆現在是 Claude，直接傳給 agy
        agy_prompt = build_prompt_for_agy(history)

        print(f"\n[Agy] 思考中...")
        agy_response = call_agy(agy_prompt, env)
        if not agy_response:
            print("[System] Agy 無回應，中止對話。")
            break
        print(f"[Agy] {agy_response}")
        history.append(('Agy', agy_response))

        if round_num < rounds:
            result = wait_with_countdown()
            if result is False:
                print("\n[System] 使用者結束程式。")
                if history:
                    save_log(history, topic)
                return 'quit', history
            elif isinstance(result, str):
                if history:
                    log_path = save_log(history, topic)
                    print(f"[System] 對話紀錄已儲存：{log_path}")
                return f'new:{result}', []  # 新主題從空歷史開始

    # 全部輪次完成
    if history:
        log_path = save_log(history, topic)
        print(f"\n[System] 對話紀錄已儲存：{log_path}")

    return 'done', history  # 由 Claude 修改：回傳歷史，供延續使用


def main():
    env = make_env()
    rounds, topic = get_settings()

    current_topic = topic
    current_history = None  # 由 Claude 修改：None 表示全新開始

    while True:
        status, current_history = run_topic(rounds, current_topic, env, current_history)

        if status == 'quit':
            break

        if status.startswith('new:'):
            # 使用者在對話中途輸入了新主題
            current_topic = status[4:]
            current_history = None  # 清除歷史，全新開始
            print(f"\n[System] 開啟新主題：{current_topic}")
            continue

        # status == 'done'：所有輪次正常完成，詢問下一步
        # 由 Claude 修改：改用倒數計時，超過 5 秒自動延續舊主題
        print("\n" + "=" * 60)
        print(f"已完成 {rounds} 輪對話。")
        next_input = wait_with_countdown(auto_msg="自動延續舊主題")

        if next_input is False:
            break
        elif isinstance(next_input, str):
            # 新主題，清除歷史
            current_topic = next_input
            current_history = None
            print(f"\n[System] 開啟新主題：{current_topic}")
        else:
            # None = 超時或空 Enter，延續舊主題，保留歷史
            print(f"\n[System] 延續主題：{current_topic}")

    print("\n" + "=" * 60)
    print("感謝使用 AI 聊天橋樑，再見！")
    print("=" * 60)


if __name__ == '__main__':
    main()
