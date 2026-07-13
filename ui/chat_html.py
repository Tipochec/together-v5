from .chat_styles import CSS
from .chat_script import JS

HTML = r"""
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">

<style>
{styles}
</style>

</head>

<body>

<div class="titlebar">
<div class="title">
💬 Чат
</div>

<button class="close" onclick="clearChat()" title="Очистить историю (только у себя)" style="margin-right:4px">
🗑
</button>

<button class="close" onclick="pywebview.api.close_chat()">
✕
</button>

</div>

<div id="chat-list" class="messages">

</div>

<div id="emoji-picker" class="emoji-picker" style="display:none">
<div class="emoji-grid" id="emoji-grid"></div>
</div>

<div class="input">

<input
id="message"
placeholder="Напишите сообщение...">

<button
class="send emoji-btn"
id="emoji-toggle-btn"
onclick="toggleEmojiPicker()"
title="Смайлики">

🙂

</button>

<button
class="send"
onclick="sendMessage()">

➤

</button>

</div>

<div id="confirm-overlay" class="confirm-overlay" style="display:none">
  <div class="confirm-box">
    <div class="confirm-text">Очистить историю чата у себя?<br>Партнёра переписка не тронется.</div>
    <div class="confirm-btns">
      <button class="confirm-btn confirm-cancel" onclick="hideConfirm()">Отмена</button>
      <button class="confirm-btn confirm-ok" onclick="confirmClearChat()">Очистить</button>
    </div>
  </div>
</div>

<script>

{script}

</script>

</body>
</html>
"""

HTML = HTML.format(
    styles=CSS,
    script=JS
)