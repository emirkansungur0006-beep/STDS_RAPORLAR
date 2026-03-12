/* ============================================
   T.C. SAĞLIK BAKANLIĞI - STDS Dashboard JS
   ============================================ */

// ========== STATE ==========
let gozlemPage = 1;
let gozlemFilterPage = 1;
let komitePage = 1;
let gelisimPage = 1;
let searchTimeout = null;
let chartInstances = {};
let gorseliOlanHastaneler = new Set();
let gelisimMap = null;
let currentUser = null;
let currentRole = null;

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', async () => {
    initClock();
    initNavigation();
    initSubmenus();
    
    // Auth Check - Devre dışı bırakıldı (Her seferinde şifre istensin diye)
    // await checkAuthStatus();
    showLoginScreen();
});

// ========== CLOCK ==========
function initClock() {
    const update = () => {
        const now = new Date();
        const opts = { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
        document.getElementById('header-clock').textContent = now.toLocaleDateString('tr-TR', opts);
    };
    update();
    setInterval(update, 1000);
}

// ========== NAVIGATION ==========
function initNavigation() {
    document.querySelectorAll('.nav-item[data-page]').forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            switchPage(page);

            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            item.classList.add('active');
        });
    });
}

function switchPage(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const el = document.getElementById('page-' + page);
    if (el) {
        el.classList.add('active');
        // Veri yükleme
        if (page === 'dashboard') loadDashboard();
        else if (page === 'gozlem-rapor') loadGozlemData(1);
        else if (page === 'gozlem-filtre') loadGozlemFiltered();
        else if (page === 'komite-rapor') loadKomiteData(1);
        else if (page === 'gelisim-rapor') {
            loadFilters();
            loadGelisimData(1);
            initGelisimMap();
        }

        // Başlık güncelle
        const titles = {
            'dashboard': 'SDS Dashboard',
            'gozlem-rapor': 'Gözlem Rapor Analizi',
            'gozlem-filtre': 'Gözlem Filtreleme',
            'komite-rapor': 'Komite/Komisyon Raporları',
            'komite-detay': 'Standart Değerlendirme Detayı',
            'gelisim-rapor': 'Gelişim Planı Analizi',
            'admin-users': 'Kullanıcı Yönetimi'
        };
        const pt = document.getElementById('page-title');
        if (pt) pt.textContent = titles[page] || 'SDS Dashboard';

        if (page === 'admin-users') loadAdminUsers();
    }
}

function initSubmenus() {
    document.querySelectorAll('.nav-section-title[data-toggle]').forEach(title => {
        title.addEventListener('click', () => {
            const menuId = title.dataset.toggle;
            const menu = document.getElementById(menuId);
            if (menu) {
                menu.classList.toggle('open');
                title.classList.toggle('expanded');
            }
        });
    });

    // İlk menüleri aç
    document.querySelectorAll('.nav-submenu').forEach(m => m.classList.add('open'));
    document.querySelectorAll('.nav-section-title').forEach(t => t.classList.add('expanded'));
}

// ========== API HELPERS ==========
async function api(url, options = {}) {
    try {
        const resp = await fetch(url, options);
        if (resp.status === 401) {
            showLoginScreen();
            return null;
        }
        if (resp.status === 403) {
            alert('Bu işlem için yetkiniz bulunmamaktadır.');
            return null;
        }
        const data = await resp.json();
        return data; // Caller handles errors within data
    } catch (err) {
        console.error('API Error:', url, err);
        return null;
    }
}

// ========== AUTHENTICATION LOGIC ==========

function showLoginScreen() {
    document.getElementById('login-overlay').classList.add('show');
    document.getElementById('login-overlay').style.display = 'flex';
    document.getElementById('main-header').style.display = 'none';
    document.getElementById('app-container').style.display = 'none';
}

function hideLoginScreen() {
    document.getElementById('login-overlay').classList.remove('show');
    document.getElementById('login-overlay').style.display = 'none';
    document.getElementById('main-header').style.display = 'flex';
    document.getElementById('app-container').style.display = 'flex';
}

async function handleLogin() {
    const userEl = document.getElementById('login-username');
    const passEl = document.getElementById('login-password');
    const errEl = document.getElementById('login-error');
    
    errEl.textContent = '';
    
    const res = await api('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: userEl.value,
            password: passEl.value
        })
    });
    
    if (res && res.success) {
        currentUser = res.user.username;
        currentRole = res.user.role;
        hideLoginScreen();
        applyRolePermissions();
        
        // Load initial data
        await fetchGorselHastaneler();
        loadDashboard();
        loadFilters();
        loadHierarchyTree();
    } else {
        errEl.textContent = 'Giriş başarısız. Lütfen bilgilerinizi kontrol edin.';
    }
}

async function handleLogout() {
    await api('/api/auth/logout');
    window.location.reload();
}

async function checkAuthStatus() {
    const data = await fetch('/api/auth/current').then(r => r.json());
    if (data.authenticated) {
        currentUser = data.user.username;
        currentRole = data.user.role;
        hideLoginScreen();
        applyRolePermissions();
        
        // Load initial data
        await fetchGorselHastaneler();
        loadDashboard();
        loadFilters();
        loadHierarchyTree();
    } else {
        showLoginScreen();
    }
}

function applyRolePermissions() {
    const adminSection = document.getElementById('nav-admin-section');
    const gorselControls = document.getElementById('gorsel-admin-controls');
    
    if (currentRole === 'admin') {
        if (adminSection) adminSection.style.display = 'block';
        if (gorselControls) gorselControls.style.display = 'block';
    } else {
        if (adminSection) adminSection.style.display = 'none';
        if (gorselControls) gorselControls.style.display = 'none';
        
        // If on admin page, go back to dashboard
        const activePage = document.querySelector('.page.active');
        if (activePage && activePage.id === 'page-admin-users') {
            switchPage('dashboard');
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            document.getElementById('nav-dashboard').classList.add('active');
        }
    }
}

// ========== USER MANAGEMENT (ADMIN) ==========

