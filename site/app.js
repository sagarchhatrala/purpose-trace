"use strict";

const byId = (id) => document.getElementById(id);
const scenarios = {
  leak: {status: "VIOLATION", state: "violation", symbol: "≠", a: "billing-east", b: "billing-west", input: "Standard support", explanation: "Authorized inputs match. The selected queue changes with the private note."},
  clean: {status: "CONSISTENT", state: "consistent", symbol: "=", a: "billing-east", b: "billing-east", input: "Standard support", explanation: "Both runs choose from the authorized view alone. Changing the private note leaves the route unchanged."},
  mismatch: {status: "INCONCLUSIVE", state: "inconclusive", symbol: "?", a: "billing-east", b: "billing-west", input: "Priority support", explanation: "The service level also changed. These runs cannot isolate the effect of the private note."}
};

document.querySelectorAll("[data-scenario]").forEach((button) => {
  button.addEventListener("click", () => {
    const value = scenarios[button.dataset.scenario];
    document.querySelectorAll("[data-scenario]").forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
    byId("output-a").textContent = value.a;
    byId("output-b").textContent = value.b;
    byId("input-b").textContent = value.input;
    byId("comparison-symbol").textContent = value.symbol;
    byId("lab-status").textContent = value.status;
    byId("lab-explanation").textContent = value.explanation;
    byId("lab-verdict").dataset.state = value.state;
  });
});

byId("copy-command").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(byId("quickstart").textContent);
    byId("copy-status").textContent = "Commands copied. The first campaign intentionally exits 1 when it detects the routing dependency.";
  } catch {
    byId("copy-status").textContent = "Clipboard unavailable. Select and copy the commands from the terminal above.";
  }
});

const knownStatuses = new Set(["CONSISTENT", "NO_DIFFERENCE_DETECTED", "VIOLATION", "INCONCLUSIVE"]);
const text = (value, max = 512) => typeof value === "string" && value.length <= max;
const count = (value) => Number.isInteger(value) && value >= 0 && value <= 20000;
function validateReport(report) {
  if (!report || report.schema_version !== 1 || report.tool !== "purpose-trace" ||
      !knownStatuses.has(report.status) || !count(report.records) || !count(report.groups) ||
      !report.policy || !text(report.policy.name, 80) || !text(report.policy.fingerprint, 64) ||
      !Array.isArray(report.results) || report.results.length !== report.groups || report.groups > 1024 ||
      !Array.isArray(report.limitations) || report.limitations.length > 20 ||
      !report.limitations.every((item) => text(item, 2000))) throw new Error("This is not a supported PurposeTrace version 1 report.");
  for (const group of report.results) {
    if (!group || !knownStatuses.has(group.status) || !text(group.cohort, 160) ||
        !text(group.reason, 160) || !count(group.contexts) || !count(group.samples)) throw new Error("The report contains an invalid comparison group.");
    if (group.witness && (!Array.isArray(group.witness.changed_paths) ||
        group.witness.changed_paths.length > 64 || !group.witness.changed_paths.every((p) => text(p)))) throw new Error("The report contains invalid witness paths.");
    if ("p_value" in group && (typeof group.p_value !== "number" || group.p_value < 0 || group.p_value > 1 ||
        !Number.isFinite(group.max_total_variation) || group.max_total_variation < 0 || group.max_total_variation > 1)) throw new Error("The report contains invalid statistical evidence.");
  }
}

function showReport(report, source) {
  validateReport(report);
  byId("report-status").textContent = report.status;
  byId("report-counts").textContent = `${report.records} records · ${report.groups} groups`;
  byId("report-policy").textContent = `${report.policy.name} / ${report.policy.fingerprint}`;
  const fragment = document.createDocumentFragment();
  for (const group of report.results) {
    const row = document.createElement("article");
    row.className = "group-row";
    const left = document.createElement("div");
    const heading = document.createElement("strong");
    heading.textContent = group.status;
    const cohort = document.createElement("p");
    cohort.textContent = group.cohort;
    left.append(heading, cohort);
    const right = document.createElement("div");
    right.className = "group-detail";
    const counts = document.createElement("p");
    counts.textContent = `${group.contexts} contexts · ${group.samples} samples · ${group.reason.replaceAll("_", " ")}`;
    const detail = document.createElement("p");
    detail.textContent = group.witness ? `Changed: ${group.witness.changed_paths.join(", ")}` :
      "p_value" in group ? `TV ${group.max_total_variation} · p ${group.p_value}` : "No changed field witness in this group.";
    right.append(counts, detail);
    row.append(left, right);
    fragment.append(row);
  }
  byId("report-groups").replaceChildren(fragment);
  byId("report-limitations").replaceChildren(...report.limitations.map((value) => {
    const item = document.createElement("li");
    item.textContent = value;
    return item;
  }));
  byId("report-content").hidden = false;
  byId("report-message").dataset.error = "false";
  byId("report-message").textContent = `${source} Displayed locally; the viewer does not recompute or authenticate the audit.`;
}

function reportError(error) {
  byId("report-content").hidden = true;
  byId("report-message").dataset.error = "true";
  byId("report-message").textContent = error instanceof SyntaxError ? "The selected file is not valid JSON." : error.message;
}

let loadGeneration = 0;
byId("report-file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const generation = ++loadGeneration;
  try {
    if (file.size > 8 * 1024 * 1024) throw new Error("Report exceeds the viewer's 8 MiB limit. Inspect it with the CLI instead.");
    const report = JSON.parse(await file.text());
    if (generation === loadGeneration) showReport(report, "Your report is open.");
  } catch (error) { if (generation === loadGeneration) reportError(error); }
  finally { event.target.value = ""; }
});

byId("sample-report").addEventListener("click", async () => {
  const generation = ++loadGeneration;
  byId("report-message").textContent = "Loading the recorded synthetic campaign…";
  try {
    const response = await fetch("./evidence.json", {signal: AbortSignal.timeout(10000)});
    if (!response.ok) throw new Error("The recorded report could not be loaded. You can still open a local report.");
    const report = await response.json();
    if (generation === loadGeneration) showReport(report, "Recorded synthetic campaign loaded.");
  } catch (error) { if (generation === loadGeneration) reportError(error); }
});
