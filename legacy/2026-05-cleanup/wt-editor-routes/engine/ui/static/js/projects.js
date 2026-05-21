/**
 * Proje yönetimi - Yeni proje oluşturma ve seçme
 */

// Yeni proje modal'ını aç
function openProjectWizard() {
  const modal = document.getElementById('new-project-modal');
  if (!modal) {
    console.error('Modal element bulunamadı');
    return;
  }
  modal.style.display = 'flex';
  const input = document.getElementById('project-name-input');
  if (input) input.focus();
}

// Modal'ı kapat
function closeProjectWizard() {
  const modal = document.getElementById('new-project-modal');
  if (modal) {
    modal.style.display = 'none';
  }
  const input = document.getElementById('project-name-input');
  if (input) input.value = '';
}

// Modal dışını tıklandığında kapat
document.addEventListener('click', function(event) {
  const modal = document.getElementById('new-project-modal');
  if (modal && event.target === modal) {
    closeProjectWizard();
  }
});

// Yeni proje oluştur
async function createProject() {
  const input = document.getElementById('project-name-input');
  const name = input ? input.value.trim() : '';

  if (!name) {
    alert('Proje adı gerekli!');
    return;
  }

  // Proje adı doğrulaması
  if (!/^[a-zA-Z0-9\-_]+$/.test(name)) {
    alert('Proje adı sadece alfanümerik karakterler, tire ve alt çizgi içerebilir!');
    return;
  }

  const btn = event.target;
  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = '⏳ Oluşturuluyor...';

  try {
    const res = await fetch('/api/projects/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || 'Proje oluşturulamadı');
    }

    alert(`✅ Proje "${name}" başarıyla oluşturuldu!`);
    closeProjectWizard();
    loadProjects();

  } catch (error) {
    console.error('Hata:', error);
    alert(`❌ Hata: ${error.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

// Projeleri yükle ve selector'ı doldur
async function loadProjects() {
  try {
    const res = await fetch('/api/projects');
    if (!res.ok) throw new Error('Proje listesi yüklenemedi');

    const data = await res.json();
    const select = document.getElementById('active-project-select');

    if (!select) return; // Select element yoksa işlem yapma

    select.innerHTML = '<option value="">📁 Proje Seçin...</option>';

    if (data.projects && Array.isArray(data.projects)) {
      data.projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.name;
        const activeIndicator = p.is_active ? ' ✓' : '';
        opt.textContent = `${p.name}${activeIndicator}`;
        select.appendChild(opt);
      });
    }
  } catch (error) {
    console.error('Proje yükleme hatası:', error);
  }
}

// Proje değiştir
async function switchProject(projectName) {
  if (!projectName) return;

  try {
    const res = await fetch('/api/projects/open', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: projectName })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || 'Proje açılamadı');
    }

    alert(`✅ Proje "${projectName}" açıldı`);
    // Dashboard'u yenile
    setTimeout(() => location.reload(), 500);

  } catch (error) {
    console.error('Proje açma hatası:', error);
    alert(`❌ Hata: ${error.message}`);
    // Selector'ı reset et
    const select = document.getElementById('active-project-select');
    if (select) select.value = '';
  }
}

// Sayfa yüklendiğinde projeleri listele
document.addEventListener('DOMContentLoaded', function() {
  loadProjects();

  // Enter tuşu ile oluştur
  const input = document.getElementById('project-name-input');
  if (input) {
    input.addEventListener('keyup', function(event) {
      if (event.key === 'Enter') {
        createProject();
      }
    });
  }
});
