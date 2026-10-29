"use strict";

const questionForm = document.querySelector("#question-form");
const questionInput = document.querySelector("#question");
const askButton = document.querySelector("#ask-button");
const runSQLButton = document.querySelector("#run-sql-button");
const sqlEditor = document.querySelector("#sql-editor");
const sqlSection = document.querySelector("#sql-section");
const resultsSection = document.querySelector("#results-section");
const resultsTable = document.querySelector("#results-table");
const resultMeta = document.querySelector("#result-meta");
const truncatedMessage = document.querySelector("#truncated-message");
const errorMessage = document.querySelector("#error-message");
const historyList = document.querySelector("#history-list");
const historyEmpty = document.querySelector("#history-empty");
const historyCount = document.querySelector("#history-count");
const connectionStatus = document.querySelector("#connection-status");
let activeQuestion = "";

async function requestJSON(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
    });
  } catch {
    throw new Error("Cannot connect to InsightSQL. Check that the app is running.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || "The request could not be completed.");
  }
  return body;
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.classList.remove("hint-message");
  errorMessage.classList.add("error-message");
  errorMessage.hidden = false;
}

function showHint(message) {
  errorMessage.textContent = message;
  errorMessage.classList.remove("error-message");
  errorMessage.classList.add("hint-message");
  errorMessage.hidden = false;
}

function clearError() {
  errorMessage.textContent = "";
  errorMessage.hidden = true;
  errorMessage.classList.remove("hint-message");
  errorMessage.classList.add("error-message");
}

function setLoading(button, loading) {
  button.disabled = loading;
  button.classList.toggle("loading", loading);
}

function displaySQL(sql) {
  sqlEditor.value = sql;
  sqlSection.hidden = false;
  resultsSection.hidden = true;
}

function displayResults(result) {
  resultsTable.replaceChildren();
  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headerRow = document.createElement("tr");
  for (const column of result.columns) {
    const header = document.createElement("th");
    header.scope = "col";
    header.textContent = column;
    headerRow.append(header);
  }
  head.append(headerRow);
  table.append(head);

  const body = document.createElement("tbody");
  for (const row of result.rows) {
    const tableRow = document.createElement("tr");
    for (const value of row) {
      const cell = document.createElement("td");
      cell.textContent = value === null ? "NULL" : String(value);
      tableRow.append(cell);
    }
    body.append(tableRow);
  }
  table.append(body);
  resultsTable.append(table);
  resultMeta.textContent =
    `${result.row_count} row${result.row_count === 1 ? "" : "s"} · ${result.elapsed_ms} ms`;
  truncatedMessage.hidden = !result.truncated;
  truncatedMessage.textContent = result.truncated
    ? "Showing the first rows only. Refine the query to narrow the results."
    : "";
  resultsSection.hidden = false;
}

async function refreshHistory() {
  const data = await requestJSON("/api/history");
  historyList.replaceChildren();
  historyCount.textContent = String(data.items.length);
  historyEmpty.hidden = data.items.length > 0;
  for (const item of data.items) {
    const listItem = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "history-item";
    const question = document.createElement("span");
    question.className = "history-question";
    question.textContent = item.question;
    const details = document.createElement("span");
    details.className = "history-details";
    const date = new Date(item.created_at);
    details.textContent = `${date.toLocaleString()} · ${item.row_count} rows`;
    button.append(question, details);
    button.addEventListener("click", () => {
      activeQuestion = item.question;
      questionInput.value = item.question;
      displaySQL(item.sql);
      clearError();
      resultsSection.hidden = true;
      questionInput.focus();
    });
    listItem.append(button);
    historyList.append(listItem);
  }
}

questionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  const question = questionInput.value.trim();
  if (!question) {
    showError("Enter a question about the employee database.");
    questionInput.focus();
    return;
  }
  activeQuestion = question;
  setLoading(askButton, true);
  sqlSection.hidden = true;
  resultsSection.hidden = true;
  try {
    const result = await requestJSON("/api/ask", {
      method: "POST",
      body: JSON.stringify({ question }),
    });
    displaySQL(result.sql);
    showHint("SQL is ready. Review it above, then select “Run SQL” to view results.");
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(askButton, false);
  }
});

runSQLButton.addEventListener("click", async () => {
  clearError();
  setLoading(runSQLButton, true);
  try {
    const result = await requestJSON("/api/query", {
      method: "POST",
      body: JSON.stringify({ sql: sqlEditor.value, question: activeQuestion }),
    });
    displaySQL(result.sql);
    displayResults(result);
    await refreshHistory();
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(runSQLButton, false);
  }
});

async function initialize() {
  try {
    const health = await requestJSON("/api/health");
    const generationMode = health.sql_generation_mode === "offline"
      ? "offline SQL"
      : "AI SQL";
    connectionStatus.textContent =
      `${health.database} · ${health.tables_available} tables · ${generationMode}`;
    connectionStatus.classList.add("connected");
    await refreshHistory();
  } catch (error) {
    connectionStatus.textContent = "Database unavailable";
    connectionStatus.classList.add("offline");
    showError(error.message);
  }
}

initialize();