async function loadAdminUsers() {
    const users = await api('/api/admin/users');
    if (!users) return;
    
    const tbody = document.getElementById('admin-users-tbody');
    tbody.innerHTML = '';
    
    users.forEach(u => {
        const tr = document.createElement('tr');
        const roleBadge = u.role === 'admin' ? '<span class="role-badge role-admin">Admin</span>' : '<span class="role-badge role-user">Kullanıcı</span>';
        
        tr.innerHTML = `
            <td><strong>${esc(u.username)}</strong></td>
            <td>${roleBadge}</td>
            <td>${u.created_at || '-'}</td>
            <td>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${u.id}, '${escJs(u.username)}')" ${u.username === currentUser ? 'disabled' : ''}>
                    <i class="fas fa-trash-alt"></i> Sil
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function openAddUserModal() {
    document.getElementById('user-modal-overlay').classList.add('show');
}

function closeUserModal() {
    document.getElementById('user-modal-overlay').classList.remove('show');
}

async function saveNewUser() {
    const username = document.getElementById('new-user-username').value;
    const password = document.getElementById('new-user-password').value;
    const role = document.getElementById('new-user-role').value;
    
    if (!username || !password) {
        alert('Lütfen tüm alanları doldurun.');
        return;
    }
    
    const res = await api('/api/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role })
    });
    
    if (res && res.success) {
        closeUserModal();
        loadAdminUsers();
        // Clear fields
        document.getElementById('new-user-username').value = '';
        document.getElementById('new-user-password').value = '';
    } else {
        alert('Kullanıcı eklenemedi: ' + (res ? res.error : 'Bilinmeyen hata'));
    }
}

async function deleteUser(userId, username) {
    if (!confirm(`${username} isimli kullanıcıyı silmek istediğinize emin misiniz?`)) return;
    
    const res = await api(`/api/admin/users/${userId}`, { method: 'DELETE' });
    if (res && res.success) {
        loadAdminUsers();
    }
}

// ========== DASHBOARD ==========
async function loadDashboard() {
    const stats = await api('/api/dashboard/stats');
    if (!stats) return;

    animateNumber('stat-hastane', stats.toplam_hastane);
    animateNumber('stat-gozlem', stats.toplam_gozlem);
    animateNumber('stat-komite', stats.toplam_komite);
    animateNumber('stat-il', Math.max(stats.gozlem_il_sayisi, stats.komite_il_sayisi));

    // Charts
    renderDereceChart(stats.derece_dagilimi);
    renderUygunlukChart(stats.uygunluk_dagilimi);
    renderSondurumChart(stats.sondurum_dagilimi);
    renderIlChart(stats.il_komite_dagilimi);
}

function animateNumber(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const duration = 800;
    const start = parseInt(el.textContent) || 0;
    const startTime = performance.now();

    function tick(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(start + (target - start) * eased).toLocaleString('tr-TR');
        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

// ========== CHARTS ==========
const chartColors = {
    primary: ['#0054A6', '#1A6FBF', '#3B82F6', '#60A5FA', '#93C5FD'],
    success: ['#10B981', '#34D399', '#6EE7B7'],
    warning: ['#F59E0B', '#FBBF24', '#FCD34D'],
    danger: ['#EF4444', '#F87171', '#FCA5A5'],
    mixed: ['#0054A6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316']
};

function destroyChart(id) {
    if (chartInstances[id]) {
        chartInstances[id].destroy();
        delete chartInstances[id];
    }
}

function renderDereceChart(data) {
    if (!data || !data.length) return;
    destroyChart('derece');
    const ctx = document.getElementById('chart-derece');
    if (!ctx) return;

    const colorMap = {
        'Cok Iyi': '#10B981', 'Iyi': '#22C55E', 'Orta': '#EAB308',
        'Zayif': '#F97316', 'Kotu': '#F97316', 'Cok Zayif': '#EF4444', 'Cok Kotu': '#EF4444',
        // Orijinal labellar (tedbir amaçlı)
        'Çok İyi': '#10B981', 'İyi': '#22C55E', 'Çok Zayıf': '#EF4444'
    };

    chartInstances['derece'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.derece),
            datasets: [{
                data: data.map(d => d.sayi),
                backgroundColor: data.map(d => colorMap[d.derece] || '#94A3B8'),
                borderRadius: 8,
                borderSkipped: false,
                barThickness: 48
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { backgroundColor: '#1E293B', titleFont: { family: 'Inter' }, bodyFont: { family: 'Inter' } }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#F1F5F9' }, ticks: { font: { family: 'Inter', size: 11 } } },
                x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11, weight: 600 } } }
            }
        }
    });
}

function renderUygunlukChart(data) {
    if (!data || !data.length) return;
    destroyChart('uygunluk');
    const ctx = document.getElementById('chart-uygunluk');
    if (!ctx) return;

    const colorMap = {
        'Karşılanıyor': '#10B981',
        'Kısmen Karşılanıyor': '#F59E0B',
        'Karşılanmıyor': '#EF4444'
    };

    chartInstances['uygunluk'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(d => d.durum),
            datasets: [{
                data: data.map(d => d.sayi),
                backgroundColor: data.map(d => colorMap[d.durum] || '#94A3B8'),
                borderWidth: 3,
                borderColor: '#FFFFFF'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '55%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { family: 'Inter', size: 11 }, padding: 16, usePointStyle: true }
                }
            }
        }
    });
}

function renderSondurumChart(data) {
    if (!data || !data.length) return;
    destroyChart('sondurum');
    const ctx = document.getElementById('chart-sondurum');
    if (!ctx) return;

    const colorMap = {
        'Tamamlandı': '#10B981',
        'Devam Ediyor': '#3B82F6',
        'Tamamlanmadı': '#EF4444'
    };

    chartInstances['sondurum'] = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.map(d => d.durum),
            datasets: [{
                data: data.map(d => d.sayi),
                backgroundColor: data.map(d => colorMap[d.durum] || '#94A3B8'),
                borderWidth: 3,
                borderColor: '#FFFFFF'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { family: 'Inter', size: 11 }, padding: 16, usePointStyle: true }
                }
            }
        }
    });
}

function renderIlChart(data) {
    if (!data || !data.length) return;
    destroyChart('il');
    const ctx = document.getElementById('chart-il');
    if (!ctx) return;

    // İlk 20 il göster
    const sortedData = data.sort((a, b) => b.sayi - a.sayi).slice(0, 20);

    chartInstances['il'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedData.map(d => d.il),
            datasets: [{
                data: sortedData.map(d => d.sayi),
                backgroundColor: '#0054A6',
                borderRadius: 4,
                borderSkipped: false,
                barThickness: 18
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { beginAtZero: true, grid: { color: '#F1F5F9' }, ticks: { font: { family: 'Inter', size: 10 } } },
                y: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 10 } } }
            }
        }
    });
}

// ========== GÖZLEM DATA ==========
async function loadGozlemData(page) {
    gozlemPage = page || 1;
    const data = await api(`/api/gozlem/list?page=${gozlemPage}&per_page=50`);
    if (!data) return;
    renderGozlemTable(data.data, 'gozlem-tbody');
    renderPagination(data, 'gozlem-pagination', loadGozlemData);
}

async function loadGozlemFiltered(page) {
    gozlemFilterPage = page || 1;
    const il = document.getElementById('filter-gozlem-il').value;
    const ilce = document.getElementById('filter-gozlem-ilce').value;
    const hastane = document.getElementById('filter-gozlem-hastane').value;
    const derece = document.getElementById('filter-gozlem-derece').value;
    const servis = document.getElementById('filter-gozlem-servis').value;
    const search = document.getElementById('filter-gozlem-search').value;

    let url = `/api/gozlem/list?page=${gozlemFilterPage}&per_page=50`;
    if (il) url += `&il=${encodeURIComponent(il)}`;
    if (ilce) url += `&ilce=${encodeURIComponent(ilce)}`;
    if (hastane) url += `&hastane=${encodeURIComponent(hastane)}`;
    if (derece) url += `&derece=${encodeURIComponent(derece)}`;
    if (servis) url += `&servis=${encodeURIComponent(servis)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    const data = await api(url);
    if (!data) return;

    renderGozlemTable(data.data, 'gozlem-filter-tbody');
    renderPagination(data, 'gozlem-filter-pagination', loadGozlemFiltered);

    // Filtre bilgisi
    const info = document.getElementById('filter-gozlem-info');
    if (data.total > 0) {
        info.textContent = `${data.total.toLocaleString('tr-TR')} kayıt bulundu (Sayfa ${data.page}/${data.total_pages})`;
        info.classList.add('visible');
    } else {
        info.textContent = 'Kayıt bulunamadı';
        info.classList.add('visible');
    }
}

function renderGozlemTable(rows, tbodyId) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;

    if (!rows || !rows.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-state" style="padding:40px"><i class="fas fa-inbox" style="font-size:32px;opacity:0.3"></i><p>Kayıt bulunamadı</p></td></tr>';
        return;
    }

    tbody.innerHTML = rows.map(r => {
        const dereceClass = getDereceClass(r.verilen_derece);
        const notText = r.notlar ? r.notlar.substring(0, 60) + (r.notlar.length > 60 ? '...' : '') : '-';

        return `<tr>
            <td>${esc(r.il)}</td>
            <td>${esc(r.ilce || '-')}</td>
            <td class="hastane-cell">${esc(r.hastane_adi)}</td>
            <td>${esc(r.bolum)}</td>
            <td style="text-align:center">${r.soru_no || '-'}</td>
            <td>${esc(r.soru || '-')}</td>
            <td><span class="derece-badge ${dereceClass}">${esc(r.verilen_derece || '-')}</span></td>
            <td>${r.notlar ? `<span class="not-cell" onclick="showNot('${esc(r.hastane_adi)} - ${esc(r.bolum)}', '${escJs(r.notlar)}')">${esc(notText)}</span>` : '-'}</td>
            <td style="text-align:center">
                ${gorseliOlanHastaneler.has(normalizeName(r.hastane_adi)) ?
                `<button class="btn btn-outline" style="padding:4px 8px; font-size:12px; color:var(--primary); border-color:var(--primary);" onclick="openGorselModal('${escJs(r.hastane_adi)}')">
                        <i class="fas fa-images"></i> İncele
                    </button>` :
                `<button class="btn btn-outline" style="padding:4px 8px; font-size:12px; opacity:0.4; cursor:not-allowed;" disabled>
                        <i class="fas fa-images"></i> Yok
                    </button>`
            }
            </td>
        </tr>`;
    }).join('');
}

function getDereceClass(derece) {
    if (!derece) return '';
    const d = derece.toLocaleLowerCase('tr-TR').replace(/\s+/g, '');
    if (d.includes('çokiyi') || d.includes('cokiyi')) return 'derece-cok-iyi';
    if (d.includes('çokkötü') || d.includes('cokkotu') || d.includes('çokzayıf') || d.includes('cokzayif')) return 'derece-cok-zayif';
    if (d.includes('iyi')) return 'derece-iyi';
    if (d === 'orta') return 'derece-orta';
    if (d.includes('kötü') || d.includes('kotu') || d.includes('zayıf') || d.includes('zayif')) return 'derece-zayif';
    return '';
}

// ========== KOMİTE DATA ==========
async function loadKomiteData(page) {
    komitePage = page || 1;
    const il = document.getElementById('filter-komite-il')?.value || '';
    const ilce = document.getElementById('filter-komite-ilce')?.value || '';
    const hastane = document.getElementById('filter-komite-hastane')?.value || '';
    const tip = document.getElementById('filter-komite-tip')?.value || '';

    let url = `/api/komite/list?page=${komitePage}&per_page=50`;
    if (il) url += `&il=${encodeURIComponent(il)}`;
    if (ilce) url += `&ilce=${encodeURIComponent(ilce)}`;
    if (hastane) url += `&hastane=${encodeURIComponent(hastane)}`;
    if (tip) url += `&rapor_tipi=${encodeURIComponent(tip)}`;

    const data = await api(url);
    if (!data) return;

    renderKomiteTable(data.data);
    renderPagination(data, 'komite-pagination', loadKomiteData);
}

function loadKomiteFiltered() { loadKomiteData(1); }

function renderKomiteTable(rows) {
    const tbody = document.getElementById('komite-tbody');
    if (!tbody) return;

    if (!rows || !rows.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state" style="padding:40px"><i class="fas fa-inbox" style="font-size:32px;opacity:0.3"></i><p>Kayıt bulunamadı</p></td></tr>';
        return;
    }

    tbody.innerHTML = rows.map(r => {
        const tipBadge = r.rapor_tipi === 'Komite'
            ? '<span class="derece-badge derece-iyi">Komite</span>'
            : '<span class="derece-badge derece-cok-iyi">Komisyon</span>';

        return `<tr>
            <td>${esc(r.il)}</td>
            <td>${esc(r.ilce || '-')}</td>
            <td class="hastane-cell">${esc(r.hastane_adi)}</td>
            <td>${tipBadge}</td>
            <td>${r.degerlendirme_tarihi || '-'}</td>
            <td>${r.degerlendirme_saati || '-'}</td>
            <td><button class="btn-uyeler" onclick="showUyeler(${r.id})"><i class="fas fa-users"></i> Üye Listesi</button></td>
            <td><button class="btn-detay" onclick="showKomiteDetay(${r.id})"><i class="fas fa-eye"></i> Detay</button></td>
        </tr>`;
    }).join('');
}

// ========== FILTERS ==========
async function loadFilters() {
    // Gözlem İl listesi
    const gozlemIller = await api('/api/filter/iller?modul=gozlem');
    if (gozlemIller) fillSelect('filter-gozlem-il', gozlemIller);

    // Komite İl listesi
    const komiteIller = await api('/api/filter/iller?modul=komite');
    if (komiteIller) fillSelect('filter-komite-il', komiteIller);

    // Gelişim İl listesi
    const gelisimIller = await api('/api/filter/gelisim/iller');
    if (gelisimIller) fillSelect('filter-gelisim-il', gelisimIller);

    // Dereceler
    const dereceler = await api('/api/gozlem/dereceler');
    if (dereceler) fillSelect('filter-gozlem-derece', dereceler);
}

function fillSelect(selectId, options) {
    const select = document.getElementById(selectId);
    if (!select) return;
    const currentVal = select.value;
    // Keep first option
    select.innerHTML = '<option value="">Tümü</option>';
    options.forEach(opt => {
        const o = document.createElement('option');
        o.value = opt;
        o.textContent = opt;
        select.appendChild(o);
    });
    if (currentVal) select.value = currentVal;
}

async function onGozlemIlChange() {
    const il = document.getElementById('filter-gozlem-il').value;
    const ilceSelect = document.getElementById('filter-gozlem-ilce');
    const hastaneSelect = document.getElementById('filter-gozlem-hastane');

    ilceSelect.innerHTML = '<option value="">Tümü</option>';
    hastaneSelect.innerHTML = '<option value="">Tümü</option>';

    if (il) {
        const ilceler = await api(`/api/filter/ilceler/${encodeURIComponent(il)}?modul=gozlem`);
        if (ilceler) fillSelect('filter-gozlem-ilce', ilceler);
        const hastaneler = await api(`/api/filter/hastaneler?modul=gozlem&il=${encodeURIComponent(il)}`);
        if (hastaneler) fillSelect('filter-gozlem-hastane', hastaneler);
    }
    loadGozlemFiltered();
}

async function onGozlemIlceChange() {
    const il = document.getElementById('filter-gozlem-il').value;
    const ilce = document.getElementById('filter-gozlem-ilce').value;
    const hastaneSelect = document.getElementById('filter-gozlem-hastane');

    hastaneSelect.innerHTML = '<option value="">Tümü</option>';

    if (il) {
        let url = `/api/filter/hastaneler?modul=gozlem&il=${encodeURIComponent(il)}`;
        if (ilce) url += `&ilce=${encodeURIComponent(ilce)}`;
        const hastaneler = await api(url);
        if (hastaneler) fillSelect('filter-gozlem-hastane', hastaneler);
    }
    loadGozlemFiltered();
}

async function onKomiteIlChange() {
    const il = document.getElementById('filter-komite-il').value;
    const ilceSelect = document.getElementById('filter-komite-ilce');
    const hastaneSelect = document.getElementById('filter-komite-hastane');

    ilceSelect.innerHTML = '<option value="">Tümü</option>';
    hastaneSelect.innerHTML = '<option value="">Tümü</option>';

    if (il) {
        const ilceler = await api(`/api/filter/ilceler/${encodeURIComponent(il)}?modul=komite`);
        if (ilceler) fillSelect('filter-komite-ilce', ilceler);
    }
    loadKomiteFiltered();
}

async function onKomiteIlceChange() {
    const il = document.getElementById('filter-komite-il').value;
    const ilce = document.getElementById('filter-komite-ilce').value;
    const hastaneSelect = document.getElementById('filter-komite-hastane');

    hastaneSelect.innerHTML = '<option value="">Tümü</option>';

    if (il) {
        let url = `/api/filter/hastaneler?modul=komite&il=${encodeURIComponent(il)}`;
        if (ilce) url += `&ilce=${encodeURIComponent(ilce)}`;
        const hastaneler = await api(url);
        if (hastaneler) fillSelect('filter-komite-hastane', hastaneler);
    }
    loadKomiteFiltered();
}

function clearGozlemFilters() {
    document.getElementById('filter-gozlem-il').value = '';
    document.getElementById('filter-gozlem-ilce').value = '';
    document.getElementById('filter-gozlem-hastane').value = '';
    document.getElementById('filter-gozlem-derece').value = '';
    document.getElementById('filter-gozlem-search').value = '';
    document.getElementById('filter-gozlem-info').classList.remove('visible');
    loadGozlemFiltered();
}

function debounceGozlemSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => loadGozlemFiltered(), 400);
}

