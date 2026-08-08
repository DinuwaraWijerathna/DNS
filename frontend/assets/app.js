const api = "/api/v1";
const keyStorageKey = "bdns_demo_private_key";
const toastEl = document.getElementById("toast");

function showToast(message, type = "ok") {
  toastEl.textContent = message;
  toastEl.className = `toast show ${type}`;
  setTimeout(() => { toastEl.className = "toast"; }, 2400);
}

async function request(path, options = {}) {
  const res = await fetch(`${api}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

function formDataToJson(form) { return Object.fromEntries(new FormData(form).entries()); }
function setPre(id, value) { document.getElementById(id).textContent = JSON.stringify(value, null, 2); }
function getStoredPrivateKey() { return localStorage.getItem(keyStorageKey); }
function storePrivateKey(privateKey) { localStorage.setItem(keyStorageKey, privateKey); }
function clearStoredPrivateKey() { localStorage.removeItem(keyStorageKey); }

async function generateKeypair() {
  const pair = await request("/crypto/keypair", { method: "POST", body: "{}" });
  storePrivateKey(pair.private_key);
  setPre("keyInfo", {
    private_key_preview: `${pair.private_key.slice(0, 28)}...`,
    public_key: pair.public_key,
    status: "Stored in browser localStorage for quick demo signing.",
  });
}

async function signPayload({ txType, domain, payload }) {
  const privateKey = getStoredPrivateKey();
  if (!privateKey) throw new Error("No keypair found. Click Generate Keypair first.");
  return request("/crypto/sign", {
    method: "POST",
    body: JSON.stringify({ private_key: privateKey, tx_type: txType, domain, payload }),
  });
}

async function refreshDashboard() {
  const [metrics, report] = await Promise.all([
    request("/resolver/metrics/summary"),
    request("/security/report"),
  ]);
  document.getElementById("mHeight").textContent = report.chain_height;
  document.getElementById("mValid").textContent = report.chain_valid ? "YES" : "NO";
  document.getElementById("mTotal").textContent = metrics.total_queries;
  document.getElementById("mRate").textContent = `${(metrics.cache_hit_rate * 100).toFixed(1)}%`;
}

function bindButton(id, handler) {
  document.getElementById(id).addEventListener("click", async () => {
    try { await handler(); } catch (err) { showToast(err.message, "err"); }
  });
}

function bindForm(id, handler) {
  document.getElementById(id).addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await handler(e.currentTarget); } catch (err) { showToast(err.message, "err"); }
  });
}

bindButton("generateKeyBtn", async () => { await generateKeypair(); showToast("Demo keypair generated"); });
bindButton("clearKeyBtn", async () => { clearStoredPrivateKey(); setPre("keyInfo", { status: "No keypair stored." }); showToast("Stored key cleared"); });
bindButton("refreshAllBtn", async () => { await refreshDashboard(); showToast("Dashboard refreshed"); });
bindButton("loadDomainsBtn", async () => { setPre("domainsResult", await request("/domains")); });

bindButton("signRegisterBtn", async () => {
  const form = document.getElementById("registerForm");
  const data = formDataToJson(form);
  const signed = await signPayload({ txType: "register", domain: data.domain, payload: { ip: data.ip } });
  form.elements.owner_public_key.value = signed.owner_public_key;
  form.elements.signature.value = signed.signature;
  form.elements.domain.value = signed.normalized_domain;
  showToast("Register payload signed");
});

bindButton("signUpdateBtn", async () => {
  const form = document.getElementById("updateForm");
  const data = formDataToJson(form);
  const signed = await signPayload({ txType: "update", domain: data.domain, payload: { ip: data.ip } });
  form.elements.owner_public_key.value = signed.owner_public_key;
  form.elements.signature.value = signed.signature;
  form.elements.domain.value = signed.normalized_domain;
  showToast("Update payload signed");
});

bindButton("signTransferBtn", async () => {
  const form = document.getElementById("transferForm");
  const data = formDataToJson(form);
  const signed = await signPayload({ txType: "transfer", domain: data.domain, payload: { new_owner_public_key: data.new_owner_public_key } });
  form.elements.owner_public_key.value = signed.owner_public_key;
  form.elements.signature.value = signed.signature;
  form.elements.domain.value = signed.normalized_domain;
  showToast("Transfer payload signed");
});

bindForm("registerForm", async (form) => {
  const result = await request("/domains/register", { method: "POST", body: JSON.stringify(formDataToJson(form)) });
  showToast(`Registered block #${result.chain_height}`);
  await refreshDashboard();
});

bindForm("updateForm", async (form) => {
  const payload = formDataToJson(form); const { domain, ...body } = payload;
  const result = await request(`/domains/${domain}/ip`, { method: "PUT", body: JSON.stringify(body) });
  showToast(`Updated block #${result.chain_height}`);
  await refreshDashboard();
});

bindForm("transferForm", async (form) => {
  const payload = formDataToJson(form); const { domain, ...body } = payload;
  const result = await request(`/domains/${domain}/transfer`, { method: "POST", body: JSON.stringify(body) });
  showToast(`Transferred block #${result.chain_height}`);
  await refreshDashboard();
});

bindForm("resolveForm", async (form) => {
  const data = formDataToJson(form);
  setPre("resolveResult", await request(`/resolver/${data.domain}`));
  await refreshDashboard();
});

bindForm("lookupForm", async (form) => {
  const data = formDataToJson(form);
  setPre("lookupResult", await request(`/domains/${data.domain}`));
});

bindForm("historyForm", async (form) => {
  const data = formDataToJson(form);
  setPre("historyResult", await request(`/domains/${data.domain}/history`));
});

bindForm("spoofForm", async (form) => {
  const data = formDataToJson(form);
  setPre("securityResult", await request("/security/simulate/spoofing", { method: "POST", body: JSON.stringify(data) }));
});

bindForm("cacheAttackForm", async (form) => {
  const data = formDataToJson(form);
  setPre("securityResult", await request("/security/simulate/cache-poisoning", { method: "POST", body: JSON.stringify(data) }));
  await refreshDashboard();
});

if (getStoredPrivateKey()) setPre("keyInfo", { status: "Stored keypair is active for auto-sign." });
else setPre("keyInfo", { status: "No keypair stored." });
refreshDashboard().catch(() => showToast("Dashboard metrics unavailable", "err"));
