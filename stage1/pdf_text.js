// Stage 1: read the FULL raw text of every page in a PDF using macOS PDFKit.
//
// Same approach as stage0/tools/pdf_pages.js, with one deliberate difference:
// that script normalises whitespace and keeps only head/tail (it was built for
// page-number analysis). This one keeps the text exactly as PDFKit returns it,
// because Stage 1 must preserve the extracted page text verbatim.
//
// Usage: osascript -l JavaScript pdf_text.js <absolute-path-to-pdf>
// Output: one JSON object on stdout: { path, pages, page_data: [{i, chars, text}] }
// i is the 0-based PDFKit page index.

ObjC.import('Quartz');
ObjC.import('Foundation');

function run(argv) {
  var path = argv[0];
  var doc = $.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath($(path)));
  if (!doc || doc.isNil()) {
    return JSON.stringify({ error: 'could not open PDF', path: path });
  }
  var n = doc.pageCount;
  var pages = [];
  for (var i = 0; i < n; i++) {
    var txt = '';
    try {
      var s = doc.pageAtIndex(i).string;
      if (s && !s.isNil()) txt = ObjC.unwrap(s);
    } catch (e) {
      txt = '';
    }
    pages.push({ i: i, chars: txt.length, text: txt });
  }
  return JSON.stringify({ path: path, pages: n, page_data: pages });
}
