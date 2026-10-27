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
  <div class="title-left">
    <div class="title-icon-badge">💬</div>
    <div class="title-name">Чат</div>
  </div>

  <div class="title-actions">
    <button class="title-btn btn-clear" onclick="clearChat()" title="Очистить историю (только у себя)">🗑</button>
    <button class="title-btn btn-close" onclick="pywebview.api.close_chat()" title="Закрыть">✕</button>
  </div>
</div>

<div id="chat-list" class="messages">

</div>

<div id="emoji-picker" class="emoji-picker" style="display:none">
  <div class="emoji-grid" id="emoji-grid"></div>
  <div class="kaomoji-header">Каомодзи</div>
  <div class="kaomoji-grid" id="kaomoji-grid"></div>
</div>

<div id="reply-preview" class="reply-preview" style="display:none">
  <div class="reply-preview-body">
    <div class="reply-preview-sender" id="reply-preview-sender"></div>
    <div class="reply-preview-text" id="reply-preview-text"></div>
  </div>
  <button class="reply-preview-cancel" onclick="cancelReply()" title="Отменить ответ">✕</button>
</div>

<div class="input-dock">

  <div class="input-wrapper">
    <textarea
      id="message"
      rows="1"
      maxlength="500"
      placeholder="Напишите сообщение..."
      style="height:38px;overflow-y:hidden;"></textarea>
    <div id="char-counter" class="char-counter" style="display:none">0/500</div>
  </div>

  <button
    class="dock-btn emoji-btn"
    id="emoji-toggle-btn"
    onclick="toggleEmojiPicker()"
    title="Смайлики">
    🙂
  </button>

  <button
    class="dock-btn send-btn"
    onclick="sendMessage()"
    title="Отправить">
    ➤
  </button>

</div>

<div id="confirm-overlay" class="confirm-overlay" style="display:none">
  <div class="confirm-box">
    <div class="confirm-text">Очистить историю чата у себя?<br>У партнёра переписка не тронется.</div>
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
