const $ = id => document.getElementById(id);
let selectedFile = null;
let useSavedRecords = false;

function localDateTime() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}
$("recordedAt").value = localDateTime();

$("recordForm").addEventListener("submit", async event => {
  event.preventDefault();
  const data = {
    recorded_at: $("recordedAt").value,
    temperature_f: $("temperature").value,
    sleep_hours: $("sleep").value,
    feeding_count: $("feeding").value,
    wet_diapers: $("diapers").value,
    heart_rate_bpm: $("heartRate").value,
    symptoms: $("symptoms").value,
    notes: $("notes").value
  };
  const response = await fetch("/api/records", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data)
  });
  const result = await response.json();
  $("recordMessage").textContent = response.ok ? result.message : result.error;
  if (response.ok) {
    event.target.reset();
    $("recordedAt").value = localDateTime();
    await loadRecords();
  }
});

async function loadRecords() {
  const response = await fetch("/api/records");
  const data = await response.json();
  $("savedCount").textContent = data.records.length;
  $("historyBody").innerHTML = data.records.length ? data.records.map(r => `
    <tr><td>${escapeText(r.recorded_at)}</td><td>${r.temperature_f.toFixed(1)}</td>
    <td>${r.sleep_hours.toFixed(1)}</td><td>${r.feeding_count}</td>
    <td>${r.wet_diapers}</td></tr>`).join("") :
    '<tr><td colspan="5" class="empty">No entries yet. Add your first record.</td></tr>';
}
$("refreshRecords").addEventListener("click", loadRecords);

$("contamination").addEventListener("input", e => $("contaminationValue").value = Number(e.target.value).toFixed(2));
$("estimators").addEventListener("input", e => $("estimatorsValue").value = e.target.value);
$("fileInput").addEventListener("change", e => {
  selectedFile = e.target.files[0] || null;
  useSavedRecords = false;
  if (selectedFile) $("sampleSelect").value = "";
});
$("sampleSelect").addEventListener("change", () => {
  selectedFile = null;
  $("fileInput").value = "";
  useSavedRecords = false;
});
$("savedDataButton").addEventListener("click", () => {
  selectedFile = null;
  $("fileInput").value = "";
  $("sampleSelect").value = "";
  useSavedRecords = true;
  $("modelMessage").textContent = "Saved daily records selected. At least five records are needed.";
});
$("runButton").addEventListener("click", runDetection);

async function loadExamples() {
  const response = await fetch("/api/examples");
  const data = await response.json();
  $("sampleSelect").innerHTML = '<option value="">Choose example dataset</option>' +
    data.datasets.map(name => `<option value="${escapeText(name)}">${escapeText(name)}</option>`).join("");
}

async function runDetection() {
  const sample = $("sampleSelect").value;
  if (!selectedFile && !sample && !useSavedRecords) {
    $("modelMessage").textContent = "Upload a CSV, select an example or use saved daily entries.";
    return;
  }
  const form = new FormData();
  if (selectedFile) form.append("file", selectedFile);
  if (sample) form.append("sample", sample);
  if (useSavedRecords) form.append("source", "records");
  form.append("contamination", $("contamination").value);
  form.append("n_estimators", $("estimators").value);
  $("runButton").disabled = true;
  $("modelMessage").textContent = "Analysing observations…";
  try {
    const response = await fetch("/api/detect", {method: "POST", body: form});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Detection failed.");
    renderResults(data);
    $("modelMessage").textContent = "Analysis complete. Adjust parameters and run again to compare results.";
  } catch (error) {
    $("modelMessage").textContent = error.message;
  } finally {
    $("runButton").disabled = false;
  }
}

function renderResults(data) {
  $("totalCount").textContent = data.rows;
  $("normalCount").textContent = data.normal_count;
  $("anomalyCount").textContent = data.anomaly_count;
  $("anomalyRate").textContent = data.anomaly_percentage + "%";
  $("chartCaption").textContent = `${data.dataset} · ${data.columns[0]} vs ${data.columns[1]}`;
  const normal = data.results.filter(r => r.label === "Normal");
  const anomalies = data.results.filter(r => r.label === "Anomaly");
  const makeTrace = (items, name, color, symbol) => ({
    x: items.map(r => r.x), y: items.map(r => r.y),
    text: items.map(r => `${r.label}<br>Score: ${r.score}`),
    mode: "markers", type: "scatter", name,
    marker: {color, size: 9, opacity: .82, symbol}
  });
  Plotly.newPlot("chart", [
    makeTrace(normal, "Normal", "#8fcfbd", "circle"),
    makeTrace(anomalies, "Anomaly", "#e995b5", "diamond")
  ], {
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: {color: "#85819c", family: "Manrope"},
    margin: {l: 55, r: 18, t: 15, b: 55},
    xaxis: {title: data.columns[0], gridcolor: "#eee8f5"},
    yaxis: {title: data.columns[1], gridcolor: "#eee8f5"},
    legend: {orientation: "h", y: -0.23}
  }, {responsive: true, displaylogo: false});
  $("resultBody").innerHTML = data.results.slice(0, 100).map((r, i) => `
    <tr><td>${i + 1}</td><td>${r.x.toFixed(3)}</td><td>${r.y.toFixed(3)}</td>
    <td><span class="label ${r.label.toLowerCase()}">${r.label} (${r.label_code})</span></td>
    <td>${r.score.toFixed(6)}</td></tr>`).join("");
}
function escapeText(value) {
  return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
loadExamples().catch(() => $("sampleSelect").innerHTML = '<option value="">Examples unavailable</option>');
loadRecords().catch(() => {});
