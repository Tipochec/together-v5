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

<div class="titlebar pywebview-drag-region">
<div class="title">
💬 Чат
</div>

<div style="display:flex;align-items:center;gap:4px">
<button class="close" onclick="clearChat()" title="Очистить историю (только у себя)">
🗑
</button>

<button class="close" onclick="pywebview.api.close_chat()" title="Закрыть">
✕
</button>
</div>

</div>

<div id="chat-list" class="messages">

</div>

<div id="emoji-picker" class="emoji-picker" style="display:none">
  <div class="emoji-tabs">
    <button class="emoji-tab active" data-tab="faces" onclick="switchEmojiTab('faces')" title="Смайлы">😀</button>
    <button class="emoji-tab" data-tab="love" onclick="switchEmojiTab('love')" title="Любовь">❤️</button>
    <button class="emoji-tab" data-tab="cute" onclick="switchEmojiTab('cute')" title="Милота и зверушки">🐱</button>
    <button class="emoji-tab" data-tab="gestures" onclick="switchEmojiTab('gestures')" title="Жесты">👍</button>
    <button class="emoji-tab" data-tab="vibes" onclick="switchEmojiTab('vibes')" title="Вайб и разное">✨</button>
    <button class="emoji-tab" data-tab="kaomoji" onclick="switchEmojiTab('kaomoji')" title="Милые каомодзи">(◕‿◕)</button>
  </div>
  <div class="emoji-grid" id="emoji-grid"></div>
</div>

<div id="reply-preview" class="reply-preview" style="display:none">
  <div class="reply-preview-body">
    <div class="reply-preview-sender" id="reply-preview-sender"></div>
    <div class="reply-preview-text" id="reply-preview-text"></div>
  </div>
  <button class="reply-preview-cancel" onclick="cancelReply()" title="Отменить ответ">✕</button>
</div>

<div class="input">

<textarea
id="message"
rows="1"
placeholder="Напишите сообщение..."></textarea>

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
<div id="heart-burst" class="heart-burst"></div>

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