// ========== PAGINATION ==========
function renderPagination(data, containerId, callback) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const { page, total_pages } = data;
    if (total_pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '';

    // Prev
    html += `<button class="page-btn" ${page <= 1 ? 'disabled' : ''} onclick="${callback.name}(${page - 1})"><i class="fas fa-chevron-left"></i></button>`;

    // Pages
    const range = 3;
    let start = Math.max(1, page - range);
    let end = Math.min(total_pages, page + range);

    if (start > 1) {
        html += `<button class="page-btn" onclick="${callback.name}(1)">1</button>`;
        if (start > 2) html += `<span style="padding:0 6px;color:#94A3B8">...</span>`;
    }

    for (let i = start; i <= end; i++) {
        html += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="${callback.name}(${i})">${i}</button>`;
    }

    if (end < total_pages) {
        if (end < total_pages - 1) html += `<span style="padding:0 6px;color:#94A3B8">...</span>`;
        html += `<button class="page-btn" onclick="${callback.name}(${total_pages})">${total_pages}</button>`;
    }

    // Next
    html += `<button class="page-btn" ${page >= total_pages ? 'disabled' : ''} onclick="${callback.name}(${page + 1})"><i class="fas fa-chevron-right"></i></button>`;

    container.innerHTML = html;
}

// ========== HIERARCHY TREE ==========
async function loadHierarchyTree() {
    const tree = await api('/api/tree/komite');
    if (!tree) return;

    const container = document.getElementById('hierarchy-tree');
    let html = '';

    const iller = Object.keys(tree).sort();
    for (const il of iller) {
        html += `<div class="tree-il">
            <div class="tree-label" onclick="toggleTree(this)">
                <i class="fas fa-chevron-right"></i>
                <i class="fas fa-map-marker-alt" style="color:#3B82F6"></i>
                <span>${esc(il)}</span>
            </div>
            <div class="tree-children">`;

        const ilceler = Object.keys(tree[il]).sort();
        for (const ilce of ilceler) {
            html += `<div class="tree-il">
                <div class="tree-label" onclick="toggleTree(this)">
                    <i class="fas fa-chevron-right"></i>
                    <i class="fas fa-map-pin" style="color:#10B981;font-size:10px"></i>
                    <span>${esc(ilce)}</span>
                </div>
                <div class="tree-children">`;

            for (const h of tree[il][ilce]) {
                html += `<div class="tree-leaf" onclick="filterFromTree('${escJs(il)}','${escJs(ilce)}','${escJs(h.hastane)}')">
                    <i class="fas fa-hospital" style="color:#94A3B8;font-size:9px;margin-right:4px"></i>
                    ${esc(h.hastane)} (${h.rapor_sayisi})
                </div>`;
            }

            html += `</div></div>`;
        }

        html += `</div></div>`;
    }

    container.innerHTML = html;
}

function toggleTree(el) {
    const children = el.nextElementSibling;
    if (children) {
        children.classList.toggle('open');
        el.classList.toggle('expanded');
    }
}

function filterFromTree(il, ilce, hastane) {
    // Komite sayfasına geç ve filtrele
    switchPage('komite-rapor');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById('nav-komite-rapor').classList.add('active');

    document.getElementById('filter-komite-il').value = il;
    onKomiteIlChange().then(() => {
        setTimeout(() => {
            document.getElementById('filter-komite-ilce').value = ilce;
            onKomiteIlceChange().then(() => {
                setTimeout(() => {
                    document.getElementById('filter-komite-hastane').value = hastane;
                    loadKomiteFiltered();
                }, 200);
            });
        }, 200);
    });
}

// ========== MODALS ==========
function showNot(title, content) {
    document.getElementById('modal-title').innerHTML = `<i class="fas fa-sticky-note"></i> ${title}`;
    document.getElementById('modal-body').innerHTML = `<p>${content.replace(/\n/g, '<br>')}</p>`;
    document.getElementById('modal-overlay').classList.add('show');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('show');
}

async function showUyeler(raporId) {
    const data = await api(`/api/komite/uyeler/${raporId}`);
    if (!data) return;

    const body = document.getElementById('uye-modal-body');
    if (data.uyeler && data.uyeler.length > 0) {
        body.innerHTML = `<ul class="member-list">${data.uyeler.map(u => {
            const initials = u.split(/\s+/).map(w => w.charAt(0)).slice(0, 2).join('').toUpperCase();
            return `<li class="member-item">
                <div class="member-avatar">${initials}</div>
                <span class="member-name">${esc(u)}</span>
            </li>`;
        }).join('')}</ul>`;
    } else {
        body.innerHTML = '<div class="empty-state" style="padding:30px"><i class="fas fa-user-slash"></i><p>Üye bilgisi bulunamadı</p></div>';
    }

    document.getElementById('uye-modal-overlay').classList.add('show');
}

function closeUyeModal() {
    document.getElementById('uye-modal-overlay').classList.remove('show');
}

async function showKomiteDetay(raporId) {
    switchPage('komite-detay');

    const data = await api(`/api/komite/detail/${raporId}`);
    if (!data) return;

    const container = document.getElementById('komite-detail-content');
    const r = data.rapor;

    let html = `
    <div class="detail-card">
        <div class="detail-card-header"><i class="fas fa-hospital"></i> Kurum Bilgileri</div>
        <div class="detail-card-body">
            <div class="detail-row"><span class="detail-label">Sağlık Tesisi Adı</span><span class="detail-value">${esc(r.hastane_adi)}</span></div>
            <div class="detail-row"><span class="detail-label">Kurum Kodu</span><span class="detail-value">${r.kurum_kodu || '-'}</span></div>
            <div class="detail-row"><span class="detail-label">İl / İlçe</span><span class="detail-value">${esc(r.il)} / ${esc(r.ilce || '-')}</span></div>
            <div class="detail-row"><span class="detail-label">Rapor Tipi</span><span class="detail-value">${esc(r.rapor_tipi)}</span></div>
            <div class="detail-row"><span class="detail-label">Değerlendirme Tarihi</span><span class="detail-value">${r.degerlendirme_tarihi || '-'}</span></div>
            <div class="detail-row"><span class="detail-label">Saat</span><span class="detail-value">${r.degerlendirme_saati || '-'}</span></div>
            <div class="detail-row"><span class="detail-label">Kaynak Dosya</span><span class="detail-value" style="font-size:12px;"><a href="javascript:void(0)" onclick="openFilePreviewModal(${r.id}, '${escJs(r.kaynak_dosya)}')" style="color: var(--primary); display: flex; align-items: center; gap: 6px; text-decoration: none; padding: 6px 10px; background: rgba(0, 84, 166, 0.08); border-radius: 6px; transition: all 0.2s; font-weight: 500;"><i class="fas fa-file-signature" style="font-size: 14px;"></i> ${esc(r.kaynak_dosya)}</a></span></div>
        </div>
    </div>`;

    // Ekip Üyeleri
    if (r.ekip_uyeleri) {
        html += `
        <div class="detail-card">
            <div class="detail-card-header"><i class="fas fa-users"></i> Değerlendirme Ekibi</div>
            <div class="detail-card-body">
                <p style="white-space:pre-line">${esc(r.ekip_uyeleri)}</p>
            </div>
        </div>`;
    }

    // Standart Değerlendirmeler
    if (data.standartlar && data.standartlar.length > 0) {
        html += `
        <div class="detail-card">
            <div class="detail-card-header"><i class="fas fa-clipboard-check"></i> Standart Değerlendirmeler (${data.standartlar.length})</div>
            <div class="detail-card-body" style="padding:0">
                <div class="table-responsive">
                    <table class="data-table">
                        <thead><tr>
                            <th>Standart No</th>
                            <th>Uygunluk Durumu</th>
                            <th>Eksikler</th>
                            <th>Sorumlu</th>
                            <th>Son Durum</th>
                        </tr></thead>
                        <tbody>`;

        data.standartlar.forEach(s => {
            const uygunlukBadge = getUygunlukBadge(s.uygunluk_durumu);
            const sondurumBadge = getSondurumBadge(s.son_durum);

            html += `<tr>
                <td><strong>${esc(s.standart_no || '-')}</strong></td>
                <td>${uygunlukBadge}</td>
                <td>${s.eksikler ? `<span class="not-cell" onclick="showNot('Eksikler - Standart ${esc(s.standart_no)}','${escJs(s.eksikler)}')">${esc((s.eksikler || '').substring(0, 80))}...</span>` : '-'}</td>
                <td>${s.sorumlu ? `<span class="not-cell" onclick="showNot('Sorumlu - Standart ${esc(s.standart_no)}','${escJs(s.sorumlu)}')">${esc((s.sorumlu || '').substring(0, 50))}...</span>` : '-'}</td>
                <td>${sondurumBadge}</td>
            </tr>`;
        });

        html += `</tbody></table></div></div></div>`;
    }

    // Komisyon Kararları
    if (data.kararlar && data.kararlar.length > 0) {
        data.kararlar.forEach(k => {
            html += `
            <div class="detail-card">
                <div class="detail-card-header"><i class="fas fa-gavel"></i> Komisyon Kararı</div>
                <div class="detail-card-body">
                    ${k.iyilestirme_alanlari ? `<div class="detail-row"><span class="detail-label">İyileştirmeye Açık Alanlar</span><span class="detail-value">${esc(k.iyilestirme_alanlari)}</span></div>` : ''}
                    ${k.komisyon_karari ? `<div class="detail-row"><span class="detail-label">Komisyon Kararı</span><span class="detail-value">${esc(k.komisyon_karari)}</span></div>` : ''}
                    ${k.muafiyetler ? `<div class="detail-row"><span class="detail-label">Muafiyetler</span><span class="detail-value">${esc(k.muafiyetler)}</span></div>` : ''}
                </div>
            </div>`;
        });
    }

    container.innerHTML = html;
}

function getUygunlukBadge(durum) {
    if (!durum) return '<span style="color:var(--text-muted)">-</span>';
    const d = durum.toLowerCase();
    if (d.includes('kısmen')) return `<span class="uygunluk-badge uygunluk-kismenkarsilaniyor"><i class="fas fa-minus-circle"></i> ${esc(durum)}</span>`;
    if (d.includes('karşılanmıyor')) return `<span class="uygunluk-badge uygunluk-karsilanmiyor"><i class="fas fa-times-circle"></i> ${esc(durum)}</span>`;
    if (d.includes('karşılanıyor')) return `<span class="uygunluk-badge uygunluk-karsilaniyor"><i class="fas fa-check-circle"></i> ${esc(durum)}</span>`;
    return `<span>${esc(durum)}</span>`;
}

function getSondurumBadge(durum) {
    if (!durum) return '<span style="color:var(--text-muted)">-</span>';
    const d = durum.toLowerCase();
    if (d.includes('tamamlandı') && !d.includes('tamamlanmadı')) return `<span class="sondurum-badge sondurum-tamamlandi"><i class="fas fa-check"></i> Tamamlandı</span>`;
    if (d.includes('tamamlanmadı')) return `<span class="sondurum-badge sondurum-tamamlanmadi"><i class="fas fa-times"></i> Tamamlanmadı</span>`;
    if (d.includes('devam')) return `<span class="sondurum-badge sondurum-devam"><i class="fas fa-spinner"></i> Devam Ediyor</span>`;
    return `<span>${esc(durum)}</span>`;
}

// ========== CHART MODALS ==========
function showGozlemChart() {
    document.getElementById('chart-modal-title').innerHTML = '<i class="fas fa-chart-bar"></i> Gözlem Formları - Grafiksel Analiz';
    document.getElementById('chart-modal-overlay').classList.add('show');

    // Derece dağılımını al ve çiz
    api('/api/dashboard/stats').then(stats => {
        if (!stats || !stats.derece_dagilimi) return;

        destroyChart('modal');
        const ctx = document.getElementById('chart-modal-canvas');

        const colorMap = {
            'Çok İyi': '#10B981', 'İyi': '#22C55E', 'Orta': '#EAB308',
            'Zayıf': '#F97316', 'Kötü': '#F97316', 'Çok Zayıf': '#EF4444', 'Çok Kötü': '#EF4444'
        };

        chartInstances['modal'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: stats.derece_dagilimi.map(d => d.derece),
                datasets: [{
                    label: 'Kayıt Sayısı',
                    data: stats.derece_dagilimi.map(d => d.sayi),
                    backgroundColor: stats.derece_dagilimi.map(d => colorMap[d.derece] || '#94A3B8'),
                    borderRadius: 12,
                    borderSkipped: false,
                    barThickness: 60
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1E293B', padding: 12,
                        titleFont: { family: 'Inter', size: 13 },
                        bodyFont: { family: 'Inter', size: 12 }
                    }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#F1F5F9' }, ticks: { font: { family: 'Inter', size: 12 } } },
                    x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 13, weight: 600 } } }
                }
            }
        });
    });
}

function showKomiteChart() {
    document.getElementById('chart-modal-title').innerHTML = '<i class="fas fa-chart-bar"></i> Komite Raporları - Grafiksel Analiz';
    document.getElementById('chart-modal-overlay').classList.add('show');

    api('/api/dashboard/stats').then(stats => {
        if (!stats) return;

        destroyChart('modal');
        const ctx = document.getElementById('chart-modal-canvas');

        const colorMap = {
            'Karşılanıyor': '#10B981',
            'Kısmen Karşılanıyor': '#F59E0B',
            'Karşılanmıyor': '#EF4444'
        };

        const data = stats.uygunluk_dagilimi || [];

        chartInstances['modal'] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(d => d.durum),
                datasets: [{
                    data: data.map(d => d.sayi),
                    backgroundColor: data.map(d => colorMap[d.durum] || '#94A3B8'),
                    borderWidth: 4,
                    borderColor: '#FFFFFF'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '50%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { font: { family: 'Inter', size: 13 }, padding: 20, usePointStyle: true }
                    }
                }
            }
        });
    });
}

function closeChartModal() {
    document.getElementById('chart-modal-overlay').classList.remove('show');
    destroyChart('modal');
}

// ========== UTILS ==========
function esc(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function escJs(str) {
    if (!str) return '';
    return String(str)
        .replace(/\\/g, '\\\\')
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '');
}

// Keyboard shortcuts
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        closeModal();
        closeUyeModal();
        closeChartModal();
        closeGorselModal();
    }
});

// ========== GÖRSELLER CAROUSEL (Anti-Gravity) ==========
let gorselList = [];
let currentGorselIndex = 0;
let currentGorselHastane = '';

function normalizeName(name) {
    if (!name) return "";
    // NFD: Karakterleri bileşenlerine ayırır (İ -> I + nokta markı)
    let s = name.toString().normalize('NFD').replace(/[\u0300-\u036f]/g, "");
    // Noktaları sil
    s = s.replace(/\./g, '');
    // Boşlukları temizle ve BÜYÜK harf yap (NFD sonrası I olduğu için güvenli)
    return s.trim().toUpperCase().split(/\s+/).join(' ');
}

async function fetchGorselHastaneler() {
    try {
        const res = await fetch('/api/gorseller/mevcut');
        const data = await res.json();
        // Backend zaten normalize gönderiyor ama JS tarafında da Set içinde normalize tutalım
        gorseliOlanHastaneler = new Set(data.map(h => normalizeName(h)));
    } catch (e) {
        console.error("Gorseli olan hastaneler alinamadi", e);
    }
}

async function openGorselModal(hastane_adi) {
    if (!hastane_adi) return;
    currentGorselHastane = hastane_adi;

    document.getElementById('gorsel-modal-overlay').classList.add('show');
    document.getElementById('gorsel-modal-title').innerHTML = `<i class="fas fa-images"></i> Saha Görselleri - ${esc(hastane_adi)}`;

    // Hide components temporarily
    document.getElementById('gorsel-carousel-container').style.display = 'none';
    document.getElementById('gorsel-empty-state').style.display = 'none';
    document.getElementById('gorsel-current-img').style.display = 'none';
    document.getElementById('gorsel-admin-controls').style.display = 'none';

    try {
        const res = await fetch(`/api/gorseller/hastane/${encodeURIComponent(hastane_adi)}`);
        gorselList = await res.json();
        currentGorselIndex = 0;

        if (gorselList.length > 0) {
            document.getElementById('gorsel-carousel-container').style.display = 'flex';
            document.getElementById('gorsel-admin-controls').style.display = 'flex';
            renderGorsel();
        } else {
            document.getElementById('gorsel-empty-state').style.display = 'block';
        }
    } catch (e) {
        console.error("Görsel listesi yüklenemedi", e);
        document.getElementById('gorsel-empty-state').style.display = 'block';
    }
}

function renderGorsel() {
    if (gorselList.length === 0) return;
    const g = gorselList[currentGorselIndex];

    const imgElement = document.getElementById('gorsel-current-img');
    const safePath = g.dosya_yolu.replace(/\\/g, '/');
    imgElement.src = `/gorsel/${encodeURI(safePath)}?t=${new Date().getTime()}`;
    imgElement.style.display = 'inline-block';

    document.getElementById('gorsel-current-hastane').textContent = g.hastane_adi || 'Bilinmeyen Tesis';
    document.getElementById('gorsel-counter').textContent = `${currentGorselIndex + 1} / ${gorselList.length}`;

    document.getElementById('gorsel-prev-btn').disabled = (currentGorselIndex === 0 && gorselList.length > 1) ? false : (gorselList.length <= 1);
    document.getElementById('gorsel-next-btn').disabled = (currentGorselIndex === gorselList.length - 1 && gorselList.length > 1) ? false : (gorselList.length <= 1);
}

function prevGorsel() {
    if (gorselList.length > 0) {
        currentGorselIndex = (currentGorselIndex - 1 + gorselList.length) % gorselList.length;
        renderGorsel();
    }
}

function nextGorsel() {
    if (gorselList.length > 0) {
        currentGorselIndex = (currentGorselIndex + 1) % gorselList.length;
        renderGorsel();
    }
}

async function uploadGorsel(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('hastane_adi', currentGorselHastane);

    try {
        const res = await fetch('/api/gorseller/upload', {
            method: 'POST',
            body: formData
        });
        const result = await res.json();
        if (result.success) {
            // Yükleme başarılı, yeniden listele
            openGorselModal(currentGorselHastane);

            // Set'i güncelle ve tabloyu render et
            if (!gorseliOlanHastaneler.has(currentGorselHastane)) {
                gorseliOlanHastaneler.add(currentGorselHastane);
                // Tabloyu refreshleyebiliriz
                loadGozlemData(gozlemPage);
            }
        } else {
            alert("Yükleme başarısız: " + result.error);
        }
    } catch (e) {
        console.error("Yükleme hatası:", e);
        alert("Bir hata oluştu.");
    }
}

async function deleteCurrentGorsel() {
    if (gorselList.length === 0) return;
    if (!confirm('Bu görseli silmek istediğinize emin misiniz?')) return;

    const g = gorselList[currentGorselIndex];

    try {
        const res = await fetch('/api/gorseller/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dosya_yolu: g.dosya_yolu })
        });
        const result = await res.json();

        if (result.success) {
            // Listeden çıkar
            gorselList.splice(currentGorselIndex, 1);
            if (gorselList.length > 0) {
                // Sildiğimiz elemandan sonrakine (veya öncekine) kay
                currentGorselIndex = Math.max(0, currentGorselIndex - 1);
                renderGorsel();
            } else {
                // Hiç kalmadı, state'i güncelle
                document.getElementById('gorsel-carousel-container').style.display = 'none';
                document.getElementById('gorsel-admin-controls').style.display = 'none';
                document.getElementById('gorsel-empty-state').style.display = 'block';

                gorseliOlanHastaneler.delete(currentGorselHastane);
                // Tabloyu refreshleyebiliriz
                loadGozlemData(gozlemPage);
            }
        } else {
            alert("Silme başarısız: " + result.error);
        }
    } catch (e) {
        console.error("Silme hatası:", e);
        alert("Bir hata oluştu.");
    }
}

function closeGorselModal() {
    const overlay = document.getElementById('gorsel-modal-overlay');
    if (overlay) overlay.classList.remove('show');
    gorselList = [];
    currentGorselIndex = 0;
    currentGorselHastane = '';
}

function escJs(str) {
    if (!str) return '';
    return str.toString()
        .replace(/\\/g, '\\\\')
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '\\r');
}

// ========== FILE PREVIEW MODAL ==========
function openFilePreviewModal(raporId, dosyaAd) {
    document.getElementById('file-preview-title').innerHTML = `<i class="fas fa-file-alt"></i> ${esc(dosyaAd)}`;
    document.getElementById('file-preview-modal-overlay').classList.add('show');

    document.getElementById('file-preview-loading').style.display = 'block';
    document.getElementById('file-preview-iframe').style.display = 'none';
    document.getElementById('file-preview-content').style.display = 'none';

    document.getElementById('file-preview-iframe').src = '';
    document.getElementById('file-preview-content').innerHTML = '';

    const url = `/api/komite/preview/${raporId}?t=${new Date().getTime()}`;
    document.getElementById('file-preview-iframe').src = url;

    document.getElementById('file-preview-iframe').onload = function () {
        document.getElementById('file-preview-loading').style.display = 'none';
        document.getElementById('file-preview-iframe').style.display = 'block';
    };

    // Hata durumunda (eğer iframe içeriğinde 404/500 dönerse) onload yine tetiklenir, 
    // hata mesajı iframe içinde app.py'den gelen formatta gösterilir.
}

// ========== GELİŞİM DATA ==========
async function loadGelisimData(page) {
    gelisimPage = page || 1;
    const il = document.getElementById('filter-gelisim-il').value;
    const hastane = document.getElementById('filter-gelisim-hastane').value;
    const search = document.getElementById('filter-gelisim-search').value;

    let url = `/api/gelisim/list?page=${gelisimPage}&per_page=50`;
    if (il) url += `&il=${encodeURIComponent(il)}`;
    if (hastane) url += `&hastane=${encodeURIComponent(hastane)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    const data = await api(url);
    if (!data) return;

    renderGelisimTable(data.data);
    renderPagination(data, 'gelisim-pagination', loadGelisimData);

    // Rozeti güncelle
    const badge = document.getElementById('gelisim-count-badge');
    if (badge) {
        badge.textContent = `${(data.total || 0).toLocaleString('tr-TR')} KAYIT`;
    }

    const info = document.getElementById('filter-gelisim-info');
    if (info) {
        if (data.total > 0) {
            info.textContent = `${data.total.toLocaleString('tr-TR')} kayıt bulundu`;
            info.classList.add('visible');
        } else {
            info.textContent = 'Kayıt bulunamadı';
            info.classList.add('visible');
        }
    }
}

function renderGelisimTable(rows) {
    const tbody = document.getElementById('gelisim-tbody');
    if (!tbody) {
        return;
    }

    if (!rows || !rows.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state" style="padding:40px"><i class="fas fa-inbox" style="font-size:32px;opacity:0.3"></i><p>Kayıt bulunamadı</p></td></tr>';
        return;
    }

    try {
        const html = rows.map((r, index) => {
            if (!r) return '';
            return `
                <tr>
                    <td style="font-weight:600">${esc(r.il)}</td>
                    <td class="hastane-cell" style="color:var(--primary); font-weight:700">${esc(r.hastane_adi)}</td>
                    <td style="font-size:12px">${esc(r.kurum_hedefleri || '-')}</td>
                    <td style="text-align:center">${esc(r.gerceklesme_suresi || '-')}</td>
                    <td style="font-size:11px">${esc(r.mevcut_durum ? (r.mevcut_durum.length > 150 ? r.mevcut_durum.substring(0, 150) + '...' : r.mevcut_durum) : '-')}</td>
                    <td style="font-size:11px">${esc(r.cozum_secenekleri ? (r.cozum_secenekleri.length > 150 ? r.cozum_secenekleri.substring(0, 150) + '...' : r.cozum_secenekleri) : '-')}</td>
                    <td>
                        <div style="font-size:10px; color:var(--text-muted)">Takvim: ${esc(r.uygulama_takvimi || '-')}</div>
                        <div style="font-size:10px; color:var(--primary)">İşbirliği: ${esc(r.isbirligi_plani || '-')}</div>
                    </td>
                </tr>
            `;
        }).join('');

        tbody.innerHTML = html;
    } catch (err) {
        console.error('Render hatası:', err);
        tbody.innerHTML = `<tr><td colspan="7" class="alert alert-danger">Tablo oluşturulurken hata: ${err.message}</td></tr>`;
    }
}

async function onGelisimIlChange() {
    const il = document.getElementById('filter-gelisim-il').value;
    const hospSelect = document.getElementById('filter-gelisim-hastane');

    hospSelect.innerHTML = '<option value="">Tümü</option>';

    if (il) {
        const hastaneler = await api(`/api/filter/gelisim/hastaneler?il=${encodeURIComponent(il)}`);
        if (hastaneler) fillSelect('filter-gelisim-hastane', hastaneler);
    }
    loadGelisimData(1);
}


function clearGelisimFilters() {
    document.getElementById('filter-gelisim-il').value = '';
    document.getElementById('filter-gelisim-hastane').value = '';
    document.getElementById('filter-gelisim-search').value = '';
    if (document.getElementById('filter-gelisim-info')) {
        document.getElementById('filter-gelisim-info').classList.remove('visible');
    }
    loadGelisimData(1);
}

function debounceGelisimSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => loadGelisimData(1), 400);
}

