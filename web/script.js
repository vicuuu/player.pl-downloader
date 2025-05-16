// web/script.js
let saveFolder = "";

function startFetching() {
  const urls = document.getElementById("urls").value.trim().split(/\n+/);
  eel.start_fetching(urls);
}
function showFetching() {
  hideDynamicSections();
  document.getElementById("fetchSection").style.display = "block";
}
function showDownloading() {
  hideDynamicSections();
  document.getElementById("downloadSection").style.display = "block";
  loadCommands();
}
function loadCommands() {
  eel.load_commands()(cmds => {
    document.getElementById("commandsList").value = cmds.join("\n");
  });
}
function chooseFolder() {
  eel.choose_folder()(folder => {
    saveFolder = folder;
    document.getElementById("selectedFolder").textContent = folder;
  });
}
function startDownload() {
  const cmds = document.getElementById("commandsList").value.trim().split(/\n+/);
  const res  = document.getElementById("resolutionSelect").value;
  const aud  = document.getElementById("audioSelect").value;
  eel.start_download(cmds, res, aud, saveFolder);
}

function startLogin() {
  hideDynamicSections();
  eel.login_player();
  document.getElementById("confirmButton").style.display = "inline-block";
}
function confirmCode() {
  eel.confirm_login();
}
function logout() {
  eel.logout_user();
  document.getElementById("loginBtn").style.display = "inline-block";
  document.getElementById("logoutBtn").style.display = "none";
  document.getElementById("userInfo").style.display = "none";
  hideDynamicSections();
}
function update_status(msg) {
  const sb = document.getElementById("status");
  sb.value += msg + "\n";
  sb.scrollTop = sb.scrollHeight;
}
eel.expose(update_status);
function update_progress(val) {
  document.getElementById("progressBar").value = val;
}
eel.expose(update_progress);
function on_login_success(username) {
  document.getElementById("loginBtn").style.display = "none";
  document.getElementById("logoutBtn").style.display = "inline-block";
  const ui = document.getElementById("userInfo");
  ui.textContent = "Zalogowano jako: " + username;
  ui.style.display = "block";
  hideDynamicSections();
}
document.getElementById("commandsList").addEventListener("keydown", function (e) {
  const textarea = this;
  if (e.key === "Delete" || e.key === "Backspace") {
    const selectionStart = textarea.selectionStart;
    const selectionEnd = textarea.selectionEnd;
    if (selectionStart === selectionEnd) return;
    const text = textarea.value;
    const lines = text.split("\n");
    let startLine = text.substring(0, selectionStart).split("\n").length - 1;
    let endLine = text.substring(0, selectionEnd).split("\n").length - 1;
    lines.splice(startLine, endLine - startLine + 1);
    textarea.value = lines.join("\n");
    e.preventDefault(); 
  }
});
eel.expose(on_login_success);
function hideDynamicSections() {
  document.getElementById("confirmButton").style.display = "none";
  document.getElementById("fetchSection").style.display = "none";
  document.getElementById("downloadSection").style.display = "none";
}
window.addEventListener("DOMContentLoaded", () => eel.check_logged_in());


