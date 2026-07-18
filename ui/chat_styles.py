CSS = r"""
*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{
    background:#0f0f13;
    color:#fff;
    font-family:-apple-system,'Segoe UI',sans-serif;
    height:100vh;
    overflow:hidden;
    -webkit-app-region:no-drag;
}

.titlebar{
    height:40px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:0 14px;
    border-bottom:.5px solid rgba(255,255,255,.06);
    -webkit-app-region:drag;
}

.title{
    color:#d4537e;
    font-size:14px;
}

.close{
    width:28px;
    height:28px;
    border:none;
    border-radius:6px;
    background:transparent;
    color:rgba(255,255,255,.4);
    cursor:pointer;
    -webkit-app-region:no-drag;
}

.close:hover{
    background:rgba(255,255,255,.08);
}

.messages{
    height:calc(100vh - 95px);
    overflow-y:auto;
    padding:14px;
}

.messages::-webkit-scrollbar{
    width:6px;
}
.messages::-webkit-scrollbar-track{
    background:transparent;
}
.messages::-webkit-scrollbar-thumb{
    background:rgba(255,255,255,0.12);
    border-radius:10px;
}
.messages::-webkit-scrollbar-thumb:hover{
    background:rgba(255,255,255,0.2);
}

.input{
    height:55px;
    border-top:.5px solid rgba(255,255,255,.06);
    display:flex;
    gap:8px;
    padding:10px;
}

.input input{
    flex:1;
    background:#1a1820;
    border:none;
    outline:none;
    border-radius:10px;
    padding:0 12px;
    color:white;
}

.send{
    width:42px;
    border:none;
    border-radius:10px;
    background:#534ab7;
    color:white;
    cursor:pointer;
}

.emoji-btn{
    background:#1a1820;
    font-size:16px;
}
.emoji-btn:hover{
    background:#232030;
}

.emoji-picker{
    position:fixed;
    left:10px;
    right:10px;
    bottom:65px;
    max-height:180px;
    background:#1a1820;
    border:0.5px solid rgba(255,255,255,0.1);
    border-radius:12px;
    padding:8px;
    box-shadow:0 8px 24px rgba(0,0,0,0.4);
    overflow-y:auto;
    z-index:20;
}

.emoji-grid{
    display:grid;
    grid-template-columns:repeat(8,1fr);
    gap:2px;
}

.emoji-item{
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:19px;
    line-height:1;
    padding:6px 0;
    border-radius:8px;
    cursor:pointer;
    user-select:none;
}
.emoji-item:hover{
    background:rgba(255,255,255,0.08);
}

.message{
    max-width:75%;
    padding:10px 30px 10px 14px;
    border-radius:14px;
    margin-bottom:8px;
    word-break:break-word;
    font-size:13px;
    position:relative;
}

.msg-text{
    white-space:pre-wrap;
    user-select:text;
}

.msg-copy{
    position:absolute;
    top:6px;
    right:6px;
    width:20px;
    height:20px;
    border:none;
    border-radius:5px;
    background:rgba(0,0,0,0.25);
    color:rgba(255,255,255,0.75);
    font-size:11px;
    line-height:1;
    cursor:pointer;
    display:none;
    align-items:center;
    justify-content:center;
    padding:0;
    -webkit-app-region:no-drag;
}
.message:hover .msg-copy{
    display:flex;
}
.msg-copy:hover{
    background:rgba(0,0,0,0.4);
    color:#fff;
}

.sender{
    font-size:11px;
    font-weight:600;
    margin-bottom:3px;
    color:#a89ef0;
}

.message.me{
    margin-left:auto;
    background:#534ab7;
}

.message.partner{
    margin-right:auto;
    background:#1a1820;
}

.time{
    margin-top:4px;
    font-size:10px;
    opacity:.5;
}

.confirm-overlay{
    position:fixed;
    inset:0;
    background:rgba(0,0,0,0.55);
    display:flex;
    align-items:center;
    justify-content:center;
    z-index:50;
}

.confirm-box{
    width:calc(100% - 48px);
    max-width:280px;
    background:#1e1c26;
    border:0.5px solid rgba(255,255,255,0.08);
    border-radius:14px;
    padding:16px;
    box-shadow:0 8px 24px rgba(0,0,0,0.4);
}

.confirm-text{
    font-size:12.5px;
    line-height:1.5;
    color:rgba(255,255,255,0.8);
    margin-bottom:14px;
}

.confirm-btns{
    display:flex;
    gap:8px;
}

.confirm-btn{
    flex:1;
    border:none;
    border-radius:9px;
    padding:8px 0;
    font-size:12px;
    cursor:pointer;
}

.confirm-cancel{
    background:rgba(255,255,255,0.08);
    color:rgba(255,255,255,0.6);
}

.confirm-ok{
    background:#d4537e;
    color:white;
}
"""