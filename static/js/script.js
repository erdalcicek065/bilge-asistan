// --- ESKİ JS KODLARININ AYNISI (KARIŞIKLIK OLMASIN DİYE TAMAMINI VERİYORUM) ---

// 1. GLOBAL DEĞİŞKENLER
let currentStudentId = null;
let currentStudentName = "";
let currentLesson = null;
let curriculumData = {};
let targetModule = "";
const AGE_ORDER = ["0-3 Ay", "4-6 Ay", "7-9 Ay", "10-12 Ay", "13-18 Ay", "19-24 Ay", "25-30 Ay", "31-36 Ay", "37-48 Ay", "49-60 Ay", "61-76 Ay"];

// 2. YARDIMCI FONKSİYONLAR
function goToAuth(t) { 
    document.getElementById('landing-screen').classList.add('hidden'); 
    document.getElementById('auth-screen').classList.remove('hidden'); 
    if(t === 'login') {
        document.getElementById('login-box').classList.remove('hidden');
        document.getElementById('register-box').classList.add('hidden');
    } else {
        document.getElementById('register-box').classList.remove('hidden');
        document.getElementById('login-box').classList.add('hidden');
    }
}
function goToLanding() { document.getElementById('auth-screen').classList.add('hidden'); document.getElementById('landing-screen').classList.remove('hidden'); }
function showApp() { document.getElementById('auth-screen').classList.add('hidden'); document.getElementById('app-screen').classList.remove('hidden'); showDashboardHome(); }
function logout() { fetch('/logout').then(() => window.location.reload()); }
function hideAll() { document.querySelectorAll('.content-panel').forEach(p => p.classList.remove('active')); }
function showDashboardHome() { hideAll(); document.getElementById('dashboard-home').classList.add('active'); }

function openModule(moduleName) {
    hideAll();
    
    // MOBİLDE MENÜYE TIKLAYINCA MENÜYÜ KAPAT (YENİ EKLENDİ)
    if(window.innerWidth < 768) {
        document.getElementById('sidebar').classList.remove('active');
    }

    if (moduleName === 'kaba-degerlendirme-list' || moduleName === 'bep-olustur-list' || moduleName === 'bep-listesi-secim') {
        targetModule = moduleName;
        document.getElementById('panel-student-select').classList.add('active');
        let title = "Öğrenci Seçiniz";
        if(moduleName.includes('kaba')) title += " (Kaba Değerlendirme)";
        if(moduleName.includes('olustur')) title += " (BEP Oluşturma)";
        if(moduleName.includes('listesi')) title += " (Geçmiş Raporlar)";
        document.getElementById('student-select-title').innerText = title;
        loadStudents();
    }
    else if (moduleName === 'add-student') document.getElementById('panel-add-student').classList.add('active');
    else if (moduleName === 'student-list') { targetModule = 'none'; document.getElementById('panel-student-select').classList.add('active'); document.getElementById('student-select-title').innerText = "Öğrenci Listesi"; loadStudents(); }
    else if (moduleName === 'ask-bilge') document.getElementById('panel-ask-bilge').classList.add('active');
    else { alert("Bu modül yapım aşamasında."); showDashboardHome(); }
}

function selectStudent(id, name) {
    currentStudentId = id; currentStudentName = name; hideAll();
    if (targetModule === 'kaba-degerlendirme-list') { document.getElementById('panel-kaba-degerlendirme').classList.add('active'); document.getElementById('kaba-student-name').innerText = name + " - Kaba Değerlendirme"; document.getElementById('lesson-select').value = ""; document.getElementById('checklist-wrapper').classList.add('hidden'); }
    else if (targetModule === 'bep-olustur-list') { document.getElementById('panel-bep-create').classList.add('active'); document.getElementById('bep-create-student-name').innerText = name; document.getElementById('ai-result').classList.add('hidden'); }
    else if (targetModule === 'bep-listesi-secim') { document.getElementById('panel-bep-list').classList.add('active'); document.getElementById('bep-list-student-name').innerText = name; loadBepList(id); }
}

