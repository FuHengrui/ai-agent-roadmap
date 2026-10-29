/* 全站搜索的前端逻辑（site/search.html 引用，零依赖）
 *
 * 为什么不在页面里内联：内联就得跟 build_search.py 的 .format 大括号转义打架，
 * 每次改一行都要数花括号。拆成独立文件，改逻辑只改这里。
 *
 * 匹配策略是"逐步放宽"：
 *   ① 原样按空格切词（"向量 数据库"）
 *   ② 去掉中文疑问词再切（"MCP是什么" → "MCP"）
 *   ③ 全都搜不到 → 不给空白页，给几个可点的关键词
 * 2026-10-27 的真实 bug：有人搜「MCP是什么」，整句当一个词，命中 0，
 * 页面只改了一行小字，看起来像卡住了。
 */
(function () {
  var q = document.getElementById('q');
  var hits = document.getElementById('hits');
  var stat = document.getElementById('stat');
  var D = { chapters: [] };
  var MAX = 40;
  var ready = false;      // 索引到位了没
  var full = false;       // 全文索引（不只是标题）到位了没
  var pending = null;     // 索引还没到就先记住用户输入

  // 中文提问里的虚词：搜之前剥掉，不然「是什么」会把结果全过滤没
  var STOP = /(是什么|是啥|为什么|为啥|怎么回事|怎么办|怎么样|怎么|如何|哪些|哪个|什么是|什么|介绍|讲讲|教我|请问|一下|能不能|可以|需要|有没有|的|了|吗|呢|啊|呀)/g;
  var PUNCT = /[，。、？！；：""''（）【】《》,.!?;:'"()\[\]{}<>\/\\|·~`@#$%^&*+=_]/g;

  function esc(s) {
    return String(s).replace(/[&<>]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c];
    });
  }
  function rx(t) {
    return new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
  }
  function mark(s, ts) {
    var out = esc(s);
    ts.forEach(function (t) {
      if (t) out = out.replace(rx(t), function (m) { return '<mark>' + m + '</mark>'; });
    });
    return out;
  }
  function tokens(s) {
    return String(s || '').toLowerCase().split(/\s+/).filter(Boolean);
  }
  function clean(s) {
    return String(s || '').toLowerCase()
      .replace(PUNCT, ' ').replace(STOP, ' ')
      .replace(/\s+/g, ' ').trim();
  }
  function allIn(hay, ts) {
    for (var i = 0; i < ts.length; i++) if (hay.indexOf(ts[i]) < 0) return false;
    return true;
  }
  function snippet(text, ts) {
    var low = text.toLowerCase(), at = -1;
    for (var i = 0; i < ts.length; i++) {
      var k = low.indexOf(ts[i]);
      if (k >= 0 && (at < 0 || k < at)) at = k;
    }
    if (at < 0) at = 0;
    var start = Math.max(0, at - 40);
    var seg = text.substr(start, 120);
    return (start > 0 ? '…' : '') + mark(seg, ts) + (start + 120 < text.length ? '…' : '');
  }

  function scan(ts) {
    var res = [];
    D.chapters.forEach(function (ch) {
      var title = ch[0], stage = ch[1], url = ch[2], blob = ch[3] || '', pts = ch[4] || [];
      var head = (title + ' ' + stage).toLowerCase();
      var titleHit = allIn(head, ts);

      if (titleHit && blob) {
        res.push({ score: 120, url: url, ch: ch, anchor: '', text: blob, label: '章节' });
      }
      pts.forEach(function (p) {
        var pid = p[0], ptitle = p[1], text = p[2] || '';
        var hay = (ptitle + ' ' + text).toLowerCase();
        if (!allIn(hay, ts)) return;
        var s = 50, n;
        ts.forEach(function (t) {
          if (ptitle.toLowerCase().indexOf(t) >= 0) s += 25;
          n = hay.split(t).length - 1;
          s += Math.min(n, 10) * 3;
        });
        if (titleHit) s += 20;
        res.push({ score: s, url: url, ch: ch, anchor: '#p' + pid, text: text, label: ptitle });
      });
    });
    res.sort(function (a, b) { return b.score - a.score; });
    return res;
  }

  function guessWords(raw) {
    var parts = String(raw).replace(PUNCT, ' ').split(/\s+/).filter(Boolean);
    var out = [];
    parts.forEach(function (p) {
      if (/^[a-z0-9][a-z0-9._+#-]*$/i.test(p) && p.length >= 2) {
        out.push(p);
      } else {
        var cn = p.replace(STOP, '');
        if (cn.length >= 2) out.push(cn.slice(0, 8));
      }
    });
    if (!out.length) out = ['Python', 'RAG', 'Agent'];
    var seen = {};
    return out.filter(function (x) {
      if (seen[x]) return false;
      seen[x] = 1;
      return true;
    }).slice(0, 5);
  }

  function renderEmpty(raw) {
    var words = guessWords(raw);
    hits.innerHTML =
      '<div class="no-hit"><strong>没搜到「' + esc(raw) + '」</strong>' +
      '<div class="no-hit-tip">换短一点的词试试，或者直接点这些：</div>' +
      '<div class="chips">' +
      words.map(function (w) {
        return '<button class="chip" data-q="' + esc(w) + '">' + esc(w) + '</button>';
      }).join('') +
      '</div></div>';
    Array.prototype.forEach.call(hits.querySelectorAll('.chip'), function (b) {
      b.addEventListener('click', function () {
        q.value = b.getAttribute('data-q');
        run();
        q.focus();
      });
    });
    stat.textContent = full ? '没有命中 —— 试着只搜一个词' : '标题里也没找到；正文索引还在载入，等一下再试';
  }

  function render(res, total, ts) {
    var frag = document.createDocumentFragment();
    res.forEach(function (r) {
      var a = document.createElement('a');
      a.className = 'hit';
      a.href = r.url + r.anchor;
      a.innerHTML =
        '<div class="hit-ch">' + esc(r.ch[1]) + ' · ' + esc(r.ch[0]) + '</div>' +
        '<div class="hit-t">' + (r.label === '章节' ? '（整章）' : mark(r.label, ts)) + '</div>' +
        '<div class="hit-s">' + snippet(r.text, ts) + '</div>';
      frag.appendChild(a);
    });
    hits.innerHTML = '';
    hits.appendChild(frag);
    stat.textContent = '命中 ' + total + ' 处' +
      (total > MAX ? '，只显示前 ' + MAX + ' 处' : '') + ' —— 点一下直接跳过去' +
      (full ? '' : '（正文还在载入，先按标题命中）');
  }

  function run() {
    var raw = q.value.trim();
    if (!raw) {
      hits.innerHTML = '';
      stat.textContent = '输入关键词，边打边出结果（Esc 清空）';
      return;
    }
    var attempts = [tokens(raw)];
    var cl = clean(raw);
    if (cl && cl !== tokens(raw).join(' ')) attempts.push(tokens(cl));

    for (var i = 0; i < attempts.length; i++) {
      if (!attempts[i].length) continue;
      var res = scan(attempts[i]);
      if (res.length) {
        render(res.slice(0, MAX), res.length, attempts[i]);
        return;
      }
    }
    renderEmpty(raw);
  }

  var timer = null;
  q.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () {
      if (ready) run();
      else pending = q.value;      // 索引还在路上，先记着
    }, 120);
  });
  q.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { q.value = ''; if (ready) run(); }
  });

  // ---- 启动：先把索引异步拉下来，别让 2 MB 的解析卡住页面 ----
  // 之前是 <script src="search-index.js"> 直接写在页面里，网慢的时候整页要等它，
  // 用户敲了字却半天没反应 —— 看着就像「卡住了」。
  var want = '';
  var m = /[?&]q=([^&]*)/.exec(location.search);
  if (m) {
    want = decodeURIComponent(m[1].replace(/\+/g, ' '));
    q.value = want;
  }

  q.disabled = true;
  stat.textContent = '正在载入索引（先出标题，正文随后补上）…';

  function loadScript(src, ok, fail) {
    var s = document.createElement('script');
    s.src = src;
    s.onload = ok;
    s.onerror = fail;
    document.body.appendChild(s);
  }

  function activate(d) {
    D = d;
    ready = true;
    q.disabled = false;
    q.focus();
    if (q.value.trim()) run();
  }

  // 先拿轻量索引（一两百 KB，秒到）出标题结果，再在后台补全文那 2 MB。
  // 网慢的时候这能让人立刻看到东西，而不是盯着空页面。
  // 正文索引按阶段分片：先出标题结果，再一片片把正文补进来。
  function loadShards() {
    var list = window.KB_STAGE_MANIFEST || [];
    var acc = [];
    var i = 0;
    function next() {
      if (i >= list.length) {
        full = true;
        if (acc.length) D = { chapters: acc };
        stat.textContent = '';
        if (q.value.trim()) run();
        return;
      }
      var item = list[i++];
      loadScript(item[1], function () {
        var part = (window.KB_STAGES || {})[item[0]] || [];
        acc = acc.concat(part);
        D = { chapters: acc };
        stat.textContent = '正文已加载 ' + i + '/' + list.length + ' 个阶段';
        if (q.value.trim()) run();
        next();
      }, function () { next(); });
    }
    next();
  }

  loadScript('search-index-lite.js', function () {
    activate(window.KB_SEARCH_LITE || { chapters: [] });
    loadScript('search/manifest.js', loadShards, function () {
      stat.textContent = '正文索引没加载出来，先用标题搜着（刷新可重试）';
    });
  }, function () {
    loadScript('search/manifest.js', function () {
      loadShards();
    }, function () {
      stat.textContent = '索引没加载出来：刷新一次试试（断网的话，本地打开 site/index.html 也能用）';
    });
  });
})();