function closeFilePreviewModal(force) {
    if (force === true || (event && event.target.id === 'file-preview-modal-overlay')) {
        document.getElementById('file-preview-modal-overlay').classList.remove('show');
        document.getElementById('file-preview-iframe').src = '';
        document.getElementById('file-preview-content').innerHTML = '';
    }
}
// ========== GELİŞİM HARİTASI (HIGHCHARTS MAPS) ==========
function trUpper(str) {
    if (!str) return '';
    return str.toString()
        .replace(/i/g, 'İ')
        .replace(/ı/g, 'I')
        .replace(/ş/g, 'Ş')
        .replace(/ç/g, 'Ç')
        .replace(/ğ/g, 'Ğ')
        .replace(/ü/g, 'Ü')
        .replace(/ö/g, 'Ö')
        .toUpperCase();
}

// Utility: HTML Escape
function esc(str) {
    if (!str) return '';
    return str.toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function escJs(str) {
    if (!str) return '';
    return str.toString().replace(/'/g, "\\'").replace(/"/g, '\\"');
}

function filterByCity(cityName) {
    const ilSelect = document.getElementById('filter-gelisim-il');
    if (ilSelect) {
        const normCity = trUpper(cityName);
        let found = false;
        for (let i = 0; i < ilSelect.options.length; i++) {
            const optVal = trUpper(ilSelect.options[i].value);
            if (optVal === normCity) {
                ilSelect.value = ilSelect.options[i].value;
                found = true;
                break;
            }
        }
        if (found) onGelisimIlChange();
    }
}

async function initGelisimMap() {
    const container = document.getElementById('gelisim-map-container');
    if (!container) return;

    if (gelisimMap) {
        loadGelisimMapData();
        return;
    }

    container.innerHTML = `
        <div class="d-flex flex-column align-items-center justify-content-center h-100" style="background: rgba(248, 250, 252, 0.5); border-radius: 12px;">
            <div class="spinner-border text-primary mb-3" role="status" style="width: 3rem; height: 3rem;"></div>
            <div class="fw-bold text-secondary">Harita Verileri Yükleniyor...</div>
        </div>`;

    try {
        const topology = await fetch('/static/js/tr-all.json').then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}: Veri yüklenemedi`);
            return res.json();
        });

        gelisimMap = Highcharts.mapChart('gelisim-map-container', {
            chart: {
                map: topology,
                backgroundColor: 'transparent',
                spacing: [15, 15, 15, 15],
                style: { fontFamily: "'Inter', sans-serif" }
            },
            title: { text: null },
            credits: { enabled: false },
            mapNavigation: {
                enabled: true,
                buttonOptions: {
                    verticalAlign: 'bottom',
                    theme: {
                        fill: 'white',
                        stroke: '#e2e8f0',
                        'stroke-width': 1,
                        r: 6,
                        states: { hover: { fill: '#f8fafc' } }
                    }
                }
            },
            colorAxis: {
                min: 0,
                stops: [
                    [0, '#f8fafc'],   // Slate 50
                    [0.2, '#e0e7ff'], // Indigo 100
                    [0.6, '#6366f1'], // Indigo 500
                    [1, '#4f46e5']    // Indigo 600
                ]
            },
            tooltip: {
                backgroundColor: 'rgba(255, 255, 255, 0.98)',
                borderWidth: 0,
                borderRadius: 12,
                shadow: true,
                useHTML: true,
                headerFormat: '<div style="padding: 8px 12px; border-bottom: 1px solid #f1f5f9; margin-bottom: 4px;"><b style="color: #1e293b; font-size: 13px;">{point.key}</b></div>',
                pointFormat: '<div style="padding: 0 12px 8px;"><span style="color: #6366f1; font-weight: 600; font-size: 16px;">{point.value}</span> <span style="color: #64748b; font-size: 12px;">Gelişim Planı</span></div>',
                followPointer: true
            },
            plotOptions: {
                series: {
                    cursor: 'pointer',
                    borderColor: '#ffffff',
                    borderWidth: 0.8,
                    states: {
                        hover: { color: '#4f46e5', borderColor: '#ffffff', borderWidth: 2 }
                    },
                    point: {
                        events: {
                            click: function () {
                                filterByCity(this.name);
                            }
                        }
                    }
                }
            },
            series: [{
                data: [],
                name: 'Gelişim Planı',
                allAreas: true,
                allowPointSelect: true,
                joinBy: ['hc-key', 'hc-key'],
                dataLabels: {
                    enabled: true,
                    format: '{point.name}',
                    style: { fontSize: '10px', fontWeight: '500', color: '#1e293b', textOutline: '2px rgba(255,255,255,0.7)' }
                }
            }]
        });

        loadGelisimMapData();
    } catch (err) {
        console.error('Harita yükleme hatası:', err);
        container.innerHTML = `<div class="alert alert-danger m-4">
            <b>Harita Yüklenemedi!</b><br>
            <small>${err.message}</small><br>
            Lütfen tarayıcı konsolunu kontrol edin (F12).
        </div>`;
    }
}

async function loadGelisimMapData() {
    if (!gelisimMap) return;
    const stats = await api('/api/stats/gelisim/iller');
    if (!stats) return;

    const ilMapping = {
        'ADANA': 'tr-aa', 'ADIYAMAN': 'tr-ad', 'AFYONKARAHİSAR': 'tr-af', 'AĞRI': 'tr-ag',
        'AMASYA': 'tr-am', 'ANKARA': 'tr-an', 'ANTALYA': 'tr-al', 'ARTVİN': 'tr-av',
        'AYDIN': 'tr-ay', 'BALIKESİR': 'tr-bk', 'BİLECİK': 'tr-bc', 'BİNGÖL': 'tr-bg',
        'BİTLİS': 'tr-bt', 'BOLU': 'tr-bl', 'BURDUR': 'tr-bd', 'BURSA': 'tr-bu',
        'ÇANAKKALE': 'tr-ck', 'ÇANKIRI': 'tr-ci', 'ÇORUM': 'tr-cm', 'DENİZLİ': 'tr-dn',
        'DİYARBAKIR': 'tr-dy', 'EDİRNE': 'tr-ed', 'ELAZIĞ': 'tr-eg', 'ERZİNCAN': 'tr-en',
        'ERZURUM': 'tr-em', 'ESKİŞEHİR': 'tr-es', 'GAZİANTEP': 'tr-ga', 'GİRESUN': 'tr-gi',
        'GÜMÜŞHANE': 'tr-gu', 'HAKKARİ': 'tr-hk', 'HATAY': 'tr-ht', 'ISPARTA': 'tr-ip',
        'MERSİN': 'tr-ic', 'İSTANBUL': 'tr-ib', 'İZMİR': 'tr-iz', 'KARS': 'tr-ka',
        'KASTAMONU': 'tr-ks', 'KAYSERİ': 'tr-ky', 'KIRKLARELİ': 'tr-kl', 'KIRŞEHİR': 'tr-kh',
        'KOCAELİ': 'tr-kc', 'KONYA': 'tr-ko', 'KÜTAHYA': 'tr-ku', 'MALATYA': 'tr-ml',
        'MANİSA': 'tr-mn', 'KAHRAMANMARAŞ': 'tr-km', 'MARDİN': 'tr-mr', 'MUĞLA': 'tr-mg',
        'MUŞ': 'tr-ms', 'NEVŞEHİR': 'tr-nv', 'NİĞDE': 'tr-ng', 'ORDU': 'tr-or',
        'RİZE': 'tr-ri', 'SAKARYA': 'tr-sk', 'SAMSUN': 'tr-ss', 'SİİRT': 'tr-si',
        'SİNOP': 'tr-sp', 'SİVAS': 'tr-sv', 'TEKİRDAĞ': 'tr-tg', 'TOKAT': 'tr-tt',
        'TRABZON': 'tr-tb', 'TUNCELİ': 'tr-tc', 'ŞANLIURFA': 'tr-su', 'UŞAK': 'tr-us',
        'VAN': 'tr-va', 'YOZGAT': 'tr-yz', 'ZONGULDAK': 'tr-zo', 'AKSARAY': 'tr-ak',
        'BAYBURT': 'tr-bb', 'KARAMAN': 'tr-kr', 'KIRIKKALE': 'tr-kk', 'BATMAN': 'tr-bm',
        'ŞIRNAK': 'tr-sr', 'BARTIN': 'tr-br', 'ARDAHAN': 'tr-ar', 'IĞDIR': 'tr-ig',
        'YALOVA': 'tr-yl', 'KARABÜK': 'tr-kb', 'KİLİS': 'tr-ki', 'OSMANİYE': 'tr-os',
        'DÜZCE': 'tr-du'
    };

    const mapData = [];
    for (const [il, count] of Object.entries(stats)) {
        const dbName = il; // Backend zaten map_normalize ile gönderiyor
        const mapKey = ilMapping[dbName];
        if (mapKey) {
            mapData.push({ 'hc-key': mapKey, value: count });
        } else {
            console.warn('ilMapping missing for:', dbName);
            mapData.push({ name: il, value: count });
        }
    }
    console.log('Prepared mapData:', mapData);
    if (gelisimMap.series && gelisimMap.series[0]) {
        gelisimMap.series[0].setData(mapData);
    }
}

function resetGelisimMap() {
    const ilSelect = document.getElementById('filter-gelisim-il');
    if (ilSelect) {
        ilSelect.value = '';
        onGelisimIlChange();
    }
    if (gelisimMap && gelisimMap.series && gelisimMap.series[0]) {
        gelisimMap.series[0].points.forEach(p => p.select(false));
    }
}
