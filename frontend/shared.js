const API = "http://localhost:8000";

// Maps internal page ids -> actual HTML filenames
const PAGE_FILES = {
  overview: "/customer/index.html",
  customerDashboardOverview: "/customer/dashboard-customer.html",
  adminDashboardOverview: "/admin/dashboard-admin.html",
  pricing: "/customer/pricing.html",
  getStarted: "/customer/get-started.html",
  login: "/customer/login.html",
  registerUser: "/customer/register.html",
  myProfile: "/customer/profile.html",
  domainRegister: "/customer/domain-register.html",
  myDomains: "/customer/my-domains.html",
  updateDomain: "/customer/update-domain.html",
  transferDomain: "/customer/transfer-domain.html",
  domainDetails: "/admin/domain-details.html",
  auditHistory: "/admin/audit-history.html",
  systemMetrics: "/admin/system-metrics.html",
  resolve: "/customer/resolve.html",
  domains: "/customer/domain-registry.html",
  blockchain: "/customer/blockchain-ledger.html",
  security: "/customer/security-simulation.html",
  monitoring: "/customer/security-monitoring.html",
  adminUsers: "/admin/admin-users.html",
  domainModeration: "/admin/admin-domain-moderation.html",
  adminAuditTrail: "/admin/admin-audit-trail.html"
};

// Pages where footer should appear
const FOOTER_PAGES = ["overview", "customerDashboardOverview", "adminDashboardOverview"];

// Pages that require authentication
const PROTECTED_PAGES = [
  "domainRegister","myDomains","resolve","domains",
  "blockchain","monitoring","security",
  "updateDomain","transferDomain","domainDetails","auditHistory","systemMetrics",
  "customerDashboardOverview","adminDashboardOverview",
  "adminUsers","domainModeration","adminAuditTrail",
  "myProfile"
];

// Pages only an admin account is allowed to open (checked in guardProtectedPage)
const ADMIN_ONLY_PAGES = ["adminDashboardOverview","adminUsers","domainModeration","adminAuditTrail","domainDetails","auditHistory","systemMetrics"];

// Pages that belong to the customer workflow only - an admin account is redirected away from these
const CUSTOMER_ONLY_PAGES = ["customerDashboardOverview","domainRegister","myDomains","updateDomain","transferDomain","resolve","domains","blockchain","monitoring","security"];

// ─── SESSION ───────────────────────────────────────────────
function saveSession(user){ localStorage.setItem("bdns_user", JSON.stringify(user)); }
function getSession(){ return JSON.parse(localStorage.getItem("bdns_user")); }
function clearSession(){ localStorage.removeItem("bdns_user"); }

// ─── UI STATE ──────────────────────────────────────────────
function applySession(){
  const user = getSession();
  const navPublic = document.getElementById("navPublic");
  const navAuth   = document.getElementById("navAuth");
  const userPill  = document.getElementById("currentUser");

  if(user){
    if(navPublic) navPublic.style.display = "none";
    if(navAuth)   navAuth.style.display   = "flex";
    if(userPill) userPill.textContent = user.role === "admin" ? "Administrator" : "Customer";
    document.body.classList.remove("public-mode");
    document.body.classList.add("dashboard-mode");
  } else {
    if(navPublic) navPublic.style.display = "flex";
    if(navAuth)   navAuth.style.display   = "none";
    document.body.classList.remove("dashboard-mode");
    document.body.classList.add("public-mode");
  }
}

function updateFooter(pageId){
  const footer = document.getElementById("siteFooter");
  const footerCta = document.getElementById("footerCta");
  if(!footer) return;
  footer.style.display = FOOTER_PAGES.includes(pageId) ? "block" : "none";
  if(footerCta) footerCta.style.display = pageId === "overview" ? "block" : "none";
}

// ─── NAVIGATION (real multi-page navigation) ───────────────
function navigateTo(id){
  const file = PAGE_FILES[id];
  if(!file){ console.warn("Unknown page id:", id); return; }
  window.location.href = file;
}

function requireAuthThenGo(id){
  if(!getSession()){
    notify("Please login first.");
    navigateTo("login");
    return;
  }
  navigateTo(id);
}

// Kept for compatibility with inline onclick="showPage('x')" left in markup
function showPage(id){ navigateTo(id); }

function highlightActiveNav(pageId){
  document.querySelectorAll(".nav button, .nav a").forEach(b => b.classList.remove("active"));
  const active = document.querySelector(`.nav [data-page="${pageId}"]`);
  if(active) active.classList.add("active");
}

function guardProtectedPage(pageId){
  const user = getSession();
  if(PROTECTED_PAGES.includes(pageId) && !user){
    notify("Please login first.");
    window.location.href = PAGE_FILES["login"];
    return false;
  }
  if(ADMIN_ONLY_PAGES.includes(pageId) && user && user.role !== "admin"){
    notify("Admin access only.");
    window.location.href = PAGE_FILES["customerDashboardOverview"];
    return false;
  }
  if(CUSTOMER_ONLY_PAGES.includes(pageId) && user && user.role === "admin"){
    notify("This page belongs to customer accounts only.");
    window.location.href = PAGE_FILES["adminDashboardOverview"];
    return false;
  }
  return true;
}

