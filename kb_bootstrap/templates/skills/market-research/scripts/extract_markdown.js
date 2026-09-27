/* Runs inside the page via `surf js --file`. Returns JSON {title, url, markdown, images}.
   Picks the main content node, drops page chrome, converts DOM to Markdown.
   surf quirks: no template literals, no backtick/hash literals, no $ in regexes (all get mangled). */
var NL = String.fromCharCode(10);
var BT = String.fromCharCode(96);
var HASH = String.fromCharCode(35);
var SKIP = 'script,style,noscript,svg,nav,footer,aside,header,form,iframe,' +
  '[aria-hidden=true],[role=navigation],[role=banner],[role=contentinfo]';
var BLOCKS = ['div', 'section', 'article', 'main', 'figure', 'li', 'dl', 'dd', 'dt'];
var images = [];

function pick() {
  /* Prefer the container around the article title: climb from the h1 until it holds real text. */
  var h1s = Array.from(document.querySelectorAll('h1')).filter(function (h) { return h.innerText.trim(); });
  var h1 = h1s[h1s.length - 1];
  for (var p = h1; p && p !== document.body; p = p.parentElement) {
    if (p.innerText.length > 800 && p.querySelector('p, li')) return p;
  }
  var cands = Array.from(document.querySelectorAll(
    'article, main, [role=main], ' + HASH + 'content-area, .article-body, .article, .prose, .content'));
  cands.sort(function (a, b) { return b.innerText.length - a.innerText.length; });
  var best = cands[0];
  return best && best.innerText.length > 300 ? best : document.body;
}
function abs(u) { try { return new URL(u, location.href).href; } catch (e) { return u; } }
function block(s) { return NL + NL + s + NL + NL; }
function inline(n) { return Array.from(n.childNodes).map(conv).join(''); }
function oneLine(s) { return s.trim().split(NL).join(' '); }

function conv(n) {
  if (n.nodeType === 3) return n.textContent.replace(/[\u200b\u200c\u200d\ufeff]/g, '').replace(/[ \t\u00a0]+/g, ' ');
  if (n.nodeType !== 1 || n.matches(SKIP)) return '';
  var t = n.tagName.toLowerCase();
  var s;
  if (t === 'button') return n.querySelector('img') ? inline(n) : '';  /* lightbox wrappers */
  if (t.length === 2 && t[0] === 'h' && '123456'.indexOf(t[1]) >= 0) return block(HASH.repeat(+t[1]) + ' ' + oneLine(inline(n)));
  if (t === 'p') return block(inline(n).trim());
  if (t === 'br') return NL;
  if (t === 'strong' || t === 'b') { s = inline(n).trim(); return s ? '**' + s + '**' : ''; }
  if (t === 'em' || t === 'i') { s = inline(n).trim(); return s ? '_' + s + '_' : ''; }
  if (t === 'pre') return block(BT + BT + BT + NL + n.innerText.trim() + NL + BT + BT + BT);
  if (t === 'code') return BT + n.textContent + BT;
  if (t === 'a') {
    s = inline(n).trim();
    var h = n.getAttribute('href') || '';
    if (!s || !h || h[0] === HASH || h.indexOf('javascript') === 0) return s;
    return '[' + s + '](' + abs(h) + ')';
  }
  if (t === 'img') {
    var src = abs(n.currentSrc || n.src || n.getAttribute('data-src') || '');
    if (!src || src.indexOf('data:') === 0) return '';
    var alt = (n.alt || '').replace(/[\[\]]/g, '');
    var path = src.split('?')[0].split('/').pop();
    if (/logo|wordmark|avatar|icon|badge|emoji/i.test(path + ' ' + alt + ' ' + n.className)) return '';
    images.push({ src: src, alt: alt, width: n.naturalWidth || n.width || 0 });
    return block('![' + alt + '](' + src + ')');
  }
  if (t === 'ul' || t === 'ol') {
    var items = Array.from(n.children).filter(function (li) { return li.tagName === 'LI'; });
    return block(items.map(function (li, i) {
      return (t === 'ol' ? (i + 1) + '.' : '-') + ' ' + oneLine(inline(li));
    }).join(NL));
  }
  if (t === 'table') {
    var rows = Array.from(n.querySelectorAll('tr')).map(function (r) {
      return Array.from(r.children).map(function (c) { return oneLine(inline(c)).replace(/\|/g, '/'); });
    });
    if (!rows.length) return '';
    var w = Math.max.apply(null, rows.map(function (r) { return r.length; }));
    var line = function (r) { while (r.length < w) r.push(''); return '| ' + r.join(' | ') + ' |'; };
    var sep = []; for (var k = 0; k < w; k++) sep.push('---');
    return block([line(rows[0]), line(sep)].concat(rows.slice(1).map(line)).join(NL));
  }
  if (t === 'blockquote') return block(inline(n).trim().split(NL).map(function (l) { return '> ' + l; }).join(NL));
  if (t === 'figcaption') { s = inline(n).trim(); return s ? block('_' + s + '_') : ''; }
  if (BLOCKS.indexOf(t) >= 0) return NL + inline(n) + NL;
  return inline(n);
}

var inFence = false;
var md = conv(pick()).split(NL).map(function (l) {
  if (l.trim().indexOf(BT + BT + BT) === 0) { inFence = !inFence; return l.trim(); }
  return inFence ? l : l.trim();
}).join(NL).replace(new RegExp(NL + '{3,}', 'g'), NL + NL).trim();
return JSON.stringify({ title: document.title, url: location.href, markdown: md, images: images });
