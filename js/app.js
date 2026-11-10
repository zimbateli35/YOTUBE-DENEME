/* MiniHome - Samsung Tizen TV için reklamsız, minimal ana ekran */
(function () {
  'use strict';

  var STORE_KEY = 'minihome.favorites';
  var KEY = {
    LEFT: 37, UP: 38, RIGHT: 39, DOWN: 40, ENTER: 13, BACK: 10009, ESC: 27,
    RED: 403, GREEN: 404, YELLOW: 405, BLUE: 406
  };
  var isTizen = typeof window.tizen !== 'undefined';

  // Ana ekranda kendimizi listelememek için
  var selfId = '';
  try { selfId = tizen.application.getCurrentApplication().appInfo.id; } catch (e) {}

  var state = {
    view: 'home',
    favorites: loadFavorites(),
    installed: [],
    focus: { home: 0, picker: 0 }
  };

  /* ---------- Depolama ---------- */
  function loadFavorites() {
    try { return JSON.parse(localStorage.getItem(STORE_KEY)) || []; }
    catch (e) { return []; }
  }
  function saveFavorites() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(state.favorites)); } catch (e) {}
  }

  /* ---------- Saat ---------- */
  var days = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi'];
  var months = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz',
    'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function tick() {
    var d = new Date();
    document.getElementById('clock').textContent = pad(d.getHours()) + ':' + pad(d.getMinutes());
    document.getElementById('date').textContent =
      d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear() + ', ' + days[d.getDay()];
    var h = d.getHours();
    document.getElementById('greeting').textContent =
      h < 6 ? 'İyi geceler' : h < 12 ? 'Günaydın' : h < 18 ? 'İyi günler' : 'İyi akşamlar';
  }

  /* ---------- Uygulama listesi ---------- */
  function loadInstalledApps(cb) {
    if (!isTizen) { // Bilgisayarda tarayıcıda deneme için sahte liste
      cb(['YouTube', 'Netflix', 'Prime Video', 'Disney+', 'Spotify', 'Plex', 'Ayarlar', 'Tarayıcı']
        .map(function (n, i) { return { id: 'demo.' + i, name: n, icon: '' }; }));
      return;
    }
    tizen.application.getAppsInfo(function (list) {
      var apps = list.filter(function (a) { return a.show && a.id !== selfId; })
        .map(function (a) { return { id: a.id, name: a.name, icon: a.iconPath || '' }; })
        .sort(function (a, b) { return a.name.localeCompare(b.name, 'tr'); });
      cb(apps);
    }, function (err) {
      toast('Uygulama listesi alınamadı: ' + err.message);
      cb([]);
    });
  }

  function launch(app) {
    if (!isTizen) { toast(app.name + ' açılıyor (demo)'); return; }
    tizen.application.launch(app.id, null, function (err) {
      toast(app.name + ' açılamadı: ' + err.message);
    });
  }

  /* ---------- Çizim ---------- */
  function tileEl(app, extraClass) {
    var el = document.createElement('div');
    el.className = 'tile' + (extraClass ? ' ' + extraClass : '');
    var iconHtml;
    if (app.icon) {
      iconHtml = '<img src="' + app.icon + '" alt="">';
    } else {
      iconHtml = '<div class="letter">' + (app.letter || app.name.charAt(0).toUpperCase()) + '</div>';
    }
    el.innerHTML = iconHtml + '<div class="name"></div><div class="check">✓</div>';
    el.querySelector('.name').textContent = app.name;
    var img = el.querySelector('img');
    if (img) img.onerror = function () {
      var l = document.createElement('div');
      l.className = 'letter';
      l.textContent = app.name.charAt(0).toUpperCase();
      img.parentNode.replaceChild(l, img);
    };
    return el;
  }

  function renderHome() {
    var grid = document.getElementById('grid');
    grid.innerHTML = '';
    state.favorites.forEach(function (app) { grid.appendChild(tileEl(app)); });
    grid.appendChild(tileEl({ name: 'Uygulama ekle', letter: '+' }, 'add'));
    clampFocus('home');
  }

  function renderPicker() {
    var grid = document.getElementById('pickerGrid');
    grid.innerHTML = '';
    state.installed.forEach(function (app) {
      grid.appendChild(tileEl(app, isFavorite(app.id) ? 'selected' : ''));
    });
    clampFocus('picker');
  }

  function tiles() {
    return document.querySelectorAll('#' + (state.view === 'home' ? 'grid' : 'pickerGrid') + ' .tile');
  }

  function clampFocus(view) {
    var count = document.querySelectorAll('#' + (view === 'home' ? 'grid' : 'pickerGrid') + ' .tile').length;
    state.focus[view] = Math.max(0, Math.min(state.focus[view], count - 1));
    if (view === state.view) paintFocus();
  }

  function paintFocus() {
    var list = tiles();
    for (var i = 0; i < list.length; i++) list[i].classList.remove('focus');
    var el = list[state.focus[state.view]];
    if (el) {
      el.classList.add('focus');
      if (el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
    }
  }

  /* ---------- Uzaktan kumanda ile gezinme (uzamsal) ---------- */
  function move(dir) {
    var list = tiles();
    var cur = list[state.focus[state.view]];
    if (!cur) return;
    var a = cur.getBoundingClientRect();
    var ax = a.left + a.width / 2, ay = a.top + a.height / 2;
    var best = -1, bestScore = Infinity;
    for (var i = 0; i < list.length; i++) {
      if (list[i] === cur) continue;
      var b = list[i].getBoundingClientRect();
      var dx = b.left + b.width / 2 - ax, dy = b.top + b.height / 2 - ay;
      var ok = (dir === 'left' && dx < -1) || (dir === 'right' && dx > 1) ||
               (dir === 'up' && dy < -1) || (dir === 'down' && dy > 1);
      if (!ok) continue;
      var main = (dir === 'left' || dir === 'right') ? Math.abs(dx) : Math.abs(dy);
      var cross = (dir === 'left' || dir === 'right') ? Math.abs(dy) : Math.abs(dx);
      var score = main + cross * 3;
      if (score < bestScore) { bestScore = score; best = i; }
    }
    if (best >= 0) { state.focus[state.view] = best; paintFocus(); }
  }

  /* ---------- Eylemler ---------- */
  function isFavorite(id) {
    return state.favorites.some(function (f) { return f.id === id; });
  }

  function showView(name) {
    state.view = name;
    document.getElementById('home').classList.toggle('active', name === 'home');
    document.getElementById('picker').classList.toggle('active', name === 'picker');
    paintFocus();
  }

  function openPicker() {
    loadInstalledApps(function (apps) {
      state.installed = apps;
      renderPicker();
      showView('picker');
    });
  }

  function onEnter() {
    var i = state.focus[state.view];
    if (state.view === 'home') {
      if (i >= state.favorites.length) openPicker();
      else launch(state.favorites[i]);
    } else {
      var app = state.installed[i];
      if (!app) return;
      if (isFavorite(app.id)) {
        state.favorites = state.favorites.filter(function (f) { return f.id !== app.id; });
      } else {
        state.favorites.push(app);
      }
      saveFavorites();
      tiles()[i].classList.toggle('selected');
    }
  }

  function removeFocused() {
    var i = state.focus.home;
    if (state.view !== 'home' || i >= state.favorites.length) return;
    var removed = state.favorites.splice(i, 1)[0];
    saveFavorites();
    renderHome();
    toast(removed.name + ' kaldırıldı');
  }

  function shiftFocused(delta) {
    var i = state.focus.home, j = i + delta;
    if (state.view !== 'home' || i >= state.favorites.length || j < 0 || j >= state.favorites.length) return;
    var tmp = state.favorites[i];
    state.favorites[i] = state.favorites[j];
    state.favorites[j] = tmp;
    saveFavorites();
    state.focus.home = j;
    renderHome();
  }

  function onBack() {
    if (state.view === 'picker') {
      renderHome();
      showView('home');
    } else if (isTizen) {
      // Ana ekrandayken uygulamayı arka plana al (kapatmadan)
      try { tizen.application.getCurrentApplication().hide(); } catch (e) {}
    }
  }

  var toastTimer;
  function toast(msg) {
    var t = document.querySelector('.toast');
    if (!t) { t = document.createElement('div'); t.className = 'toast'; document.body.appendChild(t); }
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove('show'); }, 2500);
  }

  document.addEventListener('keydown', function (e) {
    switch (e.keyCode) {
      case KEY.LEFT: move('left'); break;
      case KEY.RIGHT: move('right'); break;
      case KEY.UP: move('up'); break;
      case KEY.DOWN: move('down'); break;
      case KEY.ENTER: onEnter(); break;
      case KEY.BACK: case KEY.ESC: case 8: onBack(); break;
      case KEY.RED: case 82 /* R */: removeFocused(); break;
      case KEY.GREEN: case 71 /* G */: shiftFocused(-1); break;
      case KEY.YELLOW: case 89 /* Y */: shiftFocused(1); break;
      default: return;
    }
    e.preventDefault();
  });

  /* ---------- Başlat ---------- */
  function init() {
    if (isTizen) {
      try {
        tizen.tvinputdevice.registerKeyBatch(['ColorF0Red', 'ColorF1Green', 'ColorF2Yellow', 'ColorF3Blue']);
      } catch (e) {}
    }
    tick();
    setInterval(tick, 10000);
    renderHome();
    showView('home');
    if (!state.favorites.length) toast('Başlamak için "Uygulama ekle"ye basın');
  }

  window.onload = init;
})();
