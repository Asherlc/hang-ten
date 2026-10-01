import Foundation
import AppKit
import PDFKit
let input = URL(fileURLWithPath: CommandLine.arguments[1])
guard let document = PDFDocument(url: input) else { fatalError("Unreadable PDF") }
for index in 0..<document.pageCount {
    guard let page = document.page(at: index) else { fatalError("Missing page") }
    let rect = page.bounds(for: .mediaBox)
    let size = NSSize(width: 1400, height: 1400 * rect.height / rect.width)
    let picture = page.thumbnail(of: size, for: .mediaBox)
    var proposed = CGRect(origin: .zero, size: size)
    guard let cg = picture.cgImage(forProposedRect: &proposed, context: nil, hints: nil),
          let data = NSBitmapImageRep(cgImage: cg).representation(using: .png, properties: [:]) else { fatalError("Rendering failed") }
    let destination = input.deletingLastPathComponent().appendingPathComponent("mounting-instructions-page-\(index + 1).png")
    try data.write(to: destination)
}
print("Complete pages: \(document.pageCount)")
