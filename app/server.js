const express = require('express');
const path = require('path');
const { runGPT3 } = require('./gpt');
const { PrismaClient } = require('@prisma/client');
require('dotenv').config();

const passwordRequired = false;
const useGPT = true;

const authorizedPasswords = process.env.AUTHORIZED_PASSWORDS.split(',');

const app = express();
const port = parseInt(process.env.PORT || '3000');

const prisma = new PrismaClient();

app.use(express.static(path.join(__dirname, 'dist')));

app.get('/session', async (req, res) => {
  const { id } = await prisma.conversation.create({
    select: {
      id: true
    },
    data: {}
  });

  res.status(200).send(id.toString());
});

app.get('/ask', async (req, res) => {
  const userPassword = req.header('Authorization').replace('Bearer ', '');
  const userMessage = req.query.message;
  const conversation_id = parseInt(req.query.conversation_id);

  if (passwordRequired && !authorizedPasswords.includes(userPassword)) {
    res.status(401).send('Unautorisiert: Falsches Passwort');
    return;
  }
  const { id: question_id } = await prisma.question.create({
    data: {
      conversation_id,
      text: userMessage
    },
    select: {
      id: true
    }
  });

  if (!useGPT) {
    const text = 'Der Hochschulassistent ist ausgeschaltet.';
    const { id: answer_id } = await prisma.answer.create({
      data: {
        conversation_id,
        question_id,
        text
      },
      select: {
        id: true
      }
    });

    res.send(
      JSON.stringify({
        text,
        answer_id
      })
    );
    return;
  }

  try {
    const { text } = await runGPT3(userMessage);
    const { id: answer_id } = await prisma.answer.create({
      data: {
        conversation_id,
        question_id,
        text
      },
      select: {
        id: true
      }
    });

    res.send(
      JSON.stringify({
        text,
        answer_id
      })
    );
  } catch (error) {
    console.error('Fehler beim Ausführen der GPT-Anfrage:', error);
    res.status(500).send('Ein interner Fehler ist aufgetreten.');
    return;
  }
});

app.get('/feedback', async (req, res) => {
  try {
    const is_positive = req.query.approve === '1';
    const answer_id = parseInt(req.query.answer_id);
    const text = req.query.text;

    await prisma.feedback.create({
      data: {
        answer_id,
        is_positive,
        text: text
      }
    });
    res.send('ok');
  } catch (e) {
    res.status(500).send(e.message);
  }
});

app.get('/sql', async (req, res) => {
  try {
    const conversations = await prisma.conversation.findMany({
      select: {
        id: true,
        questions: {
          select: {
            id: true,
            text: true,
            answer: {
              select: {
                id: true,
                text: true,
                feedback: {
                  select: {
                    is_positive: true,
                    text: true
                  }
                }
              }
            }
          },
          orderBy: {
            id: 'asc'
          }
        }
      },
      orderBy: {
        id: 'asc'
      }
    });

    let htmlTable = '';
    let prevConversationId = null;

    conversations.forEach((conversation) => {
      if (prevConversationId !== null) {
        htmlTable += '<tr><td colspan="8" class="table-separator"></td></tr>';
      }
      htmlTable += `
          <tr>
            <td>${conversation.id}</td>
            <td colspan="7" class="conversation-header"><strong>Conversation ${conversation.id}</strong></td>
          </tr>
        `;

      conversation.questions.forEach((question) => {
        if (question.answer) {
          const feedback = question.answer.feedback;
          const feedbackText = feedback ? feedback.text : '';
          const feedbackValue = feedback && feedback.is_positive;
          const backgroundColor = feedbackValue ? '#b4e6b4' : '#ffb3b3';
          const textColor = feedbackValue ? 'black' : 'white';
          htmlTable += `
              <tr style="background-color: ${backgroundColor}; color: ${textColor};">
                <td></td>
                <td>${question.id}</td>
                <td>${question.text}</td>
                <td>${question.answer.id}</td>
                <td>${question.answer.text}</td>
                <td>${feedbackValue}</td>
                <td>${feedbackText}</td>
              </tr>
            `;
        }
      });

      prevConversationId = conversation.id;
    });
    const htmlPage = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Conversation Data</title>
        <style>
          table {
            width: 100%;
            border-collapse: collapse;
            font-family: Arial, sans-serif;
          }
          th, td {
            border: 1px solid #000;
            padding: 8px;
          }
          .table-separator {
            border-top: 2px solid #000;
          }
          .conversation-header {
            background-color: #f2f2f2;
          }
        </style>
      </head>
      <body>
      <h1>Conversation Data</h1>
      <table>
        <tr>
          <th>Conversation ID</th>
          <th>Question ID</th>
          <th>Question Text</th>
          <th>Answer ID</th>
          <th>Answer Text</th>
          <th>Feedback</th>
          <th>Feedback Text</th>
        </tr>
        ${htmlTable}
      </table>
    </body>
      </html>
    `;
    res.send(htmlPage);
  } catch (e) {
    res.status(500).send(e.message);
  }
});

app.get('/set-password-required', (req, res) => {
  res.send({ passwordRequired });
});

app.listen(port, () => {
  console.log(`Server läuft auf Port ${port}`);
});
