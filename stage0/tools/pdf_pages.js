// Stage 0 Step 1: read per-page text and PDF page labels from a PDF using
// macOS PDFKit (built in - no packages installed).
// Usage: osascript -l JavaScript pdf_pages.js <path-to-pdf>
// Output: one JSON object on stdout.
ObjC.import('Quartz');
ObjC.import('Foundation');

function norm(s) {
  return s.replace(/\s+/g, ' ').trim();
}

function run(argv) {
  var path = argv[0];
  var url = $.NSURL.fileURLWithPath($(path));
  var doc = $.PDFDocument.alloc.initWithURL(url);
  if (!doc || doc.isNil()) {
    return JSON.stringify({ error: 'could not open PDF', path: path });
  }
  var n = doc.pageCount;
  var pages = [];
  for (var i = 0; i < n; i++) {
    var pg = doc.pageAtIndex(i);
    var txt = '';
    try {
      var s = pg.string;
      if (s && !s.isNil()) txt = norm(ObjC.unwrap(s));
    } catch (e) {
      txt = '';
    }
    var label = '';
    try {
      var l = pg.label;
      if (l && !l.isNil()) label = ObjC.unwrap(l);
    } catch (e) {
      label = '';
    }
    pages.push({
      i: i,
      label: label,
      chars: txt.length,
      head: txt.slice(0, 90),
      tail: txt.length > 170 ? txt.slice(-170) : txt
    });
  }
  return JSON.stringify({ path: path, pages: n, page_data: pages });
}
