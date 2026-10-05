import Foundation
import AVFoundation
import AppKit
let output = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
for (name, file) in [("plateau", "FF88F87E-A40C-45C0-AAF9-397DD661E934.mp4"), ("stone", "B254B326-C8AE-4EC0-AC92-CBB2EE98F119.mp4")] {
    let url = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true).appendingPathComponent(file)
    let asset = AVURLAsset(url: url)
    let duration = try await asset.load(.duration).seconds
    let generator = AVAssetImageGenerator(asset: asset)
    generator.appliesPreferredTrackTransform = true
    generator.requestedTimeToleranceBefore = .zero
    generator.requestedTimeToleranceAfter = .zero
    for requested in [5.0, 7.5, 8.0, max(0, duration - 0.1)] {
        let time = CMTime(seconds: requested, preferredTimescale: 600)
        let result = try await generator.image(at: time)
        let image = NSBitmapImageRep(cgImage: result.image)
        let data = image.representation(using: .png, properties: [:])!
        let target = output.appendingPathComponent(String(format: "%@-%.3fs.png", name, requested))
        try data.write(to: target, options: .withoutOverwriting)
        print("\(name) duration=\(duration) requested=\(requested) actual=\(result.actualTime.seconds) whole-frame=\(target.path)")
    }
}