// ─── SIDEBAR RENDERING ─────────────────────────────────────
function renderSidebar(role){
  const nav = document.getElementById("sidebarNav");
  if(!nav) return;

  if(role === "admin"){
    nav.innerHTML = `
      <button data-page="adminDashboardOverview" onclick="navigateTo('adminDashboardOverview')">Overview</button>
      <button data-page="domainDetails"          onclick="navigateTo('domainDetails')">Domain Details</button>
      <button data-page="auditHistory"           onclick="navigateTo('auditHistory')">Audit History</button>
      <button data-page="systemMetrics"          onclick="navigateTo('systemMetrics')">System Metrics</button>
      <div class="sidebar-title" style="margin-top:18px">Admin Tools</div>
      <button data-page="adminUsers"             onclick="navigateTo('adminUsers')">User Management</button>
      <button data-page="domainModeration"       onclick="navigateTo('domainModeration')">Domain Moderation</button>
      <button data-page="adminAuditTrail"        onclick="navigateTo('adminAuditTrail')">Global Audit Trail</button>
    `;
  } else {
    nav.innerHTML = `
      <button data-page="customerDashboardOverview" onclick="navigateTo('customerDashboardOverview')">Overview</button>
      <button data-page="domainRegister"            onclick="navigateTo('domainRegister')">Register Domain</button>
      <button data-page="myDomains"                 onclick="navigateTo('myDomains')">My Domains</button>
      <button data-page="updateDomain"              onclick="navigateTo('updateDomain')">Update IP</button>
      <button data-page="transferDomain"            onclick="navigateTo('transferDomain')">Transfer Ownership</button>
      <button data-page="resolve"                   onclick="navigateTo('resolve')">Resolve Domain</button>
      <button data-page="domains"                   onclick="navigateTo('domains')">Domain Registry</button>
      <button data-page="blockchain"                onclick="navigateTo('blockchain')">Blockchain Ledger</button>
      <button data-page="monitoring"                onclick="navigateTo('monitoring')">Security Monitoring</button>
      <button data-page="security"                  onclick="navigateTo('security')">Security Simulation</button>
    `;
  }
}

// ─── AUTH ──────────────────────────────────────────────────
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;

function setButtonLoading(btn, isLoading, loadingText, normalText){
  if(!btn) return;
  btn.disabled = isLoading;
  btn.textContent = isLoading ? loadingText : normalText;
}

async function demoLogin(){
  const btn = document.getElementById("loginBtn");
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;
  const selectedRole = document.getElementById("loginRole").value;

  if(!email || !password){
    notify("Please enter your email and password.");
    return;
  }
  if(!EMAIL_REGEX.test(email)){
    notify("Please enter a valid email address.");
    return;
  }

  setButtonLoading(btn, true, "Logging in...", "Login");
  try{
    const data = await apiPost("/api/v1/auth/login", { email, password });

    if(data.error){
      notify(data.error);
      return;
    }

    const user = {
      user_id: data.user.user_id,
      email: data.user.email,
      name: data.user.full_name,
      role: data.user.role,
      token: data.token
    };

    if(user.role !== selectedRole){
      notify("Selected role does not match this account.");
      return;
    }

    saveSession(user);
    applySession();
    renderSidebar(user.role);

    if(user.role === "admin"){
      notify("Admin access granted.");
      navigateTo("adminDashboardOverview");
    } else {
      notify("Customer access granted.");
      navigateTo("customerDashboardOverview");
    }

  }catch(e){
    notify("Login failed. Check backend connection.");
  }finally{
    setButtonLoading(btn, false, "Logging in...", "Login");
  }
}

// ─── REGISTER: customer / admin role tabs ─────────────────
function setRegisterRole(role){
  const tabCustomer = document.getElementById("tabCustomer");
  const tabAdmin = document.getElementById("tabAdmin");
  const panelCustomer = document.getElementById("panelCustomer");
  const panelAdmin = document.getElementById("panelAdmin");
  const authGlass = document.getElementById("authGlass");
  if(!tabCustomer || !tabAdmin || !panelCustomer || !panelAdmin) return;

  const isAdmin = role === "admin";
  tabCustomer.classList.toggle("active", !isAdmin);
  tabAdmin.classList.toggle("active", isAdmin);
  panelCustomer.classList.toggle("active", !isAdmin);
  panelAdmin.classList.toggle("active", isAdmin);
  if(authGlass) authGlass.classList.toggle("admin-theme", isAdmin);
}

