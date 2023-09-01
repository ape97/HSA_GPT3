const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const chatContainer = document.getElementById('chat');

const passwordInput = document.getElementById('passwordInput');
const userMessage = userInput.value;
const password = passwordInput.value;

let hideBotIndicator = true;
let conversation_id = null;

init();

async function init() {
  await initSession();
  recievePasswordRequired();
  userInput.focus();
  sendButton.addEventListener('click', sendMessage);
  userInput.addEventListener('keypress', async function (event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      await sendMessage();
    }
  });
}

async function initSession() {
  conversation_id = await fetch('/session').then((b) => b.text());
}

async function sendMessage() {
  const message = userInput.value;
  const password = getPasswordInputValue();

  appendMessage(message, true);
  showIndicatorMessage(true);

  const params = new URLSearchParams();
  params.append('message', message);
  params.append('conversation_id', conversation_id);

  const headers = new Headers();
  headers.append('Authorization', `Bearer ${password}`);

  userInput.disabled = true;
  sendButton.disabled = true;

  const { text, answer_id } = await fetch(`/ask?${params.toString()}`, {
    headers
  }).then((response) => response.json());

  showIndicatorMessage(false);
  appendMessage(text, false, answer_id);
  userInput.disabled = false;
  userInput.focus();
  sendButton.disabled = false;

  userInput.value = '';
}

async function feedback(approve, answer_id) {
  const div = document.getElementById(`answer-${answer_id}`);
  [...div.children].forEach((c) => (c.disabled = true));

  const params = new URLSearchParams();
  params.append('approve', approve ? '1' : '0');
  params.append('answer_id', answer_id);
  await fetch(`/feedback?${params.toString()}`);
}

async function submitFeedback() {
  var approve = document.getElementById('approveInput').value === 'positive';
  var answer_id = document.getElementById('answer_idInput').value;
  var feedbackText = document.getElementById('feedbackText').value.toString();

  const div = document.getElementById(`answer-${answer_id}`);
  [...div.children].forEach((c) => (c.disabled = true));

  const params = new URLSearchParams();
  params.append('approve', approve ? '1' : '0');
  params.append('answer_id', answer_id);
  params.append('text', feedbackText);
  await fetch(`/feedback?${params.toString()}`);

  closeFeedbackModal();
}

function openFeedbackModal(approve, answer_id) {
  var approveInput = document.getElementById('approveInput');
  var answerIdInput = document.getElementById('answer_idInput');
  var feedbackModal = document.getElementById('feedbackModal');
  var feedbackTextPlaceholder = document.getElementById(
    'feedbackTextPlaceholder'
  );

  approveInput.value = approve ? 'positive' : 'negative';
  answerIdInput.value = answer_id;

  if (approve) {
    feedbackTextPlaceholder.textContent = 'Positives Feedback geben';
  } else {
    feedbackTextPlaceholder.textContent = 'Negatives Feedback geben';
  }

  feedbackModal.style.display = 'block';
}

function closeFeedbackModal() {
  var feedbackModal = document.getElementById('feedbackModal');
  var feedbackForm = document.getElementById('feedbackForm');
  var feedbackText = document.getElementById('feedbackText');

  feedbackModal.style.display = 'none';
  feedbackForm.reset();
  feedbackText.value = '';
}

window.openFeedbackModal = openFeedbackModal;
window.submitFeedback = submitFeedback;
window.closeFeedbackModal = closeFeedbackModal;

function appendMessage(message, isUser, answer_id) {
  const div = isUser
    ? `<div class="chat-message-right pb-4">
  <div>
      <img src="images/person_50x50.jpg" class="rounded-circle mr-1" alt="Chris Wood" width="40" height="40">
  </div>
  <div class="bubble-right flex-shrink-1 bg-light rounded py-2 px-3 mr-3">
      <div class="fw-bold mb-1">Du</div>
      ${message}
  </div>
</div>`
    : `<div class="chat-message-left pb-4">
  <div>
      <img src="images/bot_50x50.png" class="rounded-circle mr-1" alt="Sharon Lessman" width="40" height="40">
  </div>
  <div class="bubble-left flex-shrink-1 bg-light rounded py-2 px-3 ml-3">
      <div class="fw-bold mb-1" id="answer-${answer_id}">
          Hochschulassistent   
          <button class="thumbs-up" onclick="openFeedbackModal(true, ${answer_id})">👍</button>
          <button class="thumbs-down" onclick="openFeedbackModal(false, ${answer_id})">👎</button>
      </div>
      ${message}
  </div>
</div>`;

  chatContainer.innerHTML += div;
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

const indicator = `<div id="bot-indicator-message" class="chat-message-left pb-4">
<div>
  <img src="images/bot_50x50.png" class="rounded-circle mr-1" alt="Sharon Lessman" width="40" height="40">
</div>
<div class="bubble-left flex-shrink-1 bg-light rounded py-2 px-3 ml-3">
  <div class="fw-bold mb-1">Hochschulassistent</div>
  <div class="typing-indicator">
    <span class="dot"></span>
    <span class="dot"></span>
    <span class="dot"></span>
  </div> 
</div>
</div>
`;

// indicator for bot message
let indicatorMessage;
function showIndicatorMessage(isVisible) {
  hideBotIndicator = !isVisible;

  if (isVisible) {
    chatContainer.innerHTML += indicator;
    chatContainer.scrollTop = chatContainer.scrollHeight;
    indicatorMessage = document.getElementById('bot-indicator-message');
  }

  if (hideBotIndicator) {
    indicatorMessage.remove();
  }
}

function recievePasswordRequired() {
  fetch('/set-password-required')
    .then((response) => response.json())
    .then((data) => {
      if (data.passwordRequired === false) {
        passwordInput.remove();
      }
    });
}

function getPasswordInputValue() {
  if (passwordInput) {
    return passwordInput.value;
  } else {
    return '';
  }
}
