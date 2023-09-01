const { Configuration, OpenAIApi } = require('openai');
const { pathToFileURL } = require('url');
const dotenv = require('dotenv');
dotenv.config();

const model = 'davinci:ft-personal:hsa-final-2023-08-29-16-33-05';

const configuration = new Configuration({
  organization: prozcess.env.ORGANIZATION,
  apiKey: process.env.OPENAI_API_KEY
});
const openai = new OpenAIApi(configuration);

async function runGPT3(prompt) {
  prompt = prompt + '\n\n###\n\n';
  const completion = await openai.createCompletion({
    model: model,
    prompt: prompt,
    max_tokens: 200, // Maximale Anzahl von Tokens
    n: 1, // Anzahl der alternativen Antworten
    temperature: 0.0, // Niedrige Temperatur für konservative und präzise Antworten
    stop: [' END'] // Das Stop-Token angeben, um den Text an der erwarteten Stelle zu beenden
  });

  return completion.data.choices[0];
}

module.exports = { runGPT3 };