// 3. API İŞLEMLERİ
async function login() {
    const e = document.getElementById('login-email').value, p = document.getElementById('login-pass').value;
    try { const r = await fetch('/login', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:e, password:p})}); const d = await r.json(); d.status === 'success' ? showApp() : alert(d.error); } catch(err) { alert("Sunucu hatası"); }
}
async function register() {
    const s = document.getElementById('reg-school').value, e = document.getElementById('reg-email').value, p = document.getElementById('reg-pass').value;
    if(!e || !p) return alert("E-posta ve şifre zorunlu.");
    try { const r = await fetch('/register', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:e, password:p, school:s})}); const d = await r.json(); d.status === 'success' ? (alert('Başarılı'), goToAuth('login')) : alert(d.error); } catch(err) { alert("Hata"); }
}
async function saveStudent() {
    const data = { name: document.getElementById('new-name').value, tc_no: document.getElementById('new-tc').value, dob: document.getElementById('new-dob').value, gender: document.getElementById('new-gender').value, diagnosis: document.getElementById('new-diagnosis').value, parent_name: document.getElementById('new-parent').value, parent_phone: document.getElementById('new-phone').value, medication_info: document.getElementById('new-meds').value, notes: document.getElementById('new-notes').value };
    if(!data.name) return alert("İsim giriniz.");
    const r = await fetch('/add_student', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    const d = await r.json(); d.status === 'success' ? (alert('Kaydedildi'), openModule('student-list')) : alert(d.error);
}
async function loadStudents() {
    const r = await fetch('/get_students'); const s = await r.json();
    let h = `<table><thead><tr><th>Ad</th><th>Tanı</th><th>İşlem</th></tr></thead><tbody>`;
    s.forEach(st => { let btnText = targetModule === 'none' ? "Görüntüle" : "Seç"; h += `<tr><td>${st.name}</td><td>${st.diagnosis || '-'}</td><td><button class='btn-primary' onclick='selectStudent(${st.id},"${st.name}")'>${btnText}</button></td></tr>`; });
    document.getElementById('student-list-container').innerHTML = h + `</tbody></table>`;
}

// 4. KABA & BEP
async function loadCurriculum() { try { const r = await fetch('/get_curriculum'); curriculumData = await r.json(); } catch(e) {} }
function switchLesson(l) { 
    currentLesson = l; document.getElementById('checklist-wrapper').classList.remove('hidden'); const c = document.getElementById('checklist-area'); c.innerHTML = "";
    if(curriculumData[l]) { Object.keys(curriculumData[l]).sort((a,b) => AGE_ORDER.indexOf(a) - AGE_ORDER.indexOf(b)).forEach(age => { let h = document.createElement('h4'); h.innerText = age; h.style.background = '#e3f2fd'; h.style.padding = '8px'; h.style.marginTop = '10px'; c.appendChild(h); curriculumData[l][age].forEach((item, idx) => { let uid = `item-${age.replace(/\s/g,'')}-${idx}`; c.innerHTML += `<div class="assessment-row"><div class="assessment-label">${item}</div><div class="assessment-options"><label class="radio-group yes"><input type="radio" name="${uid}" value="EVET" data-text="${item}"> Evet</label><label class="radio-group partial"><input type="radio" name="${uid}" value="KISMEN" data-text="${item}"> Kısmen</label><label class="radio-group no"><input type="radio" name="${uid}" value="HAYIR" data-text="${item}"> Hayır</label></div></div>`; }); }); }
}
async function saveAssessment() {
    if(!currentStudentId || !currentLesson) return alert('Ders seçilmedi.');
    let y=[], k=[], n=[]; document.querySelectorAll('.assessment-row input:checked').forEach(r => { let t = r.getAttribute('data-text'); if(r.value === 'EVET') y.push(t); else if(r.value === 'KISMEN') k.push(t); else n.push(t); });
    if(!y.length && !k.length && !n.length) return alert("Seçim yapın.");
    await fetch('/save_assessment', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({student_id: currentStudentId, lesson: currentLesson, performance: `BAĞIMSIZ: ${y.join(', ')}. DESTEKLE: ${k.join(', ')}. YAPAMIYOR: ${n.join(', ')}.`, expectation: document.getElementById('expect').value, needs: '-'})});
    alert('✅ Kaydedildi!');
}
async function generateBEP() {
    const r = document.getElementById('ai-result'); r.classList.remove('hidden'); r.innerHTML = "Hazırlanıyor...";
    const res = await fetch('/generate_full_bep', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({student_id: currentStudentId})});
    const d = await res.json(); d.error ? r.innerHTML = `<span style="color:red">${d.error}</span>` : r.innerHTML = d.ai_response;
}
async function loadBepList(id) {
    const r = await fetch('/get_bep_list', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({student_id: id})});
    const l = await r.json(); const c = document.getElementById('bep-history-container');
    if(!l.length) return c.innerHTML = "Rapor yok.";
    c.innerHTML = l.map(i => `<div style='padding:10px; border:1px solid #eee; margin-bottom:5px; display:flex; justify-content:space-between'><span>📅 ${i.created_at}</span><button class='btn-primary' onclick='viewBep(${i.id})'>Görüntüle</button></div>`).join('');
}
async function viewBep(rid) {
    const r = await fetch('/get_bep_content', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({report_id: rid})});
    const d = await r.json(); const v = document.getElementById('bep-viewer'); v.classList.remove('hidden'); v.innerHTML = d.content || "Hata"; v.scrollIntoView({behavior: 'smooth'});
}
async function sendChatMessage() {
    const i = document.getElementById('chat-input'), c = document.getElementById('chat-container'), m = i.value.trim(); if(!m) return;
    c.innerHTML += `<div class="chat-message user-message">${m}</div>`; i.value = ""; c.scrollTop = c.scrollHeight;
    const lid = "load-" + Date.now(); c.innerHTML += `<div id="${lid}" class="chat-message bot-message">...</div>`;
    try { const r = await fetch('/ask_bilge_chat', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message: m})}); const d = await r.json(); document.getElementById(lid).remove(); c.innerHTML += `<div class="chat-message bot-message">${d.ai_response ? d.ai_response.replace(/\n/g, '<br>') : d.error}</div>`; } catch(e) { if(document.getElementById(lid)) document.getElementById(lid).remove(); } c.scrollTop = c.scrollHeight;
}
function handleEnter(e) { if(e.key === 'Enter') sendChatMessage(); }

// --- 5. MENÜ AÇ/KAPA (TEK YENİ FONKSİYON) ---
function toggleMenu() {
    const sb = document.getElementById('sidebar');
    sb.classList.toggle('active');
}

// 6. BAŞLATICI
document.addEventListener('DOMContentLoaded', async () => { await loadCurriculum(); });