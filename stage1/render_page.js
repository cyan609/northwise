// Render one PDF page to PNG via macOS PDFKit, for manual verification of the
// printed folio against the rendered page.
//
// This exists so a page label can be checked by looking at the page rather than
// by re-reading the text the extractor already produced. It is a verification
// tool only: it is not part of the extraction path and writes nothing into the
// JSONL.
//
// Usage:
//   osascript -l JavaScript stage1/render_page.js <pdf> <page_index_0based> <out.png> [scale]
//
// Prints JSON: {"out": "...", "width": W, "height": H}

ObjC.import('Foundation');
ObjC.import('AppKit');
ObjC.import('PDFKit');

function run(argv) {
  if (argv.length < 3) {
    return JSON.stringify({ error: 'usage: <pdf> <page_index> <out.png> [scale]' });
  }
  var pdfPath = argv[0];
  var pageIndex = parseInt(argv[1], 10);
  var outPath = argv[2];
  var scale = argv.length > 3 ? parseFloat(argv[3]) : 2.0;

  var doc = $.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(pdfPath));
  if (!doc || doc.isNil()) {
    return JSON.stringify({ error: 'cannot open PDF' });
  }
  if (pageIndex < 0 || pageIndex >= doc.pageCount) {
    return JSON.stringify({ error: 'page index out of range', pages: doc.pageCount });
  }

  var page = doc.pageAtIndex(pageIndex);
  var box = page.boundsForBox($.kPDFDisplayBoxMediaBox);
  var w = box.size.width * scale;
  var h = box.size.height * scale;

  var img = page.thumbnailOfSizeForBox($.NSMakeSize(w, h), $.kPDFDisplayBoxMediaBox);
  var tiff = img.TIFFRepresentation;
  var rep = $.NSBitmapImageRep.imageRepWithData(tiff);
  var png = rep.representationUsingTypeProperties($.NSBitmapImageFileTypePNG, $());
  var ok = png.writeToFileAtomically(outPath, true);

  return JSON.stringify({
    out: outPath,
    ok: !!ok,
    width: Math.round(img.size.width),
    height: Math.round(img.size.height)
  });
}