async function demoRegisterUser(role){
  role = role === "admin" ? "admin" : "customer";
  const prefix = role === "admin" ? "admin" : "customer";
  const btn = document.getElementById(role === "admin" ? "registerAdminBtn" : "registerBtn");
  const normalText = role === "admin" ? "Create Admin Account" : "Create Customer Account";

  const name     = document.getElementById(prefix + "Name").value.trim();
  const email    = document.getElementById(prefix + "Email").value.trim();
  const password = document.getElementById(prefix + "Password").value;
  const confirm  = document.getElementById(prefix + "ConfirmPassword").value;
  const country  = document.getElementById(prefix + "Country").value.trim();
  const contact  = document.getElementById(prefix + "Contact").value.trim();
  const dob      = role === "customer" ? document.getElementById("customerDob").value : null;
  const adminCode = role === "admin" ? document.getElementById("adminCode").value.trim() : null;

  if(!name || !email || !password || !confirm){
    notify("Please fill in name, email, and password.");
    return;
  }
  if(!country){
    notify("Please enter your country.");
    return;
  }
  if(!EMAIL_REGEX.test(email)){
    notify("Please enter a valid email address.");
    return;
  }
  if(password.length < MIN_PASSWORD_LENGTH){
    notify(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
    return;
  }
  if(password !== confirm){
    notify("Passwords do not match.");
    return;
  }
  if(role === "admin" && !adminCode){
    notify("Please enter the admin invite code.");
    return;
  }

  setButtonLoading(btn, true, "Creating account...", normalText);
  try{
    const data = await apiPost("/api/v1/auth/register", {
      full_name: name, email, password,
      country, contact_number: contact, date_of_birth: dob || null,
      role, admin_code: adminCode
    });

    if(data.error){
      notify(data.error);
      return;
    }

    notify(role === "admin" ? "Admin account created successfully. Please login." : "Account created successfully. Please login.");
    navigateTo("login");

  }catch(e){
    notify("Registration failed. Check backend connection.");
  }finally{
    setButtonLoading(btn, false, "Creating account...", normalText);
  }
}

function logout(){
  clearSession();
  applySession();
  notify("Logged out successfully.");
  navigateTo("overview");
}

function showProfile(){
  const user = getSession();
  if(user) navigateTo("myProfile");
  else navigateTo("registerUser");
}

// ─── CUSTOMER / ADMIN PROFILE PAGE ─────────────────────────
async function loadProfile(){
  const user = getSession();
  if(!user){ notify("Please login first."); navigateTo("login"); return; }

  try{
    const data = await apiGet("/api/v1/users/me");
    if(data.detail || data.error){ notify(data.detail || data.error); return; }

    const nameEl = document.getElementById("profileFullName");
    const emailEl = document.getElementById("profileEmail");
    const countryEl = document.getElementById("profileCountry");
    const contactEl = document.getElementById("profileContact");
    const dobEl = document.getElementById("profileDob");
    const roleEl = document.getElementById("profileRole");

    if(nameEl) nameEl.value = data.full_name || "";
    if(emailEl) emailEl.value = data.email || "";
    if(countryEl) countryEl.value = data.country || "";
    if(contactEl) contactEl.value = data.contact_number || "";
    if(dobEl) dobEl.value = data.date_of_birth || "";
    if(roleEl) roleEl.value = data.role === "admin" ? "Administrator" : "Customer";
  }catch(e){
    notify("Could not load your profile. Check backend connection.");
  }
}

async function saveProfile(){
  const btn = document.getElementById("saveProfileBtn");
  const fullName = document.getElementById("profileFullName").value.trim();
  const country = document.getElementById("profileCountry").value.trim();
  const contact = document.getElementById("profileContact").value.trim();
  const dob = document.getElementById("profileDob").value;

  if(!fullName){
    notify("Full name is required.");
    return;
  }

  setButtonLoading(btn, true, "Saving...", "Save Changes");
  try{
    const data = await apiPut("/api/v1/users/me", {
      full_name: fullName,
      country: country || null,
      contact_number: contact || null,
      date_of_birth: dob || null
    });

    if(data.detail || data.error){
      notify(data.detail || data.error);
      return;
    }

    // Keep the locally cached session name in sync with the saved profile.
    const user = getSession();
    if(user){
      user.name = data.full_name;
      saveSession(user);
    }

    notify("Profile updated successfully.");
  }catch(e){
    notify("Could not save your profile. Check backend connection.");
  }finally{
    setButtonLoading(btn, false, "Saving...", "Save Changes");
  }
}

async function changePassword(){
  const btn = document.getElementById("changePasswordBtn");
  const current = document.getElementById("currentPassword").value;
  const next = document.getElementById("newPassword").value;
  const confirm = document.getElementById("confirmNewPassword").value;

  if(!current || !next || !confirm){
    notify("Please fill in all password fields.");
    return;
  }
  if(next.length < MIN_PASSWORD_LENGTH){
    notify(`New password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
    return;
  }
  if(next !== confirm){
    notify("New password and confirmation do not match.");
    return;
  }

  setButtonLoading(btn, true, "Updating...", "Update Password");
  try{
    const data = await apiPut("/api/v1/users/me/password", {
      current_password: current,
      new_password: next
    });

    if(data.detail || data.error){
      notify(data.detail || data.error);
      return;
    }

    notify("Password updated successfully.");
    document.getElementById("currentPassword").value = "";
    document.getElementById("newPassword").value = "";
    document.getElementById("confirmNewPassword").value = "";
  }catch(e){
    notify("Could not update your password. Check backend connection.");
  }finally{
    setButtonLoading(btn, false, "Updating...", "Update Password");
  }
}

// ─── AUDIT LOGS ────────────────────────────────────────────
let auditLogs = JSON.parse(localStorage.getItem("bdns_audit_logs") || "[]");

function addLog(type, details){
  auditLogs.push({ time: new Date().toISOString(), type, details });
  localStorage.setItem("bdns_audit_logs", JSON.stringify(auditLogs));
  if(document.getElementById("alertFeed")) refreshMonitoring();
}

// ─── TOAST ─────────────────────────────────────────────────
function notify(message){
  const area = document.getElementById("toastArea");
  if(!area) return;
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  area.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// ─── UTILS ─────────────────────────────────────────────────
function show(id, data){ const el = document.getElementById(id); if(el) el.textContent = JSON.stringify(data, null, 2); }
function hex(buffer){ return [...new Uint8Array(buffer)].map(b => b.toString(16).padStart(2,"0")).join(""); }
function buildMessage(domain, ip){ return `{"domain":"${domain}","payload":{"ip":"${ip}"},"tx_type":"register"}`; }
function shortText(t){ if(!t || t==="-") return "-"; return t.substring(0,22)+"..."; }

async function signData(domain, ip){
  const key    = await crypto.subtle.generateKey({name:"ECDSA",namedCurve:"P-256"},true,["sign","verify"]);
  const pub    = await crypto.subtle.exportKey("raw", key.publicKey);
  const pubHex = hex(pub).substring(2);
  const msg    = new TextEncoder().encode(buildMessage(domain, ip));
  const sig    = await crypto.subtle.sign({name:"ECDSA",hash:"SHA-256"}, key.privateKey, msg);
  return { publicKey: pubHex, signature: hex(sig) };
}

// Attaches the logged-in user's JWT (if any) so admin-only endpoints can verify the caller.
function authHeaders(){
  const user = getSession();
  return user && user.token ? { "Authorization": "Bearer " + user.token } : {};
}

async function apiGet(path){
  const r = await fetch(API+path, { headers: { ...authHeaders() } });
  return await r.json();
}
async function apiPost(path, body){
  const r = await fetch(API+path, {
    method: "POST",
    headers: {"Content-Type":"application/json", ...authHeaders()},
    body: JSON.stringify(body)
  });
  return await r.json();
}
async function apiPut(path, body){
  const r = await fetch(API+path, {
    method: "PUT",
    headers: {"Content-Type":"application/json", ...authHeaders()},
    body: JSON.stringify(body)
  });
  return await r.json();
}

// ─── DOMAIN ACTIONS ────────────────────────────────────────
async function globalDomainSearch(){
  const domain = document.getElementById("globalSearchDomain").value.trim().toLowerCase();
  if(!domain){
    renderAvailabilityResult("globalSearchOutput", { status:"ERROR", reason:"EMPTY_DOMAIN", domain:"-", message:"Please enter a domain name." });
    return;
  }
  try{
    const data = await apiGet("/api/v1/domains/" + encodeURIComponent(domain) + "/availability");
    renderAvailabilityResult("globalSearchOutput", data);
    if(data.status === "BLOCKED"){ notify(data.message); addLog("GLOBAL_SEARCH_BLOCKED", data); }
    else { notify("Domain is available."); addLog("GLOBAL_SEARCH_AVAILABLE", data); }
  }catch(e){
    renderAvailabilityResult("globalSearchOutput", { status:"ERROR", reason:"CHECK_FAILED", domain, message:"Could not check domain availability." });
  }
}

async function checkDomainAvailability(){
  const domain = document.getElementById("domain").value.trim().toLowerCase();
  if(!domain){ show("availabilityOutput", { status:"ERROR", message:"Please enter a domain name first." }); return; }
  try{
    const data = await apiGet("/api/v1/domains/" + encodeURIComponent(domain) + "/availability");
    renderAvailabilityResult("availabilityOutput", data);
    notify(data.status === "BLOCKED" ? data.message : "Domain is available.");
  } catch(e){
    show("availabilityOutput", { status:"ERROR", message:"Could not check domain availability.", detail:e.message });
  }
}

async function registerDomain(){
  const domain = document.getElementById("domain").value.trim().toLowerCase();
  const ip     = document.getElementById("ip").value.trim();
  if(!domain||!ip){ show("registerOutput",{error:"Please enter both domain and IP address."}); return; }
  try{
    const existing = await apiGet("/api/v1/domains/"+encodeURIComponent(domain));
    if(existing && existing.domain){
      show("registerOutput",{error:"Registration blocked",message:"Domain already exists. Please choose another domain.",existing_ip:existing.ip});
      return;
    }
  } catch(e){}
  try{
    const signed  = await signData(domain, ip);
    const payload = { domain, ip, owner_public_key: signed.publicKey, signature: signed.signature };
    const data    = await apiPost("/api/v1/domains/register", payload);
    show("registerOutput",{message:"Domain registered successfully with valid ECDSA signature.",transaction:data});
    notify("Secure blockchain DNS registration completed.");
    addLog("DOMAIN_REGISTERED",{domain,ip});
    saveOwnedDomain({domain, ip, owner_public_key: signed.publicKey});
    loadMyDomains();
    await loadDomains();
    await loadChain();
  } catch(e){ show("registerOutput",{error:"Registration failed.",detail:e.message}); }
}

async function resolveDomain(){
  const domain = document.getElementById("resolveDomain").value.trim().toLowerCase();
  if(!domain){ show("resolveOutput",{error:"Please enter a domain name."}); return; }
  try{
    const data = await apiGet("/api/v1/domains/"+encodeURIComponent(domain));
    show("resolveOutput",{message:"Domain resolved successfully using blockchain verified record.",result:data});
    notify("Domain resolved successfully.");
    addLog("DOMAIN_RESOLVED",{domain,result:data});
  } catch(e){ show("resolveOutput",{error:"Resolve failed.",detail:e.message}); }
}

async function loadDomains(){
  try{
    const data    = await apiGet("/api/v1/domains");
    const domains = Array.isArray(data) ? data : (data.domains||[]);
    const el = document.getElementById("domainCount");
    if(el) el.textContent = domains.length;
    const table = document.getElementById("domainTable");
    if(!table) return;
    table.innerHTML = "";
    if(domains.length===0){ table.innerHTML=`<tr><td colspan="4">No registered domains found.</td></tr>`; return; }
    domains.forEach(item=>{
      const frozen = item.status === "frozen";
      const badge = frozen ? `<span class="badge danger">Frozen</span>` : `<span class="badge ok">Verified</span>`;
      table.innerHTML+=`<tr><td>${item.domain||"-"}</td><td>${item.ip||item.ip_address||"-"}</td><td>${shortText(item.owner_public_key||"-")}</td><td>${badge}</td></tr>`;
    });
  } catch(e){ const table = document.getElementById("domainTable"); if(table) table.innerHTML=`<tr><td colspan="4">Could not load domains.</td></tr>`; }
}

async function loadChain(){
  try{
    const data  = await apiGet("/api/v1/chain");
    show("chainOutput", data);
    const chain = data.chain||data.blocks||data||[];
    if(Array.isArray(chain)){
      const el = document.getElementById("chainHeight");
      if(el) el.textContent = chain.length;
      if(document.getElementById("chainVisual")) renderChain(chain);
      if(document.getElementById("chainGraph")) renderChainGraph(chain);
      if(document.getElementById("liveChainAnimation")) renderLiveChainAnimation(chain);
    }
  } catch(e){ show("chainOutput",{error:"Could not load blockchain.",detail:e.message}); }
}

function renderChain(chain){
  const c = document.getElementById("chainVisual");
  if(!c) return;
  c.innerHTML = "";
  chain.slice(-6).reverse().forEach(block=>{
    c.innerHTML+=`<div class="block-card"><strong>Block #${block.index??"-"}</strong><br>Hash: ${shortText(block.hash||"-")}<br>Previous: ${shortText(block.previous_hash||block.previousHash||"-")}<br>Validator: ${block.validator||"-"}<br>Transactions: ${(block.transactions||[]).length}</div>`;
  });
}

function renderChainGraph(chain){
  const graph = document.getElementById("chainGraph");
  if(!graph) return;
  graph.innerHTML = "";
  if(!Array.isArray(chain)||chain.length===0){ graph.textContent="No blockchain data available."; return; }
  chain.forEach((block,index)=>{
    graph.innerHTML+=`<span class="graph-node">Block ${block.index??index}</span>`;
    if(index < chain.length-1) graph.innerHTML+=`<span class="graph-arrow">→</span>`;
  });
}

function renderLiveChainAnimation(chain){
  const live = document.getElementById("liveChainAnimation");
  if(!live) return;
  live.innerHTML = "";
  if(!Array.isArray(chain)||chain.length===0){ live.textContent="No blockchain data available."; return; }
  chain.slice(-6).forEach((block,index)=>{
    live.innerHTML+=`<div class="live-block"><small>BLOCK</small><h3>#${block.index??index}</h3><p>Tx: ${(block.transactions||[]).length}</p><small>${shortText(block.hash||"-")}</small></div>`;
    if(index < chain.slice(-6).length-1) live.innerHTML+=`<div class="live-link">➜</div>`;
  });
}

async function simulateAttack(){
  const domain = document.getElementById("attackDomain").value.trim().toLowerCase();
  const fakeIp = document.getElementById("attackIp").value.trim();
  if(!domain||!fakeIp){ show("attackOutput",{error:"Please enter target domain and fake IP."}); return; }
  try{
    const real = await apiGet("/api/v1/domains/"+encodeURIComponent(domain));
    if(real.ip && real.ip!==fakeIp){
      show("attackOutput",{attack_type:"DNS_SPOOFING",target_domain:domain,fake_ip:fakeIp,verified_blockchain_ip:real.ip,result:"BLOCKED",explanation:"Fake DNS data rejected because it does not match the blockchain-verified record."});
      notify("Malicious DNS spoofing attempt blocked.");
      addLog("DNS_SPOOFING_BLOCKED",{domain,fakeIp,real_ip:real.ip});
    } else {
      show("attackOutput",{attack_type:"DNS_SPOOFING",result:"NO DIFFERENCE DETECTED"});
    }
  } catch(e){ show("attackOutput",{attack_type:"DNS_SPOOFING",result:"FAILED",detail:e.message}); }
}

// ─── MY DOMAINS ────────────────────────────────────────────
function getOwnedDomains(){ return JSON.parse(localStorage.getItem("bdns_owned_domains")||"[]"); }

function saveOwnedDomain(domainData){
  const user = getSession();
  if(!user) return;
  const owned = getOwnedDomains();
  const exists = owned.some(item => item.domain===domainData.domain && item.user_email===user.email);
  if(!exists){
    owned.push({ user_email:user.email, owner_name:user.name||user.email, domain:domainData.domain, ip:domainData.ip, owner_public_key:domainData.owner_public_key, registered_at:new Date().toISOString() });
    localStorage.setItem("bdns_owned_domains", JSON.stringify(owned));
  }
}

function loadMyDomains(){
  const user = getSession();
  if(!user){ notify("Please login first."); navigateTo("login"); return; }
  const owned = getOwnedDomains().filter(item => item.user_email===user.email);
  const countEl = document.getElementById("myDomainCount");
  if(countEl) countEl.textContent = owned.length;
  const table = document.getElementById("myDomainTable");
  if(!table) return;
  table.innerHTML = "";
  if(owned.length===0){ table.innerHTML=`<tr><td colspan="4">No domains registered by this customer yet.</td></tr>`; show("myDomainOutput",{message:"No domains found for current user.",user:user.email}); return; }
  owned.forEach(item=>{
    table.innerHTML+=`<tr><td>${item.domain}</td><td>${item.ip}</td><td>${item.owner_name}</td><td><button class="primary" onclick="quickResolve('${item.domain}')">Resolve</button> <button class="primary danger" onclick="quickAttackTest('${item.domain}')">Attack Test</button></td></tr>`;
  });
  show("myDomainOutput",{message:"My domains loaded successfully.",user:user.email,count:owned.length});
}

async function quickResolve(domain){
  try{
    const data = await apiGet("/api/v1/domains/"+encodeURIComponent(domain));
    show("myDomainOutput",{action:"QUICK_RESOLVE",message:"Domain resolved successfully.",result:data});
    notify("Quick resolve completed.");
    addLog("MY_DOMAIN_QUICK_RESOLVE",{domain,result:data});
  } catch(e){ show("myDomainOutput",{action:"QUICK_RESOLVE",error:"Resolve failed.",detail:e.message}); }
}

async function quickAttackTest(domain){
  try{
    const real   = await apiGet("/api/v1/domains/"+encodeURIComponent(domain));
    const fakeIp = "6.6.6.6";
    if(real.ip && real.ip!==fakeIp){
      show("myDomainOutput",{action:"QUICK_ATTACK_TEST",attack_type:"DNS_SPOOFING",domain,fake_ip:fakeIp,blockchain_verified_ip:real.ip,result:"BLOCKED",explanation:"Fake DNS response rejected because it does not match blockchain record."});
      notify("Quick attack test blocked.");
      addLog("MY_DOMAIN_ATTACK_TEST_BLOCKED",{domain,fakeIp,real_ip:real.ip});
    } else {
      show("myDomainOutput",{action:"QUICK_ATTACK_TEST",result:"NO DIFFERENCE DETECTED"});
    }
  } catch(e){ show("myDomainOutput",{action:"QUICK_ATTACK_TEST",error:"Attack test failed.",detail:e.message}); }
}

// ─── MONITORING ────────────────────────────────────────────
function getEventCount(type){ return auditLogs.filter(l => l.type===type).length; }

function getThreatLevel(){
  const blocked = getEventCount("DNS_SPOOFING_BLOCKED");
  if(blocked>=5) return "HIGH";
  if(blocked>=2) return "MEDIUM";
  return "LOW";
}

function refreshMonitoring(){
  const total        = auditLogs.length;
  const blocked      = getEventCount("DNS_SPOOFING_BLOCKED");
  const domainEvents = auditLogs.filter(l => ["DOMAIN_REGISTERED","DOMAIN_RESOLVED","GLOBAL_SEARCH_EXISTS","GLOBAL_SEARCH_AVAILABLE"].includes(l.type)).length;

  const te = document.getElementById("monitorTotalEvents");
  const ba = document.getElementById("monitorBlockedAttacks");
  const de = document.getElementById("monitorDomainEvents");
  const tl = document.getElementById("monitorThreatLevel");

  if(te) te.textContent = total;
  if(ba) ba.textContent = blocked;
  if(de) de.textContent = domainEvents;
  if(tl) tl.textContent = getThreatLevel();

  renderAlertFeed();
}

function renderAlertFeed(){
  const feed = document.getElementById("alertFeed");
  if(!feed) return;
  feed.innerHTML = "";
  if(auditLogs.length===0){
    feed.innerHTML=`<div class="alert-item low">No security alerts yet.<div class="alert-meta">System waiting for activity...</div></div>`;
    return;
  }
  auditLogs.slice(-8).reverse().forEach(log=>{
    let level = "low";
    if(log.type==="DNS_SPOOFING_BLOCKED") level="high";
    else if(log.type==="GLOBAL_SEARCH_EXISTS") level="medium";
    feed.innerHTML+=`<div class="alert-item ${level}"><strong>${log.type}</strong><div>${JSON.stringify(log.details)}</div><div class="alert-meta">${log.time}</div></div>`;
  });
}

function generateMonitoringSnapshot(){
  const snapshot = {
    generated_at: new Date().toISOString(),
    total_events: auditLogs.length,
    blocked_attacks: getEventCount("DNS_SPOOFING_BLOCKED"),
    domain_registered: getEventCount("DOMAIN_REGISTERED"),
    domain_resolved: getEventCount("DOMAIN_RESOLVED"),
    threat_level: getThreatLevel(),
    recent_events: auditLogs.slice(-5)
  };
  show("monitorOutput", snapshot);
  notify("Security snapshot generated.");
  addLog("SECURITY_SNAPSHOT_GENERATED", snapshot);
  refreshMonitoring();
}

// ─── EXPORT ────────────────────────────────────────────────
function downloadJSON(filename, data){
  const blob = new Blob([JSON.stringify(data,null,2)],{type:"application/json"});
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function exportLogs(){
  if(auditLogs.length===0){ notify("No logs to export yet."); return; }
  downloadJSON("bdns_audit_logs.json", auditLogs);
  notify("Audit logs exported.");
}

async function exportBlockchain(){
  try{
    const data = await apiGet("/api/v1/chain");
    downloadJSON("bdns_blockchain_export.json", data);
    notify("Blockchain exported.");
    addLog("BLOCKCHAIN_EXPORTED",{status:"success"});
  } catch(e){ notify("Blockchain export failed."); }
}

// ─── HEALTH ────────────────────────────────────────────────
async function checkHealth(){
  try{
    await apiGet("/api/v1/health");
    const el = document.getElementById("apiStatus");
    if(el) el.textContent = "Online";
  } catch{
    const el = document.getElementById("apiStatus");
    if(el) el.textContent = "Offline";
  }
}

// ─── FOOTER SUBSCRIBE ──────────────────────────────────────
function subscribeFooter(){
  const email = document.getElementById("footerEmail")?.value||"";
  if(!email){ notify("Please enter your email."); return; }
  notify("Subscribed to BDNS security updates.");
  addLog("FOOTER_SUBSCRIPTION",{email});
}

async function updateDomainIp(){
  const domain = document.getElementById("updateDomainName").value.trim().toLowerCase();
  const ip = document.getElementById("updateIp").value.trim();
  if(!domain || !ip){ show("updateDomainOutput", { error:"Please enter domain name and new IP address." }); return; }
  try{
    const signed = await signData(domain, ip);
    const payload = { domain, ip, owner_public_key: signed.publicKey, signature: signed.signature };
    const data = await apiPost("/api/v1/domains/update", payload);
    show("updateDomainOutput", { message:"Domain IP updated successfully.", result:data });
    notify("Domain IP updated.");
    addLog("DOMAIN_IP_UPDATED", { domain, ip });
    await loadDomains();
  }catch(e){
    show("updateDomainOutput", { error:"Domain update failed.", detail:e.message });
  }
}

async function transferDomainOwnership(){
  const domain = document.getElementById("transferDomainName").value.trim().toLowerCase();
  const newOwner = document.getElementById("newOwnerPublicKey").value.trim();
  if(!domain || !newOwner){ show("transferDomainOutput", { error:"Please enter domain name and new owner public key." }); return; }
  try{
    const signed = await signData(domain, newOwner);
    const payload = { domain, new_owner_public_key: newOwner, owner_public_key: signed.publicKey, signature: signed.signature };
    const data = await apiPost("/api/v1/domains/transfer", payload);
    show("transferDomainOutput", { message:"Domain ownership transferred successfully.", result:data });
    notify("Domain ownership transferred.");
    addLog("DOMAIN_TRANSFERRED", { domain });
  }catch(e){
    show("transferDomainOutput", { error:"Transfer failed.", detail:e.message });
  }
}

async function loadDomainDetails(){
  const domain = document.getElementById("detailsDomainName").value.trim().toLowerCase();
  if(!domain){ show("domainDetailsOutput", { error:"Please enter a domain name." }); return; }
  try{
    const data = await apiGet("/api/v1/domains/" + encodeURIComponent(domain));
    show("domainDetailsOutput", data);
    notify("Domain details loaded.");
  }catch(e){
    show("domainDetailsOutput", { error:"Could not load domain details.", detail:e.message });
  }
}

function loadAuditHistory(){
  const domain = document.getElementById("auditDomainName").value.trim().toLowerCase();
  if(!domain){ show("auditHistoryOutput", { error:"Please enter a domain name." }); return; }
  const logs = auditLogs.filter(log => JSON.stringify(log.details).toLowerCase().includes(domain));
  show("auditHistoryOutput", { domain, total_events: logs.length, history: logs });
  notify("Audit history loaded.");
}

function loadSystemMetrics(){
  const totalQueries = auditLogs.filter(l => ["DOMAIN_RESOLVED","GLOBAL_SEARCH_EXISTS","GLOBAL_SEARCH_AVAILABLE"].includes(l.type)).length;
  const cacheHits = auditLogs.filter(l => l.type === "GLOBAL_SEARCH_EXISTS").length;
  const cacheMisses = auditLogs.filter(l => l.type === "GLOBAL_SEARCH_AVAILABLE").length;
  const hitRate = totalQueries === 0 ? 0 : Math.round((cacheHits / totalQueries) * 100);

  document.getElementById("mTotal").textContent = totalQueries;
  document.getElementById("mHits").textContent = cacheHits;
  document.getElementById("mMisses").textContent = cacheMisses;
  document.getElementById("mRate").textContent = hitRate + "%";

  show("metricsOutput", { total_queries: totalQueries, cache_hits: cacheHits, cache_misses: cacheMisses, hit_rate: hitRate + "%" });
  notify("System metrics refreshed.");
}

async function landingDomainCheck(){
  const domain = document.getElementById("landingCheckDomain").value.trim().toLowerCase();
  if(!domain){
    renderAvailabilityResult("landingCheckOutput", { status:"ERROR", reason:"EMPTY_DOMAIN", domain:"-", message:"Please enter a domain name." });
    return;
  }
  try{
    const data = await apiGet("/api/v1/domains/" + encodeURIComponent(domain) + "/availability");
    renderAvailabilityResult("landingCheckOutput", data);
    notify(data.status === "BLOCKED" ? data.message : "Domain is available.");
  }catch(e){
    renderAvailabilityResult("landingCheckOutput", { status:"ERROR", reason:"CHECK_FAILED", domain, message:"Could not check domain availability." });
  }
}

function renderAvailabilityResult(targetId, data){
  const el = document.getElementById(targetId);
  if(!el) return;
  const blocked = data.status === "BLOCKED";
  el.className = blocked ? "availability-card warning" : "availability-card success";
  el.innerHTML = `
    <div class="availability-title">${blocked ? "DOMAIN BLOCKED" : "DOMAIN AVAILABLE"}</div>
    <div><strong>Status:</strong> ${data.status}</div>
    <div><strong>Reason:</strong> ${data.reason || "-"}</div>
    <div><strong>Domain:</strong> ${data.domain}</div>
    <div class="availability-message">${data.message}</div>
  `;
}

function togglePassword(inputId, icon){
  const input = document.getElementById(inputId);
  const eyeOpen = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>`;
  const eyeClosed = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 20C5 20 1 12 1 12a21.86 21.86 0 0 1 5.06-6.94"/><path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a21.91 21.91 0 0 1-2.16 3.19"/><path d="M1 1l22 22"/></svg>`;
  if(input.type === "password"){ input.type = "text"; icon.innerHTML = eyeClosed; }
  else{ input.type = "password"; icon.innerHTML = eyeOpen; }
}

// Sets the initial (closed/eyeOpen) icon on every password toggle on the page.
function initPasswordToggles(){
  const eyeOpen = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>`;
  document.querySelectorAll(".toggle-password").forEach(el => { el.innerHTML = eyeOpen; });
}

// ─── ADMIN: STATS (Admin Overview cards) ────────────────────
async function loadAdminStats(){
  try{
    const data = await apiGet("/api/v1/admin/stats");
    if(data.error || data.detail){ throw new Error(data.detail || data.error); }

    const domainCount = document.getElementById("adminDomainCount");
    const chainHeight  = document.getElementById("adminChainHeight");
    const eventCount   = document.getElementById("adminEventCount");
    const threatLevel  = document.getElementById("adminThreatLevel");

    if(domainCount) domainCount.textContent = data.total_domains;
    if(chainHeight)  chainHeight.textContent = data.chain_height;
    if(eventCount)   eventCount.textContent = data.total_security_events;
    if(threatLevel){
      const level = data.frozen_domains >= 3 ? "HIGH" : data.frozen_domains >= 1 ? "MEDIUM" : "LOW";
      threatLevel.textContent = level;
    }

    show("adminOutput", {
      message: "Admin security summary loaded from live backend.",
      total_users: data.total_users,
      admin_count: data.admin_count,
      customer_count: data.customer_count,
      total_domains: data.total_domains,
      frozen_domains: data.frozen_domains,
      chain_height: data.chain_height,
      total_security_events: data.total_security_events
    });
  }catch(e){
    show("adminOutput", { error: "Could not load admin stats.", detail: e.message });
  }
}

// ─── ADMIN: USER MANAGEMENT ──────────────────────────────────
async function loadAdminUsers(){
  const table = document.getElementById("adminUserTable");
  try{
    const users = await apiGet("/api/v1/admin/users");
    if(!Array.isArray(users)) throw new Error(users.detail || users.error || "Unexpected response.");

    const countEl = document.getElementById("adminUserCount");
    if(countEl) countEl.textContent = users.length;

    if(!table) return;
    table.innerHTML = "";
    if(users.length === 0){ table.innerHTML = `<tr><td colspan="5">No users found.</td></tr>`; return; }

    users.forEach(u => {
      const suspended = u.status === "suspended";
      const badgeClass = suspended ? "badge danger" : "badge ok";
      const actionBtn = suspended
        ? `<button class="primary" onclick="setUserStatus('${u.user_id}','active')">Reactivate</button>`
        : `<button class="primary danger" onclick="setUserStatus('${u.user_id}','suspended')">Suspend</button>`;
      table.innerHTML += `<tr>
        <td>${u.full_name || "-"}</td>
        <td>${u.email}</td>
        <td>${u.role}</td>
        <td><span class="${badgeClass}">${suspended ? "Suspended" : "Active"}</span></td>
        <td>${actionBtn}</td>
      </tr>`;
    });
  }catch(e){
    if(table) table.innerHTML = `<tr><td colspan="5">Could not load users: ${e.message}</td></tr>`;
  }
}

async function setUserStatus(userId, newStatus){
  if(newStatus === "suspended" && !confirm("Suspend this user? They won't be able to log in until reactivated.")) return;
  try{
    const data = await apiPut(`/api/v1/admin/users/${userId}/status`, { status: newStatus });
    if(data.detail || data.error){ notify(data.detail || data.error); return; }
    notify(`User ${newStatus === "suspended" ? "suspended" : "reactivated"}.`);
    await loadAdminUsers();
  }catch(e){
    notify("Could not update user status.");
  }
}

// ─── ADMIN: DOMAIN MODERATION ────────────────────────────────
async function loadDomainModeration(){
  const table = document.getElementById("moderationTable");
  try{
    const domains = await apiGet("/api/v1/domains");
    const list = Array.isArray(domains) ? domains : (domains.domains || []);

    const countEl = document.getElementById("moderationDomainCount");
    if(countEl) countEl.textContent = list.length;

    if(!table) return;
    table.innerHTML = "";
    if(list.length === 0){ table.innerHTML = `<tr><td colspan="4">No domains registered yet.</td></tr>`; return; }

    list.forEach(item => {
      const frozen = item.status === "frozen";
      const badgeClass = frozen ? "badge danger" : "badge ok";
      const actionBtn = frozen
        ? `<button class="primary" onclick="unfreezeDomainAdmin('${item.domain}')">Unfreeze</button>`
        : `<button class="primary danger" onclick="freezeDomainAdmin('${item.domain}')">Freeze</button>`;
      table.innerHTML += `<tr>
        <td>${item.domain}</td>
        <td>${item.ip}</td>
        <td><span class="${badgeClass}">${frozen ? "Frozen" : "Active"}</span></td>
        <td>${actionBtn}</td>
      </tr>`;
    });
  }catch(e){
    if(table) table.innerHTML = `<tr><td colspan="4">Could not load domains.</td></tr>`;
  }
}

async function freezeDomainAdmin(domain){
  const reason = prompt(`Reason for freezing "${domain}"?`, "Suspected policy violation");
  if(reason === null) return;
  try{
    const data = await apiPost(`/api/v1/admin/domains/${encodeURIComponent(domain)}/freeze`, { reason });
    if(data.detail){ notify(data.detail); return; }
    notify(`Domain "${domain}" frozen.`);
    await loadDomainModeration();
  }catch(e){ notify("Could not freeze domain."); }
}

async function unfreezeDomainAdmin(domain){
  const reason = prompt(`Reason for unfreezing "${domain}"?`, "Investigation completed");
  if(reason === null) return;
  try{
    const data = await apiPost(`/api/v1/admin/domains/${encodeURIComponent(domain)}/unfreeze`, { reason });
    if(data.detail){ notify(data.detail); return; }
    notify(`Domain "${domain}" unfrozen.`);
    await loadDomainModeration();
  }catch(e){ notify("Could not unfreeze domain."); }
}

// ─── ADMIN: GLOBAL AUDIT TRAIL ────────────────────────────────
async function loadGlobalAuditTrail(){
  const table = document.getElementById("globalAuditTable");
  try{
    const events = await apiGet("/api/v1/admin/audit");
    if(!Array.isArray(events)) throw new Error(events.detail || events.error || "Unexpected response.");

    const countEl = document.getElementById("globalAuditCount");
    if(countEl) countEl.textContent = events.length;

    if(!table) return;
    table.innerHTML = "";
    if(events.length === 0){ table.innerHTML = `<tr><td colspan="5">No blockchain activity yet.</td></tr>`; return; }

    events.forEach(e => {
      table.innerHTML += `<tr>
        <td><span class="badge ok">${e.tx_type}</span></td>
        <td>${e.domain}</td>
        <td>#${e.block_index}</td>
        <td>${shortText(e.block_hash)}</td>
        <td>${new Date(e.timestamp).toLocaleString()}</td>
      </tr>`;
    });
  }catch(e){
    if(table) table.innerHTML = `<tr><td colspan="5">Could not load audit trail: ${e.message}</td></tr>`;
  }
}

function filterGlobalAuditByDomain(){
  const filter = (document.getElementById("globalAuditFilter")?.value || "").trim().toLowerCase();
  const rows = document.querySelectorAll("#globalAuditTable tr");
  rows.forEach(row => {
    const domainCell = row.children[1];
    if(!domainCell) return;
    row.style.display = domainCell.textContent.toLowerCase().includes(filter) ? "" : "none";
  });
}

// ─── PER-PAGE BOOTSTRAP ─────────────────────────────────────
// Call this once at the bottom of every page, passing that page's id.
function initPage(pageId){
  if(!guardProtectedPage(pageId)) return;

  applySession();
  const user = getSession();
  if(user) renderSidebar(user.role || "customer");

  updateFooter(pageId);
  highlightActiveNav(pageId);
  initPasswordToggles();

  checkHealth();

  if(document.getElementById("domainTable") || document.getElementById("domainCount")){
    loadDomains();
  }
  if(document.getElementById("chainVisual") || document.getElementById("chainHeight") || document.getElementById("chainOutput")){
    loadChain();
    if(pageId === "blockchain") setInterval(loadChain, 10000);
  }
  if(document.getElementById("alertFeed") || document.getElementById("monitorTotalEvents")){
    refreshMonitoring();
    if(pageId === "monitoring") setInterval(refreshMonitoring, 5000);
  }
  if(pageId === "myDomains"){
    loadMyDomains();
  }
  if(pageId === "adminDashboardOverview"){
    loadAdminStats();
  }
  if(pageId === "adminUsers"){
    loadAdminUsers();
  }
  if(pageId === "domainModeration"){
    loadDomainModeration();
  }
  if(pageId === "adminAuditTrail"){
    loadGlobalAuditTrail();
  }
  if(pageId === "myProfile"){
    loadProfile();
  }
